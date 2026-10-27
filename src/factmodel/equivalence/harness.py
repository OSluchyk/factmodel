"""Run a consumer over its layer's corpus, compare with the references, keep outcomes only.

``fact equivalence run`` executes both sides on a local engine (the examples' seeds) through
the ``sql`` adapter's SQLAlchemy URL, or reads results an owner produced with the script that
``fact equivalence script`` writes. ``equivalence/last-run.json`` holds the last outcome per
layer; ``equivalence/accepted.json`` changes only through ``fact equivalence accept``.
"""

import importlib.util
import json
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factmodel import vocabulary
from factmodel.equivalence import compare
from factmodel.equivalence.corpus import CorpusItem, read_corpus
from factmodel.model.loader import Model
from factmodel.model.types import Consumer, Layer
from factmodel.probes import WRAPS

LAST_RUN = Path("equivalence") / "last-run.json"
ACCEPTED = Path("equivalence") / "accepted.json"
OUTCOMES = ("pass", "fail", "error")
PROVING_MODES = ("same_rows", "same_predicate")  # D-021: equal counts do not prove answers
DEFAULT_THRESHOLD = 0.9

Compile = Callable[[dict[str, Any], Layer], str]


class EquivalenceError(ValueError):
    """A layer, consumer or corpus the harness cannot use."""


@dataclass(frozen=True)
class ItemResult:
    id: str
    mode: str
    outcome: str
    detail: str = ""
    known_gap: bool = False
    finding: str | None = None


@dataclass
class RunResult:
    layer: str
    consumer: str
    source: str
    dialect: str
    ran_on: str
    items: list[ItemResult] = field(default_factory=list)
    regressions: list[str] = field(default_factory=list)
    threshold: float = DEFAULT_THRESHOLD

    def share(self) -> float:
        """Items passing in same_rows or same_predicate, over items not marked known_gap (D-021)."""
        counted = [i for i in self.items if not i.known_gap]
        if not counted:
            return 0.0
        passing = [i for i in counted if i.outcome == "pass" and i.mode in PROVING_MODES]
        return round(len(passing) / len(counted), 6)

    def unexplained(self) -> list[str]:
        """Items that do not pass and carry neither a known gap nor a finding."""
        return [
            i.id for i in self.items if i.outcome != "pass" and not i.known_gap and not i.finding
        ]

    def proven(self) -> bool:
        return self.share() >= self.threshold and not self.regressions and not self.unexplained()

    def counts(self) -> dict[str, dict[str, int]]:
        """Outcome counts per mode, and over all modes under ``all``."""
        modes = vocabulary.load()["equivalence_mode"]
        out = {mode: dict.fromkeys(OUTCOMES, 0) for mode in [*modes, "all"]}
        for item in self.items:
            out[item.mode][item.outcome] += 1
            out["all"][item.outcome] += 1
        return out

    def summary(self) -> dict[str, Any]:
        return {
            "consumer": self.consumer,
            "source": self.source,
            "dialect": self.dialect,
            "ran_on": self.ran_on,
            "counts": self.counts(),
            "threshold": self.threshold,
            "share": self.share(),
            "proven": self.proven(),
            "unexplained": self.unexplained(),
            "items": {i.id: {"mode": i.mode, "outcome": i.outcome} for i in self.items},
        }


@dataclass(frozen=True)
class Setup:
    layer: Layer
    layer_dir: Path
    consumer: Consumer
    items: list[CorpusItem]
    tables: dict[str, str]


def setup(root: Path, model: Model, layer_id: str, corpus: Path | None = None) -> Setup:
    layer = model.layers.get(layer_id)
    if layer is None:
        raise EquivalenceError(f"layer {layer_id!r} not found")
    path = next(f.path for f in model.files if f.obj is layer)
    layer_dir = root / Path(path).parent
    consumer = model.consumers.get(layer.consumer)
    if consumer is None:
        raise EquivalenceError(f"consumer {layer.consumer!r} not found")
    if corpus is None:
        if consumer.corpus is None:
            raise EquivalenceError(f"consumer {consumer.id!r} names no corpus; pass --corpus")
        corpus = layer_dir / consumer.corpus.location
    tables = {e.entity: model.entities[e.entity].physical_name for e in layer.entities}
    return Setup(layer, layer_dir, consumer, read_corpus(corpus), tables)


def load_compile(root: Path, consumer: Consumer) -> Compile:
    """Import ``compile`` from the consumer's interface, ``<path>.py:<function>``."""
    if consumer.interface is None:
        raise EquivalenceError(f"consumer {consumer.id!r} names no interface")
    file, _, name = consumer.interface.partition(":")
    path = root / file
    spec = importlib.util.spec_from_file_location(f"consumer_{consumer.id}", path)
    if spec is None or spec.loader is None or not path.is_file():
        raise EquivalenceError(f"cannot import {consumer.interface!r}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    function: Compile = getattr(module, name)
    return function


def _compile(fn: Compile, item: CorpusItem, layer: Layer) -> str | None:
    try:
        sql = fn(dict(item.request), layer)
    except Exception:  # a consumer that cannot answer fails the item, never the run
        return None
    return sql if isinstance(sql, str) and sql.strip() else None


def _fetch(url: str, sql: str) -> list[tuple[Any, ...]] | None:
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return [tuple(row) for row in conn.execute(text(sql)).fetchall()]
    except Exception:  # the error text may quote data; never keep it
        return None
    finally:
        engine.dispose()


def run(
    root: Path,
    model: Model,
    layer_id: str,
    *,
    url: str,
    source: str,
    dialect: str,
    ran_on: str,
    corpus: Path | None = None,
) -> RunResult:
    """Compile every corpus item, execute both sides, and compare them in the item's mode."""
    s = setup(root, model, layer_id, corpus)
    fn = load_compile(root, s.consumer)
    result = _result(s, source, dialect, ran_on)
    for item in s.items:
        result.items.append(_explained(item, _one(fn, item, s, url, dialect)))
    result.regressions = regressions(root, result)
    return result


def _result(s: Setup, source: str, dialect: str, ran_on: str) -> RunResult:
    threshold = s.consumer.threshold if s.consumer.threshold is not None else DEFAULT_THRESHOLD
    return RunResult(s.layer.id, s.consumer.id, source, dialect, ran_on, threshold=threshold)


def _explained(item: CorpusItem, result: ItemResult) -> ItemResult:
    return ItemResult(
        result.id,
        result.mode,
        result.outcome,
        result.detail,
        known_gap=item.known_gap is not None,
        finding=item.finding,
    )


def _one(fn: Compile, item: CorpusItem, s: Setup, url: str, dialect: str) -> ItemResult:
    sql = _compile(fn, item, s.layer)
    if sql is None:
        return ItemResult(item.id, item.mode, "error", "the consumer gave no SQL")
    try:
        if item.mode == "same_predicate":
            same = compare.normalise(sql) == compare.normalise(item.reference)
            return ItemResult(item.id, item.mode, "pass" if same else "fail", "predicate")
        mine = compare.render(compare.bind(sql, s.tables), dialect)
        theirs = compare.render(compare.bind(item.reference, s.tables), dialect)
    except Exception:  # SQL sqlglot cannot parse
        return ItemResult(item.id, item.mode, "error", "SQL does not parse")
    left, right = _fetch(url, mine), _fetch(url, theirs)
    if left is None or right is None:
        side = "consumer" if left is None else "reference"
        return ItemResult(item.id, item.mode, "error", f"{side} query failed")
    rows = f"{len(left)} vs {len(right)} rows"
    same = len(left) == len(right) if item.mode == "same_count" else compare.same_rows(left, right)
    return ItemResult(item.id, item.mode, "pass" if same else "fail", rows)


def _read(root: Path, rel: Path) -> dict[str, Any]:
    path = root / rel
    if not path.is_file():
        return {"layers": {}}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("layers", {})
    return data


def _write_json(root: Path, rel: Path, data: dict[str, Any]) -> bool:
    path = root / rel
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _measured(fn: Compile, item: CorpusItem, s: Setup, row: dict[str, Any] | None) -> ItemResult:
    if item.mode == "same_predicate":
        sql = _compile(fn, item, s.layer)
        same = sql is not None and compare.normalise(sql) == compare.normalise(item.reference)
        return ItemResult(item.id, item.mode, "pass" if same else "fail", "predicate")
    m = (row or {}).get("measurement")
    if not isinstance(m, dict):
        return ItemResult(item.id, item.mode, "error", "no result")
    counts = Counter({k: int(m.get(k, -1)) for k in ("consumer_rows", "reference_rows")})
    same = counts["consumer_rows"] == counts["reference_rows"]
    if item.mode == "same_rows":
        same = same and m.get("only_consumer") == 0 and m.get("only_reference") == 0
    detail = f"{counts['consumer_rows']} vs {counts['reference_rows']} rows"
    return ItemResult(item.id, item.mode, "pass" if same else "fail", detail)


def regressions(root: Path, result: RunResult) -> list[str]:
    """Items that passed in the accepted run and do not pass now (or are gone)."""
    accepted = _read(root, ACCEPTED)["layers"].get(result.layer)
    if not accepted:
        return []
    now = {i.id: i.outcome for i in result.items}
    return sorted(
        item_id
        for item_id, before in accepted.get("items", {}).items()
        if before.get("outcome") == "pass" and now.get(item_id) != "pass"
    )


def drops(root: Path, layer_id: str) -> list[str]:
    """Items that passed in the accepted run and do not pass in the last run (D-021)."""
    accepted = _read(root, ACCEPTED)["layers"].get(layer_id)
    if not accepted:
        return []
    last = _read(root, LAST_RUN)["layers"].get(layer_id) or {}
    now = {k: v.get("outcome") for k, v in (last.get("items") or {}).items()}
    return sorted(
        item_id
        for item_id, before in accepted.get("items", {}).items()
        if before.get("outcome") == "pass" and now.get(item_id) != "pass"
    )


def report(result: RunResult) -> str:
    counts = result.counts()
    lines = [
        f"# Equivalence: layer {result.layer}",
        "",
        "# generated by fact equivalence run - do not edit",
        "",
        f"Consumer `{result.consumer}`, source `{result.source}` ({result.dialect}), "
        f"{result.ran_on}.",
        "",
        "| Mode | pass | fail | error |",
        "| --- | --- | --- | --- |",
    ]
    for mode, row in counts.items():
        lines.append(f"| {mode} | {row['pass']} | {row['fail']} | {row['error']} |")
    verdict = "proven" if result.proven() else "not proven"
    lines += [
        "",
        f"Share passing in same_rows or same_predicate: {result.share():.3f}; "
        f"threshold {result.threshold} (D-021): {verdict}.",
        "Unexplained failures: " + (", ".join(result.unexplained()) or "none"),
    ]
    lines += [
        "",
        "| Item | Mode | Outcome | Detail | Explained by |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i in result.items:
        why = "known gap" if i.known_gap else (i.finding or "")
        lines.append(f"| {i.id} | {i.mode} | {i.outcome} | {i.detail} | {why} |")
    lines += [
        "",
        "Regressions against the accepted run: " + (", ".join(result.regressions) or "none"),
    ]
    return "\n".join(lines) + "\n"


def write(root: Path, result: RunResult) -> list[Path]:
    """Write the report and this layer's entry in last-run.json; unchanged files stay."""
    written = []
    path = root / "generated" / f"equivalence-{result.layer}.md"
    text = report(result)
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    data = _read(root, LAST_RUN)
    data["layers"][result.layer] = result.summary()
    if _write_json(root, LAST_RUN, data):
        written.append(root / LAST_RUN)
    return written


def accept(root: Path, layer_id: str) -> bool:
    """Copy the layer's last run into accepted.json (the owner's act). True when it changed."""
    last = _read(root, LAST_RUN)["layers"].get(layer_id)
    if last is None:
        raise EquivalenceError(f"no run of layer {layer_id!r} in {LAST_RUN}")
    data = _read(root, ACCEPTED)
    data["layers"][layer_id] = last
    return _write_json(root, ACCEPTED, data)


def script(
    root: Path, model: Model, layer_id: str, dialect: str, corpus: Path | None = None
) -> str:
    """A shell script that runs both sides of every executable item on a live engine and prints
    counts only: rows on each side and rows only one side has (EXCEPT, so duplicates collapse)."""
    s = setup(root, model, layer_id, corpus)
    fn = load_compile(root, s.consumer)
    default = vocabulary.text_map("dialect_runner").get(dialect)
    strategy = vocabulary.text_map("dialect_json_wrap").get(dialect)
    run_sql = (
        f'RUN_SQL="${{RUN_SQL:-{default}}}"'
        if default
        else 'RUN_SQL="${RUN_SQL:?set RUN_SQL to a command that prints one JSON object per query}"'
    )
    lines = [
        "#!/usr/bin/env bash",
        "# generated by fact equivalence script - do not edit",
        f"# Equivalence for layer {layer_id} in dialect {dialect}: counts only, never rows.",
        "# Save the output and run: fact equivalence run --layer <id> --results <file>",
        "set -uo pipefail",
        run_sql,
        "run_item() {",
        '  local id="$1" out',
        '  if out=$(printf "%s" "$2" | bash -c "$RUN_SQL" 2>/dev/null) && [ -n "$out" ]; then',
        '    printf \'{"item": "%s", "measurement": %s}\\n\' "$id" "$out"',
        "  else",
        '    printf \'{"item": "%s", "error": "QUERY FAILED"}\\n\' "$id"',
        "  fi",
        "}",
    ]
    keys = ["consumer_rows", "reference_rows", "only_consumer", "only_reference"]
    for item in s.items:
        if item.mode == "same_predicate":
            continue
        sql = _compile(fn, item, s.layer)
        if sql is None:
            lines.append(f"# {item.id}: the consumer gave no SQL")
            continue
        query = compare.render(
            compare.count_query(
                compare.bind(sql, s.tables), compare.bind(item.reference, s.tables)
            ),
            dialect,
        )
        if strategy is not None:
            query = WRAPS[strategy](query, keys)
        quoted = "'" + query.replace("'", "'\"'\"'") + "'"
        lines.append(f"run_item {item.id} {quoted}")
    return "\n".join(lines) + "\n"


def from_results(
    root: Path,
    model: Model,
    layer_id: str,
    results: Path,
    *,
    source: str,
    dialect: str,
    ran_on: str,
) -> RunResult:
    """Outcomes from the output of the script: counts decide same_rows and same_count; a
    same_predicate item needs no data and is compared here."""
    s = setup(root, model, layer_id)
    fn = load_compile(root, s.consumer)
    rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines() if line]
    measured = {r["item"]: r for r in rows if isinstance(r, dict) and "item" in r}
    result = _result(s, source, dialect, ran_on)
    for item in s.items:
        result.items.append(_explained(item, _measured(fn, item, s, measured.get(item.id))))
    result.regressions = regressions(root, result)
    return result

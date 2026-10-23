"""Turn probe results into evidence and findings (``fact probe intake``).

A results file is JSON lines: a header ``{source, pin, environment, data_quality, ran_on}``,
then one line per probe, ``{probe, measurement}`` or ``{probe, error}``. Intake keeps numbers
only, drops anything that looks like an email or an identifier, and writes one evidence file
per probe: ``evidence/probes/<probe-id>@<date>.yaml``. A result in its expected range is cited
by the fact it tests, which moves that fact to ``confirmed``; a result out of range opens a
finding. Running intake twice on the same file changes nothing.
"""

import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from factmodel.model.loader import Model, inspect_model
from factmodel.model.types import Probe
from factmodel.schemas.build import pattern

HEADER_KEYS = ("source", "pin", "environment", "data_quality", "ran_on")
SLUG = re.compile(pattern("slug"))


class IntakeError(ValueError):
    """A results file cannot be read."""


@dataclass
class IntakeResult:
    confirmed: list[str] = field(default_factory=list)
    out_of_range: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)


def read_results(path: Path) -> tuple[dict[str, str], list[dict[str, Any]]]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    try:
        rows = [json.loads(line) for line in lines]
    except json.JSONDecodeError as error:
        raise IntakeError(f"{path}: line {error.lineno} is not JSON") from error
    if not rows or not all(isinstance(r, dict) for r in rows):
        raise IntakeError(f"{path}: expected JSON objects, one per line")
    header = rows[0]
    missing = [k for k in HEADER_KEYS if not header.get(k)]
    if missing:
        raise IntakeError(f"{path}: the header line lacks {missing}")
    return {k: str(header[k]) for k in HEADER_KEYS}, rows[1:]


def clean_measurement(raw: Any) -> dict[str, float | int] | None:
    """Numbers under slug keys only; None when nothing usable is left."""
    if not isinstance(raw, dict):
        return None
    out: dict[str, float | int] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not SLUG.match(key) or isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            out[key] = value
    return out or None


def derived(kind: str, measurement: dict[str, float | int]) -> dict[str, float | int]:
    """Rates computed from counts, so probes never divide in SQL."""
    out = dict(measurement)
    if kind == "join_match" and measurement.get("source_rows"):
        out["match_rate"] = round(1 - measurement["orphans_left"] / measurement["source_rows"], 6)
    if kind == "null_rate" and measurement.get("row_count"):
        rows = measurement["row_count"]
        out["null_rate"] = round((rows - measurement.get("non_null", 0)) / rows, 6)
    return out


def in_range(probe: Probe, measurement: dict[str, float | int]) -> bool | None:
    """True or False against the expected ranges; None when nothing is expected."""
    if not probe.expected:
        return None
    for metric, bounds in probe.expected.items():
        value = measurement.get(metric)
        if value is None:
            return False
        if bounds.min is not None and value < bounds.min:
            return False
        if bounds.max is not None and value > bounds.max:
            return False
    return True


def _yaml_rt() -> YAML:
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    return yaml


def _dump(doc: Any, yaml: YAML | None = None) -> str:
    if yaml is None:
        yaml = YAML(typ="safe", pure=True)
        yaml.default_flow_style = False
        yaml.sort_base_mapping_type_on_output = False  # type: ignore[assignment]
    buf = io.StringIO()
    yaml.dump(doc, buf)
    return buf.getvalue()


def _write(path: Path, text: str, written: list[Path]) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    written.append(path)


def evidence_id(probe_id: str, day: str) -> str:
    value = f"ev-{probe_id}-{day}"
    if len(value) <= 64:
        return value
    return f"ev-{hashlib.sha1(value.encode()).hexdigest()[:12]}-{day}"


def _cite(root: Path, model: Model, probe: Probe, ev_id: str, written: list[Path]) -> None:
    """Add the evidence ID to the fact the probe tests, keeping the file's layout."""
    entity_id, _, rest = probe.fact.partition(".")
    path = next(
        (
            root / f.path
            for f in model.files
            if f.kind == "entity" and f.document.data.get("id") == entity_id
        ),
        None,
    )
    if path is None:
        return
    yaml = _yaml_rt()
    doc = yaml.load(path.read_text(encoding="utf-8"))
    target: Any = doc
    if rest and probe.probe_kind in ("join_match", "fan_out"):
        target = next((r for r in doc.get("relationships", []) if r.get("key") == rest), None)
    elif rest:
        target = next(
            (f for f in doc.get("fields", []) if (f.get("path") or f.get("name")) == rest), None
        )
    if target is None:
        return
    refs = target.setdefault("evidence", [])
    if ev_id not in refs:
        refs.append(ev_id)
        _write(path, _dump(doc, yaml), written)


def _finding(
    root: Path,
    model: Model,
    probe: Probe,
    ev_id: str,
    day: str,
    measurement: dict[str, Any],
    written: list[Path],
) -> None:
    for existing in model.findings.values():
        if (
            existing.extensions
            and existing.extensions.get("probe") == probe.id
            and existing.status == "open"
        ):
            return
    numbers = [int(f.id[2:]) for f in model.findings.values()]
    number = max(numbers, default=0) + 1
    expected = {k: v.model_dump(exclude_none=True) for k, v in (probe.expected or {}).items()}
    doc = {
        "kind": "finding",
        "id": f"F-{number:04d}",
        "title": f"Probe {probe.id} out of range",
        "status": "open",
        "opened_on": day,
        "about": [probe.fact],
        "description": f"Measured {measurement}; expected {expected}. Evidence {ev_id}.",
        "extensions": {"probe": probe.id},
    }
    _write(root / "registers" / "findings" / f"F-{number:04d}.yaml", _dump(doc), written)


def intake(root: Path, results: Path) -> IntakeResult:
    header, rows = read_results(results)
    model = inspect_model(root).model
    probes = model.probes
    out = IntakeResult()
    day = header["ran_on"]
    for row in rows:
        probe = probes.get(str(row.get("probe")))
        if probe is None:
            out.rejected.append(f"unknown probe {row.get('probe')!r}")
            continue
        if "error" in row:
            out.failed.append(probe.id)
            continue
        measurement = clean_measurement(row.get("measurement"))
        if measurement is None:
            out.rejected.append(f"{probe.id}: no usable measurement")
            continue
        measurement = derived(probe.probe_kind, measurement)
        ev_id = evidence_id(probe.id, day)
        record = {
            "id": ev_id,
            "source": header["source"],
            "pin": header["pin"],
            "measurement": measurement,
            "status": "confirmed",
            "read_on": day,
            "probe": probe.id,
            "environment": header["environment"],
            "data_quality": header["data_quality"],
        }
        doc = {"kind": "evidence", "records": [record]}
        _write(root / "evidence" / "probes" / f"{probe.id}@{day}.yaml", _dump(doc), out.written)
        verdict = in_range(probe, measurement)
        model = inspect_model(root).model
        if verdict is False:
            out.out_of_range.append(probe.id)
            _finding(root, model, probe, ev_id, day, measurement, out.written)
        else:
            out.confirmed.append(probe.id)
            _cite(root, model, probe, ev_id, out.written)
    return out

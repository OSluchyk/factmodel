"""Both reference consumers prove their layers (D-021) on SQLite and DuckDB, and the
QCEW corpus keeps at least five naive-versus-correct pairs whose answers really differ."""

import importlib.util
import json
import re
import sqlite3
from pathlib import Path
from types import ModuleType

import pytest

from factmodel.equivalence import harness
from factmodel.equivalence.compare import same_rows
from factmodel.equivalence.corpus import read_corpus
from factmodel.model.loader import load_model

ROOT = Path(__file__).resolve().parents[2]
DAY = "2026-10-27"
CASES = {
    "qcew": ("employment-wages", "qcew-sqlite", "qcew-duckdb"),
    "chinook": ("customer-purchases", "chinook-sqlite", "chinook-pg"),
}
needs_duckdb = pytest.mark.skipif(
    importlib.util.find_spec("duckdb_engine") is None, reason="extra [duckdb] not installed"
)


def _seed(example: str) -> ModuleType:
    path = ROOT / "examples" / example / "seed" / "seed.py"
    spec = importlib.util.spec_from_file_location(f"{example}_seed_eq", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _accepted(example: str, layer: str) -> dict[str, object]:
    path = ROOT / "examples" / example / "equivalence" / "accepted.json"
    data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))["layers"][layer]
    return data


def _run(example: str, url: str, source: str, dialect: str) -> harness.RunResult:
    root = ROOT / "examples" / example
    layer = CASES[example][0]
    return harness.run(
        root, load_model(root), layer, url=url, source=source, dialect=dialect, ran_on=DAY
    )


@pytest.mark.parametrize("example", sorted(CASES))
def test_sqlite_run_reproduces_the_accepted_run_and_report(example: str, tmp_path: Path) -> None:
    layer, source, _ = CASES[example]
    url = _seed(example).load_sqlite(tmp_path / "db.sqlite")
    result = _run(example, url, source, "sqlite")
    assert result.proven()
    assert result.summary() == _accepted(example, layer)
    report = ROOT / "examples" / example / "generated" / f"equivalence-{layer}.md"
    assert harness.report(result) == report.read_text(encoding="utf-8")


@needs_duckdb
@pytest.mark.filterwarnings("ignore")
@pytest.mark.parametrize("example", sorted(CASES))
def test_duckdb_gives_the_same_outcomes(example: str, tmp_path: Path) -> None:
    layer, _, _ = CASES[example]
    seed = _seed(example)
    if example == "qcew":
        url = seed.load_duckdb(tmp_path / "db.duckdb")
    else:
        url = f"duckdb:///{tmp_path / 'db.duckdb'}"
        seed.load_postgres(url)
    result = _run(example, url, "duckdb", "duckdb")
    accepted = _accepted(example, layer)
    assert result.proven()
    assert result.summary()["items"] == accepted["items"]


@pytest.mark.parametrize("example", sorted(CASES))
def test_corpus_has_thirty_items_besides_known_gaps(example: str) -> None:
    layer = CASES[example][0]
    items = read_corpus(ROOT / "examples" / example / "semantic" / layer / "corpus")
    assert len([i for i in items if i.known_gap is None]) >= 30


def test_qcew_naive_queries_give_different_answers(tmp_path: Path) -> None:
    url = _seed("qcew").load_sqlite(tmp_path / "db.sqlite")
    folder = ROOT / "examples" / "qcew" / "semantic" / "employment-wages" / "corpus"
    pairs = [i for i in read_corpus(folder) if "naive" in (i.tags or [])]
    assert len(pairs) >= 5
    with sqlite3.connect(url.removeprefix("sqlite:///")) as conn:
        for item in pairs:
            assert item.note is not None
            match = re.search(r"Naive SQL: (.*?) Why it differs:", item.note)
            assert match, item.id
            naive = conn.execute(match.group(1)).fetchall()
            correct = conn.execute(item.reference).fetchall()
            # compare the values only: the correct answer also reports suppressed cells
            width = len(naive[0])
            assert not same_rows(naive, [row[:width] for row in correct]), item.id

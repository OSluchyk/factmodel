"""Both reference consumers prove their layers (D-021) on SQLite and DuckDB, and the
QCEW corpus keeps at least five naive-versus-correct pairs whose answers really differ."""

import importlib.util
import json
import re
import sqlite3
from pathlib import Path
from types import ModuleType

import pytest
import sqlglot

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
    summary = result.summary()
    # coverage is report only and newer than the accepted runs; every verdict key is unchanged
    assert {k: v for k, v in summary.items() if k != "coverage"} == _accepted(example, layer)
    last = ROOT / "examples" / example / "equivalence" / "last-run.json"
    assert json.loads(last.read_text(encoding="utf-8"))["layers"][layer] == summary
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


COVERAGE = {
    "chinook": {
        "not_exercised": ["entity album", "join track.to-album"],
        "not_evaluated": [],
    },
    "qcew": {
        "not_exercised": [
            "entity industry_titles",
            "entity ownership_titles",
            "join qtrly.to-industry",
            "join qtrly.to-ownership",
            "join annual.to-area",
            "join annual.to-industry",
            "join annual.to-ownership",
            # the references write the area kinds with LIKE, not with the concept's substr form
            "concept area_kind_county",
            "concept area_kind_state",
            "concept area_kind_msa",
        ],
        "not_evaluated": [
            "concept level_matrix (values_table)",
            "concept distinct_areas (distinct)",
        ],
    },
}


@pytest.mark.parametrize("example", sorted(CASES))
def test_coverage_vectors(example: str) -> None:
    layer = CASES[example][0]
    last = ROOT / "examples" / example / "equivalence" / "last-run.json"
    coverage = json.loads(last.read_text(encoding="utf-8"))["layers"][layer]["coverage"]
    assert coverage["not_exercised"] == COVERAGE[example]["not_exercised"]
    assert coverage["not_evaluated"] == COVERAGE[example]["not_evaluated"]
    assert coverage["unresolved_items"] == 0
    report = (ROOT / "examples" / example / "generated" / f"equivalence-{layer}.md").read_text(
        encoding="utf-8"
    )
    if example == "qcew":
        assert (
            "- entity industry_titles (referred to by rollup of measure employment_month3 "
            "(industry_titles.parent))" in report
        )
        assert "- entity ownership_titles\n" in report
        # the area join goes through a de-duplicated subquery (F-0001)
        assert "| join qtrly.to-area | 4 | 4 |" in report


def _literals(sql: str) -> set[str]:
    tree = sqlglot.parse_one(sql)
    return {
        lit.this
        for lit in tree.find_all(sqlglot.exp.Literal)
        if lit.is_string and len(lit.this) >= 4 and re.search(r"[A-Za-z-]", lit.this)
    }


@pytest.mark.parametrize("example", sorted(CASES))
def test_no_corpus_literal_in_any_output(example: str) -> None:
    layer = CASES[example][0]
    folder = ROOT / "examples" / example / "semantic" / layer / "corpus"
    items = read_corpus(folder)
    literals = set().union(*(_literals(i.reference) for i in items))
    assert "genre-1" in literals or example != "chinook"
    outputs = [
        ROOT / "examples" / example / "generated" / f"equivalence-{layer}.md",
        ROOT / "examples" / example / "equivalence" / "last-run.json",
        ROOT / "examples" / example / "equivalence" / "accepted.json",
    ]
    for path in outputs:
        text = path.read_text(encoding="utf-8")
        # item ids are authored names and some spell a value (customers-genre-1-2024q1)
        for item in sorted(items, key=lambda i: -len(i.id)):
            text = text.replace(item.id, "")
        assert not [lit for lit in literals if lit in text], path

"""The equivalence harness on a toy layer with three toy consumers: right, wrong and
partly right; all three modes; regressions against the accepted run; idempotency."""

import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.equivalence import compare, harness
from factmodel.model.loader import load_model

CASE = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases" / "layer-minimal"
runner = CliRunner()
DAY = "2026-10-27"

TOTAL = (
    "SELECT employment.area_code, SUM(employment.employment) AS employment FROM employment "
    "JOIN areas ON employment.area_code = areas.area_code "
    "WHERE employment.year = {year} GROUP BY employment.area_code"
)
CORPUS = {
    "total-2024": {"request": {"kind": "total", "year": 2024}, "mode": "same_rows"},
    "total-2025": {"request": {"kind": "total", "year": 2025}, "mode": "same_rows"},
    "count-2025": {"request": {"kind": "total", "year": 2025}, "mode": "same_count"},
    "filter-a1": {"request": {"kind": "filter", "area": "A1"}, "mode": "same_predicate"},
}
FILTER = (
    "SELECT employment.year FROM employment "
    "WHERE employment.area_code = '{area}' AND employment.year > 2000"
)
# the same predicate, conjuncts in the other order and identifiers quoted
FILTER_RIGHT = (
    'SELECT "employment"."year" FROM "employment" WHERE "employment"."year" > 2000 '
    'AND "employment"."area_code" = \'{area}\''
)
CONSUMERS = {
    "right": f"""
def compile(request, layer):
    if request["kind"] == "total":
        return {TOTAL!r}.format(year=request["year"])
    return {FILTER_RIGHT!r}.format(area=request["area"])
""",
    "wrong": """
def compile(request, layer):
    if request["kind"] == "total":
        return "SELECT employment.area_code, employment.employment FROM employment"
    return "SELECT employment.year FROM employment"
""",
    "partial": f"""
def compile(request, layer):
    if request["kind"] == "total" and request["year"] == 2024:
        return {TOTAL!r}.format(year=2024)
    if request["kind"] == "total":
        raise ValueError("cannot answer")
    return {FILTER_RIGHT!r}.format(area=request["area"])
""",
}


def _model(tmp_path: Path, consumer: str = "right") -> tuple[Path, str]:
    root = tmp_path / "model"
    shutil.copytree(CASE, root, ignore=shutil.ignore_patterns("expected"))
    for name in ("employment", "areas", "industries"):
        path = root / "physical" / "entities" / f"{name}.yaml"
        path.write_text(path.read_text().replace(f"stats.{name}", name), encoding="utf-8")
    source = root / "sources" / "stats-db.yaml"
    source.write_text(
        source.read_text().replace("engine: postgres", "engine: sqlite")
        + "adapter: sql\ndsn_env: FACT_TEST_STATS_DSN\n",
        encoding="utf-8",
    )
    for name, code in CONSUMERS.items():
        (root / "consumers" / name).mkdir(parents=True)
        (root / "consumers" / name / "compile.py").write_text(code, encoding="utf-8")
    _interface(root, consumer)
    corpus = root / "semantic" / "employment" / "corpus"
    corpus.mkdir()
    for item_id, item in CORPUS.items():
        request = item["request"]
        reference = (
            TOTAL.format(year=request["year"])
            if request["kind"] == "total"
            else FILTER.format(area=request["area"])
        )
        doc = {"id": item_id, "request": request, "reference": reference, "mode": item["mode"]}
        (corpus / f"{item_id}.yaml").write_text(json.dumps(doc), encoding="utf-8")
    db = tmp_path / "stats.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(
            "CREATE TABLE employment (area_code TEXT, industry_code TEXT, year INTEGER,"
            " employment INTEGER, prior_year INTEGER);"
            "CREATE TABLE areas (area_code TEXT, area_title TEXT);"
            "CREATE TABLE industries (industry_code TEXT, industry_title TEXT, parent_code TEXT);"
            "INSERT INTO areas VALUES ('A1', 'one'), ('A2', 'two');"
            "INSERT INTO employment VALUES ('A1', 'I1', 2024, 10, NULL),"
            " ('A1', 'I2', 2024, 5, NULL), ('A2', 'I1', 2024, 7, NULL),"
            " ('A1', 'I1', 2025, 12, 2024), ('A2', 'I1', 2025, 8, 2024);"
        )
    return root, f"sqlite:///{db}"


def _interface(root: Path, consumer: str) -> None:
    path = root / "semantic" / "employment" / "consumer.yaml"
    lines = [
        line
        for line in path.read_text().splitlines()
        if not line.startswith(("interface", "corpus", "  location", "threshold"))
    ]
    # one of four items is same_count, which does not count towards the share (D-021)
    lines += ["threshold: 0.75"]
    lines += [
        f"interface: consumers/{consumer}/compile.py:compile",
        "corpus:",
        "  location: corpus",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run(root: Path, url: str) -> harness.RunResult:
    return harness.run(
        root,
        load_model(root),
        "employment",
        url=url,
        source="stats-db",
        dialect="sqlite",
        ran_on=DAY,
    )


def _outcomes(result: harness.RunResult) -> dict[str, str]:
    return {i.id: i.outcome for i in result.items}


def test_right_consumer_passes_every_mode(tmp_path: Path) -> None:
    root, url = _model(tmp_path)
    result = _run(root, url)
    assert _outcomes(result) == dict.fromkeys(CORPUS, "pass")
    assert result.counts()["all"] == {"pass": 4, "fail": 0, "error": 0}


def test_wrong_consumer_fails_every_mode(tmp_path: Path) -> None:
    root, url = _model(tmp_path, "wrong")
    assert _outcomes(_run(root, url)) == {
        "count-2025": "fail",
        "filter-a1": "fail",
        "total-2024": "fail",
        "total-2025": "fail",
    }


def test_partial_consumer_and_a_regression(tmp_path: Path) -> None:
    root, url = _model(tmp_path)
    harness.write(root, _run(root, url))
    assert harness.accept(root, "employment")
    _interface(root, "partial")
    result = _run(root, url)
    assert _outcomes(result) == {
        "count-2025": "error",
        "filter-a1": "pass",
        "total-2024": "pass",
        "total-2025": "error",
    }
    assert result.regressions == ["count-2025", "total-2025"]


def test_runs_and_accepts_are_idempotent(tmp_path: Path) -> None:
    root, url = _model(tmp_path)
    os.environ["FACT_TEST_STATS_DSN"] = url
    try:
        args = ["equivalence", "run", "--root", str(root), "--layer", "employment", "--date", DAY]
        first = runner.invoke(app, args)
        assert first.exit_code == 0, first.output
        assert "employment: 4 pass, 0 fail, 0 error of 4" in first.output
        files = {p: p.read_bytes() for p in (root / "equivalence").rglob("*") if p.is_file()}
        report = (root / "generated" / "equivalence-employment.md").read_bytes()
        assert runner.invoke(app, args).exit_code == 0
        assert {
            p: p.read_bytes() for p in (root / "equivalence").rglob("*") if p.is_file()
        } == files
        assert (root / "generated" / "equivalence-employment.md").read_bytes() == report
        accept = ["equivalence", "accept", "--root", str(root), "--layer", "employment"]
        assert "accepted" in runner.invoke(app, accept).output
        assert "already accepted" in runner.invoke(app, accept).output
        _interface(root, "partial")
        regressed = runner.invoke(app, args)
        assert regressed.exit_code == 1
        assert "regressions against the accepted run: count-2025, total-2025" in regressed.output
    finally:
        del os.environ["FACT_TEST_STATS_DSN"]
    text = report.decode()
    assert "| all | 4 | 0 | 0 |" in text and "A1" not in text  # outcomes and counts, never values


def test_the_gate_reads_the_accepted_run(tmp_path: Path) -> None:
    from factmodel.gate.runner import run_gate

    root, url = _model(tmp_path)
    layer = root / "semantic" / "employment" / "layer.yaml"
    layer.write_text(layer.read_text().replace("status: draft", "status: reviewed"), "utf-8")
    assert run_gate(root).failed == ["layers"]
    harness.write(root, _run(root, url))
    harness.accept(root, "employment")
    assert run_gate(root).failed == []


def test_bind_names_physical_tables_and_keeps_entity_qualifiers() -> None:
    tree = compare.bind("SELECT a.x FROM a JOIN b ON a.k = b.k", {"a": "s.Alpha", "b": "Beta"})
    assert compare.render(tree, "postgres") == (
        'SELECT "a"."x" FROM "s"."Alpha" AS "a" JOIN "Beta" AS "b" ON "a"."k" = "b"."k"'
    )


@pytest.mark.parametrize("dialect", ["sqlite", "duckdb"])
def test_count_query_takes_a_side_that_starts_with_with(dialect: str) -> None:
    # the QCEW references open with a CTE; EXCEPT <WITH ...> is a syntax error on every engine
    mine = compare.bind("SELECT k, v FROM t WHERE k < 3", {})
    theirs = compare.bind("WITH s AS (SELECT * FROM t WHERE k < 4) SELECT k, v FROM s", {})
    sql = compare.render(compare.count_query(mine, theirs), dialect)
    if dialect == "sqlite":
        conn = sqlite3.connect(":memory:")
    else:
        duckdb = pytest.importorskip("duckdb")
        conn = duckdb.connect()
    conn.execute("CREATE TABLE t (k INTEGER, v INTEGER)")
    conn.execute("INSERT INTO t VALUES (1, 10), (2, 20), (3, 30)")
    assert conn.execute(sql).fetchone() == (2, 3, 0, 1)


def test_normalise_ignores_quoting_case_and_conjunct_order() -> None:
    left = "SELECT t.a FROM t WHERE t.b = 1 AND t.c = 'X'"
    right = 'SELECT "T"."A" FROM "t" WHERE "t"."c" = \'X\' AND "t"."b" = 1'
    assert compare.normalise(left) == compare.normalise(right)
    assert compare.normalise(left) != compare.normalise(left.replace("'X'", "'Y'"))


@pytest.mark.skipif(shutil.which("sqlite3") is None, reason="sqlite3 CLI not installed")
def test_owner_run_script_gives_the_same_outcomes(tmp_path: Path) -> None:
    root, _ = _model(tmp_path, "partial")
    text = harness.script(root, load_model(root), "employment", "sqlite")
    assert "count-2025" not in text.split("run_item() {")[1].split("}")[1]  # no SQL, no line
    script = tmp_path / "eq.sh"
    script.write_text(text, encoding="utf-8")
    env = {**os.environ, "SQLITE_DB": str(tmp_path / "stats.db")}
    done = subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True, check=True
    )
    results = tmp_path / "results.jsonl"
    results.write_text(done.stdout, encoding="utf-8")
    owner = harness.from_results(
        root,
        load_model(root),
        "employment",
        results,
        source="stats-db",
        dialect="sqlite",
        ran_on=DAY,
    )
    assert _outcomes(owner) == {
        "count-2025": "error",
        "filter-a1": "pass",
        "total-2024": "pass",
        "total-2025": "error",
    }


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("duckdb_engine") is None, reason="no [duckdb] extra"
)
@pytest.mark.filterwarnings("ignore")
def test_the_same_corpus_runs_on_duckdb(tmp_path: Path) -> None:
    import duckdb

    root, sqlite_url = _model(tmp_path)
    path = tmp_path / "stats.duckdb"
    conn = duckdb.connect(str(path))
    try:
        with sqlite3.connect(tmp_path / "stats.db") as lite:
            for table in ("employment", "areas", "industries"):
                ddl = lite.execute(
                    "SELECT sql FROM sqlite_master WHERE name = ?", (table,)
                ).fetchone()[0]
                conn.execute(ddl)
                rows = lite.execute(f"SELECT * FROM {table}").fetchall()
                if rows:
                    marks = ", ".join("?" for _ in rows[0])
                    conn.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)
    finally:
        conn.close()
    result = harness.run(
        root,
        load_model(root),
        "employment",
        url=f"duckdb:///{path}",
        source="stats-db",
        dialect="duckdb",
        ran_on=DAY,
    )
    assert _outcomes(result) == _outcomes(_run(root, sqlite_url)) == dict.fromkeys(CORPUS, "pass")


def _corpus_item(root: Path, item_id: str, **extra: str) -> None:
    path = root / "semantic" / "employment" / "corpus" / f"{item_id}.yaml"
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc.update(extra)
    path.write_text(json.dumps(doc), encoding="utf-8")


def test_d021_threshold_share_and_explanations(tmp_path: Path) -> None:
    root, url = _model(tmp_path, "partial")
    result = _run(root, url)
    # two of four pass; count-2025 is same_count and does not count; total-2025 errors
    assert result.share() == 0.5
    assert result.unexplained() == ["count-2025", "total-2025"]
    assert not result.proven()
    _corpus_item(root, "total-2025", known_gap="the consumer has no 2025 totals yet")
    _corpus_item(root, "count-2025", finding="F-0001")
    result = _run(root, url)
    assert result.unexplained() == []
    assert result.share() == round(2 / 3, 6)  # known gaps leave the denominator
    assert not result.proven()  # 0.667 < 0.75
    summary = result.summary()
    assert (summary["threshold"], summary["proven"]) == (0.75, False)
    assert "| total-2025 | same_rows | error | the consumer gave no SQL | known gap |" in (
        harness.report(result)
    )


def test_accept_records_the_verdict_and_the_gate_reads_it(tmp_path: Path) -> None:
    from factmodel.gate.runner import run_gate

    root, url = _model(tmp_path, "partial")
    layer = root / "semantic" / "employment" / "layer.yaml"
    layer.write_text(layer.read_text().replace("status: draft", "status: reviewed"), "utf-8")
    harness.write(root, _run(root, url))
    harness.accept(root, "employment")
    assert run_gate(root).failed == ["layers"]  # accepted, but not proven

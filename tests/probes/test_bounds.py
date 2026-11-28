"""D-025 and D-026 on the QCEW example: a relationship states a bound that is not zero with a
reason, and a self-reference by period leaves out the first period in the source."""

import importlib.util
import shutil
import sqlite3
from pathlib import Path
from types import ModuleType

from factmodel.adapters.sql import measure
from factmodel.gate.runner import run_gate
from factmodel.model.loader import load_model
from factmodel.probes import generate, render

ROOT = Path(__file__).resolve().parents[2]
QCEW = ROOT / "examples" / "qcew"
PARENT = QCEW / "physical" / "entities" / "industry_titles.yaml"


def _seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qcew_seed_bounds", QCEW / "seed" / "seed.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _probes() -> dict[str, dict[str, object]]:
    model = load_model(QCEW)
    docs, _ = generate(model.entities, model.sources, {"qcew-duckdb-real": "duckdb"})
    return {doc["id"]: doc for doc in docs}


def test_generator_writes_the_stated_bound_and_zero_elsewhere() -> None:
    probes = _probes()
    assert probes["join-match-industry-titles-parent"]["expected"] == {"orphans_left": {"max": 53}}
    assert probes["join-match-qtrly-to-industry"]["expected"] == {"orphans_left": {"max": 0}}
    assert probes["key-duplicates-qtrly"]["expected"] == {"duplicate_keys": {"max": 0}}
    relationship = load_model(QCEW).relationships["industry_titles.parent"][1]
    assert relationship.expected is not None and "sector ranges" in relationship.expected.reason


def test_a_bound_needs_its_reason_in_the_schema_and_the_typed_model(tmp_path: Path) -> None:
    root = tmp_path / "qcew"
    shutil.copytree(QCEW, root, ignore=shutil.ignore_patterns("data", "*.duckdb*", ".DS_Store"))
    assert run_gate(root).passed
    entity = root / "physical" / "entities" / "industry_titles.yaml"
    text = entity.read_text(encoding="utf-8")
    start = text.index("    reason: The three sector ranges")
    entity.write_text(text[:start] + text[text.index("\n", start) + 1 :], encoding="utf-8")
    report = run_gate(root)
    assert not report.passed
    assert any("reason" in line for line in report.lines())


def test_first_period_is_read_from_the_data(tmp_path: Path) -> None:
    probes = load_model(QCEW).probes
    sql = render(probes["join-match-annual-prior-year"], "sqlite") or ""
    assert "MIN(" in sql and "2024" not in sql  # no literal year in the probe
    url = _seed().load_sqlite(tmp_path / "qcew.db")

    def run() -> dict[str, int]:
        result: dict[str, int] = measure(url, [("p", sql)])[0]["measurement"]
        return result

    assert run() == {"source_rows": 138, "orphans_left": 0, "orphans_right": 144}
    # load an earlier year: 2024 stops being the first period, with no edit to the relationship
    with sqlite3.connect(tmp_path / "qcew.db") as conn:
        conn.execute("CREATE TEMP TABLE earlier AS SELECT * FROM annual WHERE year = '2024'")
        conn.execute("UPDATE earlier SET year = '2023'")
        conn.execute("INSERT INTO annual SELECT * FROM earlier")
    after = run()
    assert after["orphans_left"] == 0 and after["source_rows"] > 138

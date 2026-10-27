"""The QCEW example: a domain without a subject (D-015), join expressions (D-017) and BLS code
lists as fixtures (D-016), on SQLite, PostgreSQL and DuckDB (WP2.2)."""

import hashlib
import importlib.util
import json
import re
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from factmodel.adapters.base import with_date
from factmodel.adapters.git import GitAdapter
from factmodel.adapters.sql import SqlAdapter, measure
from factmodel.core.derived import derive_model
from factmodel.core.status import effective_status
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from factmodel.model.types import Snapshot
from factmodel.probes import GENERATED_HEADER, generate, render
from factmodel.repo import dump_yaml
from tests.adapters.helpers import PG_DSN, needs_pg, neutral

ROOT = Path(__file__).resolve().parents[2]
QCEW = ROOT / "examples" / "qcew"
DAY = "2026-10-27"
RESULTS = QCEW / "probes" / "results" / f"qcew-sqlite@{DAY}.jsonl"
needs_duckdb = pytest.mark.skipif(
    importlib.util.find_spec("duckdb_engine") is None, reason="extra [duckdb] not installed"
)


def _seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qcew_seed", QCEW / "seed" / "seed.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _committed(source: str) -> Snapshot:
    return Snapshot.model_validate(
        load(QCEW / "sources" / "snapshots" / f"{source}@{DAY}.yaml").data
    )


def _results() -> dict[str, Any]:
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    return {r["probe"]: r["measurement"] for r in rows[1:]}


def _queries(dialect: str) -> list[tuple[str, str]]:
    model = load_model(QCEW)
    return [(pid, render(p, dialect) or "") for pid, p in model.probes.items()]


def test_gate_is_green() -> None:
    report = run_gate(QCEW)
    assert report.passed, "\n".join(report.lines())


def test_expected_shape() -> None:
    model = load_model(QCEW)
    assert model.config is not None and model.config.anchor_entity is None
    assert model.profile is not None and model.profile.subject is None
    values = derive_model(model)
    assert values is not None
    assert {r.subject_scope for r in values.scope.rows.values()} == {"none"}
    assert values.projection.residue == ()
    classes = {e.id: e.class_ for e in model.entities.values()}
    assert {k for k, v in classes.items() if v == "data"} == {"annual", "qtrly"}
    labels = {label.relationship: label.label for label in values.projection.labels}
    for entity in ("annual", "qtrly"):
        for key in ("to-area", "to-ownership", "to-industry", "to-agglevel", "to-size"):
            assert labels[f"{entity}.{key}"] == "dimension"
        assert labels[f"{entity}.prior-year"] == "lineage"
    assert labels["annual.to-quarters"] == "lineage"
    assert labels["area_titles.in-state"] == "hierarchy"
    assert labels["industry_titles.parent"] == "hierarchy"
    for ref in ("area_titles.in-msa", "area_titles.in-csa", "industry_titles.to-supersector"):
        assert labels[ref] == "unresolved"


def test_nine_findings_and_two_hazards_have_evidence() -> None:
    model = load_model(QCEW)
    assert sorted(model.findings) == [f"F-{n:04d}" for n in range(1, 10)]
    for finding in model.findings.values():
        assert finding.evidence, finding.id
        assert all(ref in model.evidence for ref in finding.evidence), finding.id
    probe_backed = {
        f.id for f in model.findings.values() if any(model.evidence[e].probe for e in f.evidence)
    }
    # R1 key_duplicates, V1 value_set, V2 null_rate, G2 value_set, V3 join_match
    assert probe_backed == {"F-0001", "F-0002", "F-0003", "F-0006", "F-0008"}
    assert sorted(model.hazards) == ["H-0001", "H-0002"]
    assert all(h.evidence for h in model.hazards.values())


def test_area_duplicates_and_industry_ranges_are_measured() -> None:
    results = _results()
    assert results["key-duplicates-area-titles"] == {"duplicate_keys": 4649}
    assert results["row-count-area-titles"] == {"row_count": 9458}
    assert results["join-match-industry-titles-parent"]["orphans_left"] == 53
    assert results["value-set-qtrly-disclosure-code"]["outside_values"] == 1
    assert results["join-match-area-titles-in-state"]["orphans_left"] == 0


def test_every_resolved_relationship_has_probe_evidence() -> None:
    model = load_model(QCEW)
    for ref, (_, rel) in model.relationships.items():
        if rel.status is not None:
            continue
        assert effective_status(rel.evidence, model.evidence) == "confirmed", ref
        assert any(model.evidence[e].probe for e in rel.evidence or []), ref


def test_code_lists_are_the_committed_bls_files() -> None:
    sources = (QCEW / "sources" / "codelists" / "SOURCES.md").read_text(encoding="utf-8")
    listed = dict(re.findall(r"\| `(\w+_titles\.csv)` \|.*\| `([0-9a-f]{64})` \|", sources))
    files = sorted((QCEW / "sources" / "codelists").glob("*.csv"))
    assert sorted(listed) == [p.name for p in files]
    for path in files:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == listed[path.name], path.name
    assert sum(p.stat().st_size for p in files) < 1_000_000  # D-016


def test_seed_is_deterministic_and_reproduces_the_patterns() -> None:
    seed = _seed()
    assert seed.rows() == seed.rows()
    qtrly = seed.rows()["qtrly"]
    codes = {row[7] for row in qtrly}
    assert codes == {None, "N", "-"}
    keys = [row[:7] for row in qtrly]
    assert len(keys) == len(set(keys))  # G1
    for row in qtrly:
        if row[7] == "N":
            assert row[8] > 0 and row[9:16] == (0,) * 7  # V2: establishments kept
        if row[7] == "-":
            assert row[8:16] == (0,) * 8  # G2
    assert {row[4] for row in qtrly} == {"0"}
    assert "4" not in {row[1] for row in qtrly}


def test_sqlite_snapshot_and_probes_reproduce(tmp_path: Path) -> None:
    url = _seed().load_sqlite(tmp_path / "qcew.db")
    model = load_model(QCEW)
    fresh = with_date(SqlAdapter().reflect(model.sources["qcew-sqlite"], url), DAY)
    assert fresh == _committed("qcew-sqlite")
    assert {r["probe"]: r["measurement"] for r in measure(url, _queries("sqlite"))} == _results()


def test_generated_probes_are_committed_unchanged() -> None:
    model = load_model(QCEW)
    dialects = {"qcew-sqlite": "sqlite"}
    docs, _ = generate(model.entities, model.sources, dialects)
    for doc in docs:
        path = QCEW / "probes" / f"{doc['id']}.yaml"
        assert path.read_text(encoding="utf-8") == GENERATED_HEADER + "\n" + dump_yaml(doc)


def test_ddl_agrees_with_the_catalog() -> None:
    assert neutral(_committed("qcew-ddl")) == neutral(_committed("qcew-sqlite"))
    model = load_model(QCEW)
    fresh = with_date(GitAdapter().snapshot(model.sources["qcew-ddl"], QCEW), DAY)
    assert fresh == _committed("qcew-ddl")


@needs_duckdb
@pytest.mark.filterwarnings("ignore")
def test_duckdb_gives_the_same_answers(tmp_path: Path) -> None:
    url = _seed().load_duckdb(tmp_path / "qcew.duckdb")
    model = load_model(QCEW)
    snap = SqlAdapter().reflect(model.sources["qcew-duckdb"], url, DAY)
    assert neutral(snap) == neutral(_committed("qcew-sqlite"))
    assert {r["probe"]: r["measurement"] for r in measure(url, _queries("duckdb"))} == _results()


@needs_pg
def test_postgres_gives_the_same_answers() -> None:
    from sqlalchemy import create_engine, text

    assert PG_DSN is not None
    schema = f"qcew_{uuid.uuid4().hex[:8]}"
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = f"{PG_DSN}?options=-csearch_path%3D{schema}"
    try:
        _seed().load_postgres(url)
        model = load_model(QCEW)
        snap = SqlAdapter().reflect(model.sources["qcew-pg"], url, DAY)
        assert neutral(snap) == neutral(_committed("qcew-sqlite"))
        got = {r["probe"]: r["measurement"] for r in measure(url, _queries("postgres"))}
        assert got == _results()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()

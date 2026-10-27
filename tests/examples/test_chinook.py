"""The Chinook example: the M1 gate on SQLite, and the same answers on PostgreSQL."""

import importlib.util
import json
import uuid
from pathlib import Path
from types import ModuleType
from typing import Any

from factmodel.adapters.base import with_date
from factmodel.adapters.git import GitAdapter
from factmodel.adapters.sql import SqlAdapter, measure
from factmodel.core.derived import derive_model
from factmodel.core.status import effective_status
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from factmodel.model.types import Snapshot
from factmodel.probes import render
from tests.adapters.helpers import PG_DSN, needs_pg, neutral

ROOT = Path(__file__).resolve().parents[2]
CHINOOK = ROOT / "examples" / "chinook"
DAY = "2026-10-23"
RESULTS = CHINOOK / "probes" / "results" / f"chinook-sqlite@{DAY}.jsonl"


def _seed() -> ModuleType:
    spec = importlib.util.spec_from_file_location("chinook_seed", CHINOOK / "seed" / "seed.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _committed(source: str) -> Snapshot:
    return Snapshot.model_validate(
        load(CHINOOK / "sources" / "snapshots" / f"{source}@{DAY}.yaml").data
    )


def _results() -> dict[str, Any]:
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    return {r["probe"]: r["measurement"] for r in rows[1:]}


def test_gate_is_green() -> None:
    report = run_gate(CHINOOK)
    assert report.passed, "\n".join(report.lines())


def test_expected_shape() -> None:
    values = derive_model(load_model(CHINOOK))
    assert values is not None
    scope = {r.entity: (r.subject_scope, r.basis) for r in values.scope.rows.values()}
    assert scope["customer"] == ("direct", None)
    assert scope["invoice"] == ("direct", None)
    assert scope["invoice_line"] == ("transitive", "unique_target")
    for entity in (
        "employee",
        "artist",
        "album",
        "track",
        "genre",
        "media_type",
        "playlist",
        "playlist_track",
    ):
        assert scope[entity] == ("none", None), entity
    assert values.projection.residue == ()
    labels = {label.relationship: label.label for label in values.projection.labels}
    assert labels["invoice_line.to-track"] == "customer_scoped"
    assert labels["customer.to-employee"] == "administrative"
    assert labels["track.to-album"] == "reference_data"


def test_every_relationship_is_confirmed_by_a_probe() -> None:
    model = load_model(CHINOOK)
    for ref, (_, rel) in model.relationships.items():
        assert effective_status(rel.evidence, model.evidence) == "confirmed", ref
        assert any(model.evidence[e].probe for e in rel.evidence or []), ref


def test_seed_is_deterministic() -> None:
    seed = _seed()
    assert seed.rows() == seed.rows()
    emails = [row[11] for row in seed.rows()["Customer"]]
    assert all(e.endswith("@example.invalid") for e in emails)


def test_sqlite_snapshot_and_probes_reproduce(tmp_path: Path) -> None:
    url = _seed().load_sqlite(tmp_path / "chinook.db")
    model = load_model(CHINOOK)
    fresh = with_date(SqlAdapter().reflect(model.sources["chinook-sqlite"], url), DAY)
    assert fresh == _committed("chinook-sqlite")
    queries = [(pid, render(p, "sqlite") or "") for pid, p in model.probes.items()]
    assert {r["probe"]: r["measurement"] for r in measure(url, queries)} == _results()


def test_ddl_agrees_with_the_catalog() -> None:
    assert neutral(_committed("chinook-ddl")) == neutral(_committed("chinook-sqlite"))
    model = load_model(CHINOOK)
    fresh = with_date(GitAdapter().snapshot(model.sources["chinook-ddl"], CHINOOK), DAY)
    assert fresh == _committed("chinook-ddl")


@needs_pg
def test_postgres_gives_the_same_answers() -> None:
    from sqlalchemy import create_engine, text

    assert PG_DSN is not None
    schema = f"chinook_{uuid.uuid4().hex[:8]}"
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    url = f"{PG_DSN}?options=-csearch_path%3D{schema}"
    try:
        _seed().load_postgres(url)
        model = load_model(CHINOOK)
        snap = SqlAdapter().reflect(model.sources["chinook-pg"], url, DAY)
        assert neutral(snap) == neutral(_committed("chinook-sqlite"))
        assert all(c.enforced for o in snap.objects for c in o.constraints or [])
        queries = [(pid, render(p, "postgres") or "") for pid, p in model.probes.items()]
        assert {r["probe"]: r["measurement"] for r in measure(url, queries)} == _results()
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()

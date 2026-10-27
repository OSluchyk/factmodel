"""DuckDB as a third local engine through the ``sql`` adapter (WP2.1)."""

import importlib.util
import uuid
from pathlib import Path

import pytest

from factmodel.adapters.base import enforces_foreign_keys
from factmodel.adapters.sql import SqlAdapter, measure
from factmodel.model.loader import load_model
from factmodel.probes import render
from tests.adapters.helpers import PG_DDL, PG_DSN, needs_pg, neutral, source, sqlite_db
from tests.examples import test_chinook as chinook

needs_duckdb = pytest.mark.skipif(
    importlib.util.find_spec("duckdb_engine") is None, reason="extra [duckdb] not installed"
)
pytestmark = [needs_duckdb, pytest.mark.filterwarnings("ignore")]


def _duckdb(path: Path, ddl: str = PG_DDL) -> str:
    import duckdb

    conn = duckdb.connect(str(path))
    try:
        for statement in ddl.split(";"):
            if statement.strip():
                conn.execute(statement)
    finally:
        conn.close()
    return f"duckdb:///{path}"


def test_duckdb_enforces_foreign_keys(tmp_path: Path) -> None:
    """The measurement behind ``duckdb`` in ``vocabulary:engine_enforces_foreign_keys``."""
    import duckdb

    _duckdb(tmp_path / "shop.duckdb")
    conn = duckdb.connect(str(tmp_path / "shop.duckdb"))
    try:
        with pytest.raises(duckdb.ConstraintException):
            conn.execute("INSERT INTO orders VALUES (1, 999, 10.00)")
    finally:
        conn.close()
    assert enforces_foreign_keys("duckdb")


def test_duckdb_reflection_agrees_with_sqlite(tmp_path: Path) -> None:
    url = _duckdb(tmp_path / "shop.duckdb")
    snap = SqlAdapter().reflect(source(engine="duckdb", location="shop"), url, "2026-10-27")
    lite = SqlAdapter().reflect(
        source(engine="sqlite", location="shop"), sqlite_db(tmp_path / "s.db"), "2026-10-27"
    )
    assert neutral(snap) == neutral(lite)
    assert snap.pin == "duckdb:shop@2026-10-27"
    assert all(c.enforced for o in snap.objects for c in o.constraints or [])


@needs_pg
def test_duckdb_reflection_agrees_with_postgres(tmp_path: Path) -> None:
    from sqlalchemy import create_engine, text

    assert PG_DSN is not None
    schema = f"shop_{uuid.uuid4().hex[:8]}"
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        for statement in PG_DDL.split(";"):
            if statement.strip():
                conn.execute(text(statement))
    try:
        url = f"{PG_DSN}?options=-csearch_path%3D{schema}"
        pg = SqlAdapter().reflect(source(engine="postgres", location="shop"), url, "2026-10-27")
        duck = SqlAdapter().reflect(
            source(engine="duckdb", location="shop"),
            _duckdb(tmp_path / "shop.duckdb"),
            "2026-10-27",
        )
        assert neutral(duck) == neutral(pg)
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_chinook_on_duckdb_gives_the_same_answers(tmp_path: Path) -> None:
    url = f"duckdb:///{tmp_path / 'chinook.duckdb'}"
    chinook._seed().load_postgres(url)
    model = load_model(chinook.CHINOOK)
    src = model.sources["chinook-pg"].model_copy(update={"engine": "duckdb"})
    snap = SqlAdapter().reflect(src, url, chinook.DAY)
    assert neutral(snap) == neutral(chinook._committed("chinook-sqlite"))
    queries = [(pid, render(p, "duckdb") or "") for pid, p in model.probes.items()]
    assert {r["probe"]: r["measurement"] for r in measure(url, queries)} == chinook._results()

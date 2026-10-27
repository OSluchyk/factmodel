"""The export and sql adapters, the type classes and the registry."""

import uuid
from importlib.metadata import EntryPoint
from pathlib import Path
from typing import Any

import pytest

from factmodel.adapters import registry
from factmodel.adapters.base import AdapterError, dialect_for, enforces_foreign_keys, with_date
from factmodel.adapters.export import ExportAdapter
from factmodel.adapters.sql import SqlAdapter
from factmodel.adapters.types import type_class
from tests.adapters.helpers import EXPORTS, PG_DDL, PG_DSN, needs_pg, neutral, source, sqlite_db


def _by_name(snap: Any) -> dict[str, Any]:
    return {o.name: o for o in snap.objects}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("INT64", "integer"),
        ("integer", "integer"),
        ("BIGINT", "integer"),
        ("NUMERIC(10, 2)", "decimal"),
        ("NUMBER(38,0)", "decimal"),
        ("FLOAT64", "float"),
        ("DOUBLE PRECISION", "float"),
        ("BOOL", "boolean"),
        ("character varying", "text"),
        ("NVARCHAR(64)", "text"),
        ("STRING", "text"),
        ("DATE", "date"),
        ("TIME WITH TIME ZONE", "time"),
        ("timestamp without time zone", "timestamp"),
        ("DATETIME", "timestamp"),
        ("INTERVAL", "interval"),
        ("BYTEA", "binary"),
        ("JSONB", "json"),
        ("VARIANT", "json"),
        ("ARRAY<STRING>", "array"),
        ("text[]", "array"),
        ("STRUCT<a INT64>", "struct"),
        ("GEOGRAPHY", "geography"),
        ("UUID", "other"),
    ],
)
def test_type_class(text: str, expected: str) -> None:
    assert type_class(text) == expected


def test_engine_facts_come_from_the_vocabulary() -> None:
    assert dialect_for("mssql") == "tsql"
    assert dialect_for("teradata", "teradata") == "teradata"
    with pytest.raises(AdapterError, match="no default dialect"):
        dialect_for("teradata")
    assert enforces_foreign_keys("postgres") and not enforces_foreign_keys("sqlite")


def test_export_generic_csv() -> None:
    src = source(adapter="export", engine="duckdb", location="shop")
    snap = ExportAdapter().read(EXPORTS / "generic", src, "2026-10-23")
    assert snap.pin == "duckdb:shop@2026-10-23"
    objects = _by_name(snap)
    assert sorted(objects) == ["customer_totals", "customers", "order_lines", "orders"]
    assert objects["customer_totals"].object_type == "view"
    orders = objects["orders"]
    fk = next(c for c in orders.constraints if c.constraint_type == "foreign_key")
    assert (fk.references.object, fk.references.fields, fk.enforced) == (
        "customers",
        ["customer_id"],
        True,  # DuckDB enforces foreign keys (test_duckdb.py)
    )
    lines = objects["order_lines"]
    pk = next(c for c in lines.constraints if c.constraint_type == "primary_key")
    assert pk.fields == ["order_id", "line_no"]
    assert [f.type_class for f in objects["customers"].fields] == ["integer", "text", "timestamp"]


def test_export_postgres_json_enforced_and_arrays() -> None:
    src = source(adapter="export", engine="postgres", location="shop")
    snap = ExportAdapter().read(EXPORTS / "postgres", src, "2026-10-23")
    customers = _by_name(snap)["customers"]
    tags = next(f for f in customers.fields if f.name == "tags")
    assert (tags.type, tags.type_class, tags.repeated) == ("text", "text", True)
    assert all(c.enforced for c in customers.constraints)


def test_export_bigquery_nested_partitioning_options() -> None:
    src = source(adapter="export", engine="bigquery", location="my-project.shop")
    snap = ExportAdapter().read(EXPORTS / "bigquery", src, "2026-10-23")
    assert snap.pin == "bigquery:my-project.shop@2026-10-23"
    orders = _by_name(snap)["orders"]
    fields = {f.path or f.name: f for f in orders.fields}
    assert fields["context"].type_class == "struct"
    assert fields["context.device"].name == "device"
    assert (fields["tags"].type, fields["tags"].repeated) == ("STRING", True)
    assert fields["ordered_on"].description == "Day the order was placed"
    assert orders.partitioning is not None and orders.partitioning.field == "ordered_on"
    assert orders.clustering == ["customer_id"]
    assert orders.description == "Orders placed in the shop"
    assert orders.options == {
        "description": "Orders placed in the shop",
        "partition_expiration_days": 30.0,
        "require_partition_filter": True,
    }
    assert not any(c.enforced for o in snap.objects for c in o.constraints or [])
    fk = next(c for c in orders.constraints if c.constraint_type == "foreign_key")
    assert fk.references is not None and fk.references.object == "customers"


def test_export_neutral_parts_agree_across_flavours() -> None:
    def shop(snap: Any) -> list[Any]:
        rows = [r for r in neutral(snap) if r[0] in ("customers", "order_lines")]
        return [(n, t, [f for f in fs if f[0] != "tags"], cs) for n, t, fs, cs in rows]

    generic = ExportAdapter().read(
        EXPORTS / "generic", source(engine="duckdb", location="shop"), "2026-10-23"
    )
    postgres = ExportAdapter().read(
        EXPORTS / "postgres", source(engine="postgres", location="shop"), "2026-10-23"
    )
    assert shop(generic) == shop(postgres)


def test_export_missing_required_view(tmp_path: Path) -> None:
    (tmp_path / "TABLES.csv").write_text("table_name,table_type\nx,BASE TABLE\n")
    with pytest.raises(AdapterError, match="missing views"):
        ExportAdapter().read(tmp_path, source(engine="duckdb"), "2026-10-23")


def test_export_sql_names_the_views() -> None:
    adapter = ExportAdapter()
    pg = adapter.export_sql(source(id="pg", engine="postgres", location="shop"))
    assert "information_schema.REFERENTIAL_CONSTRAINTS" in pg and "udt_name" in pg
    bq = adapter.export_sql(source(id="bq", engine="bigquery", location="my-project.shop"))
    assert "`my-project.shop`.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS" in bq
    assert "REFERENTIAL_CONSTRAINTS" not in bq
    assert "fact snapshot --source bq --from-export" in bq


def test_sql_adapter_on_sqlite(tmp_path: Path) -> None:
    url = sqlite_db(tmp_path / "shop.db")
    src = source(adapter="sql", engine="sqlite", dsn_env="FACT_TEST_DSN")
    snap = SqlAdapter().reflect(src, url, "2026-10-23")
    assert snap.pin == "sqlite:shop@2026-10-23"
    objects = _by_name(snap)
    assert objects["customer_totals"].object_type == "view"
    customers = objects["customers"]
    kinds = sorted((c.constraint_type, tuple(c.fields)) for c in customers.constraints)
    assert kinds == [("primary_key", ("customer_id",)), ("unique", ("email_hash",))]
    fk = next(c for c in objects["orders"].constraints if c.constraint_type == "foreign_key")
    assert (fk.references.object, fk.enforced) == ("customers", False)
    assert [(f.type, f.type_class) for f in customers.fields][1] == ("NVARCHAR(64)", "text")


def test_sql_adapter_reads_dsn_from_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = sqlite_db(tmp_path / "shop.db")
    src = source(adapter="sql", engine="sqlite", dsn_env="FACT_TEST_DSN")
    monkeypatch.delenv("FACT_TEST_DSN", raising=False)
    with pytest.raises(AdapterError, match="FACT_TEST_DSN is not set"):
        SqlAdapter().snapshot(src, tmp_path)
    monkeypatch.setenv("FACT_TEST_DSN", url)
    assert len(SqlAdapter().snapshot(src, tmp_path).objects) == 3


@needs_pg
def test_sql_adapter_on_postgres_agrees_with_sqlite(tmp_path: Path) -> None:
    from sqlalchemy import create_engine, text

    assert PG_DSN is not None
    schema = f"t_{uuid.uuid4().hex[:8]}"
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        for statement in filter(str.strip, PG_DDL.split(";")):
            conn.execute(text(statement))
    try:
        url = f"{PG_DSN}?options=-csearch_path%3D{schema}"
        pg = SqlAdapter().reflect(source(engine="postgres", location="shop"), url, "2026-10-23")
        lite = SqlAdapter().reflect(
            source(engine="sqlite", location="shop"), sqlite_db(tmp_path / "s.db"), "2026-10-23"
        )
        assert neutral(pg) == neutral(lite)
        pg_customers, lite_customers = _by_name(pg)["customers"], _by_name(lite)["customers"]
        assert [f.type for f in pg_customers.fields] != [f.type for f in lite_customers.fields]
        assert all(c.enforced for c in pg_customers.constraints)
        assert not any(c.enforced for c in lite_customers.constraints)
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_with_date_moves_the_pin() -> None:
    src = source(engine="duckdb", location="shop")
    snap = with_date(ExportAdapter().read(EXPORTS / "generic", src, "2026-10-23"), "2026-11-01")
    assert (snap.taken_on, snap.pin) == ("2026-11-01", "duckdb:shop@2026-11-01")


class _FakeAdapter:
    name = "fake"

    def engines(self) -> list[str]:
        return ["fakedb"]

    def default_dialect(self, engine: str) -> str:
        return "postgres"


def test_registry_finds_a_third_party_entry_point(monkeypatch: pytest.MonkeyPatch) -> None:
    builtin = list(registry._entry_points())
    fake = EntryPoint(name="fake", value=f"{__name__}:_FakeAdapter", group=registry.GROUP)
    monkeypatch.setattr(registry, "_entry_points", lambda: [*builtin, fake])
    found = registry.adapters()
    assert {"export", "sql", "fake"} <= set(found)
    assert found["fake"].engines() == ["fakedb"]
    with pytest.raises(AdapterError, match="not installed"):
        registry.get("odbc")

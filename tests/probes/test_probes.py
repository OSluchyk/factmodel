"""Probe generation, rendering per dialect, execution, scripts and intake (WP1.7)."""

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel.adapters.sql import measure
from factmodel.cli import app
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from factmodel.model.types import Probe
from factmodel.probes import build, render
from factmodel.probes.intake import IntakeError, intake, read_results
from tests.adapters.helpers import PG_DSN, needs_pg
from tests.model.helpers import dump
from tests.probes.helpers import DDL, EXPECTED, ROWS, build_model, create_sqlite

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "probes"
DIALECTS = ["bigquery", "postgres", "sqlite", "snowflake", "duckdb", "tsql", "mysql"]
runner = CliRunner()


def _probes(root: Path) -> dict[str, Probe]:
    assert runner.invoke(app, ["probe", "generate", "--root", str(root)]).exit_code == 0
    return dict(load_model(root).probes)


def _queries() -> dict[str, str]:
    """One query per probe kind, built from the AST builders with fixed names."""
    rule = build.exp.EQ(this=build.column("t", "IsCurrent"), expression=build.exp.Literal.number(1))
    return {
        "key_duplicates": build.key_duplicates("sales.Customer", ["CustomerId"]),
        "join_match": build.join_match(
            "sales.Order", "sales.Customer", [("CustomerId", "CustomerId")]
        ),
        "fan_out": build.fan_out("sales.Customer", ["CustomerId"]),
        "null_rate": build.null_rate("sales.Order", "CustomerId"),
        "row_count": build.row_count("sales.Order"),
        "current_row_ties": build.current_row_ties("sales.CustomerVersion", ["CustomerId"], rule),
        "value_set": build.value_set("sales.Customer", "EmailHash"),
    }


@pytest.mark.parametrize("dialect", DIALECTS)
def test_rendering_matches_golden(dialect: str) -> None:
    text = "".join(
        f"-- {kind}\n{query.sql(dialect=dialect, identify=True)};\n"
        for kind, query in _queries().items()
    )
    assert text == (FIXTURES / f"rendered.{dialect}.sql").read_text(encoding="utf-8")


def test_every_probe_kind_has_a_builder() -> None:
    from factmodel import vocabulary

    assert set(_queries()) == set(vocabulary.load()["probe_kind"]) == set(build.METRICS)


def test_generate_is_idempotent_and_ids_are_stable(tmp_path: Path) -> None:
    root = build_model(tmp_path)
    probes = _probes(root)
    assert sorted(probes) == sorted(EXPECTED)
    again = runner.invoke(app, ["probe", "generate", "--root", str(root)])
    assert "10 probes, 0 written" in again.output


def test_execution_on_sqlite_for_every_generated_kind(tmp_path: Path) -> None:
    root = build_model(tmp_path)
    probes = _probes(root)
    url = create_sqlite(tmp_path / "shop.db")
    results = measure(url, [(pid, render(p, "sqlite") or "") for pid, p in probes.items()])
    assert {r["probe"]: r["measurement"] for r in results} == EXPECTED


def test_value_set_counts_distinct_values_only(tmp_path: Path) -> None:
    url = create_sqlite(tmp_path / "shop.db")
    sql = build.value_set("Customer", "EmailHash").sql(dialect="sqlite", identify=True)
    assert measure(url, [("v", sql)]) == [{"probe": "v", "measurement": {"distinct_values": 3}}]


def test_failed_query_is_recorded_not_raised(tmp_path: Path) -> None:
    url = create_sqlite(tmp_path / "shop.db")
    assert measure(url, [("x", 'SELECT COUNT(*) AS n FROM "Missing"')]) == [
        {"probe": "x", "error": "QUERY FAILED"}
    ]


@needs_pg
def test_execution_on_postgres_gives_the_same_counts(tmp_path: Path) -> None:
    from sqlalchemy import create_engine, text

    assert PG_DSN is not None
    schema = f"p_{uuid.uuid4().hex[:8]}"
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        for statement in [*filter(str.strip, DDL.split(";")), *ROWS]:
            conn.execute(text(statement))
    try:
        root = build_model(tmp_path)
        probes = _probes(root)
        url = f"{PG_DSN}?options=-csearch_path%3D{schema}"
        results = measure(url, [(pid, render(p, "postgres") or "") for pid, p in probes.items()])
        assert {r["probe"]: r["measurement"] for r in results} == EXPECTED
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_nested_probe_is_never_rendered_where_unsupported() -> None:
    probe = Probe.model_validate(
        {
            "kind": "probe",
            "id": "null-rate-events-context-user-id",
            "probe_kind": "null_rate",
            "fact": "events.context.user_id",
            "dialect": "bigquery",
            "sql": build.null_rate("events", "context.user_id").sql(
                dialect="bigquery", identify=True
            ),
            "unsupported_on_dialect": ["postgres", "sqlite"],
        }
    )
    assert render(probe, "bigquery") == probe.sql
    assert "`context`.`user_id`" in probe.sql
    assert render(probe, "postgres") is None


def _run(root: Path, url: str) -> Path:
    os.environ["FACT_TEST_SHOP_DSN"] = url
    try:
        args = ["probe", "run", "--root", str(root), "--source", "shop", "--date", "2026-10-23"]
        result = runner.invoke(app, [*args, "--data-quality", "synthetic"])
    finally:
        del os.environ["FACT_TEST_SHOP_DSN"]
    assert result.exit_code == 0, result.output
    return root / "probes" / "results" / "shop@2026-10-23.jsonl"


def test_intake_cites_in_range_and_opens_findings_out_of_range(tmp_path: Path) -> None:
    root = build_model(tmp_path)
    _probes(root)
    results = _run(root, create_sqlite(tmp_path / "shop.db"))
    out = intake(root, results)
    assert sorted(out.out_of_range) == [
        "current-row-ties-customer-version",
        "join-match-order-to-customer",
    ]
    assert len(out.confirmed) == 8 and not out.failed and not out.rejected
    order = load(root / "physical" / "entities" / "order.yaml").data
    assert "ev-fan-out-order-to-customer-2026-10-23" in order["relationships"][0]["evidence"]
    record = load(
        root / "evidence" / "probes" / "join-match-order-to-customer@2026-10-23.yaml"
    ).data
    assert record["records"][0]["measurement"]["match_rate"] == 0.8
    assert record["records"][0]["data_quality"] == "synthetic"
    findings = [load(p).data for p in sorted((root / "registers" / "findings").glob("*.yaml"))]
    assert [f["extensions"]["probe"] for f in findings] == [
        "current-row-ties-customer-version",
        "join-match-order-to-customer",
    ]
    model = load_model(root)
    rel = model.entities["order"].relationships[0]
    statuses = {model.evidence[e].status for e in rel.evidence or []}
    # D-014: synthetic data attaches the probe but never confirms the fact.
    assert statuses == {"inferred"}
    assert any(model.evidence[e].probe for e in rel.evidence or [])
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert intake(root, results).written == []
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_intake_rejects_malformed_results(tmp_path: Path) -> None:
    root = build_model(tmp_path)
    _probes(root)
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json\n", encoding="utf-8")
    with pytest.raises(IntakeError, match="not JSON"):
        intake(root, bad)
    bad.write_text('{"source": "shop"}\n', encoding="utf-8")
    with pytest.raises(IntakeError, match="header line lacks"):
        read_results(bad)
    lines = [
        {
            "source": "shop",
            "pin": "sqlite:shop@2026-10-23",
            "environment": "prod",
            "data_quality": "synthetic",
            "ran_on": "2026-10-23",
        },
        {"probe": "nope", "measurement": {"row_count": 1}},
        {"probe": "row-count-order", "measurement": {"row_count": "c0042@example.invalid"}},
        {"probe": "row-count-customer", "error": "QUERY FAILED"},
    ]
    bad.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    out = intake(root, bad)
    assert out.failed == ["row-count-customer"]
    assert out.rejected == ["unknown probe 'nope'", "row-count-order: no usable measurement"]
    assert out.written == []
    assert not (root / "evidence" / "probes").exists()


@pytest.mark.skipif(shutil.which("sqlite3") is None, reason="sqlite3 CLI not installed")
def test_rendered_sqlite_script_runs_and_feeds_intake(tmp_path: Path) -> None:
    root = build_model(tmp_path)
    _probes(root)
    assert (
        runner.invoke(
            app, ["probe", "render", "--root", str(root), "--dialect", "sqlite"]
        ).exit_code
        == 0
    )
    script = root / "probes" / "scripts" / "shop.sqlite.sh"
    create_sqlite(tmp_path / "shop.db")
    env = {
        **os.environ,
        "SQLITE_DB": str(tmp_path / "shop.db"),
        "PIN": "sqlite:shop@2026-10-23",
        "RAN_ON": "2026-10-23",
        "DATA_QUALITY": "synthetic",
    }
    done = subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True, check=True
    )
    results = tmp_path / "from-script.jsonl"
    results.write_text(done.stdout, encoding="utf-8")
    _, rows = read_results(results)
    assert {r["probe"]: r["measurement"] for r in rows} == EXPECTED
    assert len(intake(root, results).confirmed) == 8


def _with_domains(root: Path) -> None:
    for name, field, values in (
        ("customer_version", "IsCurrent", [0, 1]),
        ("customer", "EmailHash", ["h1", "h2"]),
    ):
        path = root / "physical" / "entities" / f"{name}.yaml"
        doc = load(path).data
        next(f for f in doc["fields"] if f["name"] == field)["values"] = values
        path.write_text(dump(doc), encoding="utf-8")


def test_value_set_counts_values_outside_the_declared_domain(tmp_path: Path) -> None:
    root = build_model(tmp_path)
    _with_domains(root)
    probes = _probes(root)
    domain = {k: p for k, p in probes.items() if p.probe_kind == "value_set"}
    assert sorted(domain) == [
        "value-set-customer-email-hash",
        "value-set-customer-version-is-current",
    ]
    for probe in domain.values():
        assert probe.expected is not None and probe.expected["outside_values"].max == 0
        assert "'h1'" not in probe.sql.split("FROM")[0].split("CASE")[0]
    url = create_sqlite(tmp_path / "shop.db")
    results = measure(url, [(pid, render(p, "sqlite") or "") for pid, p in domain.items()])
    assert {r["probe"]: r["measurement"] for r in results} == {
        "value-set-customer-email-hash": {"distinct_values": 3, "outside_values": 1},
        "value-set-customer-version-is-current": {"distinct_values": 2, "outside_values": 0},
    }


@needs_pg
def test_value_set_on_postgres(tmp_path: Path) -> None:
    from sqlalchemy import create_engine, text

    assert PG_DSN is not None
    schema = f"v_{uuid.uuid4().hex[:8]}"
    engine = create_engine(PG_DSN)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        conn.execute(text(f'SET search_path TO "{schema}"'))
        for statement in [*filter(str.strip, DDL.split(";")), *ROWS]:
            conn.execute(text(statement))
    try:
        root = build_model(tmp_path)
        _with_domains(root)
        domain = {k: p for k, p in _probes(root).items() if p.probe_kind == "value_set"}
        url = f"{PG_DSN}?options=-csearch_path%3D{schema}"
        results = measure(url, [(pid, render(p, "postgres") or "") for pid, p in domain.items()])
        assert {r["probe"]: r["measurement"]["outside_values"] for r in results} == {
            "value-set-customer-email-hash": 1,
            "value-set-customer-version-is-current": 0,
        }
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()

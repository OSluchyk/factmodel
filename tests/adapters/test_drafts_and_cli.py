"""to_facts golden drafts, and the fact adapters / export-sql / snapshot / draft commands."""

import shutil
from pathlib import Path

from typer.testing import CliRunner

from factmodel.adapters.export import ExportAdapter
from factmodel.cli import app
from factmodel.core.drafts import slug, to_facts
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.loader import inspect_model
from factmodel.repo import dump_yaml
from tests.adapters.helpers import EXPORTS, FIXTURES, source, sqlite_db
from tests.model.helpers import dump

runner = CliRunner()
GOLDEN = FIXTURES / "drafts" / "bigquery"


def test_to_facts_matches_golden_drafts() -> None:
    src = source(id="shop", adapter="export", engine="bigquery", location="my-project.shop")
    drafts = to_facts(ExportAdapter().read(EXPORTS / "bigquery", src, "2026-10-23"))
    assert [d.path for d in drafts] == [
        f"drafts/shop/entities/{p.name}" for p in sorted(GOLDEN.glob("*.yaml"))
    ]
    for draft in drafts:
        assert dump_yaml(draft.document) == (GOLDEN / Path(draft.path).name).read_text()


def test_enforced_foreign_keys_draft_as_confirmed() -> None:
    src = source(id="shop", engine="postgres", location="shop")
    drafts = {
        d.document["id"]: d.document
        for d in to_facts(ExportAdapter().read(EXPORTS / "postgres", src, "2026-10-23"))
    }
    statuses = {r["id"]: r["status"] for r in drafts["orders"]["records"]}
    assert statuses["ev-orders-to-customers"] == "confirmed"


def test_slug_splits_camel_case() -> None:
    assert [slug(n) for n in ("InvoiceLine", "MediaType", "order_items", "Track")] == [
        "invoice_line",
        "media_type",
        "order_items",
        "track",
    ]


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "retail"]).exit_code == 0
    return root


def _add(root: Path, **fields: str) -> None:
    doc = {"kind": "source", "title": "Shop", "source_kind": "warehouse", **fields}
    (root / "sources" / f"{fields['id']}.yaml").write_text(dump(doc), encoding="utf-8")


def test_adapters_command_lists_built_ins() -> None:
    result = runner.invoke(app, ["adapters"])
    assert result.exit_code == 0
    lines = result.output.splitlines()
    assert any(line.startswith("export  engines: *") and "mssql=tsql" in line for line in lines)
    assert any(line.startswith("sql  engines: *") for line in lines)
    assert "git" in result.output


def test_export_sql_command(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _add(
        root,
        id="bq",
        access_mode="export_file",
        adapter="export",
        engine="bigquery",
        location="p.sales",
    )
    result = runner.invoke(app, ["export-sql", "--root", str(root), "--source", "bq"])
    assert result.exit_code == 0 and "`p.sales`.INFORMATION_SCHEMA.TABLES" in result.output


def test_snapshot_and_draft_from_export_are_idempotent(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _add(
        root,
        id="shop",
        access_mode="export_file",
        adapter="export",
        engine="bigquery",
        location="my-project.shop",
    )
    args = ["snapshot", "--root", str(root), "--source", "shop", "--date", "2026-10-23"]
    first = runner.invoke(app, [*args, "--from-export", str(EXPORTS / "bigquery")])
    assert first.exit_code == 0, first.output
    assert "wrote sources/snapshots/shop@2026-10-23.yaml (4 objects)" in first.output
    again = runner.invoke(app, [*args, "--from-export", str(EXPORTS / "bigquery")])
    assert "unchanged" in again.output
    source_doc = load(root / "sources" / "shop.yaml").data
    assert source_doc["current_pin"] == "bigquery:my-project.shop@2026-10-23"
    drafted = runner.invoke(app, ["draft", "--root", str(root), "--source", "shop"])
    assert drafted.exit_code == 0 and "4 drafts, 4 written" in drafted.output
    assert (
        "4 drafts, 0 written"
        in runner.invoke(app, ["draft", "--root", str(root), "--source", "shop"]).output
    )
    assert not (root / "physical" / "entities" / "orders.yaml").exists()
    for path in (root / "drafts" / "shop" / "entities").glob("*.yaml"):
        assert path.read_text() == (GOLDEN / path.name).read_text()


def test_drafts_pass_schema_references_and_evidence_in_a_model(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _add(
        root,
        id="shop",
        access_mode="export_file",
        adapter="export",
        engine="bigquery",
        location="my-project.shop",
    )
    for path in GOLDEN.glob("*.yaml"):
        shutil.copy(path, root / "physical" / "entities" / path.name)
    config = load(root / "factmodel.yaml").data
    (root / "factmodel.yaml").write_text(dump({**config, "anchor_entity": "customers"}))
    stages = {s.name: s.verdict for s in run_gate(root).stages}
    assert stages["schema"] == stages["references"] == stages["evidence"] == "PASS", stages


def test_sql_snapshot_through_the_environment(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    root = _model(tmp_path)
    _add(
        root,
        id="lite",
        access_mode="agent_read",
        adapter="sql",
        engine="sqlite",
        dsn_env="FACT_TEST_DSN",
    )
    monkeypatch.setenv("FACT_TEST_DSN", sqlite_db(tmp_path / "shop.db"))
    result = runner.invoke(
        app, ["snapshot", "--root", str(root), "--source", "lite", "--date", "2026-10-23"]
    )
    assert result.exit_code == 0, result.output
    snap = load(root / "sources" / "snapshots" / "lite@2026-10-23.yaml").data
    assert snap["pin"] == "sqlite:shop@2026-10-23"
    assert (
        "FACT_TEST_DSN" not in (root / "sources" / "snapshots" / "lite@2026-10-23.yaml").read_text()
    )
    monkeypatch.delenv("FACT_TEST_DSN")
    missing = runner.invoke(app, ["snapshot", "--root", str(root), "--source", "lite"])
    assert missing.exit_code == 1 and "FACT_TEST_DSN is not set" in missing.output


def test_literal_dsn_fails_privacy(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _add(
        root,
        id="pg",
        access_mode="agent_read",
        adapter="sql",
        engine="postgres",
        location="postgresql://app:secret@db/prod",
    )
    report = run_gate(root)
    privacy = next(s for s in report.stages if s.name == "privacy")
    assert report.failed == ["privacy"] and privacy.issues[0].code == "literal_dsn"


def test_loader_checks_anchor_class_and_dialect(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _add(root, id="tera", access_mode="owner_read", adapter="export", engine="teradata")
    for path in GOLDEN.glob("*.yaml"):
        shutil.copy(path, root / "physical" / "entities" / path.name)
    customers = load(root / "physical" / "entities" / "customers.yaml").data
    (root / "physical" / "entities" / "customers.yaml").write_text(
        dump({**customers, "class": "reference"})
    )
    config = load(root / "factmodel.yaml").data
    (root / "factmodel.yaml").write_text(dump({**config, "anchor_entity": "customers"}))
    codes = {i.code for i in inspect_model(root).issues}
    assert {"anchor_class", "missing_dialect"} <= codes

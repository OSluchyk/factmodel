"""End-to-end CLI: init, source add, check, status."""

from pathlib import Path

from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from tests.model.helpers import dump

runner = CliRunner()


def _init(tmp_path: Path) -> Path:
    root = tmp_path / "shop-model"
    result = runner.invoke(app, ["init", str(root), "--profile", "retail"])
    assert result.exit_code == 0, result.output
    return root


def test_init_source_add_check_passes_on_the_empty_model(tmp_path: Path) -> None:
    root = _init(tmp_path)
    added = runner.invoke(
        app,
        [
            "source",
            "add",
            "--root",
            str(root),
            "--id",
            "bq-public",
            "--title",
            "BigQuery public data",
            "--kind",
            "warehouse",
            "--access-mode",
            "agent_read",
            "--engine",
            "bigquery",
        ],
    )
    assert added.exit_code == 0, added.output
    checked = runner.invoke(app, ["check", "--root", str(root)])
    assert checked.exit_code == 0, checked.output
    assert checked.output.strip().endswith("gate: pass")
    assert list(load_model(root).sources) == ["bq-public"]


def test_init_writes_the_layout(tmp_path: Path) -> None:
    root = _init(tmp_path)
    config = load(root / "factmodel.yaml").data
    assert config == {
        "kind": "model-config",
        "id": "shop-model",
        "framework_version": "0.0.1",
        "profile": "retail",
        "anchor_entity": "customer",
        "treat_synthetic_as_representative": False,
    }
    for rel in (
        "AGENTS.md",
        "CHANGELOG.md",
        ".github/workflows/fact-check.yml",
        ".claude/skills/README.md",
        "agent/brief.md",
        "agent/report.md",
        "physical/entities/.gitkeep",
        "registers/hazards/.gitkeep",
        "generated/labels.tsv",
    ):
        assert (root / rel).is_file(), rel
    workflow = (root / ".github/workflows/fact-check.yml").read_text(encoding="utf-8")
    assert "factmodel==0.0.1" in workflow and "{version}" not in workflow
    assert "retail" in (root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_init_refuses_unknown_profile_and_existing_model(tmp_path: Path) -> None:
    bad = runner.invoke(app, ["init", str(tmp_path / "x"), "--profile", "banking"])
    assert bad.exit_code == 1 and "unknown profile" in bad.output
    root = _init(tmp_path)
    again = runner.invoke(app, ["init", str(root), "--profile", "retail"])
    assert again.exit_code == 1 and "already exists" in again.output


def test_source_add_validates_against_the_schema(tmp_path: Path) -> None:
    root = _init(tmp_path)
    args = ["source", "add", "--root", str(root), "--id", "dw", "--title", "Warehouse"]
    missing_engine = runner.invoke(
        app, [*args, "--kind", "warehouse", "--access-mode", "owner_read"]
    )
    assert missing_engine.exit_code == 1 and "engine" in missing_engine.output
    bad_mode = runner.invoke(app, [*args, "--kind", "git", "--access-mode", "public"])
    assert bad_mode.exit_code == 1


def test_check_reports_failure_and_exit_code(tmp_path: Path) -> None:
    root = _init(tmp_path)
    (root / "sources" / "bad.yaml").write_text("kind: source\nid: bad\n", encoding="utf-8")
    result = runner.invoke(app, ["check", "--root", str(root)])
    assert result.exit_code == 1
    assert "FAIL  schema" in result.output and "sources/bad.yaml:1:1" in result.output


def test_status_lists_what_needs_attention(tmp_path: Path) -> None:
    root = _init(tmp_path)
    source = {
        "kind": "source",
        "id": "etl",
        "title": "Loader config",
        "source_kind": "git",
        "access_mode": "owner_read",
        "current_pin": "etl@9b1d220:loaders/orders.yaml",
    }
    (root / "sources" / "etl.yaml").write_text(dump(source), encoding="utf-8")
    evidence = {
        "kind": "evidence",
        "records": [
            {
                "id": "ev-old",
                "source": "etl",
                "pin": "etl@3f2a9c1:loaders/orders.yaml",
                "quote": "schedule daily",
                "status": "inferred",
                "read_on": "2026-10-01",
            }
        ],
    }
    (root / "evidence" / "shared.yaml").write_text(dump(evidence), encoding="utf-8")
    finding = {
        "kind": "finding",
        "id": "F-0001",
        "title": "Gap in loads",
        "status": "open",
        "opened_on": "2026-11-01",
        "description": "x",
    }
    (root / "registers/findings/F-0001.yaml").write_text(dump(finding), encoding="utf-8")
    hazard = {
        "kind": "hazard",
        "id": "H-0001",
        "title": "Late loads",
        "status": "active",
        "description": "Loads can arrive a day late.",
        "applies_to": ["orders"],
        "evidence": ["ev-old"],
    }
    (root / "registers/hazards/H-0001.yaml").write_text(dump(hazard), encoding="utf-8")
    trigger = {
        "kind": "trigger",
        "id": "etl-moved",
        "event": "source_pin_moved",
        "follow_up": "Re-read evidence pinned to the old commit.",
        "fired": [{"on": "2026-11-10"}],
    }
    (root / "maintenance" / "etl-moved.yaml").write_text(dump(trigger), encoding="utf-8")
    result = runner.invoke(app, ["status", "--root", str(root)])
    assert result.exit_code == 0
    out = result.output
    assert "open findings: 1" in out and "F-0001 Gap in loads" in out
    assert "stale evidence: 1" in out and "ev-old pinned etl@3f2a9c1" in out
    assert "fired triggers without follow-up: 1" in out
    assert "hazards (permanent, not issues): 1" in out
    assert "work on finding F-0001" in out
    assert "H-0001" not in out.split("next actions:")[1]

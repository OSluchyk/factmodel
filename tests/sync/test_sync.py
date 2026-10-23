"""fact sync: drift kinds and classes, drafts, findings, triggers, idempotency (WP1.6)."""

import shutil
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.types import Entity, Snapshot
from factmodel.sync.drift import drift
from tests.model.helpers import dump

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sync"
runner = CliRunner()


def _snap(name: str) -> Snapshot:
    return Snapshot.model_validate(load(FIXTURES / name).data)


def _entity(name: str, fields: list[str]) -> dict[str, Any]:
    return {
        "kind": "entity",
        "id": name,
        "physical_name": name,
        "source": "shop",
        "grain": f"one row per {name} row",
        "class": "data",
        "status": "reviewed",
        "keys": {"primary": [fields[0]]},
        "evidence": [f"ev-{name}"],
        "fields": [
            {"name": f, "type": "integer", "nullable": i > 0, "meaning": f"The {f}."}
            for i, f in enumerate(fields)
        ],
        "records": [
            {
                "id": f"ev-{name}",
                "source": "shop",
                "pin": "postgres:shop@2026-10-01",
                "quote": f"table {name}",
                "status": "confirmed",
                "read_on": "2026-10-01",
            }
        ],
    }


MODEL = {
    "customers": _entity("customers", ["customer_id", "email", "created"]),
    "orders": _entity("orders", ["order_id", "customer_id", "total", "note"]),
    "legacy_carts": _entity("legacy_carts", ["id"]),
}


def test_every_drift_kind_is_classified() -> None:
    entities = {k: Entity.model_validate(v) for k, v in MODEL.items()}
    items = drift(_snap("shop@2026-10-01.yaml"), _snap("shop@2026-11-01.yaml"), entities)
    got = [(i.object, i.field, i.kind, i.drift_class) for i in items]
    assert got == [
        ("customers", "created", "type_class_change", "changed_fact"),
        ("customers", "email", "type_text_change", "no_effect"),
        ("customers", "phone_hash", "new_field", "new_fact"),
        ("legacy_carts", "", "dropped_object", "lost_fact"),
        ("orders", "", "constraint_change", "changed_fact"),
        ("orders", "note", "dropped_field", "lost_fact"),
        ("orders", "total", "nullability_change", "changed_fact"),
        ("refunds", "", "new_object", "new_fact"),
        ("tmp_import", "", "dropped_object", "no_effect"),
    ]


def test_first_sync_without_previous_snapshot() -> None:
    entities = {"orders": Entity.model_validate(MODEL["orders"])}
    items = drift(None, _snap("shop@2026-11-01.yaml"), entities)
    assert [(i.object, i.kind, i.drift_class) for i in items] == [
        ("customers", "new_object", "new_fact"),
        ("orders", "new_object", "no_effect"),
        ("refunds", "new_object", "new_fact"),
    ]


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    assert (
        runner.invoke(
            app, ["init", str(root), "--profile", "retail", "--anchor", "customers"]
        ).exit_code
        == 0
    )
    source = {
        "kind": "source",
        "id": "shop",
        "title": "Shop",
        "source_kind": "warehouse",
        "access_mode": "export_file",
        "adapter": "export",
        "engine": "postgres",
        "location": "shop",
    }
    (root / "sources" / "shop.yaml").write_text(dump(source), encoding="utf-8")
    for name, doc in MODEL.items():
        (root / "physical" / "entities" / f"{name}.yaml").write_text(dump(doc), encoding="utf-8")
    trigger = {
        "kind": "trigger",
        "id": "shop-moved",
        "event": "source_pin_moved",
        "follow_up": "Re-read evidence pinned to the old version.",
    }
    (root / "maintenance" / "shop-moved.yaml").write_text(dump(trigger), encoding="utf-8")
    for name in ("shop@2026-10-01.yaml", "shop@2026-11-01.yaml"):
        shutil.copy(FIXTURES / name, root / "sources" / "snapshots" / name)
    assert runner.invoke(app, ["project", "--root", str(root)]).exit_code == 0
    return root


def test_sync_writes_drafts_findings_trigger_and_report(tmp_path: Path) -> None:
    root = _model(tmp_path)
    result = runner.invoke(app, ["sync", "--root", str(root), "--source", "shop"])
    assert result.exit_code == 0, result.output
    assert result.output.startswith("changed_fact 3, lost_fact 2, new_fact 2, no_effect 2;")
    drafts = sorted(p.name for p in (root / "drafts" / "shop" / "entities").glob("*.yaml"))
    assert drafts == ["customers.yaml", "refunds.yaml"]
    assert not (root / "physical" / "entities" / "refunds.yaml").exists()
    findings = {
        load(p).data["extensions"]["sync_key"]: load(p).data["id"]
        for p in (root / "registers" / "findings").glob("F-*.yaml")
    }
    assert findings == {
        "dropped_object:legacy_carts": "F-0001",
        "dropped_field:orders.note": "F-0002",
    }
    fired = load(root / "maintenance" / "shop-moved.yaml").data["fired"]
    assert fired == [
        {
            "on": "2026-11-01",
            "detail": "shop moved from postgres:shop@2026-10-01 to postgres:shop@2026-11-01",
        }
    ]
    report = (root / "generated" / "drift-shop.md").read_text(encoding="utf-8")
    assert report == (FIXTURES / "expected-drift-shop.md").read_text(encoding="utf-8")
    assert run_gate(root).failed == ["triggers"]


def test_sync_is_idempotent(tmp_path: Path) -> None:
    root = _model(tmp_path)
    runner.invoke(app, ["sync", "--root", str(root), "--source", "shop"])
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    again = runner.invoke(app, ["sync", "--root", str(root), "--source", "shop"])
    assert again.exit_code == 0 and "; 0 files written" in again.output
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_follow_up_clears_the_triggers_stage(tmp_path: Path) -> None:
    root = _model(tmp_path)
    runner.invoke(app, ["sync", "--root", str(root), "--source", "shop"])
    path = root / "maintenance" / "shop-moved.yaml"
    doc = load(path).data
    doc["fired"][0]["follow_up_ref"] = "F-0001"
    path.write_text(dump(doc), encoding="utf-8")
    assert "triggers" not in run_gate(root).failed

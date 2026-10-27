import copy
import shutil
from pathlib import Path
from typing import Any

import pytest

from factmodel.core import derived
from factmodel.gate.runner import FAIL, PASS, SKIP, run_gate, stage_specs
from factmodel.model.loader import load_model
from tests.model.helpers import dump

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "gate"
PLAN_STAGES = [
    "yaml",
    "schema",
    "references",
    "evidence",
    "derived-not-authored",
    "projection",
    "scope",
    "layers",
    "registers",
    "triggers",
    "generated-fresh",
    "privacy",
]


def _copy_clean(tmp_path: Path) -> Path:
    target = tmp_path / "model"
    shutil.copytree(FIXTURES / "clean", target)
    return target


def _write(root: Path, rel: str, doc: dict[str, Any]) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump(doc), encoding="utf-8")


def _project(root: Path) -> None:
    values = derived.derive_model(load_model(root))
    assert values is not None
    derived.write(root, derived.render(values))
    derived.write_files(root, derived.layer_files(load_model(root)))


def test_stage_list_matches_the_plan() -> None:
    assert [s.name for s in stage_specs() if s.enabled] == PLAN_STAGES


def test_clean_fixture_passes_every_stage() -> None:
    report = run_gate(FIXTURES / "clean")
    assert [s.verdict for s in report.stages] == [PASS] * len(PLAN_STAGES)
    assert list(report.lines())[-1] == "gate: pass"


@pytest.mark.parametrize("stage", PLAN_STAGES)
def test_fixture_fails_its_stage_and_only_it(stage: str) -> None:
    report = run_gate(FIXTURES / stage / "fail")
    assert report.failed == [stage]
    assert all(s.verdict in (PASS, SKIP) for s in report.stages if s.name != stage)
    failed = next(s for s in report.stages if s.name == stage)
    assert all(i.hint and i.line >= 1 for i in failed.issues)


def test_single_stage(tmp_path: Path) -> None:
    report = run_gate(FIXTURES / "privacy" / "fail", "privacy")
    assert [(s.name, s.verdict) for s in report.stages] == [("privacy", FAIL)]
    with pytest.raises(ValueError, match="unknown or disabled stage"):
        run_gate(FIXTURES / "clean", "lineage")


def test_blocked_stages_are_skipped() -> None:
    report = run_gate(FIXTURES / "schema" / "fail")
    verdicts = {s.name: s.verdict for s in report.stages}
    assert verdicts["projection"] == verdicts["scope"] == verdicts["generated-fresh"] == SKIP
    assert list(report.lines())[-1] == "gate: fail"


def _layer(entity: str) -> dict[str, Any]:
    return {
        "kind": "layer",
        "id": "sales",
        "purpose": "Sales by day.",
        "consumer": "sales-sql",
        "status": "draft",
        "entities": [
            {"entity": entity, "current_row_rule": None},
            {"entity": "orders", "current_row_rule": None},
            {"entity": "users", "current_row_rule": None},
        ],
        "joins": ["orders.placed-by"],
        "concepts": [{"id": "day", "meaning": "The day.", "field": f"{entity}.id"}],
    }


CONSUMER = {"kind": "consumer", "id": "sales-sql", "meaning": "Sales SQL.", "layers": ["sales"]}


def _unreachable_entity() -> dict[str, Any]:
    return {
        "kind": "entity",
        "id": "daily_sales",
        "physical_name": "shop.daily_sales",
        "grain": "one row per day",
        "class": "data",
        "status": "draft",
        "keys": {"primary": ["id"]},
        "evidence": ["ev-confirmed"],
        "fields": [
            {"name": "id", "type": "INT64", "nullable": False, "meaning": "Day."},
            {"name": "orders_id", "type": "INT64", "nullable": True, "meaning": "Order."},
        ],
        "relationships": [
            {
                "key": "from-orders",
                "to": "orders",
                "join": "daily_sales.orders_id = orders.id",
                "meaning": "Summed from orders.",
                "mechanism": "derivation",
                "cardinality": "one_to_many",
                "evidence": ["ev-confirmed"],
            }
        ],
    }


def test_unreachable_layer_entity_needs_an_owner_decision(tmp_path: Path) -> None:
    root = _copy_clean(tmp_path)
    _write(root, "physical/entities/daily_sales.yaml", _unreachable_entity())
    _write(root, "semantic/sales/layer.yaml", _layer("daily_sales"))
    _write(root, "semantic/sales/consumer.yaml", CONSUMER)
    _project(root)
    report = run_gate(root)
    assert report.failed == ["scope"]
    issue = next(s for s in report.stages if s.name == "scope").issues[0]
    assert issue.code == "unreachable" and "daily_sales" in issue.message
    decision = {
        "kind": "decision",
        "id": "D-0001",
        "title": "Daily sales are lineage only",
        "status": "accepted",
        "date": "2026-11-05",
        "context": "daily_sales is computed from orders.",
        "decision": "The layer may use it without a path to the anchor.",
        "about": ["daily_sales"],
    }
    _write(root, "registers/decisions/D-0001.yaml", decision)
    assert run_gate(root).passed


def test_reused_register_id_fails_registers(tmp_path: Path) -> None:
    root = _copy_clean(tmp_path)
    finding = {
        "kind": "finding",
        "id": "F-0001",
        "title": "x",
        "status": "open",
        "opened_on": "2026-11-01",
        "description": "x",
    }
    _write(root, "registers/findings/a.yaml", finding)
    _write(root, "registers/findings/b.yaml", copy.deepcopy(finding))
    report = run_gate(root)
    assert report.failed == ["registers"]


def test_answer_with_retracted_evidence_fails_registers(tmp_path: Path) -> None:
    root = _copy_clean(tmp_path)
    escalation = {
        "kind": "escalation",
        "id": "E-0001",
        "question": "Are cancelled orders kept?",
        "status": "answered",
        "asked_on": "2026-11-01",
        "answer": {
            "text": "Yes.",
            "source": "shop-db",
            "answered_on": "2026-11-02",
            "evidence": ["ev-retracted"],
        },
    }
    _write(root, "registers/escalations/E-0001.yaml", escalation)
    report = run_gate(root)
    assert set(report.failed) == {"registers", "evidence"}


def test_hazards_are_not_issues(tmp_path: Path) -> None:
    root = _copy_clean(tmp_path)
    hazard = {
        "kind": "hazard",
        "id": "H-0001",
        "title": "Cancelled orders stay",
        "status": "active",
        "description": "A cancelled order keeps its row.",
        "applies_to": ["orders"],
        "evidence": ["ev-confirmed"],
    }
    _write(root, "registers/hazards/H-0001.yaml", hazard)
    assert run_gate(root).passed


def test_extra_generated_file_fails_generated_fresh(tmp_path: Path) -> None:
    root = _copy_clean(tmp_path)
    (root / "generated" / "notes.tsv").write_text("x\n", encoding="utf-8")
    assert run_gate(root).failed == ["generated-fresh"]

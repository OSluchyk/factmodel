"""Gate stage `layers` (D-019): each rule fails on its own, starting from a valid layer."""

import json
import shutil
from pathlib import Path

import pytest

from factmodel.gate.runner import run_gate

CASE = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases" / "layer-minimal"
LAYER = "semantic/employment/layer.yaml"


def _model(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    shutil.copytree(CASE, root, ignore=shutil.ignore_patterns("expected"))
    return root


def _codes(root: Path) -> list[str]:
    report = run_gate(root)
    stage = next(s for s in report.stages if s.name == "layers")
    assert report.failed in ([], ["layers"]), report.failed
    return [i.code for i in stage.issues]


def _edit(root: Path, old: str, new: str, rel: str = LAYER) -> None:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_the_minimal_layer_passes(tmp_path: Path) -> None:
    assert _codes(_model(tmp_path)) == []


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("consumer: employment-sql", "consumer: other-sql", "missing_consumer"),
        ("- entity: areas\n  current_row_rule: null\n", "", "join_outside_layer outside_layer"),
        ("field: areas.area_code", "field: industries.industry_code", "outside_layer"),
        ("expression: employment.employment", "expression: employment.nothing", "bad_expression"),
        ("expression: employment.employment", "expression: SUM(employment", "bad_expression"),
        (
            "  current_row_rule: null\n- entity: areas",
            "  current_row_rule: year > 0\n- entity: areas",
            "current_row_rule",
        ),
        ("  suppressed: not_applicable", "  suppressed: exclude", "missing_companion"),
        (
            "  hazards: [H-0001]\nhazards",
            "  hazards: [H-0001]\n  formula_source: ev-none\nhazards",
            "missing_evidence",
        ),
        (
            "- entity: employment\n  current_row_rule: null\n",
            "- entity: employment\n  current_row_rule: null\n  default_filters: [nothing]\n",
            "unknown_concept",
        ),
        ("status: draft", "status: reviewed", "not_accepted"),
    ],
)
def test_each_rule_fails_alone(tmp_path: Path, old: str, new: str, code: str) -> None:
    root = _model(tmp_path)
    _edit(root, old, new)
    assert _codes(root) == code.split()


def test_a_measure_hazard_must_be_listed_by_the_layer(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _edit(root, "hazards: [H-0001]\n", "", rel=LAYER)  # the layer-level list (last line)
    assert sorted(_codes(root)) == ["measure_hazard", "missing_hazard"]


def test_reviewed_with_an_accepted_run_passes(tmp_path: Path) -> None:
    root = _model(tmp_path)
    _edit(root, "status: draft", "status: reviewed")
    (root / "equivalence").mkdir()
    (root / "equivalence" / "accepted.json").write_text(
        json.dumps({"layers": {"employment": {}}}), encoding="utf-8"
    )
    assert _codes(root) == []


@pytest.mark.parametrize(
    "rollup",
    [
        "{hierarchy: employment.in-area, field: nothing}",
        "{hierarchy: employment.in-area, field: area_code, suppressed: area}",
    ],
)
def test_a_bad_rollup_fails(tmp_path: Path, rollup: str) -> None:
    root = _model(tmp_path)
    _edit(
        root, "  hazards: [H-0001]\nhazards", f"  hazards: [H-0001]\n  rollups: [{rollup}]\nhazards"
    )
    assert _codes(root) == ["bad_rollup"]

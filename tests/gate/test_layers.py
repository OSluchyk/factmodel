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
        json.dumps({"layers": {"employment": {"proven": True}}}), encoding="utf-8"
    )
    # D-023: an accepted run without coverage no longer proves a reviewed layer
    assert _codes(root) == ["no_coverage"]
    tested = ["entity employment", "entity areas", "join employment.in-area", "concept area"]
    coverage = {"tested": [*tested, "measure (weak) employment"]}
    (root / "equivalence" / "accepted.json").write_text(
        json.dumps({"layers": {"employment": {"proven": True, "coverage": coverage}}}),
        encoding="utf-8",
    )
    assert _codes(root) == []
    (root / "equivalence" / "accepted.json").write_text(
        json.dumps({"layers": {"employment": {"proven": False}}}), encoding="utf-8"
    )
    assert _codes(root) == ["not_accepted"]


D023 = {
    "layer-untested": [],
    "layer-untested-unknown": ["unknown_untested", "unknown_untested"],
    "layer-untested-no-coverage": ["no_coverage"],
    "layer-untested-missing-reason": ["missing_reason"],
    "layer-untested-stale": ["stale_untested"],
}


@pytest.mark.parametrize("case", sorted(D023))
def test_each_d023_code_fails_on_its_hard_case(case: str) -> None:
    root = CASE.parent / case
    assert _codes(root) == D023[case]


def test_a_predicate_concept_needs_no_reason_and_its_entry_is_never_stale(tmp_path: Path) -> None:
    root = tmp_path / "model"
    shutil.copytree(CASE.parent / "layer-untested", root)
    _edit(
        root,
        "concepts:\n",
        "concepts:\n- id: recent\n  meaning: After 2000.\n  predicate: employment.year > 2000\n",
    )
    assert _codes(root) == []  # not tested, not enforced
    _edit(
        root,
        "untested:\n",
        "untested:\n- kind: concept\n  id: recent\n  reason: Written with another form.\n",
    )
    accepted = root / "equivalence" / "accepted.json"
    data = json.loads(accepted.read_text(encoding="utf-8"))
    data["layers"]["employment"]["coverage"]["tested"].append("concept recent (as written)")
    accepted.write_text(json.dumps(data), encoding="utf-8")
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


def test_a_hand_edited_join_table_fails_derived_not_authored(tmp_path: Path) -> None:
    root = _model(tmp_path)
    table = root / "semantic" / "employment" / "generated" / "joins.tsv"
    table.write_text(table.read_text(encoding="utf-8") + "extra\trow\n", encoding="utf-8")
    report = run_gate(root)
    assert report.failed == ["derived-not-authored"]
    issue = next(s for s in report.stages if s.name == "derived-not-authored").issues[0]
    assert issue.code == "derived_file"


@pytest.mark.parametrize(
    ("table", "code"),
    [
        ("{columns: [kind, code], rows: [[county, '7']]}", None),
        ("{columns: [kind, code], rows: [[county]]}", "bad_values_table"),
        ("{columns: [area_code, area_title], entity: areas}", None),
        ("{columns: [nothing], entity: areas}", "bad_values_table"),
        ("{columns: [industry_code], entity: industries}", "outside_layer"),
    ],
)
def test_values_tables(tmp_path: Path, table: str, code: str | None) -> None:
    root = _model(tmp_path)
    concept = f"- id: kinds\n  meaning: A lookup table.\n  values_table: {table}\nmeasures:"
    _edit(root, "measures:", concept)
    assert _codes(root) == ([code] if code else [])


def test_a_draft_layer_is_exempt_from_the_reviewed_checks(tmp_path: Path) -> None:
    # D-023 rule 4 binds reviewed layers only; rule 5 binds every layer
    root = tmp_path / "model"
    shutil.copytree(CASE.parent / "layer-untested-missing-reason", root)
    assert _codes(root) == ["missing_reason"]
    _edit(root, "status: reviewed", "status: draft")
    assert _codes(root) == []  # accepted and proven, concept area untested, no entry
    accepted = root / "equivalence" / "accepted.json"
    data = json.loads(accepted.read_text(encoding="utf-8"))
    del data["layers"]["employment"]["coverage"]
    accepted.write_text(json.dumps(data), encoding="utf-8")
    assert _codes(root) == []  # no coverage: still nothing for a draft
    _edit(
        root,
        "untested:\n",
        "untested:\n- kind: measure\n  id: employment\n  reason: A passing item uses it.\n"
        "- kind: entity\n  id: industries\n  reason: Not in the layer.\n",
    )
    assert _codes(root) == ["unknown_untested"]  # never stale_untested for a draft

"""A profile without a subject (D-015) and join expressions (D-017)."""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.core.derived import derive_model
from factmodel.io.yaml_strict import load
from factmodel.model import joins
from factmodel.model.loader import LoadIssue, inspect_model, load_model

CASES = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases"
runner = CliRunner()


def _copy(tmp_path: Path, case: str) -> Path:
    root = tmp_path / case
    shutil.copytree(CASES / case, root, ignore=shutil.ignore_patterns("expected"))
    return root


def _edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def _codes(root: Path) -> list[str]:
    return [i.code for i in inspect_model(root).issues]


def _only(root: Path, code: str) -> LoadIssue:
    issues = list(inspect_model(root).issues)
    assert [i.code for i in issues] == [code], [str(i) for i in issues]
    assert issues[0].stage == "references"
    return issues[0]


# D-015 -------------------------------------------------------------------------------------


def test_a_model_without_subject_loads_and_scopes_nothing(tmp_path: Path) -> None:
    model = load_model(_copy(tmp_path, "no-subject"))
    assert model.profile is not None and model.profile.subject is None
    assert model.config is not None and model.config.anchor_entity is None
    derived = derive_model(model)
    assert derived is not None
    assert {r.subject_scope for r in derived.scope.rows.values()} == {"none"}
    assert {r.reachable for r in derived.scope.rows.values()} == {None}
    assert derived.scope.rejections == ()


def test_anchor_without_subject_is_an_error(tmp_path: Path) -> None:
    root = _copy(tmp_path, "no-subject")
    _edit(
        root / "factmodel.yaml",
        "profile: statistics\n",
        "profile: statistics\nanchor_entity: employment\n",
    )
    _only(root, "anchor_without_subject")


def test_subject_without_anchor_is_an_error(tmp_path: Path) -> None:
    _only(_copy(tmp_path, "subject-profile-without-anchor"), "missing_anchor")


def test_anchor_reference_without_subject_is_an_error(tmp_path: Path) -> None:
    root = _copy(tmp_path, "no-subject")
    _edit(
        root / "physical/entities/employment.yaml",
        "evidence:\n- ev-confirmed\nfields:",
        "anchor_reference:\n  field: area_code\n  evidence:\n  - ev-confirmed\n"
        "evidence:\n- ev-confirmed\nfields:",
    )
    _only(root, "no_subject")


def test_scope_admission_without_subject_is_an_error(tmp_path: Path) -> None:
    root = _copy(tmp_path, "no-subject")
    _edit(
        root / "physical/entities/employment.yaml",
        "  cardinality: many_to_one\n  evidence:",
        "  cardinality: many_to_one\n  scope_admission:\n    basis: unique_target\n"
        "    evidence:\n    - ev-confirmed\n  evidence:",
    )
    _only(root, "no_subject")


def test_subject_facets_need_a_subject(tmp_path: Path) -> None:
    root = _copy(tmp_path, "no-subject")
    _edit(root / "factmodel.yaml", "profile: statistics", "profile: local")
    (root / "profiles/local").mkdir(parents=True)
    (root / "profiles/local/profile.yaml").write_text(
        "kind: profile\nid: local\nlabels: [scoped, other]\nrules:\n"
        "  - when: {any_end_subject_scoped: true}\n    label: scoped\n"
        "  - when: {all_ends_match: [{subject_scoped: false}]}\n    label: other\n",
        encoding="utf-8",
    )
    assert _codes(root) == ["subject_facet", "subject_facet"]


def test_init_with_a_profile_without_subject_writes_no_anchor(tmp_path: Path) -> None:
    root = tmp_path / "stats"
    result = runner.invoke(app, ["init", str(root), "--profile", "statistics"])
    assert result.exit_code == 0, result.output
    config = load(root / "factmodel.yaml").data
    assert "anchor_entity" not in config
    assert config["treat_synthetic_as_representative"] is False
    checked = runner.invoke(app, ["check", "--root", str(root)])
    assert checked.exit_code == 0, checked.output
    refused = runner.invoke(
        app, ["init", str(tmp_path / "other"), "--profile", "statistics", "--anchor", "x"]
    )
    assert refused.exit_code == 1
    assert "names no subject" in refused.output


# D-017 -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("join", "message"),
    [
        ("substr(areas.area_fips, 1, 2 = areas.area_fips", "cannot parse"),
        ("area_fips = areas.area_fips", "must be <entity>.<field>"),
        ("(SELECT 1) = areas.area_fips", "not a query"),
        ("concat(other.area_fips, '000') = areas.area_fips", "must use"),
        ("concat(areas.nothing, '000') = areas.area_fips", "has no field"),
        ("areas.area_fips IN ('a') AND areas.area_fips = areas.area_fips", "comparisons"),
    ],
)
def test_bad_expression_joins_are_reported(tmp_path: Path, join: str, message: str) -> None:
    root = _copy(tmp_path, "expression-join")
    path = root / "physical/entities/areas.yaml"
    old = next(line for line in path.read_text().splitlines() if line.startswith("  join:"))
    _edit(path, old, f'  join: "{join}"')
    issues = list(inspect_model(root).issues)
    assert issues and all(i.stage == "references" for i in issues), [str(i) for i in issues]
    assert any(message in i.message for i in issues), [str(i) for i in issues]


def test_parts_sort_conjuncts_by_end() -> None:
    split = joins.parts(
        "concat(substr(a.code, 1, 2), '000') = a.code AND substr(a.code, 3, 3) <> '000'", "a", "a"
    )
    assert [(left.sql(), right.sql()) for left, right in split.pairs] == [
        ("CONCAT(SUBSTRING(a.code, 1, 2), '000')", "a.code")
    ]
    assert [f.sql() for f in split.source_filters] == ["SUBSTRING(a.code, 3, 3) <> '000'"]
    negated = joins.parts("a.code = a.parent AND a.change IS NOT NULL", "a", "a")
    assert [f.sql() for f in negated.source_filters] == ["NOT a.change IS NULL"]
    on = joins.condition("a.code = a.parent AND a.change IS NOT NULL", "a", "a", "s", "t")
    assert on.sql() == "s.code = t.parent AND NOT s.change IS NULL"
    other = joins.parts("b.y = a.x AND a.z > b.w AND b.k = 1", "a", "b")
    assert [(left.sql(), right.sql()) for left, right in other.pairs] == [("a.x", "b.y")]
    assert [o.sql() for o in other.other] == ["a.z > b.w"]
    assert [f.sql() for f in other.target_filters] == ["b.k = 1"]


@pytest.mark.parametrize(
    ("join", "unique"),
    [
        ("concat(substr(a.code, 1, 2), '000') = b.code", True),
        ("concat(substr(a.code, 1, 2), '000') = b.code AND substr(a.code, 3, 3) <> '000'", True),
        ("substr(a.code, 1, 2) = substr(b.code, 1, 2)", False),
        ("a.code = b.code AND a.x > b.y", False),
        ("a.x = b.other", False),
    ],
)
def test_unique_target_needs_a_key_on_the_target_side(join: str, unique: bool) -> None:
    assert joins.unique_right_side(join, "a", "b", [["code"], []]) is unique


def test_unique_target_on_a_non_key_expression_is_rejected() -> None:
    from factmodel.core.scope import compute_scope

    model = load_model(CASES / "no-subject")
    entities = dict(model.entities)
    rel = entities["employment"].relationships[0]
    data = rel.model_dump(by_alias=True, exclude_none=True)
    data["join"] = "substr(employment.area_code, 1, 2) = substr(areas.area_code, 1, 2)"
    data["scope_admission"] = {"basis": "unique_target", "evidence": ["ev-confirmed"]}
    admitted = type(rel).model_validate(data)
    employment = entities["employment"]
    entities["employment"] = employment.model_copy(
        update={"relationships": [admitted, *employment.relationships[1:]]}
    )
    result = compute_scope(entities, model.evidence, "areas")
    assert [(r.fact, r.reason) for r in result.rejections] == [
        ("employment.in-area", "reference_end")
    ]
    areas = entities["areas"].model_copy(update={"class_": "data"})
    result = compute_scope({**entities, "areas": areas}, model.evidence, "areas")
    assert [(r.fact, r.reason) for r in result.rejections] == [
        ("employment.in-area", "non_unique_target")
    ]

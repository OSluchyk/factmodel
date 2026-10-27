"""A discriminator on a single target, and unresolved relationships without a join (round 19,
additive under D-018)."""

import shutil
from pathlib import Path

from factmodel.model.loader import inspect_model, load_model

CASES = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases"
OLD = (
    "- key: in-industry\n  to: industries\n"
    "  join: employment.industry_code = industries.industry_code\n"
)


def _copy(tmp_path: Path) -> Path:
    root = tmp_path / "model"
    shutil.copytree(CASES / "no-subject", root, ignore=shutil.ignore_patterns("expected"))
    return root


def _edit(root: Path, new: str) -> None:
    path = root / "physical" / "entities" / "employment.yaml"
    text = path.read_text(encoding="utf-8")
    assert OLD in text
    path.write_text(text.replace(OLD, new), encoding="utf-8")


def test_single_target_discriminator_loads(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(root, OLD + "  discriminator: year\n")
    rel = load_model(root).entities["employment"].relationships[1]
    assert (rel.key, rel.discriminator) == ("in-industry", "year")


def test_discriminator_must_be_a_source_field(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(root, OLD + "  discriminator: industry_title\n")
    issues = list(inspect_model(root).issues)
    assert [(i.stage, i.code) for i in issues] == [("references", "missing_field")]


def test_unresolved_link_may_omit_its_join(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(
        root, "- key: in-industry\n  to: industries\n  status: unresolved\n  missing: not known\n"
    )
    rel = load_model(root).entities["employment"].relationships[1]
    assert rel.join is None and rel.status == "unresolved"


def test_unresolved_link_without_join_still_checks_its_target(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(root, "- key: in-industry\n  to: sectors\n  status: unresolved\n  missing: not known\n")
    issues = list(inspect_model(root).issues)
    assert [(i.stage, i.code) for i in issues] == [("references", "missing_entity")]


def test_resolved_link_without_join_is_a_schema_error(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    _edit(root, "- key: in-industry\n  to: industries\n")
    issues = list(inspect_model(root).issues)
    assert [(i.stage, i.code) for i in issues] == [("schema", "schema"), ("references", "bad_join")]

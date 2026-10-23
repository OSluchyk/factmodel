import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from factmodel import vocabulary
from factmodel.io.yaml_strict import load
from factmodel.schemas import build

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "schemas"
EXPECT = re.compile(r"^# expect: (?P<path>\S+)$", re.MULTILINE)

KINDS = [*vocabulary.load()["file_kind"], "snapshot"]
VALID = sorted(FIXTURES.glob("*/valid/*.yaml"))
INVALID = sorted(FIXTURES.glob("*/invalid/*.yaml"))


def _id(path: Path) -> str:
    return str(path.relative_to(FIXTURES))


def _validator(kind: str) -> Draft202012Validator:
    return Draft202012Validator(build.schema_for(kind))


def test_committed_schemas_equal_fresh_render() -> None:
    assert build.stale_files(ROOT / "schemas") == []


@pytest.mark.parametrize("kind", KINDS)
def test_schema_is_valid_draft_2020_12(kind: str) -> None:
    Draft202012Validator.check_schema(build.schema_for(kind))


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_has_fixtures(kind: str) -> None:
    assert list((FIXTURES / kind / "valid").glob("*.yaml")), kind
    assert len(list((FIXTURES / kind / "invalid").glob("*.yaml"))) >= 3, kind


def test_one_invalid_entity_fixture_per_derived_key() -> None:
    names = {p.stem for p in (FIXTURES / "entity" / "invalid").glob("derived-key-*.yaml")}
    expected = {f"derived-key-{v.replace('_', '-')}" for v in vocabulary.load()["derived_value"]}
    assert names == expected


@pytest.mark.parametrize("path", VALID, ids=_id)
def test_valid_fixture_passes(path: Path) -> None:
    kind = path.parts[-3]
    doc = load(path).data
    assert doc["kind"] == kind
    errors = [f"{e.json_path}: {e.message}" for e in _validator(kind).iter_errors(doc)]
    assert errors == []


@pytest.mark.parametrize("path", INVALID, ids=_id)
def test_invalid_fixture_fails_once_at_expected_path(path: Path) -> None:
    kind = path.parts[-3]
    match = EXPECT.search(path.read_text(encoding="utf-8"))
    assert match, "invalid fixture needs a '# expect: <json path>' line"
    errors = list(_validator(kind).iter_errors(load(path).data))
    assert [e.json_path for e in errors] == [match.group("path")], [e.message for e in errors]


def test_enumerations_come_from_the_vocabulary() -> None:
    entity = build.schema_for("entity")
    assert entity["properties"]["class"]["enum"] == list(vocabulary.load()["entity_class"])
    assert entity["properties"]["status"]["enum"] == list(vocabulary.load()["review_status"])


def test_unknown_vocabulary_block_fails() -> None:
    with pytest.raises(build.SchemaBuildError, match="unknown vocabulary block"):
        build._expand({"$vocab": "no_such_block"}, vocabulary.load(), "t.yaml")


def test_const_outside_its_block_fails() -> None:
    with pytest.raises(build.SchemaBuildError, match="not in vocabulary block"):
        build._expand({"$const": "file_kind:table"}, vocabulary.load(), "t.yaml")


def test_check_mode_reports_stale_file(tmp_path: Path) -> None:
    build.write(tmp_path)
    assert build.main([str(tmp_path), "--check"]) == 0
    (tmp_path / "entity.schema.json").write_text("{}\n", encoding="utf-8")
    assert build.main([str(tmp_path), "--check"]) == 1

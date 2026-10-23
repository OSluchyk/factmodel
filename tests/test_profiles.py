from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from factmodel.io.yaml_strict import load
from factmodel.model.types import Profile
from factmodel.schemas.build import schema_for
from tests.core.helpers import vector

PROFILES = sorted((Path(__file__).resolve().parents[1] / "profiles").glob("*/profile.yaml"))


@pytest.mark.parametrize("path", PROFILES, ids=lambda p: p.parent.name)
def test_profile_matches_schema(path: Path) -> None:
    data = load(path).data
    assert data["id"] == path.parent.name
    assert list(Draft202012Validator(schema_for("profile")).iter_errors(data)) == []
    profile = Profile.model_validate(data)
    assert {rule.label for rule in profile.rules} <= set(profile.labels)


def test_retail_profile_rules_match_the_vectors() -> None:
    retail = Profile.model_validate(load(PROFILES[0]).data)
    files = vector("projection", "rule-lineage")["input"]["files"]
    in_vector = Profile.model_validate(next(f for f in files if f["kind"] == "profile"))
    assert [(r.when, r.label) for r in retail.rules] == [(r.when, r.label) for r in in_vector.rules]
    assert retail.subject == in_vector.subject == "customer"

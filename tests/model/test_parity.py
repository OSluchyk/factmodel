"""The typed models accept exactly what the JSON Schemas accept, on the schema fixtures."""

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from factmodel import vocabulary
from factmodel.io.yaml_strict import load
from factmodel.model.types import FILE_MODELS
from factmodel.schemas.build import schema_for

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "schemas"
ALL = sorted(FIXTURES.glob("*/*/*.yaml"))


def test_one_model_per_schema() -> None:
    assert set(FILE_MODELS) == {*vocabulary.load()["file_kind"], "snapshot"}


@pytest.mark.parametrize("path", ALL, ids=lambda p: str(p.relative_to(FIXTURES)))
def test_model_agrees_with_schema(path: Path) -> None:
    kind = path.parts[-3]
    data = load(path).data
    schema_accepts = Draft202012Validator(schema_for(kind)).is_valid(data)
    try:
        FILE_MODELS[kind].model_validate(data)
        model_accepts = True
    except ValidationError:
        model_accepts = False
    assert model_accepts == schema_accepts == (path.parts[-2] == "valid")

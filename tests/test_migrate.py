"""``fact migrate``: report the schema version a model uses and whether it is read (WP2.3)."""

import shutil
from pathlib import Path

from typer.testing import CliRunner

from factmodel import __version__
from factmodel.cli import app
from factmodel.migrate import report
from factmodel.schemas.build import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_both_examples_are_compatible() -> None:
    for example in ("chinook", "qcew"):
        result = report(ROOT / "examples" / example)
        assert result.compatible, result.failing
        assert result.model_framework_version == "0.0.1"
        assert result.model_schema_version == SCHEMA_VERSION == "1.0.0"
        assert (result.framework_version, result.schema_version) == (__version__, SCHEMA_VERSION)
        assert result.difference() == "same"


def test_a_model_at_0_1_0_is_compatible_and_the_difference_is_named(tmp_path: Path) -> None:
    root = tmp_path / "model"
    shutil.copytree(ROOT / "examples" / "qcew", root)
    config = root / "factmodel.yaml"
    text = config.read_text(encoding="utf-8")
    config.write_text(text.replace("schema_version: 1.0.0", "schema_version: 0.1.0"), "utf-8")
    result = runner.invoke(app, ["migrate", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert "model schema_version: 0.1.0" in result.output
    assert "schema difference: 0.1.0 -> 1.0.0 (major)" in result.output
    assert "compatible: every model file validates" in result.output


def test_a_model_without_schema_version_is_named_as_such() -> None:
    result = report(ROOT / "tests" / "fixtures" / "hard-cases" / "no-subject")
    assert result.model_schema_version is None and result.compatible
    assert result.difference() == "not recorded (the model was written before schemas 1.0.0)"


def test_a_file_the_schemas_reject_is_listed(tmp_path: Path) -> None:
    root = tmp_path / "model"
    shutil.copytree(ROOT / "examples" / "qcew", root)
    path = root / "physical" / "entities" / "size_titles.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "unknown_key: 1\n", encoding="utf-8")
    result = runner.invoke(app, ["migrate", "--root", str(root)])
    assert result.exit_code == 1
    assert "not compatible: 1 file(s) do not validate" in result.output
    assert "  physical/entities/size_titles.yaml" in result.output


def test_migrate_changes_nothing(tmp_path: Path) -> None:
    root = tmp_path / "model"
    shutil.copytree(ROOT / "examples" / "chinook", root)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = runner.invoke(app, ["migrate", "--root", str(root)])
    assert result.exit_code == 0, result.output
    assert f"installed schemas: {SCHEMA_VERSION}" in result.output
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before

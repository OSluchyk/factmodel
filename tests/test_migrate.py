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
        assert (result.framework_version, result.schema_version) == (__version__, SCHEMA_VERSION)


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

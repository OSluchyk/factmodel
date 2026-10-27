"""A third-party adapter package, installed like an adopter's (docs/adapters/packaging.md)."""

from pathlib import Path

from typer.testing import CliRunner

from factmodel.adapters import registry
from factmodel.cli import app

runner = CliRunner()


def test_fact_adapters_lists_the_installed_package() -> None:
    result = runner.invoke(app, ["adapters"])
    assert result.exit_code == 0, result.output
    assert "csvdir  engines: csvdir  default dialects: csvdir=duckdb" in result.output.splitlines()
    assert registry.get("csvdir").name == "csvdir"


def test_fact_snapshot_runs_through_the_package(tmp_path: Path) -> None:
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "retail"]).exit_code == 0
    codes = root / "codes"
    codes.mkdir()
    (codes / "colours.csv").write_text("colour_code,colour_title\n1,red\n", encoding="utf-8")
    added = runner.invoke(
        app,
        [
            "source",
            "add",
            "--root",
            str(root),
            "--id",
            "codes",
            "--title",
            "Code lists",
            "--kind",
            "document",
            "--access-mode",
            "agent_read",
            "--engine",
            "csvdir",
            "--adapter",
            "csvdir",
            "--location",
            "codes",
        ],
    )
    assert added.exit_code == 0, added.output
    taken = runner.invoke(
        app, ["snapshot", "--root", str(root), "--source", "codes", "--date", "2026-10-27"]
    )
    assert taken.exit_code == 0, taken.output
    assert "sources/snapshots/codes@2026-10-27.yaml (1 objects)" in taken.output
    text = (root / "sources/snapshots/codes@2026-10-27.yaml").read_text(encoding="utf-8")
    assert "colour_title" in text and "red" not in text

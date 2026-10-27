"""The model-onboard skill, followed command by command, reproduces the Chinook drafts."""

import filecmp
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel import vocabulary
from factmodel.cli import app
from tests.examples.test_chinook import CHINOOK, _seed

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / "agent" / "skills"
NAMES = ["model-onboard", "entity-scaffold", "evidence-gather", "probe-write", "probe-intake"]
runner = CliRunner()


@pytest.mark.parametrize("name", NAMES)
def test_skill_has_front_matter_and_names_no_engine(name: str) -> None:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith(f"---\nname: {name}\ndescription: ")
    engines = set(vocabulary.load_maps()["engine_dialect"])
    words = set(re.findall(r"[a-z]+", text.lower()))
    assert not engines & words, engines & words


@pytest.mark.parametrize("name", NAMES)
def test_every_fact_command_a_skill_names_exists(name: str) -> None:
    text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
    for command in sorted(set(re.findall(r"`fact ([a-z-]+(?: [a-z]+)?)", text))):
        args = command.split()
        result = runner.invoke(app, [*args, "--help"])
        if result.exit_code != 0 and len(args) > 1:
            result = runner.invoke(app, [args[0], "--help"])
        assert result.exit_code == 0, f"{name}: fact {command}"


def test_init_copies_the_skills(tmp_path: Path) -> None:
    root = tmp_path / "m"
    assert runner.invoke(app, ["init", str(root), "--profile", "retail"]).exit_code == 0
    for name in NAMES:
        assert (root / ".claude" / "skills" / name / "SKILL.md").is_file()


def test_model_onboard_reproduces_the_committed_drafts(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    root = tmp_path / "chinook-model"
    assert runner.invoke(app, ["init", str(root), "--profile", "retail"]).exit_code == 0
    added = runner.invoke(
        app,
        [
            "source", "add", "--root", str(root), "--id", "chinook-sqlite",
            "--title", "Chinook on a local SQLite file", "--kind", "warehouse",
            "--access-mode", "agent_read", "--adapter", "sql", "--engine", "sqlite",
            "--location", "chinook", "--dsn-env", "FACT_DSN_CHINOOK_SQLITE",
        ],
    )  # fmt: skip
    assert added.exit_code == 0, added.output
    monkeypatch.setenv("FACT_DSN_CHINOOK_SQLITE", _seed().load_sqlite(tmp_path / "chinook.db"))
    args = ["--root", str(root), "--source", "chinook-sqlite"]
    assert runner.invoke(app, ["snapshot", *args, "--date", "2026-10-23"]).exit_code == 0
    assert runner.invoke(app, ["draft", *args]).exit_code == 0
    assert runner.invoke(app, ["check", "--root", str(root)]).exit_code == 0
    compared = filecmp.dircmp(
        root / "drafts" / "chinook-sqlite", CHINOOK / "drafts" / "chinook-sqlite"
    )
    assert not compared.diff_files and not compared.left_only and not compared.right_only
    entities = filecmp.dircmp(
        root / "drafts" / "chinook-sqlite" / "entities",
        CHINOOK / "drafts" / "chinook-sqlite" / "entities",
    )
    assert entities.same_files == sorted(entities.left_list) and len(entities.left_list) == 11

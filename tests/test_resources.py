"""Walks over shipped templates skip files the framework does not own (a Finder .DS_Store) and
never fail on a file that is not UTF-8."""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel import repo
from factmodel.cli import app
from factmodel.resources import framework_file, shipped_texts

ROOT = Path(__file__).resolve().parents[1]
FINDER = b"\x00\x00\x00\x01Bud1\x00\x00 \x00\xe5Ve\xcc"  # not UTF-8


def _skills_copy(tmp_path: Path) -> Path:
    skills = tmp_path / "skills"
    shutil.copytree(ROOT / "agent" / "skills", skills, ignore=shutil.ignore_patterns(".*"))
    (skills / ".DS_Store").write_bytes(FINDER)
    first = sorted(p for p in skills.iterdir() if p.is_dir())[0]
    (first / ".DS_Store").write_bytes(FINDER)
    (first / "notes.bin").write_bytes(FINDER)
    (first / ".notes.md").write_text("# a dot file in UTF-8\n", encoding="utf-8")
    return skills


def test_shipped_texts_skip_dot_files_and_non_utf8(tmp_path: Path) -> None:
    skills = _skills_copy(tmp_path)
    names = [name for name, _ in shipped_texts(skills)]
    assert names
    assert not [n for n in names if n.split("/")[-1].startswith(".")]
    assert not [n for n in names if n.endswith("notes.bin")]
    assert not [n for n in names if n.endswith(".notes.md")]  # skipped by name, not by bytes


def test_init_copies_skills_past_a_finder_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills = _skills_copy(tmp_path)

    def fake(*parts: str) -> object:
        return skills if parts == ("agent", "skills") else framework_file(*parts)

    monkeypatch.setattr(repo, "framework_file", fake)
    root = tmp_path / "model"
    result = CliRunner().invoke(app, ["init", str(root), "--profile", "statistics"])
    assert result.exit_code == 0, result.output
    copied = root / ".claude" / "skills"
    assert copied.is_dir()
    assert not list(copied.rglob(".DS_Store"))
    assert not list(copied.rglob("notes.bin"))
    assert not list(copied.rglob(".notes.md"))

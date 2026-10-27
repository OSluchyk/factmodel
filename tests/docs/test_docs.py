"""The documentation: the site builds strictly, the references cover the CLI and the schemas,
and the quickstart's commands produce what it promises."""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.docs.blocks import run

ROOT = Path(__file__).resolve().parents[2]


def _hooks():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(
        "site_hooks", ROOT / "docs" / "_site" / "hooks.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_reference_covers_every_command_with_an_example() -> None:
    text = _hooks().cli_reference()
    assert text.count("## fact ") == len(_hooks().EXAMPLES)
    assert text.count("```bash") == len(_hooks().EXAMPLES)


def test_schema_reference_has_a_page_per_file_kind() -> None:
    pages = _hooks().schema_pages()
    kinds = {p.name.removesuffix(".schema.json") for p in (ROOT / "schemas").glob("*.schema.json")}
    assert {f"reference/schemas/{k}.md" for k in kinds} | {"reference/schemas/index.md"} == set(
        pages
    )


@pytest.mark.skipif(shutil.which("mkdocs") is None, reason="mkdocs not installed")
def test_site_builds_strictly(tmp_path: Path) -> None:
    env = {**os.environ, "NO_MKDOCS_2_WARNING": "1"}
    done = subprocess.run(
        ["mkdocs", "build", "--strict", "--site-dir", str(tmp_path / "site")],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    assert (tmp_path / "site" / "reference" / "cli" / "index.html").is_file()
    decisions = (tmp_path / "site" / "decisions" / "index.html").read_text(encoding="utf-8")
    assert "D-021" in decisions and "Equivalence threshold" in decisions


@pytest.mark.skipif(shutil.which("sqlite3") is None, reason="sqlite3 CLI not installed")
def test_quickstart_commands_give_what_they_promise(tmp_path: Path) -> None:
    text = (ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if not k.startswith("FACT_")}
    outputs = run(text, tmp_path, env)
    assert "gate: pass" in outputs[0]
    assert (
        len(
            [
                line
                for block in text.split("```bash")[1:]
                for line in block.split("```")[0].splitlines()
                if line.strip()
            ]
        )
        == 10
    )

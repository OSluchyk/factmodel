"""Every example model carries the agent files `fact init` writes, identical to the framework's
(D-022): the skills under `.claude/skills/` and `AGENTS.md`. A skill is changed once, in
`agent/skills/`, and copied."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = sorted(p for p in (ROOT / "examples").iterdir() if (p / "factmodel.yaml").is_file())


def _tree(folder: Path) -> dict[str, str]:
    return {
        p.relative_to(folder).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(folder.rglob("*"))
        if p.is_file()
    }


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.name)
def test_example_skills_match_the_framework(example: Path) -> None:
    assert _tree(example / ".claude" / "skills") == _tree(ROOT / "agent" / "skills")


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.name)
def test_example_agents_file_matches_the_template(example: Path) -> None:
    expected = (ROOT / "agent" / "AGENTS.md").read_text(encoding="utf-8")
    assert (example / "AGENTS.md").read_text(encoding="utf-8") == expected
    assert (example / "agent" / "brief.md").is_file()
    assert (example / "agent" / "report.md").is_file()


def test_three_examples() -> None:
    assert [p.name for p in EXAMPLES] == ["chinook", "qcew", "tpch"]

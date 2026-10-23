"""Load the machine-readable enumerations from `spec/VOCABULARY.md`.

Every enumeration in the vocabulary is written as a fenced block that opens with
``yaml vocabulary:<name>`` and holds a YAML list of slugs. This module is the one
place that turns those blocks into Python data, so later schemas share one source.
"""

import re
from functools import cache
from importlib import resources
from pathlib import Path

from ruamel.yaml import YAML

SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")

_BLOCK = re.compile(
    r"^```yaml vocabulary:(?P<name>\S+)[ \t]*\n(?P<body>.*?)^```[ \t]*$",
    re.MULTILINE | re.DOTALL,
)

_REPO_COPY = Path(__file__).resolve().parents[2] / "spec" / "VOCABULARY.md"


class VocabularyError(ValueError):
    """A vocabulary block is malformed."""


def vocabulary_text() -> str:
    """Return the text of VOCABULARY.md, from the installed package or the source tree."""
    packaged = resources.files("plumbline").joinpath("VOCABULARY.md")
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    return _REPO_COPY.read_text(encoding="utf-8")


def parse_blocks(text: str) -> dict[str, list[str]]:
    """Parse every ``yaml vocabulary:<name>`` block in ``text``.

    Raises VocabularyError on a duplicate block name or a block that is not a list
    of strings. Value-level rules (slugs, duplicates) are checked by ``validate``.
    """
    yaml = YAML(typ="safe", pure=True)
    yaml.allow_duplicate_keys = False
    blocks: dict[str, list[str]] = {}
    for match in _BLOCK.finditer(text):
        name = match.group("name")
        if name in blocks:
            raise VocabularyError(f"duplicate vocabulary block: {name}")
        values = yaml.load(match.group("body"))
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise VocabularyError(f"block {name} must be a YAML list of strings")
        blocks[name] = values
    return blocks


def validate(blocks: dict[str, list[str]]) -> list[str]:
    """Return a list of problems: invalid block names, invalid or duplicate values."""
    problems: list[str] = []
    for name, values in blocks.items():
        if not SLUG.match(name):
            problems.append(f"block name is not a slug: {name}")
        seen: set[str] = set()
        for value in values:
            if not SLUG.match(value):
                problems.append(f"{name}: value is not a slug: {value!r}")
            if value in seen:
                problems.append(f"{name}: duplicate value: {value}")
            seen.add(value)
    return problems


@cache
def load() -> dict[str, tuple[str, ...]]:
    """Return every vocabulary block as an immutable tuple, keyed by block name."""
    blocks = parse_blocks(vocabulary_text())
    problems = validate(blocks)
    if problems:
        raise VocabularyError("; ".join(problems))
    return {name: tuple(values) for name, values in blocks.items()}

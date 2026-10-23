"""Strict YAML loading.

Duplicate keys fail, dates stay strings (a date is data for the schema to check, not a
Python object), and every node keeps its line and column so errors can point at it.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.constructor import RoundTripConstructor
from ruamel.yaml.error import MarkedYAMLError, YAMLError


class _Constructor(RoundTripConstructor):
    """Round-trip constructor that reads timestamps as plain strings."""


_Constructor.add_constructor("tag:yaml.org,2002:timestamp", _Constructor.construct_yaml_str)


class YamlLoadError(ValueError):
    """A YAML file cannot be read. Carries the file, a 1-based line and column, and a hint."""

    def __init__(self, file: str, line: int, column: int, message: str, hint: str) -> None:
        self.file = file
        self.line = line
        self.column = column
        self.message = message
        self.hint = hint
        super().__init__(f"{file}:{line}:{column}: {message} (fix: {hint})")


@dataclass(frozen=True)
class Document:
    """One loaded YAML document: plain data plus the positions of its nodes."""

    file: str
    data: Any
    tree: Any

    def position(self, location: Sequence[str | int]) -> tuple[int, int]:
        """Return the 1-based (line, column) of the node at ``location``.

        A missing node resolves to the deepest existing parent, so a "required key
        missing" error points at the object that lacks the key.
        """
        node = self.tree
        line, column = 1, 1
        for step in location:
            if isinstance(node, CommentedMap) and step in node:
                pos = node.lc.key(step)
            elif isinstance(node, CommentedSeq) and isinstance(step, int) and 0 <= step < len(node):
                pos = node.lc.item(step)
            else:
                break
            if pos is not None:
                line, column = pos[0] + 1, pos[1] + 1
            node = node[step]
        return line, column


def _yaml() -> YAML:
    yaml = YAML(typ="rt", pure=True)
    yaml.Constructor = _Constructor
    yaml.allow_duplicate_keys = False
    return yaml


def plain(node: Any) -> Any:
    """Convert ruamel's round-trip types to plain dict, list, str, int, float, bool, None."""
    if isinstance(node, dict):
        return {str(key): plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [plain(value) for value in node]
    if isinstance(node, bool):
        return bool(node)
    if isinstance(node, int):
        return int(node)
    if isinstance(node, float):
        return float(node)
    if isinstance(node, str):
        return str(node)
    return node


def loads(text: str, file: str = "<string>") -> Document:
    """Parse one YAML document from ``text``."""
    try:
        tree = _yaml().load(text)
    except MarkedYAMLError as error:
        mark = error.problem_mark or error.context_mark
        line, column = (mark.line + 1, mark.column + 1) if mark else (1, 1)
        problem = error.problem or "invalid YAML"
        hint = (
            "remove or rename the repeated key"
            if "duplicate" in problem
            else "check indentation and quoting at this position"
        )
        raise YamlLoadError(file, line, column, problem.strip(), hint) from error
    except YAMLError as error:
        raise YamlLoadError(file, 1, 1, str(error), "check the file is valid YAML") from error
    return Document(file=file, data=plain(tree), tree=tree)


def load(path: Path) -> Document:
    """Parse one YAML file."""
    return loads(path.read_text(encoding="utf-8"), str(path))

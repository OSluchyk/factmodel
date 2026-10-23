"""Gate stage `privacy`: evidence or a probe result holds something that looks like personal
data or a row sample, or any model file holds a literal connection string. Evidence holds
quotes and counts; credentials are named through `dsn_env`, never written."""

import re
from collections.abc import Iterator
from typing import Any

from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue

STAGE = "privacy"
HINT = "remove the value; quote structure or counts, never values about people or rows"
PATTERNS = {
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "long_number": re.compile(r"(?<![\w.-])\+?\d(?:[\d -]{7,}\d)(?![\w.-])"),
    "row_sample": re.compile(r"(?:[^\t\n]*\t){2,}|(?:[^|\n]*\|){3,}"),
}
RECORD_TEXT = ("quote", "note", "named_error")
# A connection string written into a model file instead of named through dsn_env.
LITERAL_DSN = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://[^\s]*@|password\s*=", re.IGNORECASE)
DSN_HINT = "remove the connection string; name the environment variable that holds it in dsn_env"


def _strings(node: Any, location: list[str | int]) -> Iterator[tuple[list[str | int], str]]:
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, [*location, key])
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _strings(item, [*location, i])
    elif isinstance(node, str):
        yield location, node


def _texts(kind: str, data: dict[str, Any]) -> Iterator[tuple[list[str | int], str]]:
    for i, record in enumerate(data.get("records") or []):
        if isinstance(record, dict):
            for key in RECORD_TEXT:
                if isinstance(record.get(key), str):
                    yield ["records", i, key], record[key]
    if kind == "probe-result" and isinstance(data.get("error"), str):
        yield ["error"], data["error"]


def run(ctx: GateContext) -> list[LoadIssue]:
    issues = []
    for f in ctx.model.files:
        data = f.document.data
        if not isinstance(data, dict):
            continue
        for location, text in _strings(data, []):
            if LITERAL_DSN.search(text):
                message = "a connection string is written in a model file"
                issues.append(ctx.issue(STAGE, "literal_dsn", f.path, location, message, DSN_HINT))
        for location, text in _texts(f.kind, data):
            for code, pattern in PATTERNS.items():
                if pattern.search(text):
                    message = f"text looks like personal data or a row sample ({code})"
                    issues.append(ctx.issue(STAGE, code, f.path, location, message, HINT))
    return issues

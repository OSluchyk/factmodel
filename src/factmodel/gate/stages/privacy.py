"""Gate stage `privacy`: evidence or a probe result holds something that looks like personal
data or a row sample. Evidence holds quotes and counts; it never holds values about people."""

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
        for location, text in _texts(f.kind, data):
            for code, pattern in PATTERNS.items():
                if pattern.search(text):
                    message = f"text looks like personal data or a row sample ({code})"
                    issues.append(ctx.issue(STAGE, code, f.path, location, message, HINT))
    return issues

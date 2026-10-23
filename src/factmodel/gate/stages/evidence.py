"""Gate stage `evidence`: an authored fact has no live evidence.

The schema makes every fact list evidence IDs unless it is explicitly unresolved. This stage
fails a fact whose evidence resolves only to retracted records: it cites evidence, but none
of it still stands.
"""

from collections.abc import Iterator
from typing import Any

from factmodel.core.status import effective_status
from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue

STAGE = "evidence"
HINT = "cite the evidence that superseded the retracted record, or mark the fact unresolved"
FACT_KEYS = ("evidence", "retirement_evidence")


def _evidence_lists(
    node: Any, location: list[str | int]
) -> Iterator[tuple[list[str | int], list[str]]]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("records", "extensions"):
                continue
            if key in FACT_KEYS and isinstance(value, list):
                yield [*location, key], [v for v in value if isinstance(v, str)]
            else:
                yield from _evidence_lists(value, [*location, key])
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _evidence_lists(item, [*location, i])


def run(ctx: GateContext) -> list[LoadIssue]:
    evidence = ctx.model.evidence
    issues = []
    for name, doc in ctx.documents():
        for location, refs in _evidence_lists(doc.data, []):
            known = [ref for ref in refs if ref in evidence]
            if known and effective_status(known, evidence) == "retracted":
                message = f"every evidence record cited here is retracted: {', '.join(known)}"
                issues.append(ctx.issue(STAGE, "retracted_only", name, location, message, HINT))
    return issues

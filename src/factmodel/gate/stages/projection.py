"""Gate stage `projection`: residue is not empty."""

from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue

STAGE = "projection"
HINT = "add a profile rule that matches it, or fix the facts it is projected from"


def run(ctx: GateContext) -> list[LoadIssue] | None:
    if ctx.derived is None:
        return None
    issues = []
    files = ctx.entity_files
    for row in ctx.derived.projection.residue:
        entity_id, _, key = row.relationship.partition(".")
        keys = [r.key for r in ctx.model.entities[entity_id].relationships]
        location: list[str | int] = ["relationships", keys.index(key), "to"]
        message = f"no rule labels {row.relationship} for target {row.target!r} (residue)"
        issues.append(ctx.issue(STAGE, "residue", files[entity_id], location, message, HINT))
    return issues

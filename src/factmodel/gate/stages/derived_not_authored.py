"""Gate stage `derived-not-authored`: a derived key appears in an authored file.

The loader reports derived keys the schema rejects. This stage also finds them anywhere the
schema allows free keys, such as `extensions`, because a derived value there would still be
a second, hand-written copy of a computed fact.
"""

from typing import Any

from factmodel import vocabulary
from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue

STAGE = "derived-not-authored"
HINT = "remove the key; derived values are computed by fact project"


def _free_maps(node: Any, location: list[str | int], inside: bool) -> list[list[str | int]]:
    found: list[list[str | int]] = []
    derived = set(vocabulary.load()["derived_value"])
    if isinstance(node, dict):
        for key, value in node.items():
            here = [*location, key]
            if inside and key in derived:
                found.append(here)
            found += _free_maps(value, here, inside or key == "extensions")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found += _free_maps(item, [*location, i], inside)
    return found


def run(ctx: GateContext) -> list[LoadIssue]:
    issues = ctx.result.stage(STAGE)
    for name, doc in ctx.documents():
        for location in _free_maps(doc.data, [], False):
            message = f"derived key {location[-1]!r} is authored under extensions"
            issues.append(ctx.issue(STAGE, "derived_key", name, location, message, HINT))
    return issues

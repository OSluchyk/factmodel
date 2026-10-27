"""Gate stage `triggers`: a fired trigger has no follow-up."""

from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue
from factmodel.model.types import Trigger

STAGE = "triggers"
HINT = "do the follow-up, then set follow_up_ref on the fired entry (a register ID, commit or file)"


def run(ctx: GateContext) -> list[LoadIssue]:
    issues = []
    for f in ctx.model.files:
        if not isinstance(f.obj, Trigger):
            continue
        for i, firing in enumerate(f.obj.fired or []):
            if firing.follow_up_ref is None:
                message = f"trigger {f.obj.id!r} fired on {firing.on} and has no follow-up"
                location: list[str | int] = ["fired", i]
                issues.append(ctx.issue(STAGE, "no_follow_up", f.path, location, message, HINT))
    return issues

"""Gate stage `registers`: register IDs reused or missing, or an entry closed without
usable evidence. Hazards are permanent semantics and are never counted as issues here."""

import re

from factmodel.core.status import effective_status, usable
from factmodel.gate.runner import GateContext
from factmodel.model.loader import REGISTER_KINDS, LoadIssue
from factmodel.model.types import Escalation, Finding

STAGE = "registers"
REGISTER_ID = re.compile(r"^(?P<prefix>[FEHD])-(?P<number>[0-9]{4})$")


def run(ctx: GateContext) -> list[LoadIssue]:
    model = ctx.model
    issues = ctx.result.stage(STAGE)
    by_prefix: dict[str, dict[int, str]] = {}
    for f in model.files:
        if f.kind not in REGISTER_KINDS or not isinstance(f.document.data, dict):
            continue
        match = REGISTER_ID.match(str(f.document.data.get("id")))
        if match:
            by_prefix.setdefault(match["prefix"], {}).setdefault(int(match["number"]), f.path)
    for prefix, numbers in sorted(by_prefix.items()):
        for missing in sorted(set(range(1, max(numbers) + 1)) - numbers.keys()):
            after = numbers[min(n for n in numbers if n > missing)]
            message = f"register ID {prefix}-{missing:04d} is missing; IDs are never deleted"
            hint = f"restore {prefix}-{missing:04d}, or close it instead of deleting it"
            issues.append(ctx.issue(STAGE, "missing_register_id", after, ["id"], message, hint))
    files = {f.obj.id: f.path for f in model.files if isinstance(f.obj, Escalation | Finding)}
    for escalation in model.escalations.values():
        if escalation.status == "answered" and escalation.answer is not None:
            status = effective_status(escalation.answer.evidence, model.evidence)
            if not usable(status):
                message = f"escalation {escalation.id} is answered, but its evidence is {status}"
                hint = "cite confirmed or inferred evidence for the answer, or reopen it"
                location: list[str | int] = ["answer", "evidence"]
                issues.append(
                    ctx.issue(STAGE, "weak_answer", files[escalation.id], location, message, hint)
                )
    for finding in model.findings.values():
        if finding.status == "resolved" and finding.evidence:
            status = effective_status(finding.evidence, model.evidence)
            if not usable(status):
                message = f"finding {finding.id} is resolved, but its evidence is {status}"
                hint = "cite confirmed or inferred evidence for the resolution, or reopen it"
                issues.append(
                    ctx.issue(
                        STAGE, "weak_resolution", files[finding.id], ["evidence"], message, hint
                    )
                )
    return issues

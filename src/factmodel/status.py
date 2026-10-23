"""What needs attention in a model (``fact status``). Read-only; never fails a model."""

from dataclasses import dataclass, field
from pathlib import Path

from factmodel.model.loader import inspect_model


@dataclass
class Status:
    issues: int = 0
    open_findings: list[str] = field(default_factory=list)
    open_escalations: list[str] = field(default_factory=list)
    unfollowed_triggers: list[str] = field(default_factory=list)
    stale_evidence: list[str] = field(default_factory=list)
    active_hazards: list[str] = field(default_factory=list)

    @property
    def next_actions(self) -> list[str]:
        actions = []
        if self.issues:
            actions.append("run fact check and fix the issues it lists")
        actions += [f"work on finding {item}" for item in self.open_findings]
        actions += [f"get an answer for escalation {item}" for item in self.open_escalations]
        actions += [f"record the follow-up for trigger {item}" for item in self.unfollowed_triggers]
        if self.stale_evidence:
            actions.append("re-read the sources of stale evidence and renew it")
        return actions

    def lines(self) -> list[str]:
        out = []
        for title, items in (
            ("open findings", self.open_findings),
            ("open escalations", self.open_escalations),
            ("fired triggers without follow-up", self.unfollowed_triggers),
            ("stale evidence", self.stale_evidence),
        ):
            out.append(f"{title}: {len(items)}")
            out += [f"  {item}" for item in items]
        out.append(f"hazards (permanent, not issues): {len(self.active_hazards)}")
        out += [f"  {item}" for item in self.active_hazards]
        actions = self.next_actions
        out.append("next actions:" if actions else "next actions: none")
        out += [f"  - {action}" for action in actions]
        return out


def status(root: Path) -> Status:
    result = inspect_model(root)
    model = result.model
    out = Status(issues=len(result.issues))
    out.open_findings = sorted(
        f"{f.id} {f.title}" for f in model.findings.values() if f.status == "open"
    )
    out.open_escalations = sorted(
        f"{e.id} {e.question}" for e in model.escalations.values() if e.status == "open"
    )
    out.unfollowed_triggers = sorted(
        f"{t.id} fired {firing.on}"
        for t in model.triggers.values()
        for firing in t.fired or []
        if firing.follow_up_ref is None
    )
    out.stale_evidence = sorted(
        f"{record.id} pinned {record.pin}, source now {source.current_pin}"
        for record in model.evidence.values()
        if (source := model.sources.get(record.source)) is not None
        and source.current_pin is not None
        and record.pin != source.current_pin
        and record.status != "retracted"
    )
    out.active_hazards = sorted(
        f"{h.id} {h.title}" for h in model.hazards.values() if h.status == "active"
    )
    return out

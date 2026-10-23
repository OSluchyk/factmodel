"""Effective evidence status of a fact (spec/ALGORITHMS.md, section 0)."""

from collections.abc import Iterable, Mapping

from factmodel import vocabulary
from factmodel.model.types import EvidenceRecord

USABLE = frozenset({"confirmed", "inferred"})


def effective_status(
    refs: Iterable[str] | None,
    evidence: Mapping[str, EvidenceRecord],
    *,
    unresolved: bool = False,
) -> str:
    """Return the best status among the referenced records.

    The vocabulary lists ``evidence_status`` from best to worst. A fact marked unresolved, or
    one whose references resolve to no record, is ``unresolved``.
    """
    if unresolved:
        return "unresolved"
    order = vocabulary.load()["evidence_status"]
    statuses = [evidence[ref].status for ref in refs or () if ref in evidence]
    if not statuses:
        return "unresolved"
    return min(statuses, key=order.index)


def usable(status: str) -> bool:
    return status in USABLE

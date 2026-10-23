"""Projection of relationships to profile labels (spec/ALGORITHMS.md, algorithm 1)."""

from collections.abc import Mapping
from dataclasses import dataclass

from factmodel.core.scope import ScopeResult
from factmodel.core.status import effective_status
from factmodel.model.types import EndPattern, Entity, EvidenceRecord, Facets, Profile

WITHHELD = "withheld"


@dataclass(frozen=True, order=True)
class Label:
    relationship: str
    label: str
    targets: tuple[tuple[str, str], ...]


@dataclass(frozen=True, order=True)
class Residue:
    relationship: str
    target: str


@dataclass(frozen=True)
class ProjectionResult:
    labels: tuple[Label, ...]
    residue: tuple[Residue, ...]


@dataclass(frozen=True)
class _End:
    class_: str
    scoped: bool


@dataclass(frozen=True)
class _Pair:
    status: str
    mechanism: str
    cardinality: str
    ends: tuple[_End, _End]


def _end_matches(end: _End, pattern: EndPattern) -> bool:
    if pattern.class_ is not None and pattern.class_ != end.class_:
        return False
    return pattern.subject_scoped is None or pattern.subject_scoped == end.scoped


def matches(when: Facets, pair: _Pair) -> bool:
    """Whether every facet of a rule holds for one pair of ends."""
    classes = [end.class_ for end in pair.ends]
    scoped = [end.scoped for end in pair.ends]
    checks = [
        when.evidence_status is None or when.evidence_status == pair.status,
        when.mechanism is None or when.mechanism == pair.mechanism,
        when.cardinality is None or when.cardinality == pair.cardinality,
        when.any_end_class is None or when.any_end_class in classes,
        when.all_ends_class is None or all(c == when.all_ends_class for c in classes),
        when.any_end_subject_scoped is None or when.any_end_subject_scoped == any(scoped),
        when.all_ends_subject_scoped is None or when.all_ends_subject_scoped == all(scoped),
        when.all_ends_match is None
        or all(any(_end_matches(end, p) for p in when.all_ends_match) for end in pair.ends),
    ]
    return all(checks)


def _first_label(profile: Profile, pair: _Pair) -> str | None:
    for rule in profile.rules:
        if matches(rule.when, pair):
            return rule.label
    return None


def project_labels(
    entities: Mapping[str, Entity],
    evidence: Mapping[str, EvidenceRecord],
    profile: Profile,
    scope: ScopeResult,
) -> ProjectionResult:
    """Label every relationship, or list it as residue."""
    labels: list[Label] = []
    residue: list[Residue] = []
    for entity_id in sorted(entities):
        source = entities[entity_id]
        for rel in source.relationships:
            ref = f"{entity_id}.{rel.key}"
            status = effective_status(rel.evidence, evidence, unresolved=rel.status is not None)
            per_target: list[tuple[str, str | None]] = []
            for target_id in sorted(rel.targets):
                target = entities.get(target_id)
                label = None
                if target is not None:
                    pair = _Pair(
                        status,
                        rel.mechanism,
                        rel.cardinality,
                        (
                            _End(source.class_, scope.scoped(entity_id)),
                            _End(target.class_, scope.scoped(target_id)),
                        ),
                    )
                    label = _first_label(profile, pair)
                per_target.append((target_id, label))
            missing = [target for target, label in per_target if label is None]
            if missing:
                residue.extend(Residue(ref, target) for target in missing)
                continue
            found = [(target, label) for target, label in per_target if label is not None]
            distinct = {label for _, label in found}
            final = found[0][1] if len(distinct) == 1 else WITHHELD
            labels.append(Label(ref, final, tuple(found) if rel.is_target_set else ()))
    return ProjectionResult(tuple(sorted(labels)), tuple(sorted(residue)))

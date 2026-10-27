"""Subject scope closure (spec/ALGORITHMS.md, algorithm 2; D-007).

A model whose profile names no subject has no anchor (D-015): every entity is ``none`` and
reachability does not apply.
"""

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass

from factmodel.core.status import effective_status, usable
from factmodel.model import joins
from factmodel.model.types import Entity, EvidenceRecord, Relationship


@dataclass(frozen=True, order=True)
class ScopeRow:
    entity: str
    subject_scope: str
    basis: str | None
    via: tuple[str, ...]
    # None when the model has no anchor (D-015)
    reachable: bool | None

    @property
    def scoped(self) -> bool:
        return self.subject_scope != "none"


@dataclass(frozen=True, order=True)
class Rejection:
    fact: str
    reason: str


@dataclass(frozen=True)
class ScopeResult:
    rows: Mapping[str, ScopeRow]
    rejections: tuple[Rejection, ...]

    def scoped(self, entity: str) -> bool:
        row = self.rows.get(entity)
        return row is not None and row.scoped


@dataclass(frozen=True)
class _Step:
    source: str
    ref: str
    target: str
    basis: str


def _rejection(
    source: Entity,
    rel: Relationship,
    entities: Mapping[str, Entity],
    evidence: Mapping[str, EvidenceRecord],
) -> str | None:
    admission = rel.scope_admission
    assert admission is not None
    if rel.is_target_set:
        return "target_set"
    if rel.mechanism not in ("declared_fk", "inferred_join"):
        return "wrong_mechanism"
    target = entities.get(rel.targets[0])
    if source.class_ == "reference" or (target is not None and target.class_ == "reference"):
        return "reference_end"
    rel_status = effective_status(rel.evidence, evidence, unresolved=rel.status is not None)
    if not (usable(rel_status) and usable(effective_status(admission.evidence, evidence))):
        return "weak_evidence"
    if admission.basis == "current_row_rule" and (
        target is None or target.keys.current_row_rule is None
    ):
        return "no_current_row_rule"
    if admission.basis == "unique_target" and rel.cardinality not in ("many_to_one", "one_to_one"):
        return "non_unique_target"
    if admission.basis == "unique_target" and isinstance(rel.join, str) and target is not None:
        keys = [target.keys.primary, *(target.keys.unique or [])]
        try:
            unique = not joins.parse(rel.join).expression or joins.unique_right_side(
                rel.join, source.id, target.id, keys
            )
        except joins.JoinError:  # reported by the loader
            unique = False
        if not unique:
            return "non_unique_target"
    return None


def _reachable(
    entities: Mapping[str, Entity], evidence: Mapping[str, EvidenceRecord], anchor: str
) -> set[str]:
    edges: dict[str, set[str]] = {entity_id: set() for entity_id in entities}

    def link(a: str, b: str) -> None:
        if a in edges and b in edges:
            edges[a].add(b)
            edges[b].add(a)

    for entity in entities.values():
        ref = entity.anchor_reference
        if ref is not None and usable(effective_status(ref.evidence, evidence)):
            link(entity.id, anchor)
        for rel in entity.relationships:
            status = effective_status(rel.evidence, evidence, unresolved=rel.status is not None)
            if status in ("unresolved", "retracted") or rel.mechanism == "derivation":
                continue
            for target in rel.targets:
                link(entity.id, target)
    if anchor not in edges:
        return set()
    seen = {anchor}
    queue = deque([anchor])
    while queue:
        for neighbour in sorted(edges[queue.popleft()]):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return seen


def compute_scope(
    entities: Mapping[str, Entity], evidence: Mapping[str, EvidenceRecord], anchor: str | None
) -> ScopeResult:
    """Compute subject scope, via-path, basis and reachability for every entity."""
    if anchor is None:
        rows = {e: ScopeRow(e, "none", None, (), None) for e in sorted(entities)}
        return ScopeResult(rows, ())
    rejections: list[Rejection] = []
    level: dict[str, int] = {}
    via: dict[str, tuple[str, ...]] = {}
    basis: dict[str, str | None] = {}

    for entity_id in sorted(entities):
        entity = entities[entity_id]
        ref = entity.anchor_reference
        if entity.class_ == "reference":
            if ref is not None:
                rejections.append(Rejection(f"{entity_id}.anchor_reference", "reference_end"))
            continue
        if entity_id == anchor:
            level[entity_id], via[entity_id], basis[entity_id] = 0, (), None
        elif ref is not None:
            if usable(effective_status(ref.evidence, evidence)):
                level[entity_id], via[entity_id], basis[entity_id] = 0, (), None
            else:
                rejections.append(Rejection(f"{entity_id}.anchor_reference", "weak_evidence"))

    steps: list[_Step] = []
    for entity_id in sorted(entities):
        entity = entities[entity_id]
        for rel in entity.relationships:
            if rel.scope_admission is None:
                continue
            rel_ref = f"{entity_id}.{rel.key}"
            reason = _rejection(entity, rel, entities, evidence)
            if reason is not None:
                rejections.append(Rejection(rel_ref, reason))
            elif rel.targets[0] in entities:
                steps.append(_Step(entity_id, rel_ref, rel.targets[0], rel.scope_admission.basis))

    depth = 0
    while True:
        chosen: dict[str, _Step] = {}
        for step in steps:
            if step.source in level or step.target not in level:
                continue
            best = chosen.get(step.source)
            if best is None or (level[step.target], step.ref) < (level[best.target], best.ref):
                chosen[step.source] = step
        if not chosen:
            break
        depth += 1
        for source, step in chosen.items():
            level[source] = depth
            via[source] = (step.ref, *via[step.target])
            basis[source] = step.basis

    reachable = _reachable(entities, evidence, anchor)
    rows = {}
    for entity_id in sorted(entities):
        if entity_id not in level:
            scope = "none"
        elif level[entity_id] == 0:
            scope = "direct"
        else:
            scope = "transitive"
        rows[entity_id] = ScopeRow(
            entity_id,
            scope,
            basis.get(entity_id),
            via.get(entity_id, ()),
            entity_id in reachable,
        )
    return ScopeResult(rows, tuple(sorted(rejections)))

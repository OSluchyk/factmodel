"""Gate stage `scope`: an admission that cannot carry scope, or a consumer-declared entity
that is unreachable from the anchor without an owner decision."""

from factmodel.gate.runner import GateContext
from factmodel.model.loader import LoadIssue
from factmodel.model.types import Layer

STAGE = "scope"
REJECTION_HINT = "fix the admission (see spec/ALGORITHMS.md, algorithm 2) or remove it"
REACH_HINT = "connect the entity to the anchor, or record an owner decision about it"


def _layer_entities(layer: Layer, relationships: dict[str, tuple[str, ...]]) -> set[str]:
    found: set[str] = set()
    for ref in layer.joins or []:
        source = ref.partition(".")[0]
        found |= {source, *relationships.get(ref, ())}
    found |= {f.entity for f in layer.filters or []}
    found |= {c.field.partition(".")[0] for c in layer.concepts or []}
    found |= {m.field.partition(".")[0] for m in layer.measures or []}
    return found


def run(ctx: GateContext) -> list[LoadIssue] | None:
    if ctx.derived is None:
        return None
    model = ctx.model
    entity_files = ctx.entity_files
    issues = []
    for rejection in ctx.derived.scope.rejections:
        entity_id, _, key = rejection.fact.partition(".")
        entity = model.entities[entity_id]
        location: list[str | int] = ["anchor_reference"]
        if key != "anchor_reference":
            keys = [r.key for r in entity.relationships]
            location = ["relationships", keys.index(key), "scope_admission"]
        message = f"{rejection.fact}: admission rejected ({rejection.reason})"
        file = entity_files[entity_id]
        issues.append(ctx.issue(STAGE, rejection.reason, file, location, message, REJECTION_HINT))
    decided = {
        ref
        for decision in model.decisions.values()
        if decision.status == "accepted"
        for ref in decision.about or []
    }
    targets = {ref: rel.targets for ref, (_, rel) in model.relationships.items()}
    rows = ctx.derived.scope.rows
    for f in model.files:
        if not isinstance(f.obj, Layer):
            continue
        for entity_id in sorted(_layer_entities(f.obj, targets)):
            row = rows.get(entity_id)
            if row is not None and row.reachable is False and entity_id not in decided:
                message = f"layer {f.obj.id!r} uses {entity_id!r}, not reachable from the anchor"
                issues.append(ctx.issue(STAGE, "unreachable", f.path, ["id"], message, REACH_HINT))
    return issues

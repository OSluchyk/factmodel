"""Gate stage `layers`: a semantic layer that breaks its contract (D-019).

The loader already checks that the IDs a layer names exist (stage `references`). This stage
checks what a consumer relies on: the consumer exists; current-row rules match the entities;
joins are resolved relationships between entities the layer reads; concepts and measures parse
and use only the layer's fields; every inherited hazard is listed; a measure that excludes
suppressed cells names its companion; a reviewed layer has an accepted equivalence run.
"""

import json
from collections.abc import Iterator
from pathlib import Path

from factmodel.gate.runner import GateContext
from factmodel.model import joins
from factmodel.model.loader import LoadIssue, Model
from factmodel.model.types import Hazard, Layer

STAGE = "layers"
HINTS = {
    "missing_consumer": "add semantic/<layer-id>/consumer.yaml with this id, listing the layer",
    "current_row_rule": "copy the entity's current_row_rule exactly (null when it has none)",
    "unknown_concept": "name a concept of this layer",
    "unresolved_join": "resolve the relationship first; a layer never joins an unresolved link",
    "join_outside_layer": "list both ends of the join under entities",
    "outside_layer": "read only entities the layer lists under entities",
    "bad_expression": "write <entity>.<field> columns of the layer's entities (D-017 form)",
    "missing_hazard": "list the hazard under hazards; the layer inherits it",
    "measure_hazard": "list the measure's hazards under the layer's hazards too",
    "missing_companion": "name the measure that counts the suppressed cells in companion",
    "missing_evidence": "cite an existing evidence record",
    "not_accepted": "run fact equivalence run and fact equivalence accept, or keep status draft",
}
ACCEPTED = Path("equivalence") / "accepted.json"


def _accepted(root: Path) -> set[str]:
    path = root / ACCEPTED
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set((data.get("layers") or {}).keys()) if isinstance(data, dict) else set()


def _columns(text: str) -> list[tuple[str, str]]:
    return list(joins.parse(text).columns)


def _fields(model: Model, entity: str) -> set[str]:
    found = model.entities.get(entity)
    return {f.path or f.name for f in found.fields} if found is not None else set()


def inherited_hazards(model: Model, layer: Layer) -> dict[str, str]:
    """Active hazards the layer inherits, with the fact each comes from."""
    entities = {e.entity for e in layer.entities}
    used: set[tuple[str, str]] = set()
    for concept in layer.concepts or []:
        if concept.field:
            used.add(_split(concept.field))
        used |= {_split(ref) for ref in concept.distinct or []}
        if concept.predicate:
            used |= set(_safe_columns(concept.predicate))
    for measure in layer.measures or []:
        used |= set(_safe_columns(measure.expression))
        used |= {(measure.grain.entity, f) for f in measure.grain.fields}
        if measure.time:
            used.add(_split(measure.time.field))
    found: dict[str, str] = {}
    for entity_id in sorted(entities):
        entity = model.entities.get(entity_id)
        if entity is None:
            continue
        for hazard in entity.hazards or []:
            found.setdefault(hazard, entity_id)
        for fld in entity.fields:
            if (entity_id, fld.path or fld.name) in used:
                for hazard in fld.hazards or []:
                    found.setdefault(hazard, f"{entity_id}.{fld.path or fld.name}")
    for ref in layer.joins or []:
        pair = model.relationships.get(ref)
        if pair is not None:
            for hazard in pair[1].hazards or []:
                found.setdefault(hazard, ref)
    for register in model.hazards.values():
        if _active(register):
            for ref in register.applies_to:
                if ref in entities or ref in (layer.joins or []):
                    found.setdefault(register.id, ref)
    return {h: src for h, src in found.items() if h in model.hazards and _active(model.hazards[h])}


def _active(hazard: Hazard) -> bool:
    return hazard.status == "active"


def _split(ref: str) -> tuple[str, str]:
    entity, _, address = ref.partition(".")
    return entity, address


def _safe_columns(text: str) -> list[tuple[str, str]]:
    try:
        return _columns(text)
    except joins.JoinError:
        return []


def _check(ctx: GateContext, layer: Layer, path: str) -> Iterator[LoadIssue]:
    model = ctx.model

    def issue(code: str, loc: list[str | int], message: str) -> LoadIssue:
        return ctx.issue(STAGE, code, path, loc, message, HINTS[code])

    consumer = model.consumers.get(layer.consumer)
    if consumer is None or layer.id not in consumer.layers:
        yield issue("missing_consumer", ["consumer"], f"no consumer {layer.consumer!r} lists it")
    entities = {e.entity for e in layer.entities}
    concepts = {c.id for c in layer.concepts or []}
    for i, item in enumerate(layer.entities):
        entity = model.entities.get(item.entity)
        if entity is not None and item.current_row_rule != entity.keys.current_row_rule:
            message = f"current_row_rule of {item.entity!r} differs from the entity's"
            yield issue("current_row_rule", ["entities", i, "current_row_rule"], message)
        for j, ref in enumerate(item.default_filters or []):
            if ref not in concepts:
                loc: list[str | int] = ["entities", i, "default_filters", j]
                yield issue("unknown_concept", loc, f"concept {ref!r} not in this layer")
    for i, ref in enumerate(layer.joins or []):
        pair = model.relationships.get(ref)
        if pair is None:
            continue
        source, rel = pair
        if rel.status is not None:
            yield issue("unresolved_join", ["joins", i], f"relationship {ref!r} is unresolved")
        ends = {source.id, *rel.targets}
        if not ends <= entities:
            missing = ", ".join(sorted(ends - entities))
            yield issue("join_outside_layer", ["joins", i], f"{ref!r} reaches {missing}")

    def expression(loc: list[str | int], text: str) -> Iterator[LoadIssue]:
        try:
            columns = _columns(text)
        except joins.JoinError as error:
            yield issue("bad_expression", loc, f"{text!r}: {error}")
            return
        for entity, address in columns:
            if entity not in entities:
                yield issue("outside_layer", loc, f"{entity!r} is not among the layer's entities")
            elif address not in _fields(model, entity):
                yield issue("bad_expression", loc, f"{entity}.{address} is not a field")

    def within(loc: list[str | int], ref: str) -> Iterator[LoadIssue]:
        entity = _split(ref)[0]
        if entity not in entities:
            yield issue("outside_layer", loc, f"{entity!r} is not among the layer's entities")

    for i, concept in enumerate(layer.concepts or []):
        if concept.field:
            yield from within(["concepts", i, "field"], concept.field)
        for j, ref in enumerate(concept.distinct or []):
            yield from within(["concepts", i, "distinct", j], ref)
        if concept.predicate:
            yield from expression(["concepts", i, "predicate"], concept.predicate)
    measures = {m.id for m in layer.measures or []}
    listed = set(layer.hazards or [])
    for i, measure in enumerate(layer.measures or []):
        yield from expression(["measures", i, "expression"], measure.expression)
        if measure.grain.entity not in entities:
            yield from within(["measures", i, "grain", "entity"], f"{measure.grain.entity}.x")
        if measure.time:
            yield from within(["measures", i, "time", "field"], measure.time.field)
        if measure.formula_source and measure.formula_source not in model.evidence:
            message = f"evidence {measure.formula_source!r} not found"
            yield issue("missing_evidence", ["measures", i, "formula_source"], message)
        for j, hazard in enumerate(measure.hazards or []):
            if hazard not in listed:
                message = f"measure {measure.id!r} names {hazard}, which the layer does not list"
                yield issue("measure_hazard", ["measures", i, "hazards", j], message)
        if measure.suppressed == "exclude" and measure.companion not in measures:
            message = f"measure {measure.id!r} excludes suppressed cells but names no companion"
            yield issue("missing_companion", ["measures", i], message)
    for hazard, origin in sorted(inherited_hazards(model, layer).items()):
        if hazard not in listed:
            message = f"the layer inherits {hazard} from {origin} but does not list it"
            yield issue("missing_hazard", ["hazards"] if listed else ["id"], message)
    if layer.status == "reviewed" and layer.id not in _accepted(ctx.root):
        message = f"layer {layer.id!r} is reviewed but has no accepted equivalence run"
        yield issue("not_accepted", ["status"], message)


def run(ctx: GateContext) -> list[LoadIssue] | None:
    if ctx.blocked:
        return None
    issues: list[LoadIssue] = []
    for f in ctx.model.files:
        if isinstance(f.obj, Layer):
            issues.extend(_check(ctx, f.obj, f.path))
    return issues

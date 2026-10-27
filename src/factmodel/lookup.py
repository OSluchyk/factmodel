"""``fact lookup``: what a reader of a model or a release needs about one layer, entity or
hazard, in plain text, with every relationship key resolved to its join (the model-lookup need
found when the reference consumers were written: the join behind each relationship key, and
the value tables a request needs)."""

from factmodel.model.loader import Model


class LookupError_(ValueError):
    """The id is not in the model."""


def _hazard_lines(model: Model, ids: list[str]) -> list[str]:
    out = []
    for hazard_id in ids:
        hazard = model.hazards.get(hazard_id)
        if hazard is not None:
            out.append(f"  {hazard.id} {hazard.title} ({hazard.status}): {hazard.description}")
    return out


def layer(model: Model, layer_id: str) -> list[str]:
    found = model.layers.get(layer_id)
    if found is None:
        raise LookupError_(f"layer {layer_id!r} not found")
    out = [f"layer {found.id} ({found.status}): {found.purpose}", f"consumer: {found.consumer}"]
    out.append("entities:")
    for item in found.entities:
        entity = model.entities.get(item.entity)
        physical = entity.physical_name if entity else "?"
        filters = ", ".join(item.default_filters or []) or "-"
        rule = item.current_row_rule or "none"
        out.append(f"  {item.entity} = {physical}; current row: {rule}; default filters: {filters}")
    out.append("joins:")
    for ref in found.joins or []:
        pair = model.relationships.get(ref)
        if pair is not None:
            rel = pair[1]
            out.append(f"  {ref}: {rel.join} ({rel.cardinality}, {rel.mechanism})")
    out.append("concepts:")
    for concept in found.concepts or []:
        required = " [required]" if concept.required else ""
        if concept.predicate:
            form = f"predicate {concept.predicate}"
        elif concept.values_table is not None:
            table = concept.values_table
            origin = f"from {table.entity}" if table.entity else f"{len(table.rows or [])} rows"
            form = f"table ({', '.join(table.columns)}), {origin}"
        elif concept.distinct:
            form = f"distinct on {', '.join(concept.distinct)}"
        else:
            values = f" in {concept.values}" if concept.values else ""
            form = f"field {concept.field}{values}"
        out.append(f"  {concept.id}{required}: {form}")
    out.append("measures:")
    for measure in found.measures or []:
        grain = f"{measure.grain.entity}({', '.join(measure.grain.fields)})"
        extra = []
        if measure.time:
            extra.append(f"time {measure.time.field} by {measure.time.granularity}")
        if measure.suppressed:
            extra.append(f"suppressed {measure.suppressed}")
        if measure.companion:
            extra.append(f"companion {measure.companion}")
        if measure.formula_source:
            record = model.evidence.get(measure.formula_source)
            quote = f': "{record.quote}"' if record is not None and record.quote else ""
            extra.append(f"formula {measure.formula_source}{quote}")
        out.append(
            f"  {measure.id}: {measure.aggregation}({measure.expression.strip()}) at {grain}"
        )
        out += [f"    {line}" for line in extra]
    out.append("hazards:")
    out += _hazard_lines(model, list(found.hazards or []))
    return out


def entity(model: Model, entity_id: str) -> list[str]:
    found = model.entities.get(entity_id)
    if found is None:
        raise LookupError_(f"entity {entity_id!r} not found")
    out = [f"entity {found.id} = {found.physical_name} ({found.class_}): {found.grain}"]
    out.append(
        f"keys: {', '.join(found.keys.primary) or '-'}; current row: {found.keys.current_row_rule}"
    )
    out.append("fields:")
    for fld in found.fields:
        values = f" in {fld.values}" if fld.values else ""
        out.append(f"  {fld.path or fld.name} {fld.type}{values}: {fld.meaning}")
    out.append("relationships:")
    for rel in found.relationships:
        status = f" [{rel.status}]" if rel.status else ""
        out.append(
            f"  {found.id}.{rel.key} -> {rel.to}{status}: {rel.join or '-'} ({rel.cardinality})"
        )
    return out


def hazard(model: Model, hazard_id: str) -> list[str]:
    found = model.hazards.get(hazard_id)
    if found is None:
        raise LookupError_(f"hazard {hazard_id!r} not found")
    return [*_hazard_lines(model, [hazard_id]), f"  applies to: {', '.join(found.applies_to)}"]

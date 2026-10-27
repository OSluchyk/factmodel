"""Export a layer as an Apache Ossie (formerly Open Semantic Interchange) semantic model.

Pinned source: https://ossie.apache.org/, read once on 2026-10-27 (round 25). The page names
the project "Apache Ossie (incubating)" and links the core specification at
https://github.com/apache/ossie/blob/main/core-spec/spec.md; it states no version number and
names no published JSON Schema. Version pinned here: "not stated (main, as shown on
ossie.apache.org on 2026-10-27)". The specification document itself was not read (one network
read only), so this exporter writes only the structure the page's example
``sales_analytics.ossie.yaml`` shows:

- ``semantic_model``: a list; each with ``name``, ``description``, ``ai_context.instructions``,
  ``datasets`` and ``metrics``;
- a dataset: ``name``, ``source``, ``primary_key``, ``fields`` (each ``name``, and
  ``dimension.is_time`` for a dimension);
- a metric: ``name`` and ``expression.dialects`` (each ``dialect`` and ``expression``).

Round-trip notes (warnings): relationships, concepts, hazards and evidence status have no key
on that page, so they travel as text in ``ai_context.instructions``, where an AI consumer
reads them; dialect identifiers are not given on the page, so sqlglot dialect names are used;
nothing is validated against a schema, because none was published at the pinned source.
"""

from typing import Any

import sqlglot

from factmodel.adapters.base import dialect_for
from factmodel.export import Export, layer_of, status_of
from factmodel.model import joins
from factmodel.model.loader import Model
from factmodel.repo import dump_yaml

SOURCE_URL = "https://ossie.apache.org/"
SPEC_URL = "https://github.com/apache/ossie/blob/main/core-spec/spec.md"
PINNED_VERSION = "not stated (main, as shown on ossie.apache.org on 2026-10-27)"
READ_ON = "2026-10-27"
FALLBACK_DIALECTS = ("duckdb", "postgres")
AGGREGATE = {
    "sum": "SUM({})",
    "count": "COUNT({})",
    "count_distinct": "COUNT(DISTINCT {})",
    "avg": "AVG({})",
    "min": "MIN({})",
    "max": "MAX({})",
    "none": "{}",
}


def _concept_fields(layer: Any) -> set[tuple[str, str]]:
    """(entity, field) of every field a concept of the layer reads: the layer's dimensions."""
    found: set[tuple[str, str]] = set()
    for concept in layer.concepts or []:
        refs = [concept.field] if concept.field else []
        refs += list(concept.distinct or [])
        found |= {(ref.split(".", 1)[0], ref.split(".", 1)[1]) for ref in refs}
        if concept.predicate:
            found |= set(joins.parse(concept.predicate).columns)
    return found


def _dialects(model: Model, entity_ids: list[str]) -> list[str]:
    found = []
    for entity_id in entity_ids:
        source = model.sources.get(model.entities[entity_id].source or "")
        if source is not None:
            try:
                found.append(dialect_for(source.engine, source.dialect))
            except ValueError:
                continue
    return sorted(set(found)) or list(FALLBACK_DIALECTS)


def _instructions(model: Model, layer: Any) -> str:
    lines = [f"Layer {layer.id} ({layer.status}). {layer.purpose}"]
    required = [c for c in layer.concepts or [] if c.required]
    if required:
        lines.append("Apply on every query:")
        for concept in required:
            form = concept.predicate or (
                f"distinct on {', '.join(concept.distinct)}"
                if concept.distinct
                else f"fix {concept.field}"
            )
            lines.append(f"- {concept.id}: {form}. {concept.meaning.strip()}")
    if layer.joins:
        lines.append("Joins (relationship keys and their conditions):")
        for ref in layer.joins:
            pair = model.relationships.get(ref)
            if pair is not None:
                lines.append(f"- {ref}: {pair[1].join} ({pair[1].cardinality})")
    for hazard_id in layer.hazards or []:
        hazard = model.hazards.get(hazard_id)
        if hazard is not None:
            lines.append(f"Hazard {hazard.id}: {hazard.title}. {hazard.description.strip()}")
    statuses = ", ".join(f"{e.entity} {status_of(model, e.entity)}" for e in layer.entities)
    lines.append(f"Evidence status: {statuses}.")
    return "\n".join(lines) + "\n"


def export(model: Model, layer_id: str) -> Export:
    layer = layer_of(model, layer_id)
    out = Export()
    datasets = []
    time_fields: dict[str, set[str]] = {}
    for measure in layer.measures or []:
        if measure.time:
            owner, _, field = measure.time.field.partition(".")
            time_fields.setdefault(owner, set()).add(field)
    dimensions = _concept_fields(layer)
    for item in layer.entities:
        entity = model.entities[item.entity]
        fields = []
        for fld in entity.fields:
            name = fld.path or fld.name
            row: dict[str, Any] = {"name": name}
            if name in time_fields.get(entity.id, set()):
                row["dimension"] = {"is_time": True}
            elif (entity.id, name) in dimensions:
                row["dimension"] = {"is_time": False}
            fields.append(row)
        datasets.append(
            {
                "name": entity.id,
                "source": entity.physical_name,
                "primary_key": list(entity.keys.primary),
                "fields": fields,
            }
        )
    dialects = _dialects(model, [e.entity for e in layer.entities])
    metrics = []
    for measure in layer.measures or []:
        expression = AGGREGATE[measure.aggregation].format(measure.expression.strip())
        tree = sqlglot.parse_one(expression)
        rendered = [{"dialect": d, "expression": tree.sql(dialect=d)} for d in dialects]
        metrics.append({"name": measure.id, "expression": {"dialects": rendered}})
    document = {
        "semantic_model": [
            {
                "name": layer.id,
                "description": layer.purpose,
                "ai_context": {"instructions": _instructions(model, layer)},
                "datasets": datasets,
                "metrics": metrics,
            }
        ]
    }
    out.files[f"{layer.id}.ossie.yaml"] = dump_yaml(document)
    out.warnings += [
        f"pinned to {SOURCE_URL} read {READ_ON}; version {PINNED_VERSION}",
        "relationships, concepts, hazards and evidence status travel as text in ai_context",
        "dialect identifiers follow sqlglot; the page read names none",
        "no JSON Schema was published at the pinned source; structural tests only",
    ]
    if layer.status != "reviewed":
        out.warnings.append(f"layer {layer.id} is {layer.status}, not reviewed")
    return out

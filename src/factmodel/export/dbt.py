"""Export a layer as dbt semantic models and metrics (MetricFlow YAML).

Pinned to dbt-core 1.12 (validated with ``dbt parse`` in the tests when dbt-core is
installed). One semantic model per layer entity: a primary entity on its key, a foreign entity
per equality join the layer lists, categorical dimensions for the fields its concepts use, a
time dimension from a measure's ``time``, and the layer's measures. Every measure becomes a
simple metric; a required predicate concept that the measure must apply becomes the metric's
filter. Evidence status, hazards and the layer status travel in ``config.meta``.

The project must hold a MetricFlow time spine model (dbt project infrastructure, not part of
a layer). Round-trip notes (what MetricFlow cannot hold, reported as warnings): a time field
that is not a date; a measure whose
aggregation is ``none`` (a formula over aggregates, or a value read at its grain); an
expression join; a distinct rule; a required concept on a field with no fixed value (the
consumer fixes it per query, for example QCEW ``level``); concept value vocabularies.
"""

import re
from typing import Any

from factmodel import vocabulary
from factmodel.adapters.types import type_class
from factmodel.export import Export, entities_in, layer_of, status_of, unqualified
from factmodel.model import joins
from factmodel.model.loader import Model
from factmodel.repo import dump_yaml

AGG = {
    "sum": "sum",
    "count": "count",
    "count_distinct": "count_distinct",
    "avg": "average",
    "min": "min",
    "max": "max",
}


def _name(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", text.lower())


def _filter(predicate: str, entity: str) -> str:
    tree_sql = predicate
    for _, field in sorted(set(joins.parse(predicate).columns), key=lambda c: -len(c[1])):
        ref = "{{ Dimension('" + f"{_name(entity)}__{_name(field)}" + "') }}"
        tree_sql = re.sub(rf"\b{re.escape(entity)}\.{re.escape(field)}\b", ref, tree_sql)
    return tree_sql


def export(model: Model, layer_id: str) -> Export:
    layer = layer_of(model, layer_id)
    out = Export()
    vocabulary.load()
    concepts = {c.id: c for c in layer.concepts or []}
    models: list[dict[str, Any]] = []
    metrics: list[dict[str, Any]] = []
    for item in layer.entities:
        entity = model.entities[item.entity]
        name = _name(entity.id)
        key = entity.keys.primary
        primary = (
            {
                "name": name,
                "type": "primary",
                "expr": " || '|' || ".join(key) if len(key) > 1 else key[0],
            }
            if key
            else None
        )
        sm: dict[str, Any] = {
            "name": name,
            "description": entity.meaning or entity.grain,
            "model": f"ref('{entity.id}')",
            "config": {
                "meta": {
                    "factmodel_layer": layer.id,
                    "factmodel_layer_status": layer.status,
                    "factmodel_evidence_status": status_of(model, entity.id),
                    "factmodel_physical_name": entity.physical_name,
                }
            },
            "entities": [primary] if primary else [],
            "dimensions": [],
            "measures": [],
        }
        for ref in layer.joins or []:
            source, _, key_name = ref.partition(".")
            if source != entity.id:
                continue
            rel = next(r for r in entity.relationships if r.key == key_name)
            parsed = joins.parse(rel.join) if isinstance(rel.join, str) else None
            if parsed is None or parsed.expression or len(parsed.columns) != 2:
                out.warnings.append(f"join {ref}: not a single-field equality; not exported")
                continue
            mine = next(f for e, f in parsed.columns if e == entity.id)
            sm["entities"].append({"name": _name(rel.targets[0]), "type": "foreign", "expr": mine})
        used: set[str] = set()
        for concept in concepts.values():
            if concept.field and concept.field.startswith(f"{entity.id}."):
                used.add(concept.field.split(".", 1)[1])
                if concept.values:
                    out.warnings.append(
                        f"concept {concept.id}: value vocabulary kept only in the meaning"
                    )
            if concept.predicate:
                used |= {f for e, f in joins.parse(concept.predicate).columns if e == entity.id}
            if concept.distinct and any(d.startswith(f"{entity.id}.") for d in concept.distinct):
                out.warnings.append(f"concept {concept.id}: a distinct rule has no MetricFlow form")
        time_dim = None
        for measure in layer.measures or []:
            if measure.grain.entity != entity.id or measure.time is None:
                continue
            time_field = measure.time.field.split(".", 1)[1]
            declared = next((f for f in entity.fields if f.name == time_field), None)
            if declared is not None and type_class(declared.type) not in ("date", "timestamp"):
                out.warnings.append(
                    f"time dimension {entity.id}.{time_field}: type {declared.type} is not a date;"
                    " MetricFlow needs an expression that yields one"
                )
            time_dim = _name(measure.time.field.split(".", 1)[1]) + "_period"
            sm["dimensions"].append(
                {
                    "name": time_dim,
                    "type": "time",
                    "expr": measure.time.field.split(".", 1)[1],
                    "type_params": {"time_granularity": measure.time.granularity},
                }
            )
            break
        for field in sorted(used):
            sm["dimensions"].append({"name": _name(field), "type": "categorical", "expr": field})
        for measure in layer.measures or []:
            if measure.grain.entity != entity.id:
                continue
            if measure.aggregation not in AGG:
                out.warnings.append(
                    f"measure {measure.id}: aggregation {measure.aggregation} has no MetricFlow"
                    " measure (a formula or a value read at its grain); not exported"
                )
                continue
            if entities_in(measure.expression) - {entity.id}:
                out.warnings.append(f"measure {measure.id}: reads several entities; not exported")
                continue
            meta: dict[str, Any] = {"factmodel_suppressed": measure.suppressed or "not_stated"}
            if measure.hazards:
                meta["factmodel_hazards"] = list(measure.hazards)
            sm["measures"].append(
                {
                    "name": _name(measure.id),
                    "description": measure.meaning.strip(),
                    "agg": AGG[measure.aggregation],
                    "expr": unqualified(measure.expression),
                    "config": {"meta": meta},
                }
            )
            metric: dict[str, Any] = {
                "name": _name(measure.id),
                "label": measure.id,
                "description": measure.meaning.strip(),
                "type": "simple",
                "type_params": {"measure": _name(measure.id)},
            }
            filters = []
            for item2 in layer.entities:
                if item2.entity != entity.id:
                    continue
                for cid in item2.default_filters or []:
                    concept = concepts[cid]
                    if concept.predicate and measure.suppressed != "include":
                        filters.append(_filter(concept.predicate, entity.id))
                    elif concept.required and not concept.predicate:
                        out.warnings.append(
                            f"metric {measure.id}: required concept {cid} has no fixed value;"
                            " the query must set it"
                        )
            if filters:
                metric["filter"] = " AND ".join(filters)
            metrics.append(metric)
        if sm["measures"]:
            if time_dim is None:
                out.warnings.append(
                    f"semantic model {name}: no time dimension; measures not exported"
                )
                sm["measures"] = []
            else:
                sm["defaults"] = {"agg_time_dimension": time_dim}
        if not sm["entities"]:
            out.warnings.append(f"semantic model {name}: no primary key; not exported")
            continue
        models.append(sm)
    exported = {m["name"] for sm in models for m in sm["measures"]}
    metrics = [m for m in metrics if m["type_params"]["measure"] in exported]
    for hazard in layer.hazards or []:
        found = model.hazards.get(hazard)
        if found is not None:
            out.warnings.append(
                f"hazard {hazard} ({found.title}) travels only in meta of the measures that name it"
            )
    out.files[f"{layer.id}.yml"] = dump_yaml({"semantic_models": models, "metrics": metrics})
    out.warnings = sorted(set(out.warnings))
    return out

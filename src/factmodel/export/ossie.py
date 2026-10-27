"""Export a layer as an Apache Ossie (formerly Open Semantic Interchange) semantic model.

Two versions of the core specification are pinned, each read once and written only with the
keys it names. Neither publishes a JSON Schema, so the tests are structural.

- **0.1.1, the default** (the released version): the document at tag ``osi-0.1.1-rc1``,
  https://github.com/apache/ossie/blob/osi-0.1.1-rc1/core-spec/spec.md, read 2026-10-27 (round
  29). A ``semantic_model`` list holds the model; no ``version`` key and no field ``datatype``;
  dialects and vendor names come from closed enumerations, so expressions are written as
  ``ANSI_SQL`` (``SNOWFLAKE`` or ``DATABRICKS`` for those engines) and the extensions use vendor
  ``COMMON`` with the framework's keys under ``factmodel`` in the JSON. Keys and
  relationship columns name source columns.
- **0.2.0.dev0** (``--spec-version 0.2.0.dev0``, a draft): the document on ``main``,
  https://github.com/apache/ossie/blob/main/core-spec/spec.md, read 2026-10-27 (round 28). One
  model at the root with ``version``; field ``datatype``; keys, relationship columns and metric
  references name dataset fields; dialect names are free-form (sqlglot names are written,
  ``OSSIE_SQL_2026`` is not) and the vendor name is ``factmodel``.

In both, each entity is a dataset (``name``, ``source``, ``primary_key``, ``description``,
``fields``), each field has ``expression.dialects``, ``description`` and ``dimension.is_time``
for a time field or a concept's field; each equality join to a one side between two layer
entities is a relationship; each measure is a model-level metric (``dataset.field``). What the
documents do not name stays in ``ai_context.instructions`` as text (required concepts,
hazards, evidence status, joins they cannot hold) and in ``custom_extensions`` as JSON.
"""

import json
from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

from factmodel.adapters.base import dialect_for
from factmodel.export import Export, ExportError, layer_of, status_of
from factmodel.model import joins
from factmodel.model.loader import Model
from factmodel.repo import dump_yaml


@dataclass(frozen=True)
class Spec:
    version: str
    url: str
    read_on: str
    note: str
    flat: bool  # one model at the root with `version`, else a `semantic_model` list
    datatype: bool  # fields carry `datatype`
    vendor: str
    dialects: dict[str, str] | None  # sqlglot dialect -> enumeration name; None: free-form


SPECS = {
    "0.1.1": Spec(
        "0.1.1",
        "https://github.com/apache/ossie/blob/osi-0.1.1-rc1/core-spec/spec.md",
        "2026-10-27",
        "the released version, at tag osi-0.1.1-rc1",
        flat=False,
        datatype=False,
        vendor="COMMON",
        dialects={"snowflake": "SNOWFLAKE", "databricks": "DATABRICKS"},
    ),
    "0.2.0.dev0": Spec(
        "0.2.0.dev0",
        "https://github.com/apache/ossie/blob/main/core-spec/spec.md",
        "2026-10-27",
        "a draft, on main",
        flat=True,
        datatype=True,
        vendor="factmodel",
        dialects=None,
    ),
}
DEFAULT_VERSION = "0.1.1"
VENDOR = "factmodel"  # the key, or vendor name, that holds the framework's own metadata
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
DATATYPES = (
    (exp.DataType.TEXT_TYPES, "String"),
    (exp.DataType.INTEGER_TYPES, "Integer"),
    (exp.DataType.REAL_TYPES - exp.DataType.FLOAT_TYPES, "Decimal"),
    (exp.DataType.FLOAT_TYPES, "Float"),
    ({exp.DataType.Type.BOOLEAN}, "Boolean"),
    ({exp.DataType.Type.DATE, exp.DataType.Type.DATE32}, "Date"),
    ({exp.DataType.Type.TIME}, "Time"),
    ({exp.DataType.Type.DATETIME, exp.DataType.Type.TIMESTAMP}, "DateTime"),
    (
        {exp.DataType.Type.TIMESTAMPTZ, exp.DataType.Type.TIMESTAMPLTZ},
        "DateTimeTz",
    ),
)
SWAP = {"many_to_one": False, "one_to_one": False, "one_to_many": True}


def _extension(spec: Spec, data: dict[str, Any]) -> list[dict[str, str]]:
    payload = data if spec.vendor == VENDOR else {VENDOR: data}
    return [{"vendor_name": spec.vendor, "data": json.dumps(payload, sort_keys=True)}]


def _render(tree: exp.Expr, dialects: list[str], spec: Spec) -> list[dict[str, str]]:
    """One entry per dialect; under an enumeration, other engines share neutral ANSI_SQL."""
    out: dict[str, str] = {}
    for dialect in dialects:
        if spec.dialects is None:
            out.setdefault(dialect, tree.sql(dialect=dialect))
        elif dialect in spec.dialects:
            out.setdefault(spec.dialects[dialect], tree.sql(dialect=dialect))
        else:
            out.setdefault("ANSI_SQL", tree.sql())
    return [{"dialect": name, "expression": sql} for name, sql in out.items()]


def _field_name(address: str) -> str:
    """A nested path becomes one name: a dot would read as ``dataset.field``."""
    return address.replace(".", "__")


def _datatype(engine_type: str, dialect: str | None) -> str | None:
    try:
        kind = exp.DataType.build(engine_type, dialect=dialect).this
    except (ParseError, ValueError):
        return None
    for kinds, name in DATATYPES:
        if kind in kinds:
            return name
    return None


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


def _source_dialect(model: Model, entity_id: str) -> str | None:
    source = model.sources.get(model.entities[entity_id].source or "")
    if source is None:
        return None
    try:
        return dialect_for(source.engine, source.dialect)
    except ValueError:
        return None


def _dialects(model: Model, entity_ids: list[str]) -> list[str]:
    found = {_source_dialect(model, entity_id) for entity_id in entity_ids}
    return sorted(d for d in found if d) or list(FALLBACK_DIALECTS)


def _relationship(model: Model, ref: str, members: set[str]) -> dict[str, Any] | None:
    """An Ossie relationship for an equality join between two layer entities, else None."""
    pair = model.relationships.get(ref)
    if pair is None:
        return None
    entity, rel = pair
    if not isinstance(rel.join, str) or not isinstance(rel.to, str) or rel.to not in members:
        return None
    if rel.cardinality not in SWAP:
        return None
    parsed = joins.parse(rel.join)
    if parsed.expression:
        return None
    sides: dict[str, list[str]] = {entity.id: [], rel.to: []}
    columns = list(parsed.columns)
    for left, right in zip(columns[::2], columns[1::2], strict=True):
        if left[0] != entity.id or right[0] != rel.to:
            return None  # a self-reference or a reversed condition: kept as text
        sides[entity.id].append(_field_name(left[1]))
        sides[rel.to].append(_field_name(right[1]))
    many, one = (rel.to, entity.id) if SWAP[rel.cardinality] else (entity.id, rel.to)
    return {
        "name": ref.replace(".", "__"),
        "from": many,
        "to": one,
        "from_columns": sides[many],
        "to_columns": sides[one],
        "ai_context": rel.meaning.strip(),
    }


def _instructions(model: Model, layer: Any, unheld: list[str]) -> str:
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
    if unheld:
        lines.append("Joins the relationships list cannot hold:")
        for ref in unheld:
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


def export(model: Model, layer_id: str, spec_version: str = DEFAULT_VERSION) -> Export:
    spec = SPECS.get(spec_version)
    if spec is None:
        raise ExportError(f"unknown Ossie version {spec_version!r}; one of {', '.join(SPECS)}")
    layer = layer_of(model, layer_id)
    out = Export()
    members = [e.entity for e in layer.entities]
    dialects = _dialects(model, members)
    time_fields: dict[str, set[str]] = {}
    for measure in layer.measures or []:
        if measure.time:
            owner, _, field = measure.time.field.partition(".")
            time_fields.setdefault(owner, set()).add(field)
    dimensions = _concept_fields(layer)
    datasets = []
    for item in layer.entities:
        entity = model.entities[item.entity]
        own = _source_dialect(model, entity.id)
        fields = []
        for fld in entity.fields:
            address = fld.path or fld.name
            column = exp.column(address) if fld.path is None else exp.to_column(address)
            per_dialect = _render(column, dialects, spec)
            row: dict[str, Any] = {
                "name": _field_name(address),
                "expression": {"dialects": per_dialect},
                "description": fld.meaning.strip(),
            }
            datatype = _datatype(fld.type, own) if spec.datatype else None
            if datatype is not None:
                row["datatype"] = datatype
            if address in time_fields.get(entity.id, set()):
                row["dimension"] = {"is_time": True}
            elif (entity.id, address) in dimensions:
                row["dimension"] = {"is_time": False}
            fields.append(row)
        datasets.append(
            {
                "name": entity.id,
                "source": entity.physical_name,
                "primary_key": [_field_name(k) for k in entity.keys.primary],
                "description": entity.grain.strip(),
                "fields": fields,
                "custom_extensions": _extension(
                    spec,
                    {
                        "evidence_status": status_of(model, entity.id),
                        "current_row_rule": item.current_row_rule or entity.keys.current_row_rule,
                        "default_filters": list(item.default_filters or []),
                    },
                ),
            }
        )
    relationships, unheld = [], []
    for ref in layer.joins or []:
        found = _relationship(model, ref, set(members))
        if found is None:
            unheld.append(ref)
        else:
            relationships.append(found)
    metrics = []
    for measure in layer.measures or []:
        expression = AGGREGATE[measure.aggregation].format(measure.expression.strip())
        tree = sqlglot.parse_one(expression)
        rendered = _render(tree, dialects, spec)
        extra: dict[str, Any] = {"aggregation": measure.aggregation}
        extra["grain"] = {"entity": measure.grain.entity, "fields": list(measure.grain.fields)}
        if measure.suppressed:
            extra["suppressed"] = measure.suppressed
        if measure.hazards:
            extra["hazards"] = list(measure.hazards)
        metrics.append(
            {
                "name": measure.id,
                "description": measure.meaning.strip(),
                "expression": {"dialects": rendered},
                "custom_extensions": _extension(spec, extra),
            }
        )
    document: dict[str, Any] = {"version": spec.version} if spec.flat else {}
    document |= {
        "name": layer.id,
        "description": layer.purpose,
        "ai_context": {"instructions": _instructions(model, layer, unheld)},
        "datasets": datasets,
    }
    if relationships:
        document["relationships"] = relationships
    document["metrics"] = metrics
    document["custom_extensions"] = _extension(
        spec,
        {
            "layer_status": layer.status,
            "consumer": layer.consumer,
            "required_concepts": [c.id for c in layer.concepts or [] if c.required],
            "hazards": list(layer.hazards or []),
        },
    )
    if not spec.flat:
        document = {"semantic_model": [document]}
    out.files[f"{layer.id}.ossie.yaml"] = dump_yaml(document)
    where = f"vendor {spec.vendor}" + ("" if spec.vendor == VENDOR else f", key {VENDOR}")
    out.warnings += [
        f"pinned to the Ossie core specification {spec.version} ({spec.note}), read "
        f"{spec.read_on}: {spec.url}",
        "required concepts, hazards and evidence status travel as text in ai_context and as "
        f"JSON in custom_extensions ({where})",
        (
            "dialect names follow sqlglot; OSSIE_SQL_2026 (the only dialect the document "
            "defines) is not written"
            if spec.dialects is None
            else "dialects come from the document's enumeration: engines it does not list are "
            "written once, as neutral ANSI_SQL"
        ),
        "no JSON Schema is published for the pinned version; structural tests only",
    ]
    if not spec.datatype:
        out.warnings.append("field types: the document has no datatype key; not written")
    out.warnings += [
        f"join {ref}: not an equality join to the one side between two layer entities; "
        "kept as text in ai_context"
        for ref in unheld
    ]
    filtered = [m.id for m in layer.measures or [] if m.suppressed]
    if filtered:
        out.warnings.append(
            "Ossie metrics have no filter; suppressed-cell handling is in custom_extensions for "
            + ", ".join(filtered)
        )
    out.warnings += [
        f"measure {m.id}: aggregation none, an expression read at its grain, not an aggregate"
        for m in layer.measures or []
        if m.aggregation == "none" and not sqlglot.parse_one(m.expression).find(exp.AggFunc)
    ]
    if layer.status != "reviewed":
        out.warnings.append(f"layer {layer.id} is {layer.status}, not reviewed")
    return out

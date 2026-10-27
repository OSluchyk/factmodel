"""Exporters (WP3.5): a semantic layer written for another tool.

Each exporter returns the files it writes and a list of warnings for what the target cannot
express; nothing is dropped silently. Evidence status travels as metadata where the target has
a place for it.
"""

from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp

from factmodel.core.status import effective_status
from factmodel.model.loader import Model
from factmodel.model.types import Layer


@dataclass
class Export:
    files: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class ExportError(ValueError):
    """A layer that cannot be exported."""


def layer_of(model: Model, layer_id: str) -> Layer:
    layer = model.layers.get(layer_id)
    if layer is None:
        raise ExportError(f"layer {layer_id!r} not found")
    return layer


def entities_in(expression: str) -> set[str]:
    return {c.table for c in sqlglot.parse_one(expression).find_all(exp.Column) if c.table}


def unqualified(expression: str, dialect: str | None = None) -> str:
    """The expression with entity qualifiers removed (columns of one table)."""
    tree = sqlglot.parse_one(expression)
    for col in tree.find_all(exp.Column):
        col.set("table", None)
    return tree.sql(dialect=dialect)


def status_of(model: Model, entity_id: str) -> str:
    entity = model.entities[entity_id]
    return effective_status(entity.evidence, model.evidence)

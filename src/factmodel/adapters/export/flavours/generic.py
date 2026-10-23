"""Generic flavour: the standard views only. Enforcement follows the vocabulary."""

from typing import Any

from factmodel.adapters.export import (
    Rows,
    fk_enforced,
    standard_constraints,
    standard_fields,
    standard_queries,
)
from factmodel.model.types import Source

EXTRA_VIEWS: tuple[str, ...] = ()


def enforced(engine: str) -> bool:
    return fk_enforced(engine)


def fields(table: str, columns: list[dict[str, Any]], rows: Rows) -> list[dict[str, Any]]:
    return standard_fields(columns)


def constraints(table: str, rows: Rows, is_enforced: bool) -> list[dict[str, Any]]:
    return standard_constraints(table, rows, is_enforced)


def extras(table: str, columns: list[dict[str, Any]], rows: Rows, obj: dict[str, Any]) -> None:
    """Nothing beyond the standard views."""


def export_queries(source: Source) -> dict[str, str]:
    return standard_queries("INFORMATION_SCHEMA.", source.location)

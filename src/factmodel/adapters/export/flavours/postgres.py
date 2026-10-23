"""PostgreSQL flavour: enforced foreign keys, and arrays read from ``udt_name``.

PostgreSQL reports an array column as ``data_type = ARRAY`` with ``udt_name = _<element>``;
the snapshot records the element type and ``repeated: true``.
"""

from typing import Any

from factmodel.adapters.export import (
    Rows,
    fk_enforced,
    standard_constraints,
    standard_fields,
    standard_queries,
)
from factmodel.adapters.types import type_class
from factmodel.model.types import Source

EXTRA_VIEWS: tuple[str, ...] = ()


def enforced(engine: str) -> bool:
    return fk_enforced(engine)


def fields(table: str, columns: list[dict[str, Any]], rows: Rows) -> list[dict[str, Any]]:
    out = standard_fields(columns)
    udt = {c["column_name"]: str(c.get("udt_name") or "") for c in columns}
    for field in out:
        name = udt.get(field["name"], "")
        if str(field["type"]).upper() == "ARRAY" and name.startswith("_"):
            field["type"] = name[1:]
            field["type_class"] = type_class(name[1:])
            field["repeated"] = True
    return out


def constraints(table: str, rows: Rows, is_enforced: bool) -> list[dict[str, Any]]:
    return standard_constraints(table, rows, is_enforced)


def extras(table: str, columns: list[dict[str, Any]], rows: Rows, obj: dict[str, Any]) -> None:
    """Nothing beyond the standard views and udt_name."""


def export_queries(source: Source) -> dict[str, str]:
    queries = standard_queries("information_schema.", source.location or "public")
    queries["COLUMNS"] = queries["COLUMNS"].replace("data_type FROM", "data_type, udt_name FROM")
    return queries

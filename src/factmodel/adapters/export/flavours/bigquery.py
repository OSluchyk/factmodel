"""BigQuery flavour: nested and repeated fields, partitioning, clustering, options.

Extra files read when present: ``COLUMN_FIELD_PATHS`` (nested and repeated fields),
``TABLE_OPTIONS`` (description and options) and ``CONSTRAINT_COLUMN_USAGE`` (foreign key
targets; BigQuery has no ``REFERENTIAL_CONSTRAINTS``). Partitioning and clustering come from
BigQuery's own ``COLUMNS`` columns. BigQuery does not enforce keys: every constraint is
``enforced: false``, and drafts keep foreign keys ``inferred`` until a probe confirms them.
Values may be strings, as the ``bq`` tool writes them.
"""

import json
from typing import Any

from factmodel.adapters.export import CONSTRAINT_TYPES, Rows, yes
from factmodel.adapters.types import type_class
from factmodel.model.types import Source

EXTRA_VIEWS = ("COLUMN_FIELD_PATHS", "TABLE_OPTIONS", "CONSTRAINT_COLUMN_USAGE")


def enforced(engine: str) -> bool:
    return False


def _int(value: Any) -> int | None:
    return None if value in (None, "", "NULL") else int(value)


def _type(data_type: str) -> tuple[str, bool]:
    """Element type text and whether the field repeats."""
    text = data_type.strip()
    repeated = text.upper().startswith("ARRAY<")
    if repeated:
        text = text[6:-1].strip()
    return ("STRUCT" if text.upper().startswith("STRUCT<") else text), repeated


def _option(value: Any) -> str | float | bool | None:
    if value is None or isinstance(value, bool | int | float):
        return value
    text = str(value).strip()
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    if text.startswith('"') and text.endswith('"'):
        try:
            return str(json.loads(text))
        except json.JSONDecodeError:
            return text[1:-1]
    try:
        return float(text) if "." in text else int(text)
    except ValueError:
        return text


def _field(
    name: str, path: str | None, data_type: str, nullable: bool, desc: Any
) -> dict[str, Any]:
    type_text, repeated = _type(data_type)
    item: dict[str, Any] = {"name": name}
    if path:
        item["path"] = path
    item.update({"type": type_text, "type_class": type_class(type_text), "nullable": nullable})
    if repeated:
        item["repeated"] = True
    if desc:
        item["description"] = str(desc)
    return item


def fields(table: str, columns: list[dict[str, Any]], rows: Rows) -> list[dict[str, Any]]:
    paths = [p for p in rows.get("COLUMN_FIELD_PATHS", []) if p["table_name"] == table]
    described = {p["field_path"]: p.get("description") for p in paths}
    ordinal = {c["column_name"]: _int(c.get("ordinal_position")) or 0 for c in columns}
    out = [
        _field(
            c["column_name"],
            None,
            str(c["data_type"]),
            yes(c.get("is_nullable", "YES")),
            described.get(c["column_name"]),
        )
        for c in sorted(columns, key=lambda c: ordinal[c["column_name"]])
    ]
    nested = [p for p in paths if "." in p["field_path"]]
    for p in sorted(nested, key=lambda p: (ordinal.get(p["column_name"], 0), p["field_path"])):
        # The view does not give nested nullability; nested fields are read as nullable.
        path = p["field_path"]
        out.append(
            _field(path.split(".")[-1], path, str(p["data_type"]), True, p.get("description"))
        )
    return out


def constraints(table: str, rows: Rows, is_enforced: bool) -> list[dict[str, Any]]:
    usage = rows.get("KEY_COLUMN_USAGE", [])
    referenced = rows.get("CONSTRAINT_COLUMN_USAGE", [])
    kinds = {
        c["constraint_name"]: str(c["constraint_type"]).upper()
        for c in rows.get("TABLE_CONSTRAINTS", [])
    }
    primary_of: dict[str, list[str]] = {}
    for u in sorted(usage, key=lambda r: _int(r.get("ordinal_position")) or 0):
        if kinds.get(u["constraint_name"]) == "PRIMARY KEY":
            primary_of.setdefault(u["table_name"], []).append(u["column_name"])
    out = []
    for c in rows.get("TABLE_CONSTRAINTS", []):
        if c["table_name"] != table:
            continue
        kind = CONSTRAINT_TYPES.get(str(c["constraint_type"]).upper())
        cols = sorted(
            (u for u in usage if u["constraint_name"] == c["constraint_name"]),
            key=lambda u: _int(u.get("ordinal_position")) or 0,
        )
        if kind is None or not cols:
            continue
        item: dict[str, Any] = {
            "constraint_type": kind,
            "name": str(c["constraint_name"]),
            "fields": [u["column_name"] for u in cols],
        }
        if kind == "foreign_key":
            targets = [r for r in referenced if r["constraint_name"] == c["constraint_name"]]
            if not targets:
                continue
            target_table = targets[0]["table_name"]
            target_pk = primary_of.get(target_table, [])
            positions = [_int(u.get("position_in_unique_constraint")) for u in cols]
            if target_pk and all(p is not None and 0 < p <= len(target_pk) for p in positions):
                ref_fields = [target_pk[p - 1] for p in positions if p is not None]
            else:
                ref_fields = [r["column_name"] for r in targets]
            item["references"] = {"object": target_table, "fields": ref_fields}
        item["enforced"] = is_enforced
        out.append(item)
    return sorted(out, key=lambda i: (i["constraint_type"], i["name"]))


def extras(table: str, columns: list[dict[str, Any]], rows: Rows, obj: dict[str, Any]) -> None:
    options = {
        o["option_name"]: _option(o.get("option_value"))
        for o in rows.get("TABLE_OPTIONS", [])
        if o["table_name"] == table
    }
    description = options.get("description")
    if isinstance(description, str) and description:
        obj["description"] = description
    partition = [c["column_name"] for c in columns if yes(c.get("is_partitioning_column"))]
    if partition:
        obj["partitioning"] = {"field": partition[0]}
    clustered = sorted(
        (c for c in columns if _int(c.get("clustering_ordinal_position")) is not None),
        key=lambda c: _int(c.get("clustering_ordinal_position")) or 0,
    )
    if clustered:
        obj["clustering"] = [c["column_name"] for c in clustered]
    if options:
        obj["options"] = dict(sorted(options.items()))


def export_queries(source: Source) -> dict[str, str]:
    """BigQuery queries; the source's location is ``<project>.<dataset>``."""
    location = source.location or "<project>.<dataset>"
    prefix = f"`{location}`.INFORMATION_SCHEMA."
    return {
        "TABLES": f"SELECT table_schema, table_name, table_type FROM {prefix}TABLES",
        "COLUMNS": (
            "SELECT table_schema, table_name, column_name, ordinal_position, is_nullable, "
            f"data_type, is_partitioning_column, clustering_ordinal_position FROM {prefix}COLUMNS"
        ),
        "COLUMN_FIELD_PATHS": (
            "SELECT table_name, column_name, field_path, data_type, description "
            f"FROM {prefix}COLUMN_FIELD_PATHS"
        ),
        "TABLE_CONSTRAINTS": (
            "SELECT table_name, constraint_name, constraint_type, enforced "
            f"FROM {prefix}TABLE_CONSTRAINTS"
        ),
        "KEY_COLUMN_USAGE": (
            "SELECT table_name, constraint_name, column_name, ordinal_position, "
            f"position_in_unique_constraint FROM {prefix}KEY_COLUMN_USAGE"
        ),
        "CONSTRAINT_COLUMN_USAGE": (
            f"SELECT table_name, column_name, constraint_name FROM {prefix}CONSTRAINT_COLUMN_USAGE"
        ),
        "TABLE_OPTIONS": (
            f"SELECT table_name, option_name, option_value FROM {prefix}TABLE_OPTIONS"
        ),
    }

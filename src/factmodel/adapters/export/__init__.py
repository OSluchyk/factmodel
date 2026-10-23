"""The ``export`` adapter: owner-exported standard ``INFORMATION_SCHEMA`` views, any engine.

The owner runs the SQL that ``fact export-sql`` prints and saves each result in one folder,
one file per view (``TABLES.csv``, ``COLUMNS.json``, ...; CSV with a header row, or JSON as an
array of objects; column names as the standard names them, in any case). The default folder
is ``sources/exports/<source-id>/``; ``fact snapshot --from-export`` names another.

Standard views read by every flavour: ``TABLES``, ``COLUMNS`` (required), ``TABLE_CONSTRAINTS``,
``KEY_COLUMN_USAGE``, ``REFERENTIAL_CONSTRAINTS``. A flavour (``flavours/<engine>.py``) reads
extra files its engine has; engines without a flavour use ``generic``.
"""

import csv
import json
from collections.abc import Mapping
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

from factmodel.adapters.base import (
    AdapterError,
    dialect_for,
    enforces_foreign_keys,
    today,
    warehouse_pin,
)
from factmodel.adapters.types import type_class
from factmodel.model.types import Snapshot, Source

STANDARD_VIEWS = (
    "TABLES",
    "COLUMNS",
    "TABLE_CONSTRAINTS",
    "KEY_COLUMN_USAGE",
    "REFERENTIAL_CONSTRAINTS",
)
REQUIRED_VIEWS = ("TABLES", "COLUMNS")
OBJECT_TYPES = {
    "BASE TABLE": "table",
    "TABLE": "table",
    "SNAPSHOT": "table",
    "CLONE": "table",
    "VIEW": "view",
    "MATERIALIZED VIEW": "materialized_view",
    "EXTERNAL": "external",
    "FOREIGN": "external",
    "FOREIGN TABLE": "external",
}
CONSTRAINT_TYPES = {"PRIMARY KEY": "primary_key", "FOREIGN KEY": "foreign_key", "UNIQUE": "unique"}

Rows = dict[str, list[dict[str, Any]]]


def flavour(engine: str | None) -> ModuleType:
    """The flavour module named after the engine, or ``generic`` when there is none."""
    if engine and engine.replace("_", "").isalnum():
        try:
            return import_module(f"factmodel.adapters.export.flavours.{engine}")
        except ModuleNotFoundError:
            pass
    return import_module("factmodel.adapters.export.flavours.generic")


def read_rows(folder: Path, views: tuple[str, ...]) -> Rows:
    """Read the views present in ``folder``; keys of every row are lowercased."""
    if not folder.is_dir():
        raise AdapterError(f"export folder {folder} does not exist")
    files = {p.stem.upper(): p for p in folder.iterdir() if p.suffix.lower() in (".csv", ".json")}
    rows: Rows = {}
    for view in views:
        path = files.get(view)
        if path is None:
            continue
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise AdapterError(f"{path}: expected a JSON array of rows")
        else:
            with path.open(newline="", encoding="utf-8") as handle:
                data = list(csv.DictReader(handle))
        rows[view] = [{str(k).lower(): v for k, v in row.items()} for row in data]
    missing = [view for view in REQUIRED_VIEWS if view not in rows]
    if missing:
        raise AdapterError(f"{folder}: missing views {missing}")
    return rows


def _int(value: Any) -> int | None:
    return None if value in (None, "", "NULL") else int(value)


def yes(value: Any) -> bool:
    return str(value).strip().upper() in ("YES", "TRUE", "1")


def _schema_filter(rows: Rows, schema: str | None) -> Rows:
    if schema is None:
        return rows
    return {
        view: [r for r in items if r.get("table_schema") in (None, "", schema)]
        for view, items in rows.items()
    }


def _ordered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda r: _int(r.get("ordinal_position")) or 0)


def standard_fields(columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for column in _ordered(columns):
        type_text = str(column["data_type"])
        out.append(
            {
                "name": column["column_name"],
                "type": type_text,
                "type_class": type_class(type_text),
                "nullable": yes(column.get("is_nullable", "YES")),
            }
        )
    return out


def standard_constraints(table: str, rows: Rows, enforced: bool) -> list[dict[str, Any]]:
    """Constraints from TABLE_CONSTRAINTS, KEY_COLUMN_USAGE and REFERENTIAL_CONSTRAINTS."""
    usage = rows.get("KEY_COLUMN_USAGE", [])
    referential = {
        r["constraint_name"]: r["unique_constraint_name"]
        for r in rows.get("REFERENTIAL_CONSTRAINTS", [])
    }
    columns_of = {
        name: _ordered([u for u in usage if u["constraint_name"] == name])
        for name in {u["constraint_name"] for u in usage}
    }
    out = []
    for c in rows.get("TABLE_CONSTRAINTS", []):
        if c["table_name"] != table:
            continue
        kind = CONSTRAINT_TYPES.get(str(c["constraint_type"]).upper())
        cols = columns_of.get(c["constraint_name"], [])
        if kind is None or not cols:
            continue
        item: dict[str, Any] = {
            "constraint_type": kind,
            "name": str(c["constraint_name"]),
            "fields": [u["column_name"] for u in cols],
        }
        if kind == "foreign_key":
            target = columns_of.get(referential.get(c["constraint_name"], ""), [])
            if not target:
                continue
            positions = [_int(u.get("position_in_unique_constraint")) for u in cols]
            if all(p is not None and 0 < p <= len(target) for p in positions):
                ref_fields = [target[p - 1]["column_name"] for p in positions if p is not None]
            else:
                ref_fields = [t["column_name"] for t in target]
            item["references"] = {"object": target[0]["table_name"], "fields": ref_fields}
        item["enforced"] = enforced
        out.append(item)
    return sorted(out, key=lambda i: (i["constraint_type"], i["name"]))


def build(
    rows: Rows, *, source: Source, taken_on: str, flavour_module: ModuleType | None = None
) -> Snapshot:
    """A snapshot from standard rows, after the flavour adds what its engine has."""
    engine = source.engine or "generic"
    module = flavour_module or flavour(source.engine)
    schema = source.location.split(".")[-1] if source.location else None
    rows = _schema_filter(rows, schema)
    enforced = module.enforced(engine)
    objects = []
    for table in rows["TABLES"]:
        name = table["table_name"]
        object_type = OBJECT_TYPES.get(str(table["table_type"]).upper())
        if object_type is None:
            raise AdapterError(f"unknown table_type {table['table_type']!r} for {name}")
        columns = [c for c in rows["COLUMNS"] if c["table_name"] == name]
        obj: dict[str, Any] = {
            "name": name,
            "object_type": object_type,
            "fields": module.fields(name, columns, rows),
        }
        constraints = module.constraints(name, rows, enforced)
        if constraints:
            obj["constraints"] = constraints
        module.extras(name, columns, rows, obj)
        objects.append(obj)
    target = source.location or source.id
    return Snapshot.model_validate(
        {
            "kind": "snapshot",
            "source": source.id,
            "engine": engine,
            "target": target,
            "taken_on": taken_on,
            "pin": warehouse_pin(engine, target, taken_on),
            "objects": sorted(objects, key=lambda o: o["name"]),
        }
    )


class ExportAdapter:
    name = "export"

    def engines(self) -> list[str]:
        return ["*"]

    def default_dialect(self, engine: str) -> str:
        return dialect_for(engine)

    def snapshot(self, source: Source, model_root: Path) -> Snapshot:
        """Read the default export folder ``sources/exports/<source-id>/``."""
        return self.read(model_root / "sources" / "exports" / source.id, source)

    def read(self, folder: Path, source: Source, taken_on: str | None = None) -> Snapshot:
        module = flavour(source.engine)
        rows = read_rows(folder, (*STANDARD_VIEWS, *module.EXTRA_VIEWS))
        return build(rows, source=source, taken_on=taken_on or today(), flavour_module=module)

    def export_sql(self, source: Source) -> str:
        """The SQL the owner runs to produce the export, one query per view."""
        module = flavour(source.engine)
        queries: Mapping[str, str] = module.export_queries(source)
        lines = [
            f"-- Export for source {source.id} (engine {source.engine or 'generic'}).",
            "-- Run each query and save its result in one folder as <VIEW>.csv (with a header",
            "-- row) or <VIEW>.json (an array of objects). Then:",
            f"--   fact snapshot --source {source.id} --from-export <folder>",
            "",
        ]
        for view, sql in queries.items():
            lines += [f"-- {view}", sql.rstrip(";") + ";", ""]
        return "\n".join(lines)


def standard_queries(prefix: str, schema: str | None) -> dict[str, str]:
    """Standard INFORMATION_SCHEMA queries; ``prefix`` qualifies the schema where needed."""
    where = f" WHERE table_schema = '{schema}'" if schema else ""
    cwhere = f" WHERE constraint_schema = '{schema}'" if schema else ""
    return {
        "TABLES": f"SELECT table_schema, table_name, table_type FROM {prefix}TABLES{where}",
        "COLUMNS": (
            "SELECT table_schema, table_name, column_name, ordinal_position, is_nullable, "
            f"data_type FROM {prefix}COLUMNS{where}"
        ),
        "TABLE_CONSTRAINTS": (
            "SELECT table_schema, table_name, constraint_name, constraint_type "
            f"FROM {prefix}TABLE_CONSTRAINTS{where}"
        ),
        "KEY_COLUMN_USAGE": (
            "SELECT table_schema, table_name, constraint_name, column_name, ordinal_position, "
            f"position_in_unique_constraint FROM {prefix}KEY_COLUMN_USAGE{where}"
        ),
        "REFERENTIAL_CONSTRAINTS": (
            "SELECT constraint_name, unique_constraint_name "
            f"FROM {prefix}REFERENTIAL_CONSTRAINTS{cwhere}"
        ),
    }


def fk_enforced(engine: str) -> bool:
    return enforces_foreign_keys(engine)

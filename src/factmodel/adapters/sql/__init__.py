"""The ``sql`` adapter: live reflection through SQLAlchemy 2, any engine with a dialect.

Reads tables, views, columns, primary keys, unique constraints, foreign keys and comments
with ``sqlalchemy.inspect``. The connection string comes only from the environment variable
the source names in ``dsn_env``; it is never written to a file or a log. Whether constraints
are enforced follows ``vocabulary:engine_enforces_foreign_keys``. Needs the extra ``[sql]``
and a driver extra for the engine (for example ``[postgres]``).
"""

import os
from collections.abc import Mapping
from pathlib import Path
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


def dsn(source: Source, env: Mapping[str, str] | None = None) -> str:
    env = os.environ if env is None else env
    if not source.dsn_env:
        raise AdapterError(f"source {source.id!r} names no dsn_env")
    value = env.get(source.dsn_env)
    if not value:
        raise AdapterError(f"environment variable {source.dsn_env} is not set")
    return value


def _target(source: Source, database: str | None) -> str:
    if source.location:
        return source.location
    name = Path(database).stem if database else ""
    return name or source.id


def _type_text(sql_type: Any) -> str:
    try:
        return str(sql_type)
    except Exception:  # some reflected types cannot compile without a dialect
        return type(sql_type).__name__.upper()


def _constraints(insp: Any, table: str, enforced: bool) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pk = insp.get_pk_constraint(table) or {}
    if pk.get("constrained_columns"):
        out.append(
            {
                "constraint_type": "primary_key",
                "name": pk.get("name") or f"pk_{table}",
                "fields": list(pk["constrained_columns"]),
                "enforced": enforced,
            }
        )
    for unique in insp.get_unique_constraints(table):
        out.append(
            {
                "constraint_type": "unique",
                "name": unique.get("name") or f"uq_{table}_{'_'.join(unique['column_names'])}",
                "fields": list(unique["column_names"]),
                "enforced": enforced,
            }
        )
    for fk in insp.get_foreign_keys(table):
        cols = list(fk["constrained_columns"])
        out.append(
            {
                "constraint_type": "foreign_key",
                "name": fk.get("name") or f"fk_{table}_{'_'.join(cols)}",
                "fields": cols,
                "references": {
                    "object": fk["referred_table"],
                    "fields": list(fk["referred_columns"]),
                },
                "enforced": enforced,
            }
        )
    return sorted(out, key=lambda c: (c["constraint_type"], c["name"]))


def _object(insp: Any, name: str, object_type: str, enforced: bool) -> dict[str, Any]:
    fields = []
    for column in insp.get_columns(name):
        text = _type_text(column["type"])
        item: dict[str, Any] = {
            "name": column["name"],
            "type": text,
            "type_class": type_class(text),
            "nullable": bool(column.get("nullable", True)),
        }
        if column.get("comment"):
            item["description"] = str(column["comment"])
        fields.append(item)
    obj: dict[str, Any] = {"name": name, "object_type": object_type, "fields": fields}
    try:
        comment = (insp.get_table_comment(name) or {}).get("text")
    except NotImplementedError:
        comment = None
    if comment:
        obj["description"] = str(comment)
    if object_type == "table":
        constraints = _constraints(insp, name, enforced)
        if constraints:
            obj["constraints"] = constraints
    return obj


class SqlAdapter:
    name = "sql"

    def engines(self) -> list[str]:
        return ["*"]

    def default_dialect(self, engine: str) -> str:
        return dialect_for(engine)

    def snapshot(self, source: Source, model_root: Path) -> Snapshot:
        return self.reflect(source, dsn(source))

    def reflect(self, source: Source, url: str, taken_on: str | None = None) -> Snapshot:
        try:
            from sqlalchemy import create_engine, inspect
        except ImportError as error:
            raise AdapterError("the sql adapter needs the extra: uv sync --extra sql") from error
        engine_name = source.engine
        if engine_name is None:
            raise AdapterError(f"source {source.id!r} names no engine")
        enforced = enforces_foreign_keys(engine_name)
        engine = create_engine(url)
        try:
            insp = inspect(engine)
            objects = [_object(insp, t, "table", enforced) for t in sorted(insp.get_table_names())]
            objects += [_object(insp, v, "view", enforced) for v in sorted(insp.get_view_names())]
            database = engine.url.database
        finally:
            engine.dispose()
        target = _target(source, database)
        day = taken_on or today()
        return Snapshot.model_validate(
            {
                "kind": "snapshot",
                "source": source.id,
                "engine": engine_name,
                "target": target,
                "taken_on": day,
                "pin": warehouse_pin(engine_name, target, day),
                "objects": sorted(objects, key=lambda o: o["name"]),
            }
        )


def target_of(source: Source, url: str) -> str:
    """The target name a pin uses for this source, without any part of the connection string."""
    from sqlalchemy.engine import make_url

    return _target(source, make_url(url).database)


def measure(url: str, queries: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """Run count queries; one result per query: ``{probe, measurement}`` or ``{probe, error}``.

    Values are kept only when they are numbers; a failed query records ``QUERY FAILED`` and the
    run goes on, as the rendered scripts do.
    """
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    results: list[dict[str, Any]] = []
    try:
        for probe_id, sql in queries:
            try:
                with engine.connect() as conn:
                    row = conn.execute(text(sql)).mappings().first()
            except Exception:  # the error text may quote data; never keep it
                results.append({"probe": probe_id, "error": "QUERY FAILED"})
                continue
            values = {str(k): v for k, v in dict(row or {}).items()}
            measurement = {
                k: (int(v) if float(v).is_integer() else float(v))
                for k, v in values.items()
                if isinstance(v, int | float) or _numeric(v)
            }
            results.append({"probe": probe_id, "measurement": measurement})
    finally:
        engine.dispose()
    return results


def _numeric(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return not isinstance(value, bool | str)

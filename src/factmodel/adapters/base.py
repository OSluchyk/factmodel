"""The adapter protocol, and engine facts every adapter reads from the vocabulary.

An adapter turns one kind of source into a ``Snapshot`` (``schemas/snapshot.schema.json``),
the only contract between adapters and the core (D-011). Engine knowledge the framework
needs (default dialects, which engines enforce foreign keys) is vocabulary, not code.
"""

import datetime
import re
from pathlib import Path
from typing import Protocol

from factmodel import vocabulary
from factmodel.model.types import Snapshot, Source


class AdapterError(ValueError):
    """A source cannot be read by its adapter as configured."""


class Adapter(Protocol):
    name: str

    def engines(self) -> list[str]: ...

    def snapshot(self, source: Source, model_root: Path) -> Snapshot: ...

    def default_dialect(self, engine: str) -> str: ...


def dialect_for(engine: str | None, explicit: str | None = None) -> str:
    """The sqlglot dialect: the source's own, else the vocabulary's default for the engine."""
    if explicit:
        return explicit
    known = vocabulary.load_maps()["engine_dialect"]
    if engine is None or engine not in known:
        raise AdapterError(f"engine {engine!r} has no default dialect; set dialect on the source")
    return known[engine]


def enforces_foreign_keys(engine: str | None) -> bool:
    return engine in vocabulary.load()["engine_enforces_foreign_keys"]


def today() -> str:
    return datetime.date.today().isoformat()


def warehouse_pin(engine: str, target: str, taken_on: str) -> str:
    """Warehouse pin format: ``<engine>:<target>@<YYYY-MM-DD>``."""
    return f"{engine}:{target}@{taken_on}"


def with_date(snap: Snapshot, taken_on: str) -> Snapshot:
    """The same snapshot read on another date; the date part of its pin follows."""
    pin = snap.pin
    if pin is not None:
        pin = re.sub(r"@\d{4}-\d{2}-\d{2}$", f"@{taken_on}", pin)
    return snap.model_copy(update={"taken_on": taken_on, "pin": pin})

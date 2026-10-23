"""Find adapters through the entry-point group ``factmodel.adapters``.

Built-in adapters register in ``pyproject.toml`` exactly as a third-party package would, so
adding an engine never needs a change to the core (D-011).
"""

from collections.abc import Callable, Iterable
from importlib.metadata import EntryPoint, entry_points
from typing import Any, cast

from factmodel.adapters.base import Adapter, AdapterError

GROUP = "factmodel.adapters"
BUILT_IN = ("export", "sql", "git")

# Indirection so tests can stand in a fake third-party entry point.
_entry_points: Callable[[], Iterable[EntryPoint]] = lambda: entry_points(group=GROUP)  # noqa: E731


def _instance(loaded: Any) -> Adapter:
    return cast(Adapter, loaded() if isinstance(loaded, type) else loaded)


def adapters() -> dict[str, Adapter]:
    """Every installed adapter by name, sorted."""
    found: dict[str, Adapter] = {}
    for point in sorted(_entry_points(), key=lambda p: p.name):
        found[point.name] = _instance(point.load())
    return found


def get(name: str | None) -> Adapter:
    if name is None:
        raise AdapterError("the source names no adapter; set adapter on the source")
    installed = adapters()
    if name not in installed:
        raise AdapterError(f"adapter {name!r} is not installed ({', '.join(installed) or 'none'})")
    return installed[name]

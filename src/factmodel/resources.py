"""Files the framework ships: profiles, agent templates, the vocabulary.

In a wheel they sit inside the package (``pyproject.toml``, ``force-include``). In a source
checkout they sit at the repository root, so the lookup falls back to that.
"""

from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def framework_file(*parts: str) -> Traversable | None:
    """Return a shipped file or folder, or None when it does not exist."""
    packaged = resources.files("factmodel").joinpath(*parts)
    if packaged.is_file() or packaged.is_dir():
        return packaged
    repo = _REPO_ROOT.joinpath(*parts)
    return repo if repo.exists() else None


def framework_text(*parts: str) -> str | None:
    found = framework_file(*parts)
    return found.read_text(encoding="utf-8") if found is not None and found.is_file() else None

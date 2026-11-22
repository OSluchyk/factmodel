"""Files the framework ships: profiles, agent templates, the vocabulary.

In a wheel they sit inside the package (``pyproject.toml``, ``force-include``). In a source
checkout they sit at the repository root, so the lookup falls back to that.
"""

from collections.abc import Iterator
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


def owned(entry: Traversable) -> bool:
    """Whether a shipped file or folder is the framework's: dot files (a Finder ``.DS_Store``,
    an editor's swap file) are not."""
    return not entry.name.startswith(".")


def shipped_texts(folder: Traversable, prefix: str = "") -> Iterator[tuple[str, str]]:
    """(relative path, text) of every file the framework owns under ``folder``, sorted; a file
    that is not UTF-8 is not a template and is skipped, never an error."""
    for entry in sorted(folder.iterdir(), key=lambda e: e.name):
        if not owned(entry):
            continue
        name = f"{prefix}{entry.name}"
        if entry.is_dir():
            yield from shipped_texts(entry, f"{name}/")
        elif entry.is_file():
            try:
                yield name, entry.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

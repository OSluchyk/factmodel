"""Corpus items: one YAML file per item under the layer's corpus folder (``corpus/*.yaml``)."""

from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

from factmodel import vocabulary
from factmodel.io.yaml_strict import load
from factmodel.model.types import FindingId, Slug, Strict, Text


class CorpusError(ValueError):
    """A corpus that cannot be read."""


class CorpusItem(Strict):
    id: Slug
    request: dict[str, Any]
    reference: Text
    mode: str
    note: Text | None = None
    # D-021: why the consumer may fail this item, or the finding that records the failure
    known_gap: Text | None = None
    finding: FindingId | None = None
    tags: Annotated[list[Slug], Field(min_length=1)] | None = None


def read_corpus(folder: Path) -> list[CorpusItem]:
    """Every item in ``folder``, sorted by id; ids are unique."""
    if not folder.is_dir():
        raise CorpusError(f"corpus folder {folder} does not exist")
    modes = vocabulary.load()["equivalence_mode"]
    items: list[CorpusItem] = []
    for path in sorted(folder.glob("*.yaml")):
        data = load(path).data
        try:
            item = CorpusItem.model_validate(data)
        except ValueError as error:
            raise CorpusError(f"{path}: {error}") from error
        if item.mode not in modes:
            raise CorpusError(f"{path}: mode {item.mode!r} is not one of {modes}")
        items.append(item)
    ids = [i.id for i in items]
    if len(ids) != len(set(ids)):
        raise CorpusError(f"{folder}: corpus item ids repeat")
    return sorted(items, key=lambda i: i.id)

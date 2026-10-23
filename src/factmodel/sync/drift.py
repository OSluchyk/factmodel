"""Drift between two snapshots of a source and the model (spec/VOCABULARY.md, section 11).

A pure function over snapshots and entities. It never names an engine: it compares names,
nullability, ``type_class`` and declared constraints, the neutral parts of a snapshot.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from factmodel.core.drafts import slug
from factmodel.model.types import Entity, Snapshot, SnapshotField, SnapshotObject


@dataclass(frozen=True, order=True)
class DriftItem:
    object: str
    field: str
    kind: str
    drift_class: str
    detail: str
    entity: str | None

    @property
    def key(self) -> str:
        """A stable identity for the item, used to avoid opening the same finding twice."""
        return f"{self.kind}:{self.object}" + (f".{self.field}" if self.field else "")


def _fields(obj: SnapshotObject) -> dict[str, SnapshotField]:
    return {f.path or f.name: f for f in obj.fields}


def _constraints(obj: SnapshotObject) -> set[tuple[str, tuple[str, ...], str]]:
    out = set()
    for c in obj.constraints or []:
        ref = f"{c.references.object}({','.join(c.references.fields)})" if c.references else ""
        out.add((c.constraint_type, tuple(c.fields), ref))
    return out


def modelled(entities: Mapping[str, Entity], source: str | None) -> dict[str, Entity]:
    """Entities of this source, by the engine name of their object."""
    found: dict[str, Entity] = {}
    for entity in entities.values():
        if entity.source == source:
            found[entity.physical_name] = entity
    return found


def drift(
    previous: Snapshot | None, latest: Snapshot, entities: Mapping[str, Entity]
) -> list[DriftItem]:
    """Every change, classified. Without a previous snapshot, every object counts as new."""
    model = modelled(entities, latest.source)
    before = {o.name: o for o in previous.objects} if previous else {}
    after = {o.name: o for o in latest.objects}
    items: list[DriftItem] = []

    def add(obj: str, field: str, kind: str, cls: str, detail: str) -> None:
        entity = model.get(obj)
        items.append(DriftItem(obj, field, kind, cls, detail, entity.id if entity else None))

    for name in sorted(set(after) - set(before)):
        known = name in model
        detail = "already modelled" if known else f"draft entity {slug(name)}"
        add(name, "", "new_object", "no_effect" if known else "new_fact", detail)
    for name in sorted((set(before) | set(model)) - set(after)):
        add(name, "", "dropped_object", "lost_fact" if name in model else "no_effect", "gone")
    for name in sorted(set(before) & set(after)):
        entity = model.get(name)
        old, new = _fields(before[name]), _fields(after[name])
        addresses = {f.address for f in entity.fields} if entity else set()

        known = entity is not None

        def cls(changed: str, known: bool = known) -> str:
            return changed if known else "no_effect"

        for address in sorted(set(new) - set(old)):
            has = address in addresses
            add(name, address, "new_field", "no_effect" if has or not entity else "new_fact", "")
        for address in sorted(set(old) - set(new)):
            gone = "lost_fact" if address in addresses else "no_effect"
            add(name, address, "dropped_field", gone, "")
        for address in sorted(set(old) & set(new)):
            a, b = old[address], new[address]
            if a.type_class != b.type_class:
                detail = f"{a.type_class} -> {b.type_class}"
                add(name, address, "type_class_change", cls("changed_fact"), detail)
            elif a.type != b.type:
                add(name, address, "type_text_change", "no_effect", f"{a.type} -> {b.type}")
            if a.nullable != b.nullable:
                detail = f"nullable {str(a.nullable).lower()} -> {str(b.nullable).lower()}"
                add(name, address, "nullability_change", cls("changed_fact"), detail)
        if _constraints(before[name]) != _constraints(after[name]):
            removed = sorted(_constraints(before[name]) - _constraints(after[name]))
            added = sorted(_constraints(after[name]) - _constraints(before[name]))
            detail = "; ".join(
                f"{verb} {kind}({', '.join(cols)}){' -> ' + ref if ref else ''}"
                for verb, group in (("removed", removed), ("added", added))
                for kind, cols, ref in group
            )
            add(name, "", "constraint_change", cls("changed_fact"), detail)
    return sorted(items)

"""From a snapshot to entity drafts (``to_facts``): one core function for every adapter.

Drafts are engine-neutral by construction: they hold what the snapshot declares and nothing
else. Declared foreign keys become ``declared_fk`` relationships whose evidence is ``confirmed``
when the engine enforces them and ``inferred`` when it does not. Class is ``data`` as a
placeholder, the entity is ``status: draft``, and every placeholder is listed under
``extensions.draft`` so the person reviewing it sees what is still to be written, with the engine's
constraint names under ``extensions.draft.constraint_name``. A comment or description from the
source becomes the meaning it proposes, cited by an ``inferred`` record that quotes it.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from factmodel.model.types import Constraint, Snapshot, SnapshotObject
from factmodel.schemas.build import pattern

GRAIN_PLACEHOLDER = "Not written yet: one sentence on what one row is."
MEANING_PLACEHOLDER = "Not written yet."
QUOTE_WORDS = 40


@dataclass(frozen=True)
class EntityDraft:
    """One proposed entity file: a path relative to the model root and its document."""

    path: str
    document: dict[str, Any]


def slug(name: str) -> str:
    """A model ID for an engine name: lowercase, camel case split, other characters as ``_``."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)
    value = re.sub(r"[^a-z0-9_-]+", "_", spaced.lower()).strip("_-")
    if len(value) > 64 or not re.match(pattern("slug"), value):
        digest = hashlib.sha1(name.encode()).hexdigest()[:8]
        value = f"{value[:55].strip('_-') or 'x'}_{digest}"
    return value


def _evidence_id(*parts: str) -> str:
    value = "-".join(["ev", *parts])
    return value if len(value) <= 64 else slug(value)


def _primary(obj: SnapshotObject) -> list[str]:
    for constraint in obj.constraints or []:
        if constraint.constraint_type == "primary_key":
            return list(constraint.fields)
    return []


def _foreign_keys(obj: SnapshotObject) -> list[Constraint]:
    return [
        c
        for c in obj.constraints or []
        if c.constraint_type == "foreign_key" and c.references is not None
    ]


def _keys(obj: SnapshotObject) -> dict[int, str]:
    """Relationship keys: ``to-<target>``, with the columns when one target appears twice."""
    fks = _foreign_keys(obj)
    targets = [slug(c.references.object) for c in fks if c.references is not None]
    keys = {}
    for i, (constraint, target) in enumerate(zip(fks, targets, strict=True)):
        key = f"to-{target}"
        if targets.count(target) > 1:
            key += "-" + "-".join(slug(f) for f in constraint.fields)
        keys[i] = key.replace("_", "-")[:64].strip("-")
    return keys


def _comment(
    records: list[dict[str, Any]], entity_id: str, suffix: str, text: str, snap: Snapshot, pin: str
) -> str:
    """Add an inferred record quoting a comment from the source; a comment is a claim."""
    record_id = _evidence_id(entity_id, "comment", suffix)
    records.append(
        {
            "id": record_id,
            "source": snap.source,
            "pin": pin,
            "quote": " ".join(text.split()[:QUOTE_WORDS]),
            "status": "inferred",
            "read_on": snap.taken_on,
        }
    )
    return record_id


def to_facts(snap: Snapshot) -> list[EntityDraft]:
    """One entity draft per snapshot object, sorted by object name."""
    if snap.source is None:
        raise ValueError("a snapshot needs its source ID to produce drafts")
    by_name = {obj.name: obj for obj in snap.objects}
    drafts = []
    for obj in sorted(snap.objects, key=lambda o: o.name):
        pin = obj.pin or snap.pin
        if pin is None:
            raise ValueError(f"no pin for {obj.name}: set the snapshot's or the object's pin")
        entity_id = slug(obj.name)
        catalog = _evidence_id(entity_id, "catalog")
        records: list[dict[str, Any]] = [
            {
                "id": catalog,
                "source": snap.source,
                "pin": pin,
                "quote": f"{obj.object_type} {obj.name} in {snap.target}",
                "status": "confirmed",
                "read_on": snap.taken_on,
            }
        ]
        placeholders = ["grain", "class"]

        entity_evidence = [catalog]
        if obj.description:
            entity_evidence.append(
                _comment(records, entity_id, "table", obj.description, snap, pin)
            )
        fields = []
        for fld in obj.fields:
            address = fld.path or fld.name
            if fld.description is None:
                placeholders.append(f"fields.{address}.meaning")
            item: dict[str, Any] = {"name": fld.name}
            if fld.path:
                item["path"] = fld.path
            item.update({"type": fld.type, "nullable": fld.nullable})
            if fld.repeated:
                item["repeated"] = True
            item["meaning"] = fld.description or MEANING_PLACEHOLDER
            if fld.description:
                suffix = slug(address).replace("_", "-")
                record = _comment(records, entity_id, suffix, fld.description, snap, pin)
                item["evidence"] = [catalog, record]
            fields.append(item)
        relationships = []
        constraint_names: dict[str, str] = {}
        keys = _keys(obj)
        for i, constraint in enumerate(_foreign_keys(obj)):
            ref = constraint.references
            assert ref is not None
            target = slug(ref.object)
            key = keys[i]
            evidence_id = _evidence_id(entity_id, key)
            if constraint.name:
                constraint_names[key] = constraint.name
            enforced = "enforced" if constraint.enforced else "not enforced"
            columns = ", ".join(constraint.fields)
            records.append(
                {
                    "id": evidence_id,
                    "source": snap.source,
                    "pin": pin,
                    "quote": f"foreign key {columns} to {ref.object} ({enforced})",
                    # A constraint the engine does not check is a claim until a probe checks it.
                    "status": "confirmed" if constraint.enforced else "inferred",
                    "read_on": snap.taken_on,
                }
            )
            target_obj = by_name.get(ref.object)
            unique_target = target_obj is not None and _primary(target_obj) == list(ref.fields)
            join = " AND ".join(
                f"{entity_id}.{a} = {target}.{b}"
                for a, b in zip(constraint.fields, ref.fields, strict=True)
            )
            relationships.append(
                {
                    "key": key,
                    "to": target,
                    "join": join,
                    "meaning": f"Declared foreign key to {ref.object}; meaning not written yet.",
                    "mechanism": "declared_fk",
                    "cardinality": "many_to_one" if unique_target else "unknown",
                    "evidence": [evidence_id],
                }
            )
            placeholders.append(f"relationships.{key}.meaning")
        document: dict[str, Any] = {
            "kind": "entity",
            "id": entity_id,
            "physical_name": obj.name,
            "source": snap.source,
            "grain": GRAIN_PLACEHOLDER,
            "class": "data",
            "status": "draft",
            "keys": {"primary": _primary(obj)},
            "evidence": entity_evidence,
            "fields": fields,
        }
        if obj.description:
            document["meaning"] = obj.description
        if relationships:
            document["relationships"] = relationships
        document["records"] = records
        draft: dict[str, Any] = {"from": pin, "placeholders": placeholders}
        if constraint_names:
            # The engine's own names, for traceability; relationship keys stay engine-neutral.
            draft["constraint_name"] = constraint_names
        document["extensions"] = {"draft": draft}
        drafts.append(EntityDraft(f"drafts/{snap.source}/entities/{entity_id}.yaml", document))
    return drafts

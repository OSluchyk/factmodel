"""Build typed inputs for the core algorithms straight from vector files."""

from pathlib import Path
from typing import Any

from factmodel.core.derived import Derived
from factmodel.core.release import ReleaseInput
from factmodel.io.yaml_strict import load
from factmodel.model.types import Entity, EvidenceRecord, Profile, ReleaseAllowlist

VECTORS = Path(__file__).resolve().parents[1] / "vectors"


def vector(algorithm: str, case: str) -> dict[str, Any]:
    data: dict[str, Any] = load(VECTORS / algorithm / f"{case}.yaml").data
    return data


def cases(algorithm: str) -> list[str]:
    return sorted(p.stem for p in (VECTORS / algorithm).glob("*.yaml"))


def typed_inputs(
    files: list[dict[str, Any]],
) -> tuple[dict[str, Entity], dict[str, EvidenceRecord], Profile, str]:
    entities = {f["id"]: Entity.model_validate(f) for f in files if f["kind"] == "entity"}
    evidence = {
        r["id"]: EvidenceRecord.model_validate(r) for f in files for r in f.get("records", [])
    }
    profile = Profile.model_validate(next(f for f in files if f["kind"] == "profile"))
    anchor = next(f for f in files if f["kind"] == "model-config")["anchor_entity"]
    return entities, evidence, profile, anchor


def scope_rows(derived: Derived) -> list[dict[str, Any]]:
    return [
        {
            "entity": row.entity,
            "subject_scope": row.subject_scope,
            "basis": row.basis or "-",
            "via": " > ".join(row.via) or "-",
            "reachable": row.reachable,
        }
        for row in derived.scope.rows.values()
    ]


def rejection_rows(derived: Derived) -> list[dict[str, str]]:
    return [{"fact": r.fact, "reason": r.reason} for r in derived.scope.rejections]


def label_rows(derived: Derived) -> list[dict[str, str]]:
    return [
        {
            "relationship": label.relationship,
            "label": label.label,
            "targets": ", ".join(f"{t}={v}" for t, v in label.targets) or "-",
        }
        for label in derived.projection.labels
    ]


def residue_rows(derived: Derived) -> list[dict[str, str]]:
    return [
        {"relationship": r.relationship, "target": r.target} for r in derived.projection.residue
    ]


def release_inputs(
    files: list[dict[str, Any]],
) -> tuple[ReleaseAllowlist, list[ReleaseInput]]:
    allowlist = next(
        ReleaseAllowlist.model_validate(f["document"])
        for f in files
        if f["document"] and f["document"]["kind"] == "release-allowlist"
    )
    inputs = [
        ReleaseInput(
            f["path"],
            f["document"]["kind"] if f["document"] else None,
            tuple(f["document"]) if f["document"] else (),
        )
        for f in files
    ]
    return allowlist, inputs

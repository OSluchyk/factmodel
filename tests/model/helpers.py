"""Write small model repositories for tests."""

import io
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from factmodel.io.yaml_strict import load

VECTORS = Path(__file__).resolve().parents[1] / "vectors"

CONFIG = {
    "kind": "model-config",
    "id": "test",
    "framework_version": "0.0.1",
    "profile": "retail",
    "anchor_entity": "users",
}


def dump(doc: Any) -> str:
    yaml = YAML(typ="safe", pure=True)
    yaml.default_flow_style = False
    yaml.sort_base_mapping_type_on_output = False
    buf = io.StringIO()
    yaml.dump(doc, buf)
    return buf.getvalue()


def path_for(doc: dict[str, Any]) -> str:
    kind = doc["kind"]
    ident = doc.get("id", "file")
    return {
        "model-config": "factmodel.yaml",
        "source": f"sources/{ident}.yaml",
        "entity": f"physical/entities/{ident}.yaml",
        "service": f"physical/services/{ident}.yaml",
        "tenants": "physical/tenants.yaml",
        "evidence": "evidence/shared.yaml",
        "profile": f"profiles/{ident}/profile.yaml",
        "hazard": f"registers/hazards/{ident}.yaml",
        "finding": f"registers/findings/{ident}.yaml",
        "escalation": f"registers/escalations/{ident}.yaml",
        "decision": f"registers/decisions/{ident}.yaml",
        "layer": f"semantic/{ident}/layer.yaml",
        "consumer": f"semantic/consumers/{ident}.yaml",
    }.get(kind, f"{kind}/{ident}.yaml")


def write_model(root: Path, files: dict[str, Any] | list[dict[str, Any]]) -> Path:
    """Write files (a path-to-document map, or documents placed by kind) under ``root``.

    A document may be a string, written as is. ``factmodel.yaml`` is added when missing.
    """
    items = files if isinstance(files, dict) else {path_for(doc): doc for doc in files}
    if "factmodel.yaml" not in items:
        items = {"factmodel.yaml": CONFIG, **items}
    for rel, doc in items.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(doc if isinstance(doc, str) else dump(doc), encoding="utf-8")
    return root


def vector_files(algorithm: str, case: str) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = load(VECTORS / algorithm / f"{case}.yaml").data["input"]["files"]
    return files

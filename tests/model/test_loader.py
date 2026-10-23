import copy
from pathlib import Path
from typing import Any

import pytest

from factmodel.model.loader import (
    LoadIssue,
    ModelLoadError,
    discover,
    inspect_model,
    load_model,
)
from factmodel.model.types import Entity
from tests.model.helpers import VECTORS, vector_files, write_model

MODEL_VECTORS = sorted(
    (p.parent.name, p.stem) for p in VECTORS.glob("*/*.yaml") if p.parent.name != "release"
)


def _base() -> list[dict[str, Any]]:
    return copy.deepcopy(vector_files("projection", "rule-customer-scoped"))


def _entity(files: list[dict[str, Any]], entity_id: str) -> dict[str, Any]:
    return next(f for f in files if f["kind"] == "entity" and f["id"] == entity_id)


def _issues(root: Path) -> list[LoadIssue]:
    return list(inspect_model(root).issues)


def _only(root: Path, code: str) -> LoadIssue:
    issues = _issues(root)
    assert [i.code for i in issues] == [code], [str(i) for i in issues]
    issue = issues[0]
    assert issue.hint and issue.line >= 1 and issue.column >= 1
    return issue


@pytest.mark.parametrize(("algorithm", "case"), MODEL_VECTORS)
def test_every_model_vector_loads_cleanly(tmp_path: Path, algorithm: str, case: str) -> None:
    model = load_model(write_model(tmp_path, vector_files(algorithm, case)))
    assert model.profile is not None and model.profile.id == "retail"
    assert model.config is not None


def test_model_contents(tmp_path: Path) -> None:
    model = load_model(write_model(tmp_path, _base()))
    assert sorted(model.entities) == ["order_items", "orders", "products", "users"]
    assert isinstance(model.entities["orders"], Entity)
    assert model.entities["orders"].class_ == "data"
    assert "ev-retracted" in model.evidence
    assert sorted(model.relationships) == [
        "order_items.part-of",
        "order_items.sells",
        "orders.placed-by",
    ]
    assert list(model.sources) == ["shop-db"]


def test_missing_entity(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "order_items")["relationships"][1]["to"] = "catalog"
    issue = _only(write_model(tmp_path, files), "missing_entity")
    assert issue.stage == "references"
    assert issue.file == "physical/entities/order_items.yaml"
    assert "catalog" in issue.message


def test_missing_evidence_id(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "orders")["evidence"] = ["ev-nowhere"]
    issue = _only(write_model(tmp_path, files), "missing_evidence")
    assert issue.file == "physical/entities/orders.yaml"


def test_duplicate_evidence_id(tmp_path: Path) -> None:
    files = _base()
    record = {
        "id": "ev-confirmed",
        "source": "shop-db",
        "pin": "postgres:shop.public@2026-11-01",
        "quote": "again",
        "status": "confirmed",
        "read_on": "2026-11-01",
    }
    _entity(files, "orders")["records"] = [record]
    issue = _only(write_model(tmp_path, files), "duplicate_evidence")
    assert issue.file == "physical/entities/orders.yaml"
    assert "evidence/shared.yaml" in issue.message


def test_duplicate_relationship_key(tmp_path: Path) -> None:
    files = _base()
    rels = _entity(files, "order_items")["relationships"]
    rels[1]["key"] = rels[0]["key"]
    issue = _only(write_model(tmp_path, files), "duplicate_relationship_key")
    assert issue.message == "relationship key 'part-of' repeats in 'order_items'"


def test_unregistered_source(tmp_path: Path) -> None:
    files = _base()
    next(f for f in files if f["kind"] == "evidence")["records"][0]["source"] = "crm"
    issue = _only(write_model(tmp_path, files), "unregistered_source")
    assert issue.file == "evidence/shared.yaml"


def test_missing_anchor_field(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "orders")["anchor_reference"]["field"] = "customer_id"
    _only(write_model(tmp_path, files), "missing_field")


def test_join_on_other_entity(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "orders")["relationships"][0]["join"] = "orders.users_id = products.id"
    _only(write_model(tmp_path, files), "bad_join")


def test_unknown_rule_label(tmp_path: Path) -> None:
    files = _base()
    next(f for f in files if f["kind"] == "profile")["rules"][0]["label"] = "mystery"
    issue = _only(write_model(tmp_path, files), "unknown_label")
    assert issue.file == "profiles/retail/profile.yaml"


def test_missing_profile(tmp_path: Path) -> None:
    files = [f for f in _base() if f["kind"] not in ("profile", "model-config")]
    config = {
        "kind": "model-config",
        "id": "t",
        "framework_version": "0.0.1",
        "profile": "nope",
        "anchor_entity": "users",
    }
    root = write_model(
        tmp_path, {"factmodel.yaml": config, **{f"f{i}.yaml": f for i, f in enumerate(files)}}
    )
    issue = _only(root, "missing_profile")
    assert issue.file == "factmodel.yaml"


def test_missing_config(tmp_path: Path) -> None:
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")
    issues = _issues(tmp_path)
    assert [i.code for i in issues] == ["missing_config"]


def test_unknown_kind(tmp_path: Path) -> None:
    root = write_model(tmp_path, {"notes.yaml": {"kind": "notes", "text": "x"}})
    issues = _issues(root)
    assert [i.code for i in issues if i.file == "notes.yaml"] == ["unknown_kind"]


def test_schema_error_with_position(tmp_path: Path) -> None:
    text = (
        "kind: source\nid: shop-db\ntitle: Shop\nsource_kind: warehouse\n"
        "access_mode: public\nengine: postgres\n"
    )
    root = write_model(tmp_path, {"sources/shop-db.yaml": text})
    issue = next(i for i in _issues(root) if i.file == "sources/shop-db.yaml")
    assert (issue.stage, issue.code, issue.line, issue.column) == ("schema", "schema", 5, 1)


def test_duplicate_yaml_key_with_position(tmp_path: Path) -> None:
    text = "kind: source\nid: shop-db\nid: other\n"
    root = write_model(tmp_path, {"sources/shop-db.yaml": text})
    issue = next(i for i in _issues(root) if i.file == "sources/shop-db.yaml")
    assert (issue.stage, issue.line, issue.column) == ("yaml", 3, 1)
    assert "duplicate" in issue.message


def test_reference_error_position(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "order_items")["relationships"][1]["to"] = "catalog"
    root = write_model(tmp_path, files)
    issue = _only(root, "missing_entity")
    lines = (root / issue.file).read_text(encoding="utf-8").splitlines()
    assert lines[issue.line - 1].strip().startswith("to: catalog")


def test_derived_key_is_its_own_stage(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "orders")["label"] = "customer_scoped"
    issue = _only(write_model(tmp_path, files), "derived_key")
    assert issue.stage == "derived-not-authored"


def test_nested_field_name_must_end_path(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "orders")["fields"].append(
        {
            "name": "id",
            "path": "meta.request_id",
            "type": "STRING",
            "nullable": True,
            "meaning": "x",
        }
    )
    _only(write_model(tmp_path, files), "path_name_mismatch")


def test_load_model_raises_with_every_issue(tmp_path: Path) -> None:
    files = _base()
    _entity(files, "orders")["evidence"] = ["ev-a"]
    _entity(files, "order_items")["evidence"] = ["ev-b"]
    with pytest.raises(ModelLoadError) as error:
        load_model(write_model(tmp_path, files))
    assert len(error.value.issues) == 2
    assert "physical/entities/orders.yaml:" in str(error.value)


def test_discover_skips_non_model_folders(tmp_path: Path) -> None:
    root = write_model(
        tmp_path,
        {
            "drafts/new.yaml": "kind: whatever\n",
            "generated/x.yaml": "a: 1\n",
            "sources/snapshots/s.yaml": "kind: snapshot\n",
            "semantic/l/corpus/q.yaml": "q: 1\n",
            ".github/workflows/ci.yml": "on: push\n",
        },
    )
    assert [p.relative_to(root).as_posix() for p in discover(root)] == ["factmodel.yaml"]

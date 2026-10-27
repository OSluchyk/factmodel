"""Test vectors for spec/ALGORITHMS.md are valid input.

The vectors are data: every input file must match its schema and every expected output
must cover the whole input. The core tests run the algorithms against them.
"""

from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from factmodel import vocabulary
from factmodel.io.yaml_strict import load
from factmodel.schemas import build

VECTORS = Path(__file__).resolve().parent / "vectors"
ALL = sorted(VECTORS.glob("*/*.yaml"))

REQUIRED = {
    "projection": {
        "rule-unresolved",
        "rule-lineage",
        "rule-representation",
        "rule-administrative",
        "rule-configuration",
        "rule-reference-data",
        "rule-customer-scoped",
        "tie",
        "residue",
        "target-set-agreement",
        "target-set-disagreement",
        "discriminator",
    },
    "scope": {
        "direct",
        "chain-of-three",
        "cycle",
        "reference-blocks",
        "missing-admission",
        "two-paths",
        "rejections",
    },
    "release": {"complete", "residue-file", "undeclared-key"},
}


def _id(path: Path) -> str:
    return f"{path.parent.name}/{path.stem}"


def _errors(doc: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(build.schema_for(doc["kind"]))
    return [f"{doc['kind']} {e.json_path}: {e.message}" for e in validator.iter_errors(doc)]


@pytest.mark.parametrize("algorithm", sorted(REQUIRED))
def test_required_cases_exist(algorithm: str) -> None:
    names = {p.stem for p in (VECTORS / algorithm).glob("*.yaml")}
    assert REQUIRED[algorithm] <= names, REQUIRED[algorithm] - names


@pytest.mark.parametrize("path", ALL, ids=_id)
def test_vector_header(path: Path) -> None:
    doc = load(path).data
    assert doc["algorithm"] == path.parent.name
    assert doc["case"] == path.stem
    assert doc["description"]


@pytest.mark.parametrize(
    "path", [p for p in ALL if p.parent.name in ("projection", "scope")], ids=_id
)
def test_model_vector_inputs_match_schemas(path: Path) -> None:
    files = load(path).data["input"]["files"]
    assert [f["kind"] for f in files].count("profile") == 1
    assert [f["kind"] for f in files].count("model-config") == 1
    errors = [error for f in files for error in _errors(f)]
    assert errors == []


@pytest.mark.parametrize("path", sorted((VECTORS / "projection").glob("*.yaml")), ids=_id)
def test_projection_expected_covers_every_relationship(path: Path) -> None:
    doc = load(path).data
    refs = {
        f"{f['id']}.{r['key']}"
        for f in doc["input"]["files"]
        if f["kind"] == "entity"
        for r in f.get("relationships", [])
    }
    labels = doc["expected"]["labels"]
    residue = doc["expected"]["residue"]
    labelled = {row["relationship"] for row in labels}
    assert labelled.isdisjoint({row["relationship"] for row in residue})
    assert labelled | {row["relationship"] for row in residue} == refs
    allowed = {*vocabulary.load()["derived_value"]} | {
        label for f in doc["input"]["files"] if f["kind"] == "profile" for label in f["labels"]
    }
    assert {row["label"] for row in labels} <= allowed


@pytest.mark.parametrize("path", sorted((VECTORS / "scope").glob("*.yaml")), ids=_id)
def test_scope_expected_covers_every_entity(path: Path) -> None:
    doc = load(path).data
    entities = sorted(f["id"] for f in doc["input"]["files"] if f["kind"] == "entity")
    rows = doc["expected"]["scope"]
    assert [row["entity"] for row in rows] == entities
    vocab = vocabulary.load()
    for row in rows:
        assert row["subject_scope"] in vocab["subject_scope"]
        assert row["basis"] == "-" or row["basis"] in vocab["scope_basis"]
        assert (row["basis"] == "-") == (row["subject_scope"] != "transitive")
        assert isinstance(row["reachable"], bool)
    for rejection in doc["expected"]["rejections"]:
        assert rejection["reason"] in vocab["admission_rejection"]


@pytest.mark.parametrize("path", sorted((VECTORS / "release").glob("*.yaml")), ids=_id)
def test_release_vector_is_a_complete_partition(path: Path) -> None:
    doc = load(path).data
    files = doc["input"]["files"]
    documents = [f["document"] for f in files if f["document"] is not None]
    assert [d["kind"] for d in documents].count("release-allowlist") == 1
    assert [error for d in documents for error in _errors(d)] == []
    expected = doc["expected"]
    disposed = [row["path"] for row in expected["files"]]
    failed = [row["path"] for row in expected["failures"]]
    assert sorted(disposed + failed) == sorted(f["path"] for f in files)
    vocab = vocabulary.load()
    assert {row["disposition"] for row in expected["files"]} <= set(vocab["release_disposition"])
    assert {row["reason"] for row in expected["failures"]} <= set(vocab["release_failure"])

"""Every test vector from spec/ALGORITHMS.md passes as an executable test."""

import pytest

from factmodel.core.derived import derive
from factmodel.core.release import glob_match, partition
from tests.core import helpers as h


@pytest.mark.parametrize("case", h.cases("projection"))
def test_projection_vector(case: str) -> None:
    doc = h.vector("projection", case)
    result = derive(*h.typed_inputs(doc["input"]["files"]))
    assert h.label_rows(result) == doc["expected"]["labels"]
    assert h.residue_rows(result) == doc["expected"]["residue"]


@pytest.mark.parametrize("case", h.cases("scope"))
def test_scope_vector(case: str) -> None:
    doc = h.vector("scope", case)
    result = derive(*h.typed_inputs(doc["input"]["files"]))
    assert h.scope_rows(result) == doc["expected"]["scope"]
    assert h.rejection_rows(result) == doc["expected"]["rejections"]


@pytest.mark.parametrize("case", h.cases("release"))
def test_release_vector(case: str) -> None:
    doc = h.vector("release", case)
    plan = partition(*h.release_inputs(doc["input"]["files"]))
    files = [
        {"path": d.path, "disposition": d.disposition, **({"keep": list(d.keep)} if d.keep else {})}
        for d in plan.files
    ]
    failures = [
        {"path": f.path, "reason": f.reason, **({"key": f.key} if f.key else {})}
        for f in plan.failures
    ]
    assert files == doc["expected"]["files"]
    assert failures == doc["expected"]["failures"]


@pytest.mark.parametrize(
    ("pattern", "path", "expected"),
    [
        ("physical/entities/*.yaml", "physical/entities/orders.yaml", True),
        ("physical/entities/*.yaml", "physical/entities/sub/orders.yaml", False),
        ("drafts/**", "drafts/a/b.yaml", True),
        ("drafts/**", "drafts", True),
        ("**", "CHANGELOG.md", True),
        ("**/*.md", "a/b/c.md", True),
        ("**/*.md", "c.md", True),
        ("registers/*/H-*.yaml", "registers/hazards/H-0001.yaml", True),
        ("registers/*/H-*.yaml", "registers/H-0001.yaml", False),
    ],
)
def test_glob_match(pattern: str, path: str, expected: bool) -> None:
    assert glob_match(pattern, path) is expected

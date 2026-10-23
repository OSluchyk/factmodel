"""Property tests for the derived values (plan WP1.2)."""

import random
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st

from factmodel import vocabulary
from factmodel.core.derived import derive, render
from factmodel.model.types import Entity
from tests.core import helpers as h

MODEL_CASES = [("projection", c) for c in h.cases("projection")] + [
    ("scope", c) for c in h.cases("scope")
]


def _files(case: tuple[str, str]) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = h.vector(*case)["input"]["files"]
    return files


def _shuffled(files: list[dict[str, Any]], seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    out = [dict(f) for f in files]
    rng.shuffle(out)
    for f in out:
        if f["kind"] == "entity" and "relationships" in f:
            rels = list(f["relationships"])
            rng.shuffle(rels)
            f["relationships"] = rels
    return out


@settings(max_examples=40, deadline=None)
@given(st.sampled_from(MODEL_CASES))
def test_projection_is_deterministic(case: tuple[str, str]) -> None:
    files = _files(case)
    assert render(derive(*h.typed_inputs(files))) == render(derive(*h.typed_inputs(files)))


@settings(max_examples=60, deadline=None)
@given(st.sampled_from(MODEL_CASES), st.integers(min_value=0, max_value=2**32))
def test_file_and_relationship_order_does_not_matter(case: tuple[str, str], seed: int) -> None:
    files = _files(case)
    expected = render(derive(*h.typed_inputs(files)))
    assert render(derive(*h.typed_inputs(_shuffled(files, seed)))) == expected


@settings(max_examples=60, deadline=None)
@given(
    st.sampled_from(MODEL_CASES),
    st.sampled_from(vocabulary.load()["entity_class"]),
    st.booleans(),
)
def test_unrelated_entity_changes_nothing(
    case: tuple[str, str], entity_class: str, with_anchor_reference: bool
) -> None:
    entities, evidence, profile = h.typed_inputs(_files(case))
    before = derive(entities, evidence, profile)
    extra: dict[str, Any] = {
        "kind": "entity",
        "id": "zz_unrelated",
        "physical_name": "other.unrelated",
        "grain": "one row per thing",
        "class": entity_class,
        "status": "draft",
        "keys": {"primary": ["id"]},
        "evidence": ["ev-confirmed"],
        "fields": [{"name": "id", "type": "INT64", "nullable": False, "meaning": "Id."}],
    }
    if with_anchor_reference:
        extra["fields"].append(
            {"name": "user_id", "type": "INT64", "nullable": True, "meaning": "U."}
        )
        extra["anchor_reference"] = {"field": "user_id", "evidence": ["ev-confirmed"]}
    after = derive({**entities, "zz_unrelated": Entity.model_validate(extra)}, evidence, profile)
    assert after.projection == before.projection
    assert {k: v for k, v in after.scope.rows.items() if k != "zz_unrelated"} == dict(
        before.scope.rows
    )
    new_rejections = set(after.scope.rejections) - set(before.scope.rejections)
    assert all(r.fact.startswith("zz_unrelated.") for r in new_rejections)

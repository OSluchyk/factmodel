"""The probe parts of the hard cases that round 7 deferred to WP1.7."""

from pathlib import Path

from factmodel.model.loader import load_model
from factmodel.probes import generate

HARD = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases"


def _ids(case: str, dialect: str) -> tuple[set[str], list[str]]:
    model = load_model(HARD / case)
    docs, skipped = generate(model.entities, model.sources, {}, default_dialect=dialect)
    return {d["id"] for d in docs}, [s.fact for s in skipped]


def test_soft_delete_gets_a_ties_probe() -> None:
    ids, _ = _ids("soft-delete", "postgres")
    assert "current-row-ties-order-items" in ids


def test_nullable_fk_gets_a_null_rate_probe() -> None:
    ids, _ = _ids("nullable-fk", "postgres")
    assert "null-rate-events-users-id" in ids


def test_nested_join_renders_only_where_paths_exist() -> None:
    bq, _ = _ids("nested-field", "bigquery")
    assert {"join-match-web-events-by-user", "null-rate-web-events-context-user-id"} <= bq
    pg, skipped = _ids("nested-field", "postgres")
    assert "join-match-web-events-by-user" not in pg
    assert {"web_events.by-user", "web_events.context.user_id"} <= set(skipped)

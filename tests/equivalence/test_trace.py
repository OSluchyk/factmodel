"""The trace of one query against a layer, coverage over a corpus, and the difference between a
consumer's query and the reference, on the toy model of the layer-minimal hard case."""

from pathlib import Path

import pytest

from factmodel.equivalence import trace as tracing
from factmodel.model.loader import Model, load_model
from factmodel.model.types import Layer

CASE = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases" / "layer-minimal"


@pytest.fixture(scope="module")
def model() -> Model:
    return load_model(CASE)


def _layer(**extra: object) -> Layer:
    doc: dict[str, object] = {
        "kind": "layer",
        "id": "employment",
        "purpose": "Employment by area.",
        "consumer": "employment-sql",
        "status": "draft",
        "entities": [
            {"entity": "employment", "current_row_rule": None},
            {"entity": "areas", "current_row_rule": None},
        ],
        "joins": ["employment.in-area"],
        "concepts": [
            {"id": "area", "meaning": "The area.", "field": "areas.area_code"},
            {"id": "recent", "meaning": "After 2000.", "predicate": "employment.year > 2000"},
            {"id": "one_area", "meaning": "Distinct.", "distinct": ["areas.area_code"]},
        ],
        "measures": [
            {
                "id": "employment",
                "meaning": "Employees.",
                "expression": "employment.employment",
                "aggregation": "sum",
                "grain": {"entity": "employment", "fields": ["area_code", "industry_code", "year"]},
            }
        ],
    }
    doc.update(extra)
    return Layer.model_validate(doc)


def _trace(sql: str, model: Model, layer: Layer | None = None) -> tracing.Trace:
    return tracing.trace(sql, layer or _layer(), model)


def test_aliases_resolve_to_entity_fields(model: Model) -> None:
    t = _trace(
        "SELECT e.area_code, SUM(e.employment) FROM employment AS e "
        "JOIN areas AS a ON e.area_code = a.area_code WHERE e.year > 2000 GROUP BY e.area_code",
        model,
    )
    assert t.entities == ("areas", "employment")
    assert t.fields == (
        "areas.area_code",
        "employment.area_code",
        "employment.employment",
        "employment.year",
    )
    assert t.joins_as_declared == ("employment.in-area",)
    assert t.concepts == ("area", "recent")
    assert t.concepts_not_evaluated == ("one_area",)
    assert t.measures_weak == ("employment",)
    assert t.unresolved == 0


def test_correlated_exists_joins_as_declared(model: Model) -> None:
    t = _trace(
        "SELECT a.area_title FROM areas AS a WHERE EXISTS "
        "(SELECT 1 FROM employment AS e WHERE e.area_code = a.area_code AND e.year > 2000)",
        model,
    )
    assert t.joins_as_declared == ("employment.in-area",)
    assert "recent" in t.concepts
    assert t.measures_weak == ()  # the field occurs, its SUM does not


def test_derived_table_joins_otherwise_and_keeps_lineage(model: Model) -> None:
    t = _trace(
        "SELECT d.code, SUM(e.employment) FROM employment AS e JOIN "
        "(SELECT area_code AS code FROM areas GROUP BY area_code) AS d "
        "ON e.area_code = d.code GROUP BY d.code",
        model,
    )
    assert t.joins_as_declared == ()
    assert t.joins_otherwise == ("employment.in-area",)
    assert "areas.area_code" in t.fields
    assert t.unresolved == 0


def test_cte_with_star_reads_only_the_columns_named_outside(model: Model) -> None:
    t = _trace(
        "WITH sel AS (SELECT * FROM employment WHERE year > 2000) "
        "SELECT SUM(employment) AS value FROM sel",
        model,
    )
    # year filters inside the CTE; employment is read outside; the other columns are not used
    assert t.fields == ("employment.employment", "employment.year")
    assert t.concepts == ("recent",)
    assert t.measures_weak == ("employment",)


def test_unqualified_column_with_one_table_and_with_two(model: Model) -> None:
    one = _trace("SELECT year FROM employment", model)
    assert one.fields == ("employment.year",) and one.unresolved == 0
    # area_code is a field of both tables: never guessed
    two = _trace("SELECT area_code FROM employment, areas", model)
    assert two.unresolved == 1
    assert two.fields == ()


def test_entity_outside_the_layer(model: Model) -> None:
    t = _trace(
        "SELECT i.industry_title FROM employment AS e "
        "JOIN industries AS i ON e.industry_code = i.industry_code",
        model,
    )
    assert t.entities == ("employment",)
    assert t.outside_layer == ("industries",)
    unknown = _trace("SELECT x.a FROM nowhere AS x", model)
    assert (unknown.unknown_tables, unknown.unresolved) == (1, 1)


def test_unparsable_sql(model: Model) -> None:
    t = _trace("SELECT FROM WHERE (", model)
    assert not t.parsed
    assert tracing.difference(t, _trace("SELECT year FROM employment", model)) == (
        "the consumer's SQL does not parse"
    )


def test_quoted_mixed_case_identifiers(model: Model) -> None:
    t = _trace('SELECT "Employment"."Year" FROM "employment"', model)
    assert t.fields == ("employment.year",) and t.unresolved == 0


def test_coverage_lists_a_join_no_item_uses(model: Model) -> None:
    layer = _layer(
        entities=[
            {"entity": "employment", "current_row_rule": None},
            {"entity": "areas", "current_row_rule": None},
            {"entity": "industries", "current_row_rule": None},
        ],
        joins=["employment.in-area", "employment.in-industry"],
    )
    sql = (
        "SELECT a.area_title, SUM(e.employment) FROM employment AS e "
        "JOIN areas AS a ON e.area_code = a.area_code GROUP BY a.area_title"
    )
    cov = tracing.coverage(
        layer,
        [("pass", tracing.trace(sql, layer, model)), ("fail", tracing.trace(sql, layer, model))],
    )
    by = {e.label: e for e in cov.elements}
    assert (by["join employment.in-area"].items, by["join employment.in-area"].passing) == (2, 1)
    assert [e.label for e in cov.not_exercised] == [
        "entity industries",
        "join employment.in-industry",
        "concept recent",
    ]
    assert [e.label for e in cov.not_evaluated] == ["concept one_area"]
    assert cov.summary() == {
        "elements": 8,
        "exercised": 5,
        "not_exercised": ["entity industries", "join employment.in-industry", "concept recent"],
        "not_evaluated": ["concept one_area (distinct)"],
        "unresolved_items": 0,
    }


def test_references_keep_an_unexercised_element_from_reading_as_unused() -> None:
    layer = _layer(
        entities=[
            {"entity": "employment", "current_row_rule": None, "default_filters": ["recent"]},
            {"entity": "areas", "current_row_rule": None},
        ],
    )
    assert tracing.references(layer, "concept", "recent") == (
        "default filter of entity employment",
    )
    assert tracing.references(layer, "entity", "areas") == ("concept area", "concept one_area")


REFERENCE = (
    "SELECT a.area_code, SUM(e.employment) FROM employment AS e "
    "JOIN areas AS a ON e.area_code = a.area_code GROUP BY a.area_code"
)


def test_difference_for_right_wrong_and_outside_consumers(model: Model) -> None:
    reference = _trace(REFERENCE, model)
    right = _trace(REFERENCE.replace("AS e", "AS x").replace("e.", "x."), model)
    assert tracing.difference(right, reference) == "nothing the trace can see"
    other_join = _trace(
        REFERENCE.replace("e.area_code = a.area_code", "e.industry_code = a.area_code"), model
    )
    assert tracing.difference(other_join, reference) == (
        "consumer only: fields employment.industry_code; joins employment.in-area (otherwise)"
        " | reference only: fields employment.area_code; joins employment.in-area (as declared)"
    )
    outside = _trace(
        "SELECT i.industry_title, SUM(e.employment) FROM employment AS e "
        "JOIN industries AS i ON e.industry_code = i.industry_code GROUP BY i.industry_title",
        model,
    )
    text = tracing.difference(outside, reference)
    assert "consumer only: entities industries" in text
    assert text.endswith("the consumer leaves the layer: industries")
    assert tracing.difference(None, reference) == "the consumer gave no SQL"


def test_a_trace_holds_no_literal(model: Model) -> None:
    t = _trace("SELECT year FROM employment WHERE area_code = 'A1-secret'", model)
    assert "A1-secret" not in repr(t.as_dict())

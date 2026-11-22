"""The trace of one query against a layer, coverage over a corpus, and the difference between a
consumer's query and the reference, on the toy model of the layer-minimal hard case."""

from pathlib import Path

import pytest

from factmodel import vocabulary
from factmodel.equivalence import trace as tracing
from factmodel.model.loader import Model, load_model
from factmodel.model.types import Layer, Relationship

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


REFERENCE = (
    "SELECT a.area_code, SUM(e.employment) FROM employment AS e "
    "JOIN areas AS a ON e.area_code = a.area_code GROUP BY a.area_code"
)


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
    traced = tracing.trace(sql, layer, model)
    cov = tracing.coverage(layer, model, [("pass", traced), ("fail", traced)])
    by = {e.label: e for e in cov.elements}
    join = by["join employment.in-area"]
    assert (join.items, join.passing, join.as_declared, join.otherwise) == (2, 1, 2, 0)
    assert cov.summary() == {
        "elements": 8,
        "exercised": 5,
        "not_exercised": ["entity industries", "join employment.in-industry"],
        # the predicate concept is not found as written: never a plain zero
        "not_found_as_written": ["concept recent (as written)"],
        "no_passing_item": [],
        "tested": [
            "entity employment",
            "entity areas",
            "join employment.in-area",
            "concept area",
            "measure (weak) employment",
        ],
        "not_evaluated": ["concept one_area (distinct)"],
        "unresolved_items": 0,
    }


def test_no_passing_item_lists_elements_only_failing_items_use(model: Model) -> None:
    layer = _layer()
    used = _trace(REFERENCE, model, layer)
    cov = tracing.coverage(layer, model, [("fail", used), ("error", used)])
    assert cov.summary()["no_passing_item"] == [
        "entity employment",
        "entity areas",
        "join employment.in-area",
        "concept area",
        "measure (weak) employment",
    ]
    assert cov.summary()["tested"] == []


def test_two_unrelated_subqueries_count_a_join_as_otherwise_only(model: Model) -> None:
    # weak by design: both entities occur, so the join counts as exercised, in class otherwise
    t = _trace("SELECT (SELECT COUNT(*) FROM employment), (SELECT COUNT(*) FROM areas)", model)
    assert (t.joins_as_declared, t.joins_otherwise) == ((), ("employment.in-area",))
    cov = tracing.coverage(_layer(), model, [("pass", t)])
    join = next(e for e in cov.elements if e.kind == "join")
    assert (join.items, join.as_declared, join.otherwise) == (1, 0, 1)


def test_a_join_the_trace_cannot_read_is_not_evaluated() -> None:
    model = load_model(CASE)
    employment = model.entities["employment"]
    employment.relationships.append(
        Relationship.model_validate(
            {
                "key": "by-place",
                "to": ["areas", "industries"],
                "discriminator": "area_code",
                "join": {
                    "areas": "employment.area_code = areas.area_code",
                    "industries": "employment.industry_code = industries.industry_code",
                },
                "meaning": "A target set.",
                "mechanism": "inferred_join",
                "cardinality": "many_to_one",
                "evidence": ["ev-shared"],
            }
        )
    )
    employment.relationships.append(
        Relationship.model_validate(
            {
                "key": "odd",
                "to": "areas",
                "join": "employment.no_such_field = areas.area_code",
                "meaning": "Names a field the entity does not have.",
                "mechanism": "inferred_join",
                "cardinality": "many_to_one",
                "evidence": ["ev-shared"],
            }
        )
    )
    layer = _layer(joins=["employment.in-area", "employment.by-place", "employment.odd"])
    assert tracing.join_form("employment.by-place", model) == "target_set"
    assert tracing.join_form("employment.odd", model) == "unreadable"
    t = tracing.trace(REFERENCE, layer, model)
    assert t.joins == ("employment.in-area",)
    cov = tracing.coverage(layer, model, [("pass", t)])
    summary = cov.summary()
    assert summary["not_evaluated"] == [
        "join employment.by-place (target_set)",
        "join employment.odd (unreadable)",
        "concept one_area (distinct)",
    ]
    assert not any("by-place" in label or "odd" in label for label in summary["not_exercised"])


def test_an_unread_cte_uses_nothing(model: Model) -> None:
    t = _trace("WITH x AS (SELECT * FROM areas) SELECT e.year FROM employment AS e", model)
    assert t.entities == ("employment",)
    assert t.fields == ("employment.year",)
    # a CTE that is read, through another CTE, still counts
    read = _trace(
        "WITH y AS (SELECT * FROM areas), x AS (SELECT * FROM y) SELECT area_code FROM x", model
    )
    assert read.entities == ("areas",) and read.fields == ("areas.area_code",)
    derived = _trace(
        "SELECT e.year FROM employment AS e WHERE EXISTS (SELECT 1 FROM areas AS a)", model
    )
    assert derived.entities == ("areas", "employment")


def test_physical_table_names_are_read_as_their_entity(model: Model) -> None:
    # bind leaves a table that is no entity id as written, so a reference may name stats.areas
    t = _trace("SELECT a.area_title FROM stats.areas AS a", model)
    assert t.entities == ("areas",) and t.fields == ("areas.area_title",)


def test_every_aggregation_is_mapped_or_named_as_not_checked() -> None:
    values = set(vocabulary.load()["measure_aggregation"])
    assert set(tracing.AGGREGATES) | set(tracing.NOT_CHECKED) == values
    assert not set(tracing.AGGREGATES) & set(tracing.NOT_CHECKED)


def test_a_concept_form_the_trace_does_not_know_is_not_evaluated() -> None:
    class Future:
        id = "later"

    assert tracing.concept_form(Future()) == "unknown"  # type: ignore[arg-type]
    assert not tracing.evaluated("concept", "unknown")


def test_labels_round_trip() -> None:
    for kind, element_id in [
        ("entity", "qtrly"),
        ("join", "qtrly.to-area"),
        ("measure", "employment_month3"),
        ("concept", "area_kind_county"),
    ]:
        element = tracing.Element(kind, element_id, form="predicate")
        assert tracing.parse_label(element.label) == (kind, element_id)


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


def test_difference_for_right_wrong_and_outside_consumers(model: Model) -> None:
    reference = _trace(REFERENCE, model)
    right = _trace(REFERENCE.replace("AS e", "AS x").replace("e.", "x."), model)
    assert tracing.difference(right, reference) == "nothing the trace can see"
    other_join = _trace(
        REFERENCE.replace("e.area_code = a.area_code", "e.industry_code = a.area_code"), model
    )
    assert tracing.difference(other_join, reference) == (
        "consumer only: fields employment.industry_code; joins employment.in-area (otherwise, weak)"
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

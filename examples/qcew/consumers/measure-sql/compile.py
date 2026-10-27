"""Reference consumer for the QCEW layer employment-wages (WP3.3): a structured request
becomes SQL in the neutral dialect. No model, no network.

Request keys: ``measure`` (a layer measure id), ``area`` (one code) or ``areas`` (``{kind:
county, state: "10"}``: one row per county of a state), ``industry``, ``ownership``, ``year``,
``qtr`` (quarterly measures) and optional ``level`` (agglvl_code; derived when absent).

What it takes from the layer: every measure expression and its companion, the predicates of
the required concepts ``disclosed`` / ``disclosed_annual``, the area-kind predicates and the
distinct rule for area titles. What it had to look up elsewhere (the dogfood list for the
model-lookup skill): the A4 aggregation-level matrix, which turns (geography, industry,
ownership) into agglvl_code, and the join condition behind ``qtrly.to-area``.
"""

from typing import Any


def _get(items: Any, key: str) -> Any:
    found = next((i for i in items or [] if i.id == key), None)
    if found is None:
        raise ValueError(f"the layer has no {key!r}")
    return found


def _quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def level(area: str, industry: str, ownership: str) -> str:
    """agglvl_code from the A4 matrix: geography digit, then industry and ownership level."""
    if area.startswith("C") and not area.startswith("CS"):
        geo = "4"
    elif area[2:] == "000":
        geo = "5"
    else:
        geo = "7"
    if industry == "10":
        ind = "0" if ownership == "0" else "1"
    elif industry in ("101", "102"):
        ind = "2"
    elif len(industry) == 4 and industry.startswith("10"):
        ind = "3"
    elif "-" in industry or len(industry) == 2:
        ind = "4"
    else:
        ind = str(len(industry) + 2)  # 3 to 6 digits: levels 5 to 8
    return geo + ind


def compile(request: dict[str, Any], layer: Any) -> str:
    measure = _get(layer.measures, request["measure"])
    entity = measure.grain.entity
    disclosed = _get(layer.concepts, "disclosed" if entity == "qtrly" else "disclosed_annual")
    companion = _get(layer.measures, measure.companion) if measure.companion else None
    filters = [
        f"{entity}.industry_code = {_quote(request['industry'])}",
        f"{entity}.own_code = {_quote(request['ownership'])}",
        f"{entity}.year = {_quote(request['year'])}",
    ]
    if entity == "qtrly":
        filters.append(f"{entity}.qtr = {_quote(request['qtr'])}")
    if "areas" in request:
        return _by_area(request, layer, measure, disclosed, companion, entity, filters)
    area = request["area"]
    lvl = request.get("level") or level(area, request["industry"], request["ownership"])
    where = " AND ".join(
        [f"{entity}.area_fips = {_quote(area)}", *filters, f"{entity}.agglvl_code = {_quote(lvl)}"]
    )
    # aggregation none: already an aggregate (a formula), or read at its grain (one row)
    value = measure.expression if measure.aggregation == "none" else f"SUM({measure.expression})"
    sql = f"SELECT (SELECT {value} FROM {entity} WHERE {where}"
    if measure.suppressed == "exclude":
        sql += f" AND {disclosed.predicate}"
    sql += ") AS value"
    if companion is not None:
        count = f"SELECT SUM({companion.expression}) FROM {entity} WHERE {where}"
        sql += f", ({count}) AS suppressed_cells"
    return sql


def _by_area(
    request: dict[str, Any],
    layer: Any,
    measure: Any,
    disclosed: Any,
    companion: Any,
    entity: str,
    filters: list[str],
) -> str:
    areas = request["areas"]
    if areas.get("kind") != "county" or measure.aggregation != "sum":
        raise ValueError("only county breakdowns of summed measures are supported")
    kind = _get(layer.concepts, "area_kind_county")
    distinct = _get(layer.concepts, "distinct_areas")
    fields = ", ".join(distinct.distinct)
    lvl = request.get("level") or level("00001", request["industry"], request["ownership"])
    where = " AND ".join(
        [
            kind.predicate.replace("qtrly.", f"{entity}."),
            f"substr({entity}.area_fips, 1, 2) = {_quote(areas['state'])}",
            *filters,
            f"{entity}.agglvl_code = {_quote(lvl)}",
        ]
    )
    value = f"SUM(CASE WHEN {disclosed.predicate} THEN {measure.expression} END)"
    columns = ["area_titles.area_fips", "area_titles.area_title", f"{value} AS value"]
    if companion is not None:
        columns.append(f"SUM({companion.expression}) AS suppressed_cells")
    return (
        f"SELECT {', '.join(columns)} FROM {entity} "
        f"JOIN (SELECT DISTINCT {fields} FROM area_titles) AS area_titles "
        f"ON {entity}.area_fips = area_titles.area_fips "
        f"WHERE {where} GROUP BY area_titles.area_fips, area_titles.area_title"
    )

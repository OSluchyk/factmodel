"""Reference consumer for the Chinook layer customer-purchases (WP3.3): a filter request
becomes SQL in the neutral dialect. No model, no network.

Requests:
- ``{ask: customers, genre?, country?, from, to}``: the customers who bought tracks of the
  genre (and billed to the country) in the period ``[from, to)``;
- ``{ask: measure, measure, by?: country | genre, genre?, country?, from, to}``: a layer
  measure, overall or one row per country or genre.

What it takes from the layer: measure expressions and aggregations, and the concept fields
for genre, country and period. What it had to look up elsewhere (what the model-lookup
skill now answers): the join conditions behind the relationship keys the layer lists.
"""

from typing import Any

# the join conditions of the layer's relationship keys, looked up in the physical model
JOINS = (
    "JOIN invoice ON invoice_line.InvoiceId = invoice.InvoiceId",
    "JOIN track ON invoice_line.TrackId = track.TrackId",
    "JOIN genre ON track.GenreId = genre.GenreId",
)


def _get(items: Any, key: str) -> Any:
    found = next((i for i in items or [] if i.id == key), None)
    if found is None:
        raise ValueError(f"the layer has no {key!r}")
    return found


def _quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _where(request: dict[str, Any], layer: Any) -> list[str]:
    period = _get(layer.concepts, "period").field
    where = [f"{period} >= {_quote(request['from'])}", f"{period} < {_quote(request['to'])}"]
    for key in ("genre", "country"):
        if key in request:
            where.append(f"{_get(layer.concepts, key).field} = {_quote(request[key])}")
    return where


def compile(request: dict[str, Any], layer: Any) -> str:
    where = " AND ".join(_where(request, layer))
    source = "FROM invoice_line " + " ".join(JOINS)
    if request["ask"] == "customers":
        return f"SELECT DISTINCT invoice.CustomerId {source} WHERE {where}"
    measure = _get(layer.measures, request["measure"])
    aggregate = {"sum": "SUM", "count_distinct": "COUNT(DISTINCT"}[measure.aggregation]
    value = f"{aggregate}({measure.expression})" + (")" if "DISTINCT" in aggregate else "")
    by = request.get("by")
    if by is None:
        return f"SELECT {value} AS value {source} WHERE {where}"
    key = _get(layer.concepts, by).field
    return f"SELECT {key} AS key, {value} AS value {source} WHERE {where} GROUP BY {key}"

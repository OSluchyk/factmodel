"""Bind layer SQL to physical names, normalise it, and compare result sets."""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from typing import Any

import sqlglot
from sqlglot import exp


def bind(sql: str, tables: Mapping[str, str]) -> exp.Expr:
    """Parse neutral SQL and replace each table named by an entity id with its physical name."""
    tree = sqlglot.parse_one(sql)
    for table in tree.find_all(exp.Table):
        entity = table.name
        physical = tables.get(entity)
        if physical is None or table.args.get("db") is not None:
            continue
        parts = physical.split(".")
        table.set("this", exp.to_identifier(parts[-1]))
        if len(parts) > 1:
            table.set("db", exp.to_identifier(parts[-2]))
        if len(parts) > 2:
            table.set("catalog", exp.to_identifier(parts[-3]))
        if not table.alias:
            # columns stay qualified by the entity id the consumer wrote
            table.set("alias", exp.TableAlias(this=exp.to_identifier(entity)))
    return tree


def count_query(mine: exp.Expr, theirs: exp.Expr) -> exp.Select:
    """Counts only: rows on each side, and rows only one side has (EXCEPT, so duplicates
    collapse). Built as an AST so every dialect gets its own set-operation syntax."""

    def wrapped(source: exp.Expr, alias: str) -> exp.Subquery:
        return exp.Subquery(this=source.copy(), alias=exp.TableAlias(this=exp.to_identifier(alias)))

    def count(source: exp.Expr, alias: str) -> exp.Expr:
        inner = exp.select(exp.Count(this=exp.Star())).from_(wrapped(source, alias))
        return exp.Subquery(this=inner)

    def side(source: exp.Expr, alias: str) -> exp.Select:
        # an operand of EXCEPT is a plain SELECT: a side that starts with WITH stays valid
        return exp.select(exp.Star()).from_(wrapped(source, alias))

    only_mine = exp.except_(side(mine, "m"), side(theirs, "t"), distinct=True)
    only_theirs = exp.except_(side(theirs, "t"), side(mine, "m"), distinct=True)
    return exp.select(
        exp.alias_(count(mine, "c"), "consumer_rows"),
        exp.alias_(count(theirs, "r"), "reference_rows"),
        exp.alias_(count(only_mine, "d"), "only_consumer"),
        exp.alias_(count(only_theirs, "e"), "only_reference"),
    )


def render(tree: exp.Expr, dialect: str) -> str:
    return tree.sql(dialect=dialect, identify=True)


def _sorted_conjuncts(node: exp.Expr) -> exp.Expr:
    if isinstance(node, exp.And):
        parts = list(node.flatten())
        return exp.and_(*sorted((_sorted_conjuncts(p) for p in parts), key=lambda p: p.sql()))
    return node


def normalise(sql: str) -> str:
    """The predicate-level form of a query: lower-case identifiers, no quoting, conjunctions
    sorted, literals kept. Two queries with the same form ask the same thing."""
    tree = sqlglot.parse_one(sql)
    for ident in tree.find_all(exp.Identifier):
        ident.set("this", ident.name.lower())
        ident.set("quoted", False)
    tree = tree.transform(_sorted_conjuncts)
    return tree.sql(pretty=False)


def _cell(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int | float | Decimal):
        number = float(value)
        return round(number, 6) if not number.is_integer() else int(number)
    return str(value)


def _rows(rows: Iterable[Sequence[Any]]) -> Counter[tuple[Any, ...]]:
    return Counter(tuple(_cell(v) for v in row) for row in rows)


def same_rows(left: Iterable[Sequence[Any]], right: Iterable[Sequence[Any]]) -> bool:
    """The same rows, as multisets: order does not matter, duplicates do."""
    return _rows(left) == _rows(right)

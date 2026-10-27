"""Probe queries as neutral sqlglot ASTs (WP1.7).

Every probe returns counts only, under fixed column aliases that become measurement keys. No
query selects a value or an identifier from the data. Identifiers are always quoted when
rendered (``identify=True``), so mixed-case names survive on engines that fold case.
"""

from collections.abc import Sequence

from sqlglot import exp

# Measurement keys per probe kind, in select order.
METRICS: dict[str, tuple[str, ...]] = {
    "key_duplicates": ("duplicate_keys",),
    "join_match": ("source_rows", "orphans_left", "orphans_right"),
    "fan_out": ("max_fan_out",),
    "null_rate": ("row_count", "non_null"),
    "row_count": ("row_count",),
    "current_row_ties": ("tied_keys",),
    "value_set": ("distinct_values", "outside_values", "outside_rows"),
}


def table(physical_name: str, alias: str) -> exp.Table:
    parts = physical_name.split(".")
    name = parts[-1]
    db = parts[-2] if len(parts) > 1 else None
    catalog = parts[-3] if len(parts) > 2 else None
    return exp.table_(name, db=db, catalog=catalog, alias=alias)


def column(alias: str, address: str) -> exp.Expr:
    """``alias.field``, or ``alias.struct.field`` for a nested path."""
    parts = address.split(".")
    if len(parts) == 1:
        return exp.column(parts[0], table=alias)
    return exp.Dot.build([exp.to_identifier(alias), *(exp.to_identifier(p) for p in parts)])


def _count() -> exp.Expr:
    return exp.Count(this=exp.Star())


def _not_null(cols: Sequence[exp.Expr]) -> exp.Expr:
    return exp.and_(*(exp.Not(this=exp.Is(this=c, expression=exp.Null())) for c in cols))


def _scalar(query: exp.Select, name: str) -> exp.Expr:
    return exp.alias_(exp.Subquery(this=query), name)


def key_duplicates(physical: str, keys: Sequence[str]) -> exp.Select:
    cols = [column("t", k) for k in keys]
    inner = (
        exp.select(*cols)
        .from_(table(physical, "t"))
        .where(_not_null(cols))
        .group_by(*cols)
        .having(exp.GT(this=_count(), expression=exp.Literal.number(1)))
    )
    return exp.select(exp.alias_(_count(), "duplicate_keys")).from_(inner.subquery("d"))


def join_match(source: str, target: str, pairs: Sequence[tuple[str, str]]) -> exp.Select:
    """Source rows with a key, source rows that match no target row, and target rows no source
    row points to. ``pairs`` holds (source field, target field)."""
    on = exp.and_(*(exp.EQ(this=column("s", a), expression=column("t", b)) for a, b in pairs))
    keyed = _not_null([column("s", a) for a, _ in pairs])
    any_target = exp.select(exp.Literal.number(1)).from_(table(target, "t")).where(on)
    any_source = exp.select(exp.Literal.number(1)).from_(table(source, "s")).where(on)
    source_rows = exp.select(_count()).from_(table(source, "s")).where(keyed)
    orphans_left = (
        exp.select(_count())
        .from_(table(source, "s"))
        .where(exp.and_(keyed, exp.Not(this=exp.Exists(this=any_target))))
    )
    orphans_right = (
        exp.select(_count())
        .from_(table(target, "t"))
        .where(exp.Not(this=exp.Exists(this=any_source)))
    )
    return exp.select(
        _scalar(source_rows, "source_rows"),
        _scalar(orphans_left, "orphans_left"),
        _scalar(orphans_right, "orphans_right"),
    )


def fan_out(target: str, fields: Sequence[str]) -> exp.Select:
    """The most target rows that share one join-key value: how many rows a source row meets."""
    cols = [column("t", f) for f in fields]
    per_key = (
        exp.select(exp.alias_(_count(), "n"))
        .from_(table(target, "t"))
        .where(_not_null(cols))
        .group_by(*cols)
    )
    most = exp.Coalesce(
        this=exp.Max(this=exp.column("n", table="f")), expressions=[exp.Literal.number(0)]
    )
    return exp.select(exp.alias_(most, "max_fan_out")).from_(per_key.subquery("f"))


def null_rate(physical: str, field: str) -> exp.Select:
    return exp.select(
        exp.alias_(_count(), "row_count"),
        exp.alias_(exp.Count(this=column("t", field)), "non_null"),
    ).from_(table(physical, "t"))


def row_count(physical: str) -> exp.Select:
    return exp.select(exp.alias_(_count(), "row_count")).from_(table(physical, "t"))


def current_row_ties(physical: str, keys: Sequence[str], rule: exp.Expr) -> exp.Select:
    cols = [column("t", k) for k in keys]
    inner = (
        exp.select(*cols)
        .from_(table(physical, "t"))
        .where(rule)
        .group_by(*cols)
        .having(exp.GT(this=_count(), expression=exp.Literal.number(1)))
    )
    return exp.select(exp.alias_(_count(), "tied_keys")).from_(inner.subquery("d"))


def _literal(value: str | float) -> exp.Expr:
    if isinstance(value, str):
        return exp.Literal.string(value)
    return exp.Literal.number(int(value) if float(value).is_integer() else value)


def value_set(physical: str, field: str, values: Sequence[str | float] | None = None) -> exp.Select:
    """How many distinct values a field holds, how many fall outside its declared domain, and
    on how many rows: counts, never the values. Nulls are never outside the domain."""
    col = column("t", field)
    selects = [exp.alias_(exp.Count(this=exp.Distinct(expressions=[col])), "distinct_values")]
    if values:
        outside = exp.Not(this=exp.In(this=col, expressions=[_literal(v) for v in values]))
        case = exp.Case(ifs=[exp.If(this=outside, true=col)])
        selects.append(
            exp.alias_(exp.Count(this=exp.Distinct(expressions=[case])), "outside_values")
        )
        flag = exp.Case(ifs=[exp.If(this=outside.copy(), true=exp.Literal.number(1))])
        selects.append(exp.alias_(exp.Count(this=flag), "outside_rows"))
    return exp.select(*selects).from_(table(physical, "t"))

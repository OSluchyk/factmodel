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
    "rollup": (
        "parents_compared",
        "exact",
        "within_rounding",
        "beyond",
        "parents_with_suppressed_child",
        "suppressed_parents_disclosed_children",
    ),
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
    return join_match_on(source, target, on, [column("s", a) for a, _ in pairs])


def join_match_on(
    source: str,
    target: str,
    on: exp.Expr,
    source_keys: Sequence[exp.Expr],
    source_filters: Sequence[exp.Expr] = (),
    target_filters: Sequence[exp.Expr] = (),
) -> exp.Select:
    """``join_match`` for any join condition over aliases ``s`` and ``t`` (D-017). A source row
    counts when every column in ``source_keys`` is not null and every source filter holds; a
    target row counts for ``orphans_right`` when every target filter holds."""
    keyed = exp.and_(_not_null(source_keys), *(f.copy() for f in source_filters))
    any_target = exp.select(exp.Literal.number(1)).from_(table(target, "t")).where(on)
    any_source = exp.select(exp.Literal.number(1)).from_(table(source, "s")).where(on.copy())
    source_rows = exp.select(_count()).from_(table(source, "s")).where(keyed)
    orphans_left = (
        exp.select(_count())
        .from_(table(source, "s"))
        .where(exp.and_(keyed.copy(), exp.Not(this=exp.Exists(this=any_target))))
    )
    orphans_right = (
        exp.select(_count())
        .from_(table(target, "t"))
        .where(
            exp.and_(*(f.copy() for f in target_filters), exp.Not(this=exp.Exists(this=any_source)))
        )
    )
    return exp.select(
        _scalar(source_rows, "source_rows"),
        _scalar(orphans_left, "orphans_left"),
        _scalar(orphans_right, "orphans_right"),
    )


def fan_out(target: str, fields: Sequence[str]) -> exp.Select:
    """The most target rows that share one join-key value: how many rows a source row meets."""
    return fan_out_on(target, [column("t", f) for f in fields])


def fan_out_on(
    target: str, keys: Sequence[exp.Expr], filters: Sequence[exp.Expr] = ()
) -> exp.Select:
    """``fan_out`` grouped by any target-side expressions over alias ``t``, counting target rows
    where every filter holds (D-017)."""
    per_key = (
        exp.select(exp.alias_(_count(), "n"))
        .from_(table(target, "t"))
        .where(exp.and_(_not_null(keys), *(f.copy() for f in filters)))
        .group_by(*(k.copy() for k in keys))
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


def _flag(predicate: exp.Expr | None) -> exp.Expr:
    if predicate is None:
        return exp.Literal.number(0)
    one, zero = exp.Literal.number(1), exp.Literal.number(0)
    return exp.Case(ifs=[exp.If(this=predicate, true=one)], default=zero)


def _count_if(condition: exp.Expr, name: str) -> exp.Expr:
    total = exp.Sum(this=_flag(condition))
    return exp.alias_(exp.Coalesce(this=total, expressions=[exp.Literal.number(0)]), name)


def rollup(
    physical: str,
    hierarchy: exp.Expr,
    code_field: str,
    equal_fields: Sequence[str],
    value: exp.Expr,
    suppressed: exp.Expr | None,
) -> exp.Select:
    """Each parent row against the sum of its children at one level (D-020).

    ``hierarchy`` relates a child row ``c`` to its parent row ``p`` through ``code_field``;
    ``equal_fields`` are the other key fields both share. ``value`` and ``suppressed`` are
    written over alias ``t`` and requalified for each side. Counts only.
    """

    def side(node: exp.Expr, alias: str) -> exp.Expr:
        node = node.copy()
        for col in node.find_all(exp.Column):
            col.set("table", exp.to_identifier(alias))
        return node

    on = exp.and_(
        hierarchy.copy(),
        *(exp.EQ(this=column("c", f), expression=column("p", f)) for f in equal_fields),
    )
    keys = [column("p", f) for f in [code_field, *equal_fields]]
    pairs = (
        exp.select(
            exp.alias_(exp.Max(this=side(value, "p")), "parent_value"),
            exp.alias_(
                exp.Max(this=_flag(side(suppressed, "p") if suppressed else None)),
                "parent_suppressed",
            ),
            exp.alias_(_count(), "children"),
            exp.alias_(exp.Sum(this=side(value, "c")), "child_sum"),
            exp.alias_(
                exp.Sum(this=_flag(side(suppressed, "c") if suppressed else None)),
                "suppressed_children",
            ),
        )
        .from_(table(physical, "p"))
        .join(table(physical, "c"), on=on)
        .group_by(*keys)
    )

    def col(name: str) -> exp.Expr:
        return exp.column(name, table="r")

    zero = exp.Literal.number(0)
    clean = exp.and_(
        exp.EQ(this=col("parent_suppressed"), expression=zero),
        exp.EQ(this=col("suppressed_children"), expression=zero.copy()),
    )
    diff = exp.Abs(this=exp.Sub(this=col("child_sum"), expression=col("parent_value")))
    return exp.select(
        _count_if(clean, "parents_compared"),
        _count_if(
            exp.and_(clean.copy(), exp.EQ(this=col("child_sum"), expression=col("parent_value"))),
            "exact",
        ),
        _count_if(
            exp.and_(
                clean.copy(),
                exp.GT(this=diff, expression=zero.copy()),
                exp.LTE(this=diff.copy(), expression=col("children")),
            ),
            "within_rounding",
        ),
        _count_if(
            exp.and_(clean.copy(), exp.GT(this=diff.copy(), expression=col("children"))), "beyond"
        ),
        _count_if(
            exp.GT(this=col("suppressed_children"), expression=zero.copy()),
            "parents_with_suppressed_child",
        ),
        _count_if(
            exp.and_(
                exp.EQ(this=col("parent_suppressed"), expression=exp.Literal.number(1)),
                exp.LT(this=col("suppressed_children"), expression=col("children")),
            ),
            "suppressed_parents_disclosed_children",
        ),
    ).from_(pairs.subquery("r"))

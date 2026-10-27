"""Relationship joins: the equality form and boolean expressions (D-017).

The equality form is ``<entity>.<field> = <entity>.<field>``, joined with ``AND``; a field may
be a nested path. Any other join is a boolean SQL expression in sqlglot's neutral dialect,
in which every column is ``<entity>.<field>`` and exactly the source and the target occur.
For a self-reference the left operand of each top-level comparison is the source row and the
right operand the target row, as in the equality form.
"""

import re
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

_SIDE = r"[^\s=]+\.[^\s=]+"
EQUALITY = re.compile(rf"^{_SIDE} = {_SIDE}( AND {_SIDE} = {_SIDE})*$")


class JoinError(ValueError):
    """A join that cannot be read."""


@dataclass(frozen=True)
class Join:
    text: str
    expression: bool
    # (entity, field address) of every column, in order of appearance
    columns: tuple[tuple[str, str], ...]

    @property
    def entities(self) -> set[str]:
        return {entity for entity, _ in self.columns}


def parse(text: str) -> Join:
    """Read a join; raise JoinError when it is neither form."""
    if EQUALITY.match(text):
        columns = []
        for condition in text.split(" AND "):
            for side in condition.split(" = "):
                entity, _, address = side.partition(".")
                columns.append((entity, address))
        return Join(text, False, tuple(columns))
    tree = _tree(text)
    columns = []
    for col in tree.find_all(exp.Column):
        if not col.table or col.args.get("db") is not None:
            raise JoinError(f"column {col.sql()!r} must be <entity>.<field>")
        columns.append((col.table, col.name))
    if not columns:
        raise JoinError("the join names no column")
    return Join(text, True, tuple(columns))


def _tree(text: str) -> exp.Expr:
    try:
        tree = sqlglot.parse_one(text)
    except ParseError as error:
        raise JoinError(f"cannot parse join: {error.errors[0]['description']}") from error
    if isinstance(tree, exp.Select | exp.Subquery) or tree.find(exp.Select):
        raise JoinError("a join is a condition, not a query")
    return tree


def _conjuncts(tree: exp.Expr) -> list[exp.Expr]:
    if isinstance(tree, exp.And):
        return [*_conjuncts(tree.this), *_conjuncts(tree.expression)]
    if isinstance(tree, exp.Paren):
        return _conjuncts(tree.this)
    return [tree]


def _requalify(node: exp.Expr, alias: str) -> exp.Expr:
    node = node.copy()
    for col in node.find_all(exp.Column):
        col.set("table", exp.to_identifier(alias))
    return node


@dataclass(frozen=True)
class Parts:
    """The top-level conjuncts of an expression join, sorted by which ends they read.

    ``pairs`` are equalities with the source on one side and the target on the other, as
    (source operand, target operand); ``source_filters`` and ``target_filters`` read one end
    only; ``other`` compares the ends in any other way. Columns keep their entity qualifiers.
    """

    pairs: tuple[tuple[exp.Expr, exp.Expr], ...]
    source_filters: tuple[exp.Expr, ...]
    target_filters: tuple[exp.Expr, ...]
    other: tuple[exp.Expr, ...]


def _comparison(part: exp.Expr) -> exp.Binary:
    """The comparison a self-reference conjunct is, under any NOT (``x IS NOT NULL``)."""
    inner = part
    while isinstance(inner, exp.Not | exp.Paren):
        inner = inner.this
    if not isinstance(inner, exp.Binary):
        raise JoinError("a self-reference join is a conjunction of comparisons")
    return inner


def _owner(node: exp.Expr) -> set[str]:
    return {col.table for col in node.find_all(exp.Column)}


def parts(text: str, source: str, target: str) -> Parts:
    """Split an expression join into its conjuncts (D-017).

    For a self-reference every conjunct must be a comparison, possibly negated: its left operand
    reads the source row and its right operand the target row; a comparison with columns on one
    side only is a filter on that end.
    """
    pairs: list[tuple[exp.Expr, exp.Expr]] = []
    sources: list[exp.Expr] = []
    targets: list[exp.Expr] = []
    other: list[exp.Expr] = []
    for part in _conjuncts(_tree(text)):
        if source == target:
            inner = _comparison(part)
            left, right = bool(_owner(inner.this)), bool(_owner(inner.expression))
            if left and right and isinstance(part, exp.EQ):
                pairs.append((part.this, part.expression))
            elif left and right:
                other.append(part)
            elif right:
                targets.append(part)
            else:
                sources.append(part)
            continue
        owners = _owner(part)
        if owners == {source}:
            sources.append(part)
        elif owners == {target}:
            targets.append(part)
        elif (
            isinstance(part, exp.EQ)
            and _owner(part.this) == {source}
            and _owner(part.expression) == {target}
        ):
            pairs.append((part.this, part.expression))
        elif (
            isinstance(part, exp.EQ)
            and _owner(part.this) == {target}
            and _owner(part.expression) == {source}
        ):
            pairs.append((part.expression, part.this))
        else:
            other.append(part)
    return Parts(tuple(pairs), tuple(sources), tuple(targets), tuple(other))


def condition(
    text: str, source: str, target: str, source_alias: str, target_alias: str
) -> exp.Expr:
    """The whole expression with entity ids replaced by table aliases."""
    if source != target:
        tree = _tree(text).copy()
        for col in tree.find_all(exp.Column):
            col.set(
                "table", exp.to_identifier(source_alias if col.table == source else target_alias)
            )
        return tree
    out = []
    for part in _conjuncts(_tree(text)):
        node = part.copy()
        inner = _comparison(node)
        inner.set("this", _requalify(inner.this, source_alias))
        inner.set("expression", _requalify(inner.expression, target_alias))
        out.append(node)
    return exp.and_(*out)


def aliased(nodes: tuple[exp.Expr, ...], alias: str) -> list[exp.Expr]:
    return [_requalify(n, alias) for n in nodes]


def unique_right_side(text: str, source: str, target: str, keys: list[list[str]]) -> bool:
    """Whether a key of the target is exactly the target side of the join (D-017).

    Every conjunct that compares the two ends must be an equality whose target operand is a
    bare column of the target, and the set of those columns must equal one of ``keys``.
    Conjuncts that read one end only are filters and do not count.
    """
    split = parts(text, source, target)
    if not split.pairs or split.other:
        return False
    fields = []
    for _, right in split.pairs:
        if not isinstance(right, exp.Column):
            return False
        fields.append(right.name)
    return any(set(fields) == set(key) for key in keys if key)

"""What one query uses of a layer: entities, fields, joins, concepts and measures.

The trace reads SQL text only, in the neutral dialect that names tables by entity id. Columns
are qualified with the model's entity fields as the schema; a column of a derived table or a
CTE is followed to the base columns of the projection it names. A column that cannot be
attributed is counted in ``unresolved``, never guessed. The trace holds model identifiers
only: no literal, no SQL text.

Only what the query reads counts: a CTE or derived table that no read query names, and the
tables inside it, are not used.

Joins come in two classes. ``as_declared``: the relationship's own condition, written between
the two base tables. ``otherwise`` (weak): both entities occur, but not joined by that
condition, for example through a derived table, or in two unrelated subqueries. A join whose
relationship is a target set or whose condition the trace cannot read is not evaluated.
Concepts are evaluated in the ``field`` form, and in the ``predicate`` form as written (an
equivalent condition written otherwise is not found); every other form is not evaluated. The
measure match is weak: every field of the expression occurs and, when the measure aggregates,
its function occurs.
"""

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, traverse_scope

from factmodel.model.loader import Model
from factmodel.model.types import Concept, Layer, Measure

EVALUATED_FORMS = ("field", "predicate")
CONCEPT_FORMS = ("field", "predicate", "distinct", "values_table")
# the aggregate function a measure_aggregation value names (vocabulary block
# measure_aggregation); every value is here or in NOT_CHECKED, which a test keeps true
NOT_CHECKED = ("none",)
AGGREGATES: dict[str, tuple[type[exp.Expr], bool]] = {
    "sum": (exp.Sum, False),
    "count": (exp.Count, False),
    "count_distinct": (exp.Count, True),
    "avg": (exp.Avg, False),
    "min": (exp.Min, False),
    "max": (exp.Max, False),
}

Column = tuple[str, str]  # (entity id, field name) as the model spells them


@dataclass(frozen=True)
class Trace:
    parsed: bool
    entities: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    joins_as_declared: tuple[str, ...] = ()
    joins_otherwise: tuple[str, ...] = ()
    concepts: tuple[str, ...] = ()
    concepts_not_evaluated: tuple[str, ...] = ()
    measures_weak: tuple[str, ...] = ()
    outside_layer: tuple[str, ...] = ()
    unknown_tables: int = 0
    unresolved: int = 0

    @property
    def joins(self) -> tuple[str, ...]:
        return tuple(sorted({*self.joins_as_declared, *self.joins_otherwise}))

    def as_dict(self) -> dict[str, Any]:
        return {
            "parsed": self.parsed,
            "entities": list(self.entities),
            "fields": list(self.fields),
            "joins": {
                "as_declared": list(self.joins_as_declared),
                "otherwise": list(self.joins_otherwise),
            },
            "concepts": list(self.concepts),
            "concepts_not_evaluated": list(self.concepts_not_evaluated),
            "measures_weak": list(self.measures_weak),
            "outside_layer": list(self.outside_layer),
            "unknown_tables": self.unknown_tables,
            "unresolved": self.unresolved,
        }


def concept_form(concept: Concept) -> str:
    """The form of a concept; ``unknown`` for a form the trace does not know (not evaluated)."""
    return next((f for f in CONCEPT_FORMS if getattr(concept, f, None) is not None), "unknown")


def join_form(ref: str, model: Model) -> str:
    """``condition`` when the trace can evaluate the join; otherwise why it cannot:
    ``target_set``, ``no_join`` (an unresolved relationship), ``unreadable`` or ``missing``."""
    source_id, _, key = ref.partition(".")
    owner = model.entities.get(source_id)
    rel = next((r for r in owner.relationships if r.key == key), None) if owner else None
    if rel is None:
        return "missing"
    if rel.join is None:
        return "no_join"
    if not isinstance(rel.join, str):
        return "target_set"
    if _layer_condition(rel.join, _Names.of(model)) is None:
        return "unreadable"
    return "condition"


@dataclass
class _Names:
    """Model spelling of entity ids and field names, looked up case-insensitively."""

    entities: dict[str, str]
    fields: dict[str, dict[str, str]]
    schema: dict[str, object]

    @classmethod
    def of(cls, model: Model) -> "_Names":
        entities = {e.lower(): e for e in model.entities}
        # a reference may name a table by its physical name, as bind leaves it: read the last
        # part of the physical name as the entity when no entity id and no other entity has it
        physical: dict[str, list[str]] = {}
        for e, entity in model.entities.items():
            physical.setdefault(entity.physical_name.split(".")[-1].lower(), []).append(e)
        for name, ids in physical.items():
            if name not in entities and len(ids) == 1:
                entities[name] = ids[0]
        fields = {
            key: {f.name.lower(): f.name for f in model.entities[e].fields}
            for key, e in entities.items()
        }
        schema: dict[str, object] = {
            key: {f.name.lower(): "TEXT" for f in model.entities[e].fields}
            for key, e in entities.items()
        }
        return cls(entities, fields, schema)

    def column(self, table: str, name: str) -> Column | None:
        entity = self.entities.get(table.lower())
        if entity is None:
            return None
        found = self.fields[table.lower()].get(name.lower())
        return (entity, found) if found is not None else None


@dataclass
class _Resolver:
    names: _Names
    scopes: list[Scope]
    unresolved: set[int] = field(default_factory=set)
    # column node -> base columns its value comes from
    lineage: dict[int, frozenset[Column]] = field(default_factory=dict)
    # column node -> the base column it is, read from a base table in its own or an outer scope
    direct: dict[int, Column] = field(default_factory=dict)
    # column node -> the one base column it passes through unchanged, across derived tables
    passthrough: dict[int, Column] = field(default_factory=dict)
    _done: dict[tuple[int, str], tuple[frozenset[Column], Column | None]] = field(
        default_factory=dict
    )

    def source(self, scope: Scope, name: str) -> object | None:
        current: Scope | None = scope
        while current is not None:
            if name in current.sources:
                return current.sources[name]
            current = current.parent
        return None

    def column(self, scope: Scope, col: exp.Column) -> None:
        if id(col) in self.lineage or id(col) in self.unresolved:
            return
        table = col.table
        source = self.source(scope, table) if table else None
        if isinstance(source, exp.Table):
            base = self.names.column(source.name, col.name)
            if base is None:
                self.unresolved.add(id(col))
                return
            self.lineage[id(col)] = frozenset({base})
            self.direct[id(col)] = base
            self.passthrough[id(col)] = base
            return
        if isinstance(source, Scope):
            bases, through = self.output(source, col.name)
            if bases is None:
                self.unresolved.add(id(col))
                return
            self.lineage[id(col)] = bases
            if through is not None:
                self.passthrough[id(col)] = through
            return
        self.unresolved.add(id(col))

    def output(self, scope: Scope, name: str) -> tuple[frozenset[Column] | None, Column | None]:
        """Base columns of the projection ``name`` of a derived table or CTE."""
        key = (id(scope), name.lower())
        if key in self._done:
            return self._done[key]
        select = scope.expression
        if not isinstance(select, exp.Select):
            return None, None
        projection = next(
            (p for p in select.selects if p.alias_or_name.lower() == name.lower()), None
        )
        if projection is None:
            return None, None
        bases: set[Column] = set()
        for col in projection.find_all(exp.Column):
            self.column(self.owner(scope, col), col)
            if id(col) not in self.lineage:
                return None, None
            bases |= self.lineage[id(col)]
        inner = projection.unalias() if isinstance(projection, exp.Alias) else projection
        through = self.passthrough.get(id(inner)) if isinstance(inner, exp.Column) else None
        result = (frozenset(bases), through)
        self._done[key] = result
        return result

    def owner(self, scope: Scope, col: exp.Column) -> Scope:
        """The scope a column node belongs to (a projection may hold a subquery)."""
        for candidate in self.scopes:
            if any(c is col for c in candidate.columns):
                return candidate
        return scope


def _projection_columns(scope: Scope) -> set[int]:
    select = scope.expression
    if not isinstance(select, exp.Select):
        return set()
    return {id(c) for p in select.selects for c in p.find_all(exp.Column)}


def _read_scopes(scopes: list[Scope]) -> list[Scope]:
    """The scopes the query reads: the root, the subqueries of a read scope, and the derived
    tables and CTEs a read scope names as a source."""
    if not scopes:
        return []
    root = scopes[-1]
    read: dict[int, Scope] = {id(root): root}
    todo = [root]
    while todo:
        scope = todo.pop()
        # selected_sources: what FROM and JOIN name; sources also lists every CTE in reach
        children = [s for _, s in scope.selected_sources.values() if isinstance(s, Scope)]
        children += [*scope.subquery_scopes, *scope.set_operation_scopes, *scope.udtf_scopes]
        for child in children:
            if id(child) not in read:
                read[id(child)] = child
                todo.append(child)
    return [s for s in scopes if id(s) in read]


def _derived(scope: Scope) -> bool:
    """A scope whose projections are read only when an outer query names them."""
    return scope.is_derived_table or scope.is_cte


def _canonical(node: exp.Expr, columns: dict[int, Column]) -> str | None:
    """The node with every column written as entity.field, lower case; None when a column has
    no entry. Equalities and inequalities are written with their sides sorted."""
    originals = list(node.find_all(exp.Column))
    if any(id(c) not in columns for c in originals):
        return None
    copy = node.copy()
    for original, target in zip(originals, list(copy.find_all(exp.Column)), strict=True):
        entity, name = columns[id(original)]
        target.replace(exp.column(name.lower(), table=entity.lower()))
    return _sql(copy)


def _sql(node: exp.Expr) -> str:
    def sort_sides(n: exp.Expr) -> exp.Expr:
        if isinstance(n, exp.EQ | exp.NEQ):
            left, right = sorted((n.this, n.expression), key=lambda s: s.sql())
            return n.__class__(this=left, expression=right)
        return n

    for ident in node.find_all(exp.Identifier):
        ident.set("this", ident.name.lower())
        ident.set("quoted", False)
    while isinstance(node, exp.Paren):
        node = node.this
    return node.transform(sort_sides).sql()


def _conjuncts(node: exp.Expr) -> Iterator[exp.Expr]:
    while isinstance(node, exp.Paren):
        node = node.this
    if isinstance(node, exp.And):
        yield from _conjuncts(node.this)
        yield from _conjuncts(node.expression)
    else:
        yield node


def _model_columns(node: exp.Expr, names: _Names) -> dict[int, Column] | None:
    """Columns of a layer expression, already written as entity.field."""
    out: dict[int, Column] = {}
    for col in node.find_all(exp.Column):
        base = names.column(col.table, col.name) if col.table else None
        if base is None:
            return None
        out[id(col)] = base
    return out


def _layer_condition(text: str, names: _Names) -> list[str] | None:
    try:
        tree = sqlglot.parse_one(text)
    except sqlglot.errors.ParseError:
        return None
    parts = []
    for part in _conjuncts(tree):
        columns = _model_columns(part, names)
        canonical = _canonical(part, columns) if columns is not None else None
        if canonical is None:
            return None
        parts.append(canonical)
    return parts


def _conditions(scope: Scope) -> Iterable[exp.Expr]:
    select = scope.expression
    if not isinstance(select, exp.Select):
        return
    where = select.args.get("where")
    if where is not None:
        yield where.this
    for join in select.args.get("joins") or []:
        on = join.args.get("on")
        if on is not None:
            yield on


def _measure_used(measure: Measure, fields: set[Column], aggs: set[Any], names: _Names) -> bool:
    try:
        tree = sqlglot.parse_one(measure.expression)
    except sqlglot.errors.ParseError:
        return False
    columns = _model_columns(tree, names)
    if not columns or not set(columns.values()) <= fields:
        return False
    wanted = AGGREGATES.get(measure.aggregation)
    return wanted is None or wanted in aggs


def trace(sql: str, layer: Layer, model: Model) -> Trace:
    """What ``sql`` uses of ``layer``. SQL that does not parse gives ``parsed=False``."""
    names = _Names.of(model)
    try:
        tree = sqlglot.parse_one(sql)
    except Exception:  # SQL sqlglot cannot read; the error text may quote literals
        return Trace(parsed=False)
    # the model is read case-insensitively, so quoting and case carry no meaning here
    for ident in tree.find_all(exp.Identifier):
        ident.set("this", ident.name.lower())
        ident.set("quoted", False)
    try:
        qualified = qualify(
            tree.copy(),
            schema=names.schema,
            validate_qualify_columns=False,
            quote_identifiers=False,
            identify=False,
        )
    except Exception:  # a column the schema does not know: trace as written, attribute less
        qualified = tree
    try:
        scopes = traverse_scope(qualified)
    except Exception:
        return Trace(parsed=False)
    scopes = _read_scopes(scopes)
    resolver = _Resolver(names, scopes)

    tables: set[str] = set()
    unknown: set[str] = set()
    for scope in scopes:
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                entity = names.entities.get(source.name.lower())
                if entity is None:
                    unknown.add(source.name.lower())
                else:
                    tables.add(entity)

    # a projection of a derived table or CTE is read only when an outer query names it
    used: set[Column] = set()
    unresolved = 0
    for scope in scopes:
        skip = _projection_columns(scope) if _derived(scope) else set()
        for col in scope.columns:
            if id(col) in skip:
                continue
            resolver.column(scope, col)
            if id(col) in resolver.unresolved:
                unresolved += 1
            used |= resolver.lineage.get(id(col), frozenset())

    direct: set[str] = set()
    for scope in scopes:
        for condition in _conditions(scope):
            for part in _conjuncts(condition):
                canonical = _canonical(part, resolver.direct)
                if canonical is not None:
                    direct.add(canonical)
    predicates: set[str] = set()
    for scope in scopes:
        for node in scope.find_all(exp.Predicate, exp.Not):
            canonical = _canonical(node, resolver.passthrough)
            if canonical is not None:
                predicates.add(canonical)

    layer_entities = {e.entity for e in layer.entities}
    as_declared, otherwise = [], []
    for ref in layer.joins or []:
        if join_form(ref, model) != "condition":
            continue  # not evaluated: never counted, never a zero
        source_id, _, key = ref.partition(".")
        rel = next(r for r in model.entities[source_id].relationships if r.key == key)
        target = rel.targets[0]
        if source_id not in tables or target not in tables:
            continue
        parts = _layer_condition(str(rel.join), names)
        if parts is not None and set(parts) <= direct:
            as_declared.append(ref)
        else:
            otherwise.append(ref)

    concepts, not_evaluated = [], []
    for concept in layer.concepts or []:
        form = concept_form(concept)
        if form not in EVALUATED_FORMS:
            not_evaluated.append(concept.id)
            continue
        if form == "field":
            entity_id, _, name = (concept.field or "").partition(".")
            base = names.column(entity_id, name)
            if base is not None and base in used:
                concepts.append(concept.id)
            continue
        parts = _layer_condition(concept.predicate or "", names)
        if parts is not None and set(parts) <= predicates:
            concepts.append(concept.id)

    aggs: set[tuple[type[exp.Expr], bool]] = set()
    for scope in scopes:
        for node in scope.find_all(exp.AggFunc):
            aggs.add((type(node), isinstance(node.this, exp.Distinct)))
    measures = [m.id for m in layer.measures or [] if _measure_used(m, used, aggs, names)]
    return Trace(
        parsed=True,
        entities=tuple(sorted(tables & layer_entities)),
        fields=tuple(sorted(f"{e}.{f}" for e, f in used)),
        joins_as_declared=tuple(sorted(as_declared)),
        joins_otherwise=tuple(sorted(otherwise)),
        concepts=tuple(sorted(concepts)),
        concepts_not_evaluated=tuple(sorted(not_evaluated)),
        measures_weak=tuple(sorted(measures)),
        outside_layer=tuple(sorted(tables - layer_entities)),
        unknown_tables=len(unknown),
        unresolved=unresolved,
    )


# Coverage over a corpus ---------------------------------------------------------------------

KINDS = ("entity", "join", "concept", "measure")
LABELS = {"entity": "entity", "join": "join", "concept": "concept", "measure": "measure (weak)"}


def enforced(kind: str, form: str) -> bool:
    """Whether D-023 asks a reviewed layer for a reason when no passing item uses the element:
    entities, joins the trace evaluates, field concepts and measures."""
    if kind == "join":
        return form == "condition"
    if kind == "concept":
        return form == "field"
    return True


@dataclass(frozen=True)
class Element:
    kind: str
    id: str
    evaluated: bool = True
    form: str = ""
    items: int = 0
    passing: int = 0
    references: tuple[str, ...] = ()
    as_declared: int = 0
    otherwise: int = 0

    @property
    def as_written(self) -> bool:
        return self.kind == "concept" and self.form == "predicate"

    @property
    def label(self) -> str:
        return f"{LABELS[self.kind]} {self.id}" + (" (as written)" if self.as_written else "")

    @property
    def enforced(self) -> bool:
        return self.evaluated and enforced(self.kind, self.form)


def parse_label(label: str) -> tuple[str, str]:
    """(kind, id) of a label written by ``Element.label``."""
    kind = label.split(" ", 1)[0]
    rest = label[len(LABELS.get(kind, kind)) + 1 :]
    return kind, rest.split(" ", 1)[0]


@dataclass(frozen=True)
class Coverage:
    elements: tuple[Element, ...]
    unresolved_items: int

    @property
    def evaluated(self) -> list[Element]:
        return [e for e in self.elements if e.evaluated]

    @property
    def not_exercised(self) -> list[Element]:
        """No item uses it (predicate concepts are listed apart, as not found as written)."""
        return [e for e in self.evaluated if e.items == 0 and not e.as_written]

    @property
    def not_found_as_written(self) -> list[Element]:
        return [e for e in self.evaluated if e.items == 0 and e.as_written]

    @property
    def no_passing_item(self) -> list[Element]:
        """Some item uses it, no passing item does."""
        return [e for e in self.evaluated if e.items > 0 and e.passing == 0]

    @property
    def tested(self) -> list[Element]:
        return [e for e in self.evaluated if e.passing > 0]

    @property
    def not_evaluated(self) -> list[Element]:
        return [e for e in self.elements if not e.evaluated]

    def summary(self) -> dict[str, Any]:
        """The ``coverage`` key of last-run.json: model identifiers and counts only."""
        exercised = [e for e in self.evaluated if e.items > 0]
        return {
            "elements": len(self.evaluated),
            "exercised": len(exercised),
            "not_exercised": [e.label for e in self.not_exercised],
            "not_found_as_written": [e.label for e in self.not_found_as_written],
            "no_passing_item": [e.label for e in self.no_passing_item],
            "tested": [e.label for e in self.tested],
            "not_evaluated": [f"{e.label} ({e.form})" for e in self.not_evaluated],
            "unresolved_items": self.unresolved_items,
        }


def uses(t: Trace, kind: str) -> tuple[str, ...]:
    return {
        "entity": t.entities,
        "join": t.joins,
        "concept": t.concepts,
        "measure": t.measures_weak,
    }[kind]


def references(layer: Layer, kind: str, element_id: str) -> tuple[str, ...]:
    """Other layer keys that name an element, so that an element no item uses is not read as
    unused. Joins that name an entity are elements of their own and are left out."""
    out: list[str] = []
    measures = layer.measures or []
    if kind == "entity":
        prefix = f"{element_id}."
        for m in measures:
            out += [
                f"rollup of measure {m.id} ({r.hierarchy})"
                for r in m.rollups or []
                if r.hierarchy.startswith(prefix)
            ]
        for c in layer.concepts or []:
            text = " ".join(
                [
                    c.field or "",
                    c.predicate or "",
                    *(c.distinct or []),
                    (c.values_table.entity or "") if c.values_table else "",
                ]
            )
            if prefix in text or (c.values_table and c.values_table.entity == element_id):
                out.append(f"concept {c.id}")
        for m in measures:
            if m.grain.entity == element_id or prefix in m.expression:
                out.append(f"measure {m.id}")
    elif kind == "join":
        out += [
            f"rollup of measure {m.id}"
            for m in measures
            for r in m.rollups or []
            if r.hierarchy == element_id
        ]
    elif kind == "concept":
        out += [
            f"default filter of entity {e.entity}"
            for e in layer.entities
            if element_id in (e.default_filters or [])
        ]
        out += [
            f"rollup of measure {m.id} (suppressed)"
            for m in measures
            for r in m.rollups or []
            if r.suppressed == element_id
        ]
    else:
        out += [f"companion of measure {m.id}" for m in measures if m.companion == element_id]
    return tuple(sorted(set(out)))


def forms(layer: Layer, model: Model) -> list[tuple[str, str, str]]:
    """(kind, id, form) of every element of the layer, in layer order."""
    out = [("entity", e.entity, "") for e in layer.entities]
    out += [("join", j, join_form(j, model)) for j in layer.joins or []]
    out += [("concept", c.id, concept_form(c)) for c in layer.concepts or []]
    out += [("measure", m.id, "") for m in layer.measures or []]
    return out


def evaluated(kind: str, form: str) -> bool:
    if kind == "join":
        return form == "condition"
    if kind == "concept":
        return form in EVALUATED_FORMS
    return True


def coverage(layer: Layer, model: Model, traced: Iterable[tuple[str, Trace]]) -> Coverage:
    """For every element of the layer, the items whose reference uses it and how many of those
    pass; ``traced`` holds (outcome, trace of the reference) per item."""
    rows = list(traced)
    elements = []
    for kind, element_id, form in forms(layer, model):
        ok = evaluated(kind, form)
        using = [(outcome, t) for outcome, t in rows if ok and element_id in uses(t, kind)]
        outcomes = [outcome for outcome, _ in using]
        elements.append(
            Element(
                kind,
                element_id,
                ok,
                form,
                len(using),
                outcomes.count("pass"),
                references(layer, kind, element_id),
                as_declared=sum(1 for _, t in using if element_id in t.joins_as_declared),
                otherwise=sum(1 for _, t in using if element_id in t.joins_otherwise),
            )
        )
    unresolved = sum(1 for _, t in rows if not t.parsed or t.unresolved)
    return Coverage(tuple(elements), unresolved)


def difference(consumer: Trace | None, reference: Trace) -> str:
    """What only one side uses, for an item that does not pass; model identifiers only."""
    if consumer is None:
        return "the consumer gave no SQL"
    if not consumer.parsed:
        return "the consumer's SQL does not parse"
    if not reference.parsed:
        return "the reference does not parse"

    def joins(t: Trace) -> set[str]:
        return {f"{j} (as declared)" for j in t.joins_as_declared} | {
            f"{j} (otherwise, weak)" for j in t.joins_otherwise
        }

    parts = []
    for side, mine, theirs in (
        ("consumer only", consumer, reference),
        ("reference only", reference, consumer),
    ):
        found = []
        for name, a, b in (
            (
                "entities",
                set(mine.entities) | set(mine.outside_layer),
                set(theirs.entities) | set(theirs.outside_layer),
            ),
            ("fields", set(mine.fields), set(theirs.fields)),
            ("joins", joins(mine), joins(theirs)),
            ("concepts", set(mine.concepts), set(theirs.concepts)),
        ):
            extra = sorted(a - b)
            if extra:
                found.append(f"{name} {', '.join(extra)}")
        if found:
            parts.append(f"{side}: " + "; ".join(found))
    if consumer.outside_layer:
        parts.append("the consumer leaves the layer: " + ", ".join(consumer.outside_layer))
    if consumer.unknown_tables:
        parts.append(f"the consumer names {consumer.unknown_tables} table(s) not in the model")
    return " | ".join(parts) or "nothing the trace can see"

"""Key and join proposals measured on data (``fact propose keys``, ``fact propose joins``).

Both commands read a snapshot of a source and measure the live source through the ``sql``
adapter, counts only. ``keys`` tests single columns and column pairs of every table that
declares no primary key for uniqueness and non-null. ``joins`` tests every type-compatible
column pair across tables for inclusion: the share of the source column's distinct non-null
values that exist in the target column, where the target column (or pair) is unique.
Candidates go to ``drafts/<source>/keys.yaml`` and ``drafts/<source>/joins.yaml``, each with a
measurement record (``status: inferred``), never into ``physical/``: a person, not this code,
turns a candidate into a key or a relationship. The method is a brute-force check with two
prunings, adequate for tens of tables (``spec/ALGORITHMS.md``, section 4).
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from sqlglot import exp

from factmodel import vocabulary
from factmodel.core.drafts import slug
from factmodel.model.types import Snapshot, SnapshotObject
from factmodel.probes import build

KEYS_FILE = "keys.yaml"
JOINS_FILE = "joins.yaml"
HEADER = "# written by fact propose - a proposal, not a model file; the gate never reads drafts/"


def key_classes() -> frozenset[str]:
    """Type classes a key or a join column may have (``vocabulary:key_type_class``)."""
    return frozenset(vocabulary.load()["key_type_class"])


# Queries (neutral sqlglot ASTs, rendered per dialect, counts only) ---------------------------


def column_stats(physical: str, fields: Sequence[str]) -> exp.Select:
    """Row count, non-null count and distinct count of every field, in one query."""
    selects: list[exp.Expr] = [exp.alias_(exp.Count(this=exp.Star()), "row_count")]
    for i, name in enumerate(fields):
        col = build.column("t", name)
        selects.append(exp.alias_(exp.Count(this=col), f"non_null_{i}"))
        distinct = exp.Count(this=exp.Distinct(expressions=[col.copy()]))
        selects.append(exp.alias_(distinct, f"distinct_{i}"))
    return exp.select(*selects).from_(build.table(physical, "t"))


def _not_null(cols: Sequence[exp.Expr]) -> exp.Expr:
    return exp.and_(*(exp.Not(this=exp.Is(this=c.copy(), expression=exp.Null())) for c in cols))


def _count() -> exp.Expr:
    return exp.Count(this=exp.Star())


def _scalar(query: exp.Select, name: str) -> exp.Expr:
    return exp.alias_(exp.Subquery(this=query), name)


def pair_stats(physical: str, fields: Sequence[str]) -> exp.Select:
    """Rows where every field is not null, and distinct combinations among them."""
    cols = [build.column("t", f) for f in fields]
    table = build.table(physical, "t")
    non_null = exp.select(_count()).from_(table).where(_not_null(cols))
    inner = exp.select(*cols).distinct().from_(table.copy()).where(_not_null(cols))
    distinct = exp.select(_count()).from_(inner.subquery("d"))
    return exp.select(_scalar(non_null, "non_null"), _scalar(distinct, "distinct"))


def inclusion(
    source: str, source_fields: Sequence[str], target: str, target_fields: Sequence[str]
) -> exp.Select:
    """Distinct non-null source values (or combinations), and how many exist in the target."""
    s_cols = [build.column("s", f) for f in source_fields]
    projected = [exp.alias_(c, f"c{i}") for i, c in enumerate(s_cols)]
    distinct = (
        exp.select(*projected).distinct().from_(build.table(source, "s")).where(_not_null(s_cols))
    )
    on = exp.and_(
        *(
            exp.EQ(this=build.column("t", tf), expression=exp.column(f"c{i}", table="d"))
            for i, tf in enumerate(target_fields)
        )
    )
    exists = exp.select(exp.Literal.number(1)).from_(build.table(target, "t")).where(on)
    total = exp.select(_count()).from_(distinct.subquery("d"))
    included = (
        exp.select(_count()).from_(distinct.copy().subquery("d")).where(exp.Exists(this=exists))
    )
    return exp.select(_scalar(total, "source_distinct"), _scalar(included, "included"))


# Measurements ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnStats:
    object: str
    field: str
    type_class: str
    row_count: int
    non_null: int
    distinct: int

    @property
    def unique(self) -> bool:
        """Every non-null value appears once: fit to be referenced."""
        return self.non_null > 0 and self.distinct == self.non_null

    @property
    def key(self) -> bool:
        """Unique and never null: fit to be a primary key."""
        return self.unique and self.non_null == self.row_count


Runner = Callable[[list[tuple[str, str]]], list[dict[str, Any]]]


@dataclass
class Session:
    """Runs rendered queries, keeps the count and the failures."""

    run: Runner
    dialect: str
    queries: int = 0
    failed: list[str] = field(default_factory=list)

    def one(self, query_id: str, query: exp.Select) -> dict[str, float] | None:
        sql = query.sql(dialect=self.dialect, identify=True)
        self.queries += 1
        result = self.run([(query_id, sql)])[0]
        if "error" in result:
            self.failed.append(query_id)
            return None
        measurement: dict[str, float] = result["measurement"]
        return measurement


def _tables(snap: Snapshot) -> list[SnapshotObject]:
    return [o for o in snap.objects if o.object_type == "table"]


def _candidate_fields(obj: SnapshotObject) -> list[tuple[str, str]]:
    """Top-level fields whose type class may carry a key: (name, type class)."""
    classes = key_classes()
    out = []
    for f in obj.fields:
        cls = f.type_class or "other"
        if f.path is None and cls in classes:
            out.append((f.name, cls))
    return out


def stats_of(session: Session, obj: SnapshotObject) -> dict[str, ColumnStats]:
    """Column statistics of one table, by field name; empty when the query failed."""
    fields = _candidate_fields(obj)
    if not fields:
        return {}
    got = session.one(f"stats-{slug(obj.name)}", column_stats(obj.name, [n for n, _ in fields]))
    if got is None:
        return {}
    rows = int(got["row_count"])
    return {
        name: ColumnStats(
            obj.name, name, cls, rows, int(got[f"non_null_{i}"]), int(got[f"distinct_{i}"])
        )
        for i, (name, cls) in enumerate(fields)
    }


def _declared(obj: SnapshotObject, kinds: Sequence[str]) -> list[tuple[str, ...]]:
    return [tuple(c.fields) for c in obj.constraints or [] if c.constraint_type in kinds]


# Keys ------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyCandidate:
    object: str
    fields: tuple[str, ...]
    row_count: int
    non_null: int
    distinct: int


def propose_keys(
    snap: Snapshot, session: Session, max_columns: int = 2
) -> tuple[list[KeyCandidate], list[str]]:
    """Unique, non-null columns and column pairs of every table without a primary key.

    A pair is tried only when neither column is a key on its own (minimal keys), both are
    never null, and the product of their distinct counts reaches the row count; otherwise the
    pair cannot be unique. Returns the candidates and the tables that were skipped, with why.
    """
    if max_columns not in (1, 2):
        raise ValueError("--max-columns is 1 or 2")
    candidates: list[KeyCandidate] = []
    skipped: list[str] = []
    for obj in sorted(_tables(snap), key=lambda o: o.name):
        if _declared(obj, ["primary_key"]):
            skipped.append(f"{obj.name}: declares a primary key")
            continue
        stats = stats_of(session, obj)
        if not stats:
            skipped.append(f"{obj.name}: no column of a key type class, or the query failed")
            continue
        rows = next(iter(stats.values())).row_count
        if rows == 0:
            skipped.append(f"{obj.name}: no rows")
            continue
        singles = [s for s in stats.values() if s.key]
        for s in singles:
            candidates.append(KeyCandidate(obj.name, (s.field,), rows, s.non_null, s.distinct))
        if max_columns < 2:
            continue
        rest = [s for s in stats.values() if not s.key and s.non_null == rows]
        for a, b in combinations(rest, 2):
            if a.distinct * b.distinct < rows:
                continue
            got = session.one(
                f"pair-{slug(obj.name)}-{slug(a.field)}-{slug(b.field)}",
                pair_stats(obj.name, [a.field, b.field]),
            )
            if got is None:
                continue
            non_null, distinct = int(got["non_null"]), int(got["distinct"])
            if non_null == rows and distinct == rows:
                candidates.append(
                    KeyCandidate(obj.name, (a.field, b.field), rows, non_null, distinct)
                )
    return candidates, skipped


# Joins -----------------------------------------------------------------------------------------


@dataclass(frozen=True)
class JoinCandidate:
    source: str
    source_fields: tuple[str, ...]
    target: str
    target_fields: tuple[str, ...]
    source_distinct: int
    included: int
    target_distinct: int
    source_unique: bool

    @property
    def inclusion(self) -> float:
        return round(self.included / self.source_distinct, 6) if self.source_distinct else 0.0

    @property
    def coverage(self) -> float:
        """The share of the target's distinct values the source reaches: reported, not a rule."""
        return round(self.included / self.target_distinct, 6) if self.target_distinct else 0.0

    @property
    def cardinality(self) -> str:
        """From the uniqueness side only: the target is unique by construction."""
        return "one_to_one" if self.source_unique else "many_to_one"


def _suffix(name: str) -> str:
    head, sep, tail = name.partition("_")
    return tail if sep and len(head) <= 3 and tail else name


def name_note(a: str, b: str) -> str:
    """How the two column names relate. Reported for the reader; never a criterion."""
    if a == b:
        return "same column name (reported, not a criterion)"
    if _suffix(a) == _suffix(b):
        return f"names share the suffix {_suffix(a)} (reported, not a criterion)"
    short, long = sorted((a, b), key=len)
    if short in long:
        return f"{short} is part of {long} (reported, not a criterion)"
    return "names differ (reported, not a criterion)"


def unique_pairs(
    snap: Snapshot, keys: Mapping[str, Sequence[Sequence[str]]]
) -> dict[str, list[tuple[str, ...]]]:
    """Two-column keys per table: declared primary or unique constraints, and the pairs a
    ``keys`` proposal found (``drafts/<source>/keys.yaml``)."""
    out: dict[str, list[tuple[str, ...]]] = {}
    for obj in _tables(snap):
        pairs: list[tuple[str, ...]] = [
            k for k in _declared(obj, ["primary_key", "unique"]) if len(k) == 2
        ]
        pairs += [tuple(k) for k in keys.get(obj.name, []) if len(k) == 2]
        seen: list[tuple[str, ...]] = []
        for p in pairs:
            if p not in seen:
                seen.append(p)
        out[obj.name] = seen
    return out


def propose_joins(
    snap: Snapshot,
    session: Session,
    threshold: float = 0.999,
    keys: Mapping[str, Sequence[Sequence[str]]] | None = None,
) -> tuple[list[JoinCandidate], list[str]]:
    """Inclusions at or above the threshold from every column to every unique column of
    another table of the same type class, and from column pairs to unique column pairs.

    Pruning: a source with more distinct values than the target divided by the threshold
    cannot reach it; a pair is tried only when each of its columns is included on its own.
    """
    if not 0 < threshold <= 1:
        raise ValueError("--threshold is a share between 0 and 1")
    tables = sorted(_tables(snap), key=lambda o: o.name)
    stats = {obj.name: stats_of(session, obj) for obj in tables}
    skipped = [
        f"{name}: no column of a key type class, or the query failed"
        for name, s in stats.items()
        if not s
    ]
    pairs = unique_pairs(snap, keys or {})
    candidates: list[JoinCandidate] = []
    cache: dict[tuple[str, str, str, str], tuple[int, int] | None] = {}

    def single(a: ColumnStats, b: ColumnStats) -> tuple[int, int] | None:
        key = (a.object, a.field, b.object, b.field)
        if key not in cache:
            got = session.one(
                f"inc-{slug(a.object)}-{slug(a.field)}-{slug(b.object)}-{slug(b.field)}",
                inclusion(a.object, [a.field], b.object, [b.field]),
            )
            cache[key] = (int(got["source_distinct"]), int(got["included"])) if got else None
        return cache[key]

    for src in tables:
        for tgt in tables:
            if src.name == tgt.name or not stats[src.name] or not stats[tgt.name]:
                continue
            for a in stats[src.name].values():
                for b in stats[tgt.name].values():
                    if not b.unique or a.type_class != b.type_class or a.distinct == 0:
                        continue
                    if b.distinct < threshold * a.distinct:
                        continue
                    got = single(a, b)
                    if got is None:
                        continue
                    total, included = got
                    if total and included / total >= threshold:
                        candidates.append(
                            JoinCandidate(
                                src.name,
                                (a.field,),
                                tgt.name,
                                (b.field,),
                                total,
                                included,
                                b.distinct,
                                a.unique,
                            )
                        )
            for b_pair in pairs.get(tgt.name, []):
                b1, b2 = (stats[tgt.name].get(f) for f in b_pair)
                if b1 is None or b2 is None:
                    continue
                for a1, a2 in combinations(stats[src.name].values(), 2):
                    for x, y in ((a1, a2), (a2, a1)):
                        if (x.type_class, y.type_class) != (b1.type_class, b2.type_class):
                            continue
                        if x.distinct == 0 or y.distinct == 0:
                            continue
                        if any(
                            (got := single(p, q)) is None
                            or not got[0]
                            or got[1] / got[0] < threshold
                            for p, q in ((x, b1), (y, b2))
                        ):
                            continue
                        got_pair = session.one(
                            f"inc-{slug(src.name)}-{slug(x.field)}-{slug(y.field)}-{slug(tgt.name)}",
                            inclusion(src.name, [x.field, y.field], tgt.name, list(b_pair)),
                        )
                        if got_pair is None:
                            continue
                        total, included = (
                            int(got_pair["source_distinct"]),
                            int(got_pair["included"]),
                        )
                        if total and included / total >= threshold:
                            target_distinct = session.one(
                                f"pair-{slug(tgt.name)}-{slug(b1.field)}-{slug(b2.field)}",
                                pair_stats(tgt.name, list(b_pair)),
                            )
                            candidates.append(
                                JoinCandidate(
                                    src.name,
                                    (x.field, y.field),
                                    tgt.name,
                                    tuple(b_pair),
                                    total,
                                    included,
                                    int(target_distinct["distinct"]) if target_distinct else 0,
                                    total == next(iter(stats[src.name].values())).row_count,
                                )
                            )
    return candidates, skipped


# Documents -------------------------------------------------------------------------------------


def _evidence_id(*parts: str) -> str:
    value = "-".join(["ev", "propose", *parts]).replace("_", "-")
    return value if len(value) <= 64 else slug(value)


def _record(
    record_id: str,
    snap: Snapshot,
    pin: str,
    day: str,
    meta: Mapping[str, str],
    measurement: dict[str, float],
    note: str,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "source": snap.source,
        "pin": pin,
        "measurement": measurement,
        "status": "inferred",
        "read_on": day,
        "environment": meta["environment"],
        "data_quality": meta["data_quality"],
        "note": note,
    }


def keys_document(
    snap: Snapshot,
    candidates: Sequence[KeyCandidate],
    skipped: Sequence[str],
    session: Session,
    pin: str,
    day: str,
    meta: Mapping[str, str],
    max_columns: int,
) -> dict[str, Any]:
    objects: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    for c in candidates:
        entity = slug(c.object)
        item = objects.setdefault(
            c.object,
            {"object": c.object, "entity": entity, "row_count": c.row_count, "candidates": []},
        )
        record_id = _evidence_id("key", entity, *(slug(f) for f in c.fields))
        item["candidates"].append(
            {"fields": list(c.fields), "status": "inferred", "evidence": [record_id]}
        )
        records.append(
            _record(
                record_id,
                snap,
                pin,
                day,
                meta,
                {
                    "row_count": c.row_count,
                    "non_null": c.non_null,
                    "null_count": c.row_count - c.non_null,
                    "distinct": c.distinct,
                },
                "fact propose keys: unique and never null on this data; a candidate, not a key",
            )
        )
    return {
        "proposal": "keys",
        "source": snap.source,
        "snapshot_pin": snap.pin,
        "proposed_on": day,
        "environment": meta["environment"],
        "data_quality": meta["data_quality"],
        "max_columns": max_columns,
        "queries": session.queries,
        "skipped": list(skipped) + [f"query failed: {q}" for q in session.failed],
        "objects": list(objects.values()),
        "records": records,
    }


def joins_document(
    snap: Snapshot,
    candidates: Sequence[JoinCandidate],
    skipped: Sequence[str],
    session: Session,
    pin: str,
    day: str,
    meta: Mapping[str, str],
    threshold: float,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for c in sorted(
        candidates, key=lambda c: (c.source, c.source_fields, c.target, c.target_fields)
    ):
        src, tgt = slug(c.source), slug(c.target)
        record_id = _evidence_id(
            "join",
            src,
            *(slug(f) for f in c.source_fields),
            tgt,
            *(slug(f) for f in c.target_fields),
        )
        join = " AND ".join(
            f"{src}.{a} = {tgt}.{b}" for a, b in zip(c.source_fields, c.target_fields, strict=True)
        )
        notes = "; ".join(
            name_note(a, b) for a, b in zip(c.source_fields, c.target_fields, strict=True)
        )
        items.append(
            {
                "from": src,
                "fields": list(c.source_fields),
                "to": tgt,
                "to_fields": list(c.target_fields),
                "join": join,
                "mechanism": "inferred_join",
                "cardinality": c.cardinality,
                "inclusion": c.inclusion,
                "status": "inferred",
                "note": notes,
                "evidence": [record_id],
            }
        )
        records.append(
            _record(
                record_id,
                snap,
                pin,
                day,
                meta,
                {
                    "source_distinct": c.source_distinct,
                    "included": c.included,
                    "inclusion": c.inclusion,
                    "target_distinct": c.target_distinct,
                    "coverage": c.coverage,
                },
                "fact propose joins: distinct non-null source values found in a unique "
                "target; a candidate, not a relationship",
            )
        )
    return {
        "proposal": "joins",
        "source": snap.source,
        "snapshot_pin": snap.pin,
        "proposed_on": day,
        "environment": meta["environment"],
        "data_quality": meta["data_quality"],
        "threshold": threshold,
        "queries": session.queries,
        "skipped": list(skipped) + [f"query failed: {q}" for q in session.failed],
        "candidates": items,
        "records": records,
    }


def keys_from_document(doc: Mapping[str, Any] | None) -> dict[str, list[list[str]]]:
    """The candidate key fields per object of a ``keys`` proposal document."""
    out: dict[str, list[list[str]]] = {}
    for item in (doc or {}).get("objects", []):
        out[str(item["object"])] = [list(c["fields"]) for c in item.get("candidates", [])]
    return out

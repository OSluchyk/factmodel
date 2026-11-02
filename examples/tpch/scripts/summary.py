"""Counts for the README of examples/tpch, read from the committed artifacts.

    python3 examples/tpch/scripts/summary.py examples/tpch 2026-11-02

Prints: constraints in snapshot A and B, key candidates on A (and whether each kit primary key
is among them), join candidates on A, how many of the kit's foreign keys they recover, which
candidates are the specification's two foreign keys the kit leaves out, and the rest, which a
reader must judge; plus the probe results on B.
"""

import json
import sys
from pathlib import Path

from ruamel.yaml import YAML

# The kit's constraints (scripts/apply-constraints.sql), by table and column.
KIT_PRIMARY = {
    "region": ("r_regionkey",),
    "nation": ("n_nationkey",),
    "supplier": ("s_suppkey",),
    "customer": ("c_custkey",),
    "part": ("p_partkey",),
    "partsupp": ("ps_partkey", "ps_suppkey"),
    "orders": ("o_orderkey",),
    "lineitem": ("l_orderkey", "l_linenumber"),
}
KIT_FOREIGN = {
    ("nation", ("n_regionkey",), "region", ("r_regionkey",)),
    ("supplier", ("s_nationkey",), "nation", ("n_nationkey",)),
    ("customer", ("c_nationkey",), "nation", ("n_nationkey",)),
    ("partsupp", ("ps_suppkey",), "supplier", ("s_suppkey",)),
    ("partsupp", ("ps_partkey",), "part", ("p_partkey",)),
    ("orders", ("o_custkey",), "customer", ("c_custkey",)),
    ("lineitem", ("l_orderkey",), "orders", ("o_orderkey",)),
    ("lineitem", ("l_partkey", "l_suppkey"), "partsupp", ("ps_partkey", "ps_suppkey")),
}
# Listed by the specification (clause 1.4.2.3) but not in dss.ri: implied through partsupp.
SPEC_ONLY = {
    ("lineitem", ("l_partkey",), "part", ("p_partkey",)),
    ("lineitem", ("l_suppkey",), "supplier", ("s_suppkey",)),
}


def _yaml(path: Path) -> dict:  # type: ignore[type-arg]
    return YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))


def constraints(snapshot: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for obj in _yaml(snapshot)["objects"]:
        for c in obj.get("constraints") or []:
            counts[c["constraint_type"]] = counts.get(c["constraint_type"], 0) + 1
    return counts


def main(root: Path, day: str) -> None:
    source = "tpch-duckdb"
    a = root / "sources" / "snapshots" / f"{source}@{day}.yaml"
    b = root / "sources" / "snapshots" / f"{source}@{day}_2.yaml"
    print(f"snapshot A ({a.name}): constraints {constraints(a) or 'none'}")
    print(f"snapshot B ({b.name}): constraints {constraints(b)}")

    keys = _yaml(root / "drafts" / source / "keys.yaml")
    found = {o["object"]: [tuple(c["fields"]) for c in o["candidates"]] for o in keys["objects"]}
    total = sum(len(v) for v in found.values())
    hits = [t for t, k in KIT_PRIMARY.items() if k in found.get(t, [])]
    print(f"keys on A: {total} candidates over {len(found)} tables, {keys['queries']} queries;")
    print(f"  the kit's primary key is among them for {len(hits)} of 8 tables")
    for table, cands in found.items():
        print(f"  {table}: " + ", ".join("(" + ", ".join(c) + ")" for c in cands))

    joins = _yaml(root / "drafts" / source / "joins.yaml")
    cands = {
        (c["from"], tuple(c["fields"]), c["to"], tuple(c["to_fields"])): c
        for c in joins["candidates"]
    }
    recovered = KIT_FOREIGN & set(cands)
    spec_only = SPEC_ONLY & set(cands)
    rest = sorted(set(cands) - KIT_FOREIGN - SPEC_ONLY)
    print(
        f"joins on A: {len(cands)} candidates at threshold {joins['threshold']}, "
        f"{joins['queries']} queries;"
    )
    print(f"  {len(recovered)} of the kit's 8 foreign keys recovered")
    print(f"  {len(spec_only)} of the specification's 2 foreign keys the kit leaves out")
    print(f"  {len(rest)} other inclusions above the threshold, for a reader to judge:")
    for key in rest:
        c = cands[key]
        print(f"    {c['join']}  ({c['cardinality']}, coverage {_coverage(joins, c)})")

    results = sorted((root / "probes" / "results").glob(f"{source}@*.jsonl"))
    if results:
        rows = [json.loads(line) for line in results[-1].read_text(encoding="utf-8").splitlines()]
        failed = sum(1 for r in rows[1:] if "error" in r)
        print(f"probes on B: {len(rows) - 1} run, {failed} failed ({results[-1].name})")


def _coverage(joins: dict, candidate: dict) -> float:  # type: ignore[type-arg]
    record = next(r for r in joins["records"] if r["id"] == candidate["evidence"][0])
    return float(record["measurement"]["coverage"])


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2])

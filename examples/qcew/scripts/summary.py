"""What fact propose found on the published rows, against what the model documents.

    python3 examples/qcew/scripts/summary.py examples/qcew

Reads drafts/qcew-duckdb-real/keys.yaml and joins.yaml and the physical entities. Prints the
key candidates per table and whether the documented key is among them, the named keys that
were measured (D-024), then the join candidates: the documented equality joins found, the
documented ones not found, the targets that are not unique, and the rest.
"""

import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

SOURCE = "qcew-duckdb-real"


def _yaml(path: Path) -> Any:
    return YAML(typ="safe", pure=True).load(path.read_text(encoding="utf-8"))


def main(root: Path) -> None:
    keys = _yaml(root / "drafts" / SOURCE / "keys.yaml")
    joins = _yaml(root / "drafts" / SOURCE / "joins.yaml")
    entities = {p.stem: _yaml(p) for p in sorted((root / "physical" / "entities").glob("*.yaml"))}
    found = {o["object"]: [tuple(c["fields"]) for c in o["candidates"]] for o in keys["objects"]}
    total = sum(len(v) for v in found.values())
    print(f"keys: {total} candidates over {len(entities)} tables, {keys['queries']} queries,")
    print(f"  single columns and pairs only (max_columns {keys['max_columns']})")
    for name, entity in entities.items():
        documented = tuple(entity["keys"]["primary"])
        candidates = found.get(name, [])
        shown = ", ".join("(" + ", ".join(c) + ")" for c in candidates) or "none"
        among = "among them" if documented in candidates else "not among them"
        print(f"  {name}: {shown}; documented ({', '.join(documented)}): {among}")
    for key in keys.get("named") or []:
        verdict = "unique" if key["unique"] else "not unique"
        print(
            f"  named key {key['object']} ({', '.join(key['fields'])}): {verdict}, "
            f"{key['duplicate_rows']} duplicate rows, {key['row_count']} rows"
        )
    documented_joins = {}
    for name, entity in entities.items():
        for rel in entity.get("relationships") or []:
            join = rel.get("join", "")
            if " AND " not in join and join.count("=") == 1 and "(" not in join:
                documented_joins[join] = f"{name}.{rel['key']}"
    proposed = {c["join"]: c for c in joins["candidates"]}
    print(f"joins: {len(proposed)} candidates at threshold {joins['threshold']}, ", end="")
    print(f"{joins['queries']} queries")
    hits = sorted(j for j in proposed if j in documented_joins)
    print(f"  {len(hits)} of the model's {len(documented_joins)} one-column equality joins found")
    for join in sorted(j for j in documented_joins if j not in proposed):
        print(f"  not proposed: {join}  ({documented_joins[join]})")
    for target in joins.get("targets_not_unique") or []:
        print(
            f"  target not unique: {target['object']}.{target['field']}, "
            f"{target['duplicate_rows']} duplicate rows of {target['non_null']}"
        )
    rest = sorted(j for j in proposed if j not in documented_joins)
    print(f"  {len(rest)} other inclusions above the threshold, for a reader to judge:")
    for join in rest:
        print(f"    {join}  ({proposed[join]['cardinality']})")


if __name__ == "__main__":
    main(Path(sys.argv[1]))

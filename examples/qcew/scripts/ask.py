"""Answer one corpus item through the layer's consumer, on the QCEW DuckDB file.

    uv run python examples/qcew/scripts/ask.py de-private-total-2025q1

Prints the item's request, the SQL the consumer measure-sql compiles from the request and the
layer employment-wages, the rows that SQL returns, and the rows of the item's reference SQL.
The database is the file FACT_DSN_QCEW_REAL names (duckdb:///<path>), or ``--db <path>``.
"""

import os
import sys
from pathlib import Path

import sqlglot

from factmodel.equivalence import harness
from factmodel.model.loader import load_model

HERE = Path(__file__).resolve().parents[1]
LAYER = "employment-wages"


def main(argv: list[str]) -> int:
    import duckdb

    db = None
    if "--db" in argv:
        at = argv.index("--db")
        db = argv[at + 1]
        argv = argv[:at] + argv[at + 2 :]
    if len(argv) != 1:
        print(__doc__)
        return 2
    if db is None:
        dsn = os.environ.get("FACT_DSN_QCEW_REAL", "")
        if not dsn.startswith("duckdb:///"):
            raise SystemExit("ask: set FACT_DSN_QCEW_REAL=duckdb:///<file> or pass --db <file>")
        db = dsn.removeprefix("duckdb:///")
    model = load_model(HERE)
    setup = harness.setup(HERE, model, LAYER)
    item = next((i for i in setup.items if i.id == argv[0]), None)
    if item is None:
        raise SystemExit(f"ask: no corpus item {argv[0]!r}")
    compile_request = harness.load_compile(HERE, setup.consumer)
    sql = sqlglot.transpile(compile_request(item.request, setup.layer), write="duckdb")[0]
    conn = duckdb.connect(db, read_only=True)
    try:
        answer = conn.execute(sql).fetchall()
        reference = conn.execute(sqlglot.transpile(item.reference, write="duckdb")[0]).fetchall()
    finally:
        conn.close()
    print("request:  ", ", ".join(f"{k} {v}" for k, v in item.request.items()))
    print("sql:      ", sql)
    print("answer:   ", sorted(answer, key=repr))
    print("reference:", sorted(reference, key=repr))
    print("same:     ", "yes" if sorted(answer, key=repr) == sorted(reference, key=repr) else "no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

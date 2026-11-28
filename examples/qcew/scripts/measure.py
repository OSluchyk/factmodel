"""Run the named measurement queries of this example on the QCEW DuckDB file.

    uv run python examples/qcew/scripts/measure.py <name> [<name> ...]
    uv run python examples/qcew/scripts/measure.py --list
    uv run python examples/qcew/scripts/measure.py --write

A query is the file measurements/<name>.sql: one SELECT, read-only, with an ORDER BY so its
output never depends on row order. The output is the column names, a rule, then one line per
row, columns padded to the same width. ``--write`` runs every query and writes each output to
measurements/<name>.txt, the files the README and the article support page quote.

The database is the file FACT_DSN_QCEW_REAL names (duckdb:///<path>), or ``--db <path>``. It
is attached read-only. When the BLS crosswalk spreadsheet is in sources/codelists/ (see
scripts/crosswalk.py), its 2024 to current sheet is there as the temporary table ``crosswalk``;
a query that reads it is skipped by ``--write`` when the file is missing.
"""

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[1]
QUERIES = HERE / "measurements"


def _cell(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".") if value % 1 else str(int(value))
    return str(value)


def table(columns: list[str], rows: list[tuple[Any, ...]]) -> str:
    """Columns padded to one width; numbers to the right, text to the left."""
    cells = [[_cell(v) for v in row] for row in rows]
    widths = [max([len(c), *(len(r[i]) for r in cells)]) for i, c in enumerate(columns)]
    numeric = [
        bool(rows) and all(isinstance(r[i], int | float) or r[i] is None for r in rows)
        for i in range(len(columns))
    ]

    def line(items: list[str]) -> str:
        cells = zip(items, widths, numeric, strict=True)
        parts = [v.rjust(w) if n else v.ljust(w) for v, w, n in cells]
        return " | ".join(parts).rstrip()

    rule = "-+-".join("-" * w for w in widths)
    return "\n".join([line(columns), rule, *(line(r) for r in cells)]) + "\n"


def connect(db: str) -> Any:
    """The database attached read-only, with the crosswalk as a temporary table when its
    spreadsheet is there."""
    import duckdb

    conn = duckdb.connect()
    conn.execute(f"ATTACH '{db}' AS qcew (READ_ONLY)")
    conn.execute("USE qcew")
    spec = importlib.util.spec_from_file_location("crosswalk", HERE / "scripts" / "crosswalk.py")
    assert spec and spec.loader
    crosswalk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crosswalk)
    if crosswalk.FILE.is_file():
        columns = ", ".join(f"{c} VARCHAR" for c in crosswalk.COLUMNS)
        conn.execute(f"CREATE TEMP TABLE crosswalk ({columns})")
        _, rows = crosswalk.sheet_name_and_rows()
        conn.executemany("INSERT INTO crosswalk VALUES (?, ?, ?, ?, ?, ?)", rows)
    return conn


def needs_crosswalk(name: str) -> bool:
    return "FROM crosswalk" in (QUERIES / f"{name}.sql").read_text(encoding="utf-8")


def run(conn: Any, name: str) -> str:
    path = QUERIES / f"{name}.sql"
    if not path.is_file():
        raise SystemExit(f"measure: no query {name!r}; --list names them")
    cursor = conn.execute(path.read_text(encoding="utf-8"))
    return table([d[0] for d in cursor.description], cursor.fetchall())


def names() -> list[str]:
    return sorted(p.stem for p in QUERIES.glob("*.sql"))


def main(argv: list[str]) -> int:
    db = None
    if "--db" in argv:
        at = argv.index("--db")
        db = argv[at + 1]
        argv = argv[:at] + argv[at + 2 :]
    if argv == ["--list"]:
        print("\n".join(names()))
        return 0
    if not argv:
        print(__doc__)
        return 2
    if db is None:
        dsn = os.environ.get("FACT_DSN_QCEW_REAL", "")
        if not dsn.startswith("duckdb:///"):
            raise SystemExit("measure: set FACT_DSN_QCEW_REAL=duckdb:///<file> or pass --db <file>")
        db = dsn.removeprefix("duckdb:///")
    conn = connect(db)
    has_crosswalk = bool(
        conn.execute("SELECT 1 FROM duckdb_tables() WHERE table_name = 'crosswalk'").fetchall()
    )
    try:
        if argv == ["--write"]:
            for name in names():
                if needs_crosswalk(name) and not has_crosswalk:
                    print(f"skipped measurements/{name}.txt: the crosswalk spreadsheet is missing")
                    continue
                (QUERIES / f"{name}.txt").write_text(run(conn, name), encoding="utf-8")
                print(f"wrote measurements/{name}.txt")
            return 0
        for name in argv:
            sys.stdout.write(run(conn, name))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

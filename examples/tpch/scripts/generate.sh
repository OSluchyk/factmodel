#!/usr/bin/env bash
# Build tpch.duckdb with DuckDB's tpch extension (CALL dbgen), the way the article does it.
#
#   uv run examples/tpch/scripts/generate.sh [SF] [OUT]
#     SF   scale factor, default 1 (about 6 million lineitem rows)
#     OUT  the DuckDB file, default examples/tpch/tpch.duckdb
#
# Fallback when the extension cannot be installed (no route to extensions.duckdb.org): run the
# reference kit, `dbgen -s SF`, and load its .tbl files into the same tables:
#
#   uv run examples/tpch/scripts/generate.sh SF OUT --from-tbl <folder with the .tbl files>
#
# scripts/schema.sql holds the extension's own table definitions, so a database loaded this way
# snapshots exactly like one the extension built. Neither path creates a primary or foreign key.
#
# With the extension file at hand but no route to install it, FACT_TPCH_EXTENSION=<path to
# tpch.duckdb_extension> loads that file instead (DuckDB still checks its signature).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SF="${1:-1}"
OUT="${2:-$HERE/../tpch.duckdb}"
TBL=""
if [ "${3:-}" = "--from-tbl" ]; then
  TBL="${4:?a folder with region.tbl ... lineitem.tbl}"
fi
rm -f "$OUT" "$OUT.wal"
python3 - "$SF" "$OUT" "$TBL" "$HERE/schema.sql" "${FACT_TPCH_EXTENSION:-}" <<'PY'
import sys
import time

import duckdb

sf, out, tbl, schema, extension = float(sys.argv[1]), sys.argv[2], *sys.argv[3:6]
TABLES = ("region", "nation", "supplier", "customer", "part", "partsupp", "orders", "lineitem")
start = time.perf_counter()
conn = duckdb.connect(out)
if tbl:
    conn.execute(open(schema, encoding="utf-8").read())
    for table in TABLES:
        path = f"{tbl}/{table}.tbl"
        width = conn.execute(
            "SELECT count(*) FROM duckdb_columns() WHERE table_name = ?", [table]
        ).fetchone()[0]
        with open(path, encoding="utf-8") as handle:
            trailing = handle.readline().rstrip("\n").endswith("|")
        # dbgen ends every line with a delimiter, which reads as one empty extra column
        drop = f" EXCLUDE (column{width:02d})" if trailing else ""
        conn.execute(
            f"INSERT INTO {table} SELECT *{drop} "
            f"FROM read_csv('{path}', delim='|', header=false)"
        )
else:
    try:
        if extension:
            conn.execute("LOAD ?", [extension])
        else:
            conn.execute("INSTALL tpch; LOAD tpch;")
    except duckdb.Error as error:
        sys.exit(f"cannot load the tpch extension: {error}\nsee the fallback in this script")
    conn.execute(f"CALL dbgen(sf={sf})")
for table in TABLES:
    count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"{table:9} {count:>10,}")
conn.close()
print(f"{out}: scale factor {sf:g}, {time.perf_counter() - start:.1f} s")
PY

#!/usr/bin/env bash
# Build qcew.duckdb from the slices scripts/fetch.sh downloaded and the committed code lists.
#
#   uv run examples/qcew/scripts/load.sh [OUT]
#     OUT  the DuckDB file, default examples/qcew/qcew.duckdb (gitignored)
#
# It creates the tables of sources/ddl/duckdb.sql, the same definitions the seeded DuckDB
# file gets, then runs scripts/load.sql. FACT_QCEW_RAW names another folder of slices
# (default examples/qcew/data/raw). Needs the extra [duckdb].
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="${1:-${FACT_QCEW_DB:-$ROOT/qcew.duckdb}}"
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac
RAW="${FACT_QCEW_RAW:-$ROOT/data/raw}"
if ! ls "$RAW"/*/a/*.csv >/dev/null 2>&1; then
  echo "load: no slices under $RAW; run scripts/fetch.sh first" >&2
  exit 1
fi
rm -f "$OUT" "$OUT.wal"
cd "$ROOT"
python3 - "$OUT" "$RAW" <<'PY'
import sys
import time

import duckdb

out, raw = sys.argv[1:3]
TABLES = (
    "annual",
    "qtrly",
    "agglevel_titles",
    "area_titles",
    "industry_titles",
    "ownership_titles",
    "size_titles",
)
start = time.perf_counter()
conn = duckdb.connect(out)
conn.execute(open("sources/ddl/duckdb.sql", encoding="utf-8").read())
conn.execute("SET VARIABLE raw = ?", [raw])
conn.execute(open("scripts/load.sql", encoding="utf-8").read())
for table in TABLES:
    count = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    print(f"{table:16} {count:>9,}")
conn.close()
print(f"load: {time.perf_counter() - start:.1f} s")
PY

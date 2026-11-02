#!/usr/bin/env bash
# Rebuild every committed artifact of examples/tpch from scratch: the walk Part 2 describes.
#
#   uv run examples/tpch/scripts/reproduce.sh [SF]      (from the framework root; SF default 1)
#
# Steps: build tpch.duckdb -> snapshot A (no keys) -> propose keys and joins on A -> draft and
# accept the entities -> gate -> apply the kit's constraints -> snapshot B -> sync (the drift)
# -> draft and accept again -> probes on B -> intake -> gate. Both snapshots are read on one
# day: A is <source>@<day>.yaml, B the day's second read, <source>@<day>_2.yaml.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT/../.."
SF="${1:-1}"
DAY="${FACT_TPCH_DAY:-2026-11-02}"
DB="$ROOT/tpch.duckdb"
export FACT_DSN_TPCH_DUCKDB="duckdb:///$DB"
M=examples/tpch
S=tpch-duckdb
run() { echo; echo "\$ $*"; "$@"; }

rm -rf "$M/drafts/$S" "$M/probes/results" "$M/evidence/probes" "$M/generated/drift-$S.md"
rm -f "$M"/physical/entities/*.yaml "$M"/probes/*.yaml "$M"/sources/snapshots/*.yaml
started=$(date +%s)

run "$HERE/generate.sh" "$SF" "$DB"
run fact snapshot --root $M --source $S --date "$DAY"
run fact propose keys --root $M --source $S --environment local --data-quality synthetic --date "$DAY"
run fact propose joins --root $M --source $S --environment local --data-quality synthetic --date "$DAY"
run fact draft --root $M --source $S
run cp "$M"/drafts/$S/entities/*.yaml "$M"/physical/entities/
run fact project --root $M
run fact check --root $M

echo; echo "\$ apply-constraints.sql"
python3 - "$DB" "$HERE/apply-constraints.sql" <<'PY'
import sys
import duckdb
conn = duckdb.connect(sys.argv[1])
conn.execute(open(sys.argv[2], encoding="utf-8").read())
print(conn.execute("SELECT constraint_type, count(*) FROM duckdb_constraints() GROUP BY 1 ORDER BY 1").fetchall())
conn.close()
PY

run fact snapshot --root $M --source $S --date "$DAY"
run fact sync --root $M --source $S
run fact draft --root $M --source $S
run cp "$M"/drafts/$S/entities/*.yaml "$M"/physical/entities/
run fact project --root $M
run fact probe generate --root $M --source $S
run fact probe run --root $M --source $S --environment local --data-quality synthetic --date "$DAY"
run fact probe intake --root $M "$M/probes/results/$S@$DAY.jsonl"
run fact project --root $M
run fact check --root $M

echo; echo "reproduce: scale factor $SF, $(( $(date +%s) - started )) s in all"
run python3 "$HERE/summary.py" "$M" "$DAY"

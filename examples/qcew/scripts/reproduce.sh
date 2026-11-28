#!/usr/bin/env bash
# Rebuild what this example holds about the published rows, from the fetched slices.
#
#   bash examples/qcew/scripts/fetch.sh                  (once; about 93 MB from BLS)
#   uv run examples/qcew/scripts/reproduce.sh            (from the framework root)
#
# Steps: load qcew.duckdb -> check the load against the slices -> snapshot -> propose keys and joins -> generate and run the probes
# -> intake -> gate -> the corpus on the published rows -> the measurement queries. Every
# command is one the tutorial and the article support page show. The run is repeatable: on
# the same slices it rewrites every file with the same bytes.
#
# The layer's accepted equivalence run is the one CI reproduces on the seeded SQLite file, so
# the run on the published rows is kept beside it, as equivalence/qcew-duckdb-real@<day>.md
# and .json, and the seeded run is written again at the end.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT/../.."
DAY="${FACT_QCEW_DAY:-2026-11-28}"
SEEDED_DAY="${FACT_QCEW_SEEDED_DAY:-2026-11-22}"
DB="${FACT_QCEW_DB:-examples/qcew/qcew.duckdb}"
case "$DB" in /*) ;; *) DB="$PWD/$DB" ;; esac
export FACT_DSN_QCEW_REAL="duckdb:///$DB"
M=examples/qcew
S=qcew-duckdb-real
L=employment-wages
run() { echo; echo "\$ $*"; "$@"; }
started=$(date +%s)

run $M/scripts/load.sh
run python3 $M/scripts/check_load.py
run fact snapshot --root $M --source $S --date "$DAY"
KEY=area_fips,own_code,industry_code,size_code,year,qtr
run fact propose keys --root $M --source $S --environment local --data-quality representative --date "$DAY" --key annual:$KEY --key qtrly:$KEY
run fact propose joins --root $M --source $S --environment local --data-quality representative --date "$DAY"
run python3 $M/scripts/summary.py $M
run fact probe generate --root $M
run fact probe run --root $M --source $S --environment local --data-quality representative --date "$DAY"
run fact probe intake --root $M "$M/probes/results/$S@$DAY.jsonl"
run fact project --root $M
run fact check --root $M
run fact equivalence run --root $M --layer $L --date "$DAY"
run cp "$M/generated/equivalence-$L.md" "$M/equivalence/$S@$DAY.md"
run cp "$M/equivalence/last-run.json" "$M/equivalence/$S@$DAY.json"
run python3 $M/scripts/measure.py --write
run python3 $M/scripts/measurement_evidence.py

# the accepted run, on the seeded fixture, as CI reproduces it
SEEDED="$(mktemp -d)/qcew.db"
python3 "$M/seed/seed.py" sqlite "$SEEDED" > /dev/null
export FACT_DSN_QCEW_SQLITE="sqlite:///$SEEDED"
run fact equivalence run --root $M --layer $L --source qcew-sqlite --date "$SEEDED_DAY"

echo; echo "reproduce: $(( $(date +%s) - started )) s in all"

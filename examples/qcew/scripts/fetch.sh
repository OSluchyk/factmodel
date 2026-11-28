#!/usr/bin/env bash
# Download the BLS QCEW open data area slices this example is built on.
#
#   bash examples/qcew/scripts/fetch.sh            (from anywhere; about 510 requests)
#   bash examples/qcew/scripts/fetch.sh --resume   (keep files already there, fetch the rest)
#
# What it reads: one CSV per area and period from the QCEW open data access,
#   https://data.bls.gov/cew/data/api/<year>/<period>/area/<area>.csv
# where <period> is 1 to 4 for a quarter and "a" for the annual averages. The areas are the
# lines of scripts/areas.tsv: the U.S. total, Delaware and Maryland, every county code of the
# two states, and the metropolitan and micropolitan areas that include one of their counties.
# Nothing is filtered: every row BLS publishes for an area is kept.
#
# What it writes, all under examples/qcew/data/raw/ (gitignored, never committed):
#   <year>/<period>/<area>.csv   the slice, byte for byte as BLS served it
#   MANIFEST.tsv                 one line per request: url, file, http status, bytes, sha256,
#                                time read (UTC). A 404 is kept as a line: not published.
#
# Then it compares the files with scripts/checksums.sha256, the checksums of the read the
# committed model was built from, and says which files are the same, changed, new or missing.
# BLS revises open quarters, so a changed file is information, not an error.
#
# Environment:
#   FACT_QCEW_YEARS    years to read, default "2024 2025"
#   FACT_QCEW_CONTACT  an e-mail address for the User-Agent, so BLS can reach whoever runs this
#   FACT_QCEW_PAUSE    seconds between requests, default 0.2
#   FACT_QCEW_BASE     base URL, default https://data.bls.gov/cew/data/api (tests point it
#                      at a local folder server)
#
# Needs bash, curl and shasum or sha256sum. Source: U.S. Bureau of Labor Statistics, Quarterly
# Census of Employment and Wages.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
RAW="${FACT_QCEW_RAW:-$ROOT/data/raw}"
BASE="${FACT_QCEW_BASE:-https://data.bls.gov/cew/data/api}"
YEARS="${FACT_QCEW_YEARS:-2024 2025}"
PAUSE="${FACT_QCEW_PAUSE:-0.2}"
AGENT="factmodel-qcew-example (+https://github.com/OSluchyk/factmodel; contact: ${FACT_QCEW_CONTACT:-not given})"
RESUME=0
if [ "${1:-}" = "--resume" ]; then RESUME=1; fi
TAB="$(printf '\t')"

if command -v sha256sum >/dev/null 2>&1; then
  sha() { sha256sum "$1" | cut -d' ' -f1; }
else
  sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
fi

mkdir -p "$RAW"
MANIFEST="$RAW/MANIFEST.tsv"
OLD="$RAW/MANIFEST.old"
if [ "$RESUME" = 1 ] && [ -f "$MANIFEST" ]; then cp "$MANIFEST" "$OLD"; else : > "$OLD"; fi
printf 'url\tfile\tstatus\tbytes\tsha256\tread_utc\n' > "$MANIFEST"

started=$(date +%s)
requests=0; got=0; absent=0; kept=0; bytes_all=0
for year in $YEARS; do
  for period in a 1 2 3 4; do
    mkdir -p "$RAW/$year/$period"
    while IFS="$TAB" read -r area group title; do
      case "$area" in ''|'#'*) continue ;; esac
      url="$BASE/$year/$period/area/$area.csv"
      file="$year/$period/$area.csv"
      if [ "$RESUME" = 1 ]; then
        line="$(grep -F "$url$TAB$file$TAB" "$OLD" || true)"
        status="$(printf '%s' "$line" | cut -f3)"
        if { [ -n "$status" ] && [ "$status" != 200 ]; } || { [ "$status" = 200 ] && [ -s "$RAW/$file" ]; }; then
          printf '%s\n' "$line" >> "$MANIFEST"
          kept=$((kept + 1))
          continue
        fi
      fi
      requests=$((requests + 1))
      tmp="$RAW/$file.part"
      status="$(curl -sS -L -A "$AGENT" -o "$tmp" -w '%{http_code}' --retry 3 --retry-delay 2 \
        --max-time 120 "$url" || true)"
      now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      if [ "$status" = 200 ] && head -c 11 "$tmp" | grep -q '"area_fips"'; then
        mv "$tmp" "$RAW/$file"
        size="$(wc -c < "$RAW/$file" | tr -d ' ')"
        printf '%s\t%s\t200\t%s\t%s\t%s\n' "$url" "$file" "$size" "$(sha "$RAW/$file")" "$now" >> "$MANIFEST"
        got=$((got + 1)); bytes_all=$((bytes_all + size))
      else
        case "$status" in
          000|403|429|5??)
            rm -f "$tmp"
            echo "fetch: $url answered $status." >&2
            echo "fetch: BLS may be refusing automated requests from this network. Wait and run" >&2
            echo "fetch: again with --resume, set FACT_QCEW_CONTACT to your e-mail address, or" >&2
            echo "fetch: download the file in a browser and save it as data/raw/$file." >&2
            exit 1 ;;
        esac
        # 404, or an answer that is not a slice: BLS publishes nothing for this area and period
        [ "$status" = 200 ] && status=200-not-a-slice
        rm -f "$tmp" "$RAW/$file"
        printf '%s\t%s\t%s\t0\t-\t%s\n' "$url" "$file" "$status" "$now" >> "$MANIFEST"
        absent=$((absent + 1))
      fi
      sleep "$PAUSE"
    done < "$HERE/areas.tsv"
  done
done
rm -f "$OLD"

echo "fetch: $requests requests, $got slices ($bytes_all bytes), $absent not published, $kept kept from the last run, $(( $(date +%s) - started )) s"
echo "fetch: wrote ${MANIFEST#"$ROOT/"} (in examples/qcew unless FACT_QCEW_RAW is set)"

SUMS="$HERE/checksums.sha256"
if [ -f "$SUMS" ]; then
  same=0; changed=0; new=0; missing=0
  while IFS="$TAB" read -r url file status size sum now; do
    [ "$status" = 200 ] || continue
    want="$(grep -F "  data/raw/$file" "$SUMS" | cut -d' ' -f1 || true)"
    if [ -z "$want" ]; then new=$((new + 1)); echo "fetch: new, not in checksums.sha256: $file"
    elif [ "$want" = "$sum" ]; then same=$((same + 1))
    else changed=$((changed + 1)); echo "fetch: changed since the committed read: $file"
    fi
  done < "$MANIFEST"
  while read -r want path; do
    [ -f "$RAW/${path#data/raw/}" ] || { missing=$((missing + 1)); echo "fetch: in checksums.sha256, not fetched: $path"; }
  done < "$SUMS"
  echo "fetch: against checksums.sha256: $same same, $changed changed, $new new, $missing missing"
  if [ $((changed + new + missing)) -gt 0 ]; then
    echo "fetch: the counts in this example's documents hold for the committed read only."
  fi
else
  echo "fetch: no scripts/checksums.sha256 to compare with"
fi

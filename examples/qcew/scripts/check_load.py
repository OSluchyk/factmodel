"""Check the load against the raw slices: rows, withheld (N) rows and padding (-) rows.

    uv run python examples/qcew/scripts/check_load.py     (writes measurements/load-check.txt)

Counts every slice under data/raw with the csv module, not with the loader, and the loaded
tables with SQL, per table, year and group of areas (DE and MD by the first two characters of
the area code, the rest as "other": the U.S. total and the metropolitan and micropolitan
areas). A line ends in "equal" when the three pairs of counts agree. Needs the fetched slices.
"""

import csv
import importlib.util
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
GROUPS = {"10": "DE", "24": "MD"}


def main() -> int:
    spec = importlib.util.spec_from_file_location("measure", HERE / "scripts" / "measure.py")
    assert spec and spec.loader
    measure = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(measure)
    raw: Counter[tuple[str, str, str, str]] = Counter()
    for path in sorted((HERE / "data" / "raw").glob("*/*/*.csv")):
        table = "annual" if path.parent.name == "a" else "qtrly"
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                key = (table, row["year"], GROUPS.get(row["area_fips"][:2], "other"))
                raw[(*key, "rows")] += 1
                if row["disclosure_code"] in ("N", "-"):
                    raw[(*key, row["disclosure_code"])] += 1
    dsn = os.environ.get("FACT_DSN_QCEW_REAL", "")
    conn = measure.connect(dsn.removeprefix("duckdb:///"))
    loaded: Counter[tuple[str, str, str, str]] = Counter()
    for table in ("annual", "qtrly"):
        query = (
            "SELECT year, CASE substr(area_fips, 1, 2) WHEN '10' THEN 'DE' WHEN '24' THEN 'MD' "
            "ELSE 'other' END, count(*), sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END), "
            f"sum(CASE WHEN disclosure_code = '-' THEN 1 ELSE 0 END) FROM {table} GROUP BY 1, 2"
        )
        for year, group, rows, withheld, padding in conn.execute(query).fetchall():
            loaded[(table, year, group, "rows")] = rows
            loaded[(table, year, group, "N")] = withheld
            loaded[(table, year, group, "-")] = padding
    conn.close()
    columns = ["source_table", "year", "areas", "raw_rows", "loaded_rows", "raw_n", "loaded_n"]
    columns += ["raw_dash", "loaded_dash", "verdict"]
    out = []
    for table, year, group in sorted({k[:3] for k in raw} | {k[:3] for k in loaded}):
        pairs = [
            (raw[(table, year, group, m)], loaded[(table, year, group, m)])
            for m in ("rows", "N", "-")
        ]
        verdict = "equal" if all(a == b for a, b in pairs) else "DIFFERENT"
        out.append((table, year, group, *(v for pair in pairs for v in pair), verdict))
    text = measure.table(columns, out)
    (HERE / "measurements" / "load-check.txt").write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0 if all(row[-1] == "equal" for row in out) else 1


if __name__ == "__main__":
    raise SystemExit(main())

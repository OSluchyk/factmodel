"""Write sources/SOURCES.md and scripts/checksums.sha256 from the manifest of a fetch.

    python3 examples/qcew/scripts/sources_md.py

Reads data/raw/MANIFEST.tsv, which scripts/fetch.sh wrote. Run it only when the model is
rebuilt on a new read: the two files it writes describe the read the committed model is
built from.
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
HEAD = """# Data sources

The published rows this example is built on: BLS QCEW open data area slices, one CSV per area
and period, read by `scripts/fetch.sh`. The files are not in the repository; this page lists
every URL with the time it was read and the SHA-256 of what BLS served. `scripts/fetch.sh`
compares a new read with `scripts/checksums.sha256`. The code lists have their own page,
[codelists/SOURCES.md](codelists/SOURCES.md).

Citation required by BLS: "Source: U.S. Bureau of Labor Statistics, Quarterly Census of
Employment and Wages." Terms: https://www.bls.gov/opub/copyright-information.htm (read
2026-10-23). BLS publications are in the public domain.

## Which years

Read on 2026-11-28. The BLS release calendar
(https://www.bls.gov/cew/release-calendar.htm) dates the fourth quarter of 2025, with the
preliminary 2025 annual averages, to 2026-06-02, and the first quarter of 2026, with the
final 2025 data, to 2026-08-28. So 2024 and 2025 are both complete: four quarters and the
annual averages. The slice layout is the one of
https://www.bls.gov/cew/additional-resources/open-data/csv-data-slices.htm.

## Which areas

The lines of `scripts/areas.tsv`: the U.S. total, Delaware and Maryland, every code of the
area list under the two state prefixes, and the metropolitan and micropolitan areas whose
title names one of the two states. The county to area membership was checked against the BLS
County-MSA-CSA crosswalk, https://www.bls.gov/cew/classifications/areas/county-msa-csa-crosswalk.htm
(table "2024 - Current", read 2026-11-28).

## The read

{summary}

## Not published

BLS answered 404 for these areas in every one of the {periods} periods: the code is in the
area list, and no slice exists for 2024 or 2025.

| Area | Title | Requests answered 404 |
| --- | --- | --- |
{absent}

## Slices

| URL | Read (UTC) | Bytes | SHA-256 |
| --- | --- | --- | --- |
{rows}
"""


def main() -> None:
    manifest = HERE / "data" / "raw" / "MANIFEST.tsv"
    with manifest.open(encoding="utf-8", newline="") as handle:
        lines = list(csv.DictReader(handle, delimiter="\t"))
    titles = {}
    for line in (HERE / "scripts" / "areas.tsv").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            code, _, title = line.split("\t")
            titles[code] = title
    got = [r for r in lines if r["status"] == "200"]
    missing = [r for r in lines if r["status"] != "200"]
    reads = sorted(r["read_utc"] for r in lines)
    periods = len({r["file"].rsplit("/", 1)[0] for r in lines})
    areas = {r["file"].rsplit("/", 1)[1][:-4] for r in got}
    summary = (
        f"{len(lines)} requests between {reads[0]} and {reads[-1]}: {len(got)} slices, "
        f"{sum(int(r['bytes']) for r in got):,} bytes, for {len(areas)} areas and {periods} "
        f"periods; {len(missing)} requests answered 404."
    )
    by_area: dict[str, int] = {}
    for r in missing:
        code = r["file"].rsplit("/", 1)[1][:-4]
        by_area[code] = by_area.get(code, 0) + 1
    absent = "\n".join(f"| `{a}` | {titles[a]} | {n} |" for a, n in sorted(by_area.items()))
    rows = "\n".join(
        f"| {r['url']} | {r['read_utc']} | {int(r['bytes']):,} | `{r['sha256']}` |" for r in got
    )
    text = HEAD.format(summary=summary, periods=periods, absent=absent, rows=rows)
    (HERE / "sources" / "SOURCES.md").write_text(text, encoding="utf-8")
    sums = "".join(f"{r['sha256']}  data/raw/{r['file']}\n" for r in got)
    (HERE / "scripts" / "checksums.sha256").write_text(sums, encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()

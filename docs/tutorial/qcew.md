# Tutorial: QCEW on the published rows

This tutorial takes the QCEW example from nothing on disk to a checked model and one answered question, on the rows BLS publishes. It needs a clone of the repository, [uv](https://docs.astral.sh/uv/), `bash`, `curl` and a route to `data.bls.gov`. The outputs below are from the read and the run of 2026-11-28; `examples/qcew/sources/SOURCES.md` lists what was read.

Measured: the download is 440 files, 92,691,103 bytes, and took 252 seconds from the first request to the last. Everything after it took 57 seconds on 4 cores. That is about five minutes in all.

Run the blocks in one shell session, in order, from the root of the clone.

## 1. Fetch

```bash
uv sync
source .venv/bin/activate
bash examples/qcew/scripts/fetch.sh
```

The script reads one CSV per area and period from the BLS open data access: 51 area codes, 2024 and 2025, the annual averages and four quarters. It keeps every row. A 404 is not an error: BLS publishes nothing for seven of the codes. The files go to `examples/qcew/data/raw/`, which git ignores. At the end the script compares what it read with the checksums of the read this model was built from. BLS revises open quarters, so a later read can differ; the counts on this page hold for the committed read.

Run again on a folder that already holds the read, with `--resume`, it prints:

Output:

```text
fetch: 0 requests, 0 slices (0 bytes), 0 not published, 510 kept from the last run, 1 s
fetch: wrote data/raw/MANIFEST.tsv (in examples/qcew unless FACT_QCEW_RAW is set)
fetch: against checksums.sha256: 440 same, 0 changed, 0 new, 0 missing
```

## 2. Load

```bash
uv run examples/qcew/scripts/load.sh
export FACT_DSN_QCEW_REAL="duckdb:///$PWD/examples/qcew/qcew.duckdb"
```

`load.sh` creates the tables of `sources/ddl/duckdb.sql` in `examples/qcew/qcew.duckdb` and runs `scripts/load.sql`, which reads every slice and the five committed title files. Nothing is filtered or cleaned.

Output:

```text
annual             110,366
qtrly              486,100
agglevel_titles         56
area_titles          9,458
industry_titles      2,678
ownership_titles         8
size_titles             10
load: 1.7 s
```

## 3. Snapshot

```bash
fact snapshot --root examples/qcew --source qcew-duckdb-real --date 2026-11-28
```

The snapshot is the catalog of the database: seven tables, their columns and types, and not one key, because nothing declares one.

Output:

```text
unchanged sources/snapshots/qcew-duckdb-real@2026-11-28.yaml (7 objects)
```

It says `unchanged` because the committed snapshot is this one. On a model without it the line starts with `wrote`.

## 4. Probe

```bash
fact probe run --root examples/qcew --source qcew-duckdb-real --environment local --data-quality representative --date 2026-11-28
fact probe intake --root examples/qcew examples/qcew/probes/results/qcew-duckdb-real@2026-11-28.jsonl
```

A probe is a count the model predicts: no duplicate of a key, no row without its title, a rollup that adds up. `--data-quality representative` says the rows are real, so a result in range confirms the fact it tests (D-014).

Output:

```text
49 probes run, 0 failed: probes/results/qcew-duckdb-real@2026-11-28.jsonl
47 in range, 2 out of range, 0 failed, 0 rejected; 0 files written
```

The two results out of range are not failures of the run. Each is a finding in `examples/qcew/registers/findings/`: the area list repeats its codes (F-0001) and `disclosure_code` holds an undocumented `-` (F-0002). One probe is in range at a bound that is not zero: 53 industry codes have no parent code, the list is built that way, and the relationship says so with its reason (D-025, F-0008).

## 5. Check

```bash
fact check --root examples/qcew
```

Output:

```text
gate: pass
```

## 6. Ask one question

```bash
uv run python examples/qcew/scripts/ask.py de-private-total-2025q1
```

The corpus item asks for private employment in Delaware in March 2025. The consumer compiles the request with the layer: it looks up the aggregation level, adds the disclosure filter and counts withheld cells beside the value.

Output:

```text
request:   measure employment_month3, area 10000, industry 10, ownership 5, year 2025, qtr 1
sql:       SELECT (SELECT SUM(qtrly.month3_emplvl) FROM qtrly WHERE qtrly.area_fips = '10000' AND qtrly.industry_code = '10' AND qtrly.own_code = '5' AND qtrly.year = '2025' AND qtrly.qtr = '1' AND qtrly.agglvl_code = '51' AND qtrly.disclosure_code IS NULL) AS value, (SELECT SUM(CASE WHEN qtrly.disclosure_code = 'N' THEN 1 ELSE 0 END) FROM qtrly WHERE qtrly.area_fips = '10000' AND qtrly.industry_code = '10' AND qtrly.own_code = '5' AND qtrly.year = '2025' AND qtrly.qtr = '1' AND qtrly.agglvl_code = '51') AS suppressed_cells
answer:    [(405199, 0)]
reference: [(405199, 0)]
same:      yes
```

The row it reads is the one BLS publishes: slice `2025/1/area/10000.csv`, `own_code` 5, `industry_code` 10, `agglvl_code` 51. Without the level filter the same question returns 2,999,697, because the slice states the same workers at eight levels:

```bash
uv run python examples/qcew/scripts/measure.py grain-mixed-level
```

Output:

```text
level_filter     | row_count | employment
-----------------+-----------+-----------
agglvl_code = 51 |         1 |     405199
none             |      1732 |    2999697
```

## Where to go next

- `uv run examples/qcew/scripts/reproduce.sh` runs steps 2 to 5, the proposals, the whole corpus and every measurement in one go.
- [The example's README](https://github.com/OSluchyk/factmodel/tree/main/examples/qcew) has the findings with their numbers on these rows.
- `examples/qcew/measurements/` holds the queries behind those numbers; `uv run python examples/qcew/scripts/measure.py --list` names them.

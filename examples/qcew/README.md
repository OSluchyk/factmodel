# QCEW example

A FactModel model of the BLS Quarterly Census of Employment and Wages (QCEW) with NAICS, the second example domain. It is built on the rows BLS publishes: the open data slices of Delaware, Maryland, their counties, the metropolitan and micropolitan areas around them and the U.S. total, for 2024 and 2025. Its shape is the one Chinook does not have: a row is an aggregate over (area, ownership, industry, size, year, quarter), so there is no subject and no anchor (D-015); its hierarchies are code prefixes, not equal fields (D-017); and its code lists are the real BLS files, committed unchanged (D-016).

Source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages. BLS publications are in the public domain (https://www.bls.gov/opub/copyright-information.htm, read 2026-10-23).

## What is here

| Path | What |
| --- | --- |
| `factmodel.yaml` | Profile `statistics`, no `anchor_entity` (D-015). Only results on the published rows confirm a fact (D-014); results on the seeded fixtures are kept as `inferred` evidence. |
| `sources/` | `qcew-duckdb-real` (adapter `sql`), the DuckDB file built from the published slices and the source every entity is bound to; `qcew-sqlite`, `qcew-pg` and `qcew-duckdb`, the seeded test fixtures; `qcew-ddl` (adapter `git`); and six documents: the BLS annual and quarterly layouts, the BLS title files, the BLS County-MSA-CSA crosswalk, BLS notice and method pages, and `profile.md` of the QCEW profiling notes (`qcew-model`). |
| `sources/SOURCES.md` | Every slice URL with the time it was read and its checksum, the areas BLS does not publish, and how the years were chosen. |
| `sources/codelists/` | The five BLS title files and the BLS County-MSA-CSA crosswalk spreadsheet, unchanged, with their own `SOURCES.md` (URL, read date, citation, checksum). |
| `sources/ddl/` | `annual`, `qtrly` and the five title tables for SQLite, PostgreSQL and DuckDB, after the `load.sh` layouts of the QCEW profiling notes (qcew-model). The published slices have the same columns. |
| `scripts/fetch.sh`, `areas.tsv`, `checksums.sha256` | Downloads the 440 slices (51 area codes, 2 years, the annual file and four quarters; 7 codes have no slice) and compares them with the checksums of the committed read. |
| `scripts/load.sh`, `load.sql` | Build `qcew.duckdb` from the slices and the code lists. The database and the slices are gitignored. |
| `scripts/reproduce.sh`, `check_load.py`, `summary.py`, `measure.py`, `measurement_evidence.py`, `ask.py`, `crosswalk.py`, `sources_md.py` | One run from the slices to every artifact below; the raw slices counted against the loaded tables; what `fact propose` found against what the model documents; the measurement queries and their evidence records; one corpus item through the consumer; a reader for the BLS crosswalk spreadsheet; the sources page. |
| `measurements/` | 38 queries (`.sql`) and their output on the published rows (`.txt`): the numbers of the findings below and of the article support page. Two of them read the BLS crosswalk spreadsheet in `sources/codelists/`. `load-check.txt` is the output of `check_load.py`. |
| `seed/seed.py` | Deterministic synthetic `annual` and `qtrly` rows (two years, two states, five counties, one MSA across a state line), plus the code lists as they are. The CI fixture: no test downloads from BLS. |
| `physical/entities/` | Seven entities: `annual`, `qtrly` (data) and the five title tables (reference). |
| `evidence/` | `documents.yaml`: quotes from the BLS pages and the QCEW profiling notes. `probes/`: one record per probe and run, `@2026-11-28` on the published rows (`confirmed`) and `@2026-10-27` on the seed (`inferred`). `measurements.yaml`: the numbers of `measurements/` as records. |
| `probes/`, `probes/results/` | 47 generated probes and 2 written by hand (`null_rate`, V2), with their results on the published rows and on the seeded SQLite file. On the published rows 47 are in range; the other two are F-0001 and F-0002. |
| `drafts/qcew-duckdb-real/` | What `fact propose keys` and `fact propose joins` measured on the published rows, and the entity drafts of the snapshot. |
| `registers/` | Findings F-0001 to F-0011 (F-0010 and F-0011 resolved), hazards H-0001 and H-0002. |
| `semantic/employment-wages/` | The layer (D-019) and its consumer `measure-sql`: required concepts `disclosed`, `level` and `distinct_areas`; measures from monthly levels; rollups over county to state and NAICS parent (D-020). |
| `consumers/measure-sql/`, `semantic/employment-wages/corpus/`, `equivalence/` | The reference consumer, its corpus of 38 items (six naive-versus-correct pairs, two known gaps; every item names the published BLS row it reads), the accepted run on the seeded SQLite file (D-021), which CI reproduces, and the run on the published rows, `qcew-duckdb-real@2026-11-28.md`. |
| `release/allowlist.yaml` | What leaves the repository in a release (`fact release --out release/out --version <v>`; the output is gitignored). |
| `generated/` | Labels, scope and residue from `fact project`, and the equivalence report. |

## The published rows

Read on 2026-11-28: 440 slices, 92,691,103 bytes, for 44 areas (the U.S. total, 2 states, 29 county codes, 7 metropolitan and 5 micropolitan areas). Loaded unfiltered: 110,366 annual rows and 486,100 quarterly rows. Every aggregation level BLS publishes for these areas is there, 40 in all; `size_code` is 0 on every row, and `own_code` takes 7 values (4 never occurs).

The documented key (area, ownership, industry, size, year, quarter) is unique on these rows: `key_duplicates` finds no duplicate in either table. `fact propose keys` cannot find it, because it tries single columns and pairs and the key has six fields; it proposes 8 candidates, the code and the title of four title tables, and none for `annual`, `qtrly` or `area_titles`. Named with `--key`, the six-field key is measured unique on all 110,366 and 486,100 rows (D-024). `fact propose joins` proposes 15 joins: 8 of the model's 10 one-column joins and 7 coincidences between one-digit codes (`own_code`, `size_code` and `qtr` all fit in each other's lists). It proposes none to `area_titles` and says why: `area_fips` is not unique there, 4,649 duplicate rows of 9,458 (F-0001). `scripts/summary.py` prints the list.

For aggregation levels 10 to 80 the first digit of `agglvl_code` is the geography and the second the industry and ownership level. Levels 94, 95 and 96 are special totals whose digits mean neither; they are 32 of the quarterly rows and sit on a national or state area code.

## Expected shape

Every entity's subject scope is `none`. Labels come from class and mechanism alone:

| Relationship | Label |
| --- | --- |
| `annual`, `qtrly` to each title table | `dimension` |
| `annual.to-quarters`, `annual.prior-year`, `qtrly.prior-year` | `lineage` |
| `area_titles.in-state` (county to state by FIPS prefix), `industry_titles.parent` (NAICS prefix) | `hierarchy` |
| `area_titles.in-msa`, `in-csa`, `in-nation`; `industry_titles.to-supersector` | `unresolved` |

## Findings

Measured on the published rows on 2026-11-28. Each number is in `probes/results/qcew-duckdb-real@2026-11-28.jsonl` or in the file under `measurements/` the finding names.

| ID | Finding | On the published rows |
| --- | --- | --- |
| F-0001 | The area code list repeats 4,649 codes (R1) | A plain join from `qtrly` returns 972,200 rows for 486,100; a join to distinct codes returns 486,100 |
| F-0002 | `disclosure_code` holds an undocumented `-` (V1) | On 27,924 quarterly rows, on no annual row |
| F-0003 | Suppressed measures are 0, not NULL (V2) | 250,155 quarterly rows are withheld; all hold 0 in employment and wages and all keep an establishment count; no NULL in 486,100 rows. Withheld: 13.3 percent of national rows, 28.4 of state, 54.9 of county, 64.7 of MSA rows. The share rises in 2025 Q1 and stays: Delaware level 73 is 24.1 percent in each quarter of 2024 and 48.9 in 2025 Q1. Raw slices and loaded tables agree in all 12 groups; the cause is not known |
| F-0004 | Field 14 named `annual_avg_estabs_count` on the layout, `annual_avg_estabs` in the file (A2) | Every annual slice says `annual_avg_estabs` |
| F-0005 | The CSV slice page lists quarterly field 14 twice (A2) | Every quarterly slice says `taxable_qtrly_wages`; the page still lists the name twice |
| F-0006 | The quarterly file pads keys to four quarters with `-` rows (G2) | Each quarter of a year has the same rows (60,663 in 2024, 60,862 in 2025); 121,525 keys, four rows each; in 2025 Q3 and Q4, 11,159 of 11,166 MSA rows are padding, which BLS announced: MSA totals only from third quarter 2025 data on |
| F-0007 | Suppression breaks every rollup (H5) | County to state: of 27,698 disclosed parents, 5,918 equal the sum of their counties and 21,780 do not, every one with a withheld child. NAICS child to parent: 101,073 of 130,999 equal, 29,926 do not, every one with a withheld child. Establishments always add up. Median gap, county to state: 34.9 percent in 2024, 43.1 in 2025, 38.7 over both years. Delaware health care, March 2025: 81,306 published, 69,379 over the disclosed counties |
| F-0008 | `industry_code` mixes NAICS, ranges, domains and supersectors (V3) | 18 of 2,159 codes in the rows are not NAICS; 44 have no prefix parent (53 in the title list); the length of the code misreads the level on 11,352 rows, the second digit of `agglvl_code` on 32, a rule that knows the code shapes on none. The probe on `industry_titles.parent` is in range at its stated bound of 53 (D-025) |
| F-0009 | Geography is a lattice; US000 excludes PR and VI (H1, H2) | C3798 holds 11 counties in 4 states. Adding the Delaware row, the Maryland row and the MSA row counts New Castle and Cecil counties twice, 341,599 workers; the other 2,538,279 of the MSA row lie in Pennsylvania and New Jersey. The territories are not in the slices |
| F-0010 | `annual.prior-year` found no prior row for 61,759 rows | Resolved: the join was wrong. It now compares rows with a blank `oty_disclosure_code` and its probe leaves out the first year in the source, read from the data (D-026): 20,993 source rows, none without a prior row |
| F-0011 | `qtrly.prior-year` found no prior row for 247,496 rows | Resolved the same way: 92,967 source rows, none without a prior row |

Hazards: H-0001 annual averages are not additive (984 of 1,362 county-to-state rollups exact, 378 within rounding, none beyond); H-0002 `avg_wkly_wage` follows a formula (it reproduces 206,810 of 206,811 published values) and must not be averaged across rows. Both are carried into the semantic layer.

## Reproduce

The published rows, from the framework root, with the extra `[duckdb]`:

```bash
bash examples/qcew/scripts/fetch.sh
uv run examples/qcew/scripts/reproduce.sh
```

`fetch.sh` reads from `data.bls.gov` and says which slices differ from the committed read; BLS revises open quarters, and the numbers on this page hold for the read of 2026-11-28. `reproduce.sh` loads the database, takes the snapshot, proposes keys and joins, runs and takes in the probes, passes the gate, runs the corpus and writes the measurements; on the same slices it changes no file. [The tutorial](../../docs/tutorial/qcew.md) walks through it.

The seeded fixtures, as CI runs them:

```bash
uv run python examples/qcew/seed/seed.py sqlite /tmp/qcew.db
uv run pytest -q tests/examples/test_qcew.py tests/examples/test_qcew_real.py
```

`test_qcew.py` seeds SQLite, DuckDB and PostgreSQL (`docker compose up -d --wait`, `export FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres`) and checks that every engine gives the snapshot and the probe counts of `probes/results/qcew-sqlite@2026-10-27.jsonl`. `test_qcew_real.py` runs `fetch.sh` against a local folder, `load.sql` on seeded rows written as slices, and every measurement query on the seeded tables; with `FACT_DSN_QCEW_REAL` set to the built database it also reruns the probes and the measurements and compares them with the committed files.

# QCEW example

A FactModel model of the BLS Quarterly Census of Employment and Wages (QCEW) with NAICS, the second domain of M2. Its shape is the one Chinook does not have: a row is an aggregate over (area, ownership, industry, size, year, quarter), so there is no subject and no anchor (D-015); its hierarchies are code prefixes, not equal fields (D-017); and its code lists are the real BLS files, committed unchanged (D-016).

Source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages. BLS publications are in the public domain (https://www.bls.gov/opub/copyright-information.htm, read 2026-10-23).

## What is here

| Path | What |
| --- | --- |
| `factmodel.yaml` | Profile `statistics`, no `anchor_entity` (D-015); `treat_synthetic_as_representative: true` (the data tables are seeded). |
| `sources/` | `qcew-sqlite`, `qcew-pg`, `qcew-duckdb` (adapter `sql`), `qcew-ddl` (adapter `git`), and four documents: the BLS annual and quarterly layouts, the BLS title files, and the owner's `profile.md` (round 1 of the owner's `qcew-model`). |
| `sources/codelists/` | The five BLS title files, unchanged, with `SOURCES.md` (URL, read date, citation, checksum). |
| `sources/ddl/` | `annual`, `qtrly` and the five title tables for SQLite, PostgreSQL and DuckDB, after the owner's `load.sh` layouts. |
| `seed/seed.py` | Deterministic synthetic `annual` and `qtrly` rows (two years, two states, five counties, one MSA across a state line), plus the code lists as they are. |
| `physical/entities/` | Seven entities: `annual`, `qtrly` (data) and the five title tables (reference). |
| `evidence/documents.yaml` | Quotes from the BLS pages and the owner's profile, each with its query id. |
| `probes/`, `evidence/probes/` | 44 generated probes and 2 written by hand (`null_rate`, V2), their SQLite results, and the evidence intake wrote. |
| `registers/` | Findings F-0001 to F-0009, hazards H-0001 and H-0002. |
| `generated/` | Labels, scope and residue from `fact project`. |

## Expected shape

Every entity's subject scope is `none`. Labels come from class and mechanism alone:

| Relationship | Label |
| --- | --- |
| `annual`, `qtrly` to each title table | `dimension` |
| `annual.to-quarters`, `annual.prior-year`, `qtrly.prior-year` | `lineage` |
| `area_titles.in-state` (county to state by FIPS prefix), `industry_titles.parent` (NAICS prefix) | `hierarchy` |
| `area_titles.in-msa`, `in-csa`, `in-nation`; `industry_titles.to-supersector` | `unresolved` |

## Findings

| ID | Finding | Evidence |
| --- | --- | --- |
| F-0001 | The area code list repeats 4,649 codes (R1) | `key_duplicates` on the committed list; profile R1 |
| F-0002 | `disclosure_code` holds an undocumented `-` (V1) | `value_set` on the seed; profile Q07 |
| F-0003 | Suppressed measures are 0, not NULL (V2) | profile Q07; two `null_rate` probes |
| F-0004 | Field 14 named `annual_avg_estabs_count` on the layout, `annual_avg_estabs` in the file (A2) | two document records; ranks decide |
| F-0005 | The CSV slice page lists quarterly field 14 twice (A2) | layout quote |
| F-0006 | The quarterly file pads keys to four quarters with `-` rows (G2) | profile Q07, Q08; `value_set` |
| F-0007 | Suppression breaks every rollup (H5) | inferred from profile Q16; rollup probe deferred to M3 |
| F-0008 | `industry_code` mixes NAICS, ranges, domains and supersectors (V3) | `join_match` on the prefix hierarchy: 53 codes without a parent; profile Q20 |
| F-0009 | Geography is a lattice; US000 excludes PR and VI (H1, H2) | profile quotes; unresolved relationships |

Hazards: H-0001 annual averages are not additive (M4); H-0002 `avg_wkly_wage` is defined by a formula over unrounded values (M1). Both point at M3.

## Reproduce

From the framework root:

```bash
uv run python examples/qcew/seed/seed.py sqlite /tmp/qcew.db
export FACT_DSN_QCEW_SQLITE=sqlite:////tmp/qcew.db
uv run fact snapshot --root examples/qcew --source qcew-sqlite --date 2026-10-27
uv run fact probe run --root examples/qcew --source qcew-sqlite --environment local --data-quality synthetic --date 2026-10-27
uv run fact check --root examples/qcew
```

PostgreSQL (`docker compose up -d --wait`, `export FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres`) and DuckDB (extra `[duckdb]`): `uv run pytest -q tests/examples/test_qcew.py` seeds each engine and checks that its snapshot and every probe count match SQLite.

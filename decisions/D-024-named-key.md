# D-024 A named key is measured, never discovered

Date: 2026-11-28 · Status: accepted
Platform that forced it: QCEW (published rows)

## Context

`fact propose keys` tries single columns and pairs. The documented QCEW key has six fields (area, ownership, industry, size, year, quarter), so on the published rows the command proposed nothing for `annual` and `qtrly`, the two tables that matter. Searching every combination of six columns in a table of 42 is millions of queries; a person who has read the documentation knows which six to test, and had no way to ask.

Separately, `fact propose joins` proposed no join to `area_titles`, whose code column repeats, and did not say why. The reader had to work out that a target that is not unique is never tried.

## Decision

- `fact propose keys` takes `--key <table>:<column>,<column>,...`, repeatable. For each named list it measures the row count, the rows without a null and the distinct combinations, in two queries whatever the length, and prints `unique` or `not unique` with the duplicate count and the row count.
- The result goes where a proposed key goes: `drafts/<source>/keys.yaml`, under `named`, with a measurement record of status `inferred`. A named key is not added to the candidates the search found, is not checked for minimality, and never becomes a key by itself. A person writes it into the entity, and the `key_duplicates` probe confirms it.
- A flag and not a separate verb. It needs the same snapshot, session, file and evidence path as the search, and one run then answers both questions: what the rows suggest, and whether the documented key holds.
- `fact propose joins` names the targets it could not use. For a table with no unique column and no unique pair of columns, each column that is not unique but holds at most two rows a value on average is printed as `skipped target`, with its duplicate count, and written under `targets_not_unique`. No query is added: the numbers come from the column statistics the command already reads. A table that a pair of columns can reference is left alone: a long text column of such a table comes close to a key and is no one's target (in TPC-H, `partsupp.ps_comment`).
- What stays impossible: finding a key of more than two columns without being told its columns.

## Consequences

- `spec/ALGORITHMS.md` section 4 describes both. `keys.yaml` may hold `named` and `joins.yaml` may hold `targets_not_unique`; each is absent when empty, so proposal files written before this record are unchanged.
- No schema changes: the gate never reads `drafts/`.
- The search itself is unchanged: same candidates, same queries, same prunings.

## Evidence

- `examples/qcew/drafts/qcew-duckdb-real/keys.yaml`: both documented keys named and measured unique on the published rows.
- `examples/qcew/drafts/qcew-duckdb-real/joins.yaml`: `area_titles.area_fips` and `area_titles.area_title` under `targets_not_unique`.
- `tests/propose/test_propose.py`.

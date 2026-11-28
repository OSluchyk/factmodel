# Changelog

Newest first. Every entry says why, not only what.

## 2026-11-28 - Built on the published BLS rows

**Why.** Synthetic rows never confirm a fact (D-014), and the article needs real keys and real dates.

- New source `qcew-duckdb-real`: 440 BLS open data area slices read on 2026-11-28 (`sources/SOURCES.md`), loaded unfiltered by `scripts/load.sh`. The seven entities are bound to it; their field types are the DuckDB ones.
- `treat_synthetic_as_representative` is now false. Probe results on the published rows are `confirmed` evidence (`@2026-11-28`); the seeded results (`@2026-10-27`) were taken in again and are `inferred`.
- Findings F-0001 to F-0009 and both hazards re-measured; all hold, with new numbers. New: F-0010 and F-0011, the prior-year joins on rows whose prior year is not loaded.
- `measurements/`: the queries behind every number, with their outputs. `evidence/measurements.yaml` holds the same numbers as records; `evidence/documents.yaml` gains two rows of the BLS County-MSA-CSA crosswalk, `confirmed` from the spreadsheet the owner saved under `sources/codelists/`, and two quotes from BLS notice and method pages, `inferred` (read by the agent, source `bls-notices`).
- Corpus: every item names its published row; the references of the two known gaps are corrected for real rows. The accepted run is unchanged.
- `annual.prior-year` and `qtrly.prior-year` compare rows with a blank `oty_disclosure_code` and name `first_period: year`, so their probes leave out the first year in the source, read from the data (D-026). F-0010 and F-0011, which the earlier NULL test had opened on the published rows, are resolved. The documented six-field key of both data tables is measured unique with `fact propose keys --key` (`drafts/qcew-duckdb-real/keys.yaml`).
- The `level` concept says that levels 94 to 96 are special totals. F-0009 states the double count of a cross-state MSA correctly.
- `industry_titles.parent` states its bound: 53 codes have no parent by construction, with the reason (D-025). Its probe is in range; F-0008 stays open for the level of a code, not for the probe. 47 of the 49 probes are in range; the other two are F-0001 and F-0002.
- Suppression by year: `measurements/withheld-by-quarter.txt`, `withheld-by-ownership-year.txt`, `parent-child-gaps-by-year.txt` and `load-check.txt`. The withheld share rises in the first quarter of 2025. The load is not the cause, and the cause is not known (F-0003, F-0007). F-0006 cites the BLS notice on MSA totals.

## 2026-10-27 - Model created

**Why.** Start a FactModel model of this platform with the `statistics` profile.

- Created with `fact init` (FactModel 0.0.1).

## 2026-10-27 - QCEW modelled on three engines

**Why.** QCEW is the second example domain: no row is about an individual, its hierarchies are code prefixes, and its code lists carry real defects. The model has to show all three with evidence.

- Seven entities (two data tables, five BLS code lists) from the SQLite catalog, reviewed with document evidence from the BLS layouts and the QCEW profiling notes.
- 46 probes run on SQLite; PostgreSQL and DuckDB give the same counts.
- Findings F-0001 to F-0009 and hazards H-0001, H-0002.

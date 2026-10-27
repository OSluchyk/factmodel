# Final report - Rounds 15 to 18: M2 on QCEW, core freeze

Date: 2026-10-27 · Brief: `rounds/2026-10-27-brief-m2-qcew-freeze.md` · Branch `main`, from `04c296f`

## 1. Outcome

Rounds 15 to 17 completed in full. Round 18 stopped at the freeze on the brief's stop condition. The core survived the second domain with three recorded decisions (D-015 to D-017, platform QCEW), and every change those rounds made to the core falls under one of them.

`examples/qcew` is green on SQLite, PostgreSQL and DuckDB:
- residue 0, and every entity's scope is `none`;
- the nine findings and two hazards of the brief, with evidence;
- 46 probes with equal counts on the three engines.

The freeze review then found three earlier contract changes (rounds 8, 11 and 14) with no decision record. The schemas stay at 0.1.0 until the owner records or reverts them. Everything else in WP2.3 is done.

Final state: ruff, ruff format, mypy (strict) and **678 tests** pass with PostgreSQL 16 through `docker compose` (672 + 6 skipped without it), in this checkout and in a fresh clone. Baseline at `04c296f`: 625 (621 + 4 skipped).

## 2. Git log for the run

```text
$ git log --oneline 04c296f..HEAD
0da3bdc WP2.3: core-change ledger, versioning, fact migrate (freeze stopped)
e137bb7 WP2.2: QCEW example on SQLite, PostgreSQL and DuckDB
98d8dc5 WP2.2a: D-015 to D-017, statistics profile, hard cases
f525716 WP2.1: adopter guides, plugin packaging, DuckDB engine
```

This final report is committed on its own after `0da3bdc`. Nothing was pushed, amended or tagged, and no commit carries an attribution line. The owner's untracked `.claude/` folder is not committed.

## 3. Rounds and acceptance

| Round | Work | Report | Acceptance |
| --- | --- | --- | --- |
| 15 | WP2.1 BigQuery adopter guide, adapter packaging with a test package, DuckDB through `sql`, `value_set` `outside_rows`, explicit `treat_synthetic_as_representative: false` | `rounds/2026-10-27-report-wp2.1.md` | all items ticked; the BigQuery adopter run is owner-pending in the plan |
| 16 | D-015, D-016, D-017 recorded first; core changes; `statistics` profile; hard cases `no-subject`, `expression-join`, `subject-profile-without-anchor` | `rounds/2026-10-27-report-wp2.2a.md` | all items ticked; every core change covered |
| 17 | WP2.2 `examples/qcew` | `rounds/2026-10-27-report-wp2.2.md` | all items ticked (M2 example gate) |
| 18 | WP2.3 ledger, `VERSIONING.md`, `fact migrate` | `rounds/2026-10-27-report-wp2.3.md` | **stopped**: schemas not bumped to 1.0.0 (section 9) |

M2 example gate (brief section 4):
- `fact check` green on `examples/qcew`; residue 0; every entity scope `none`.
- The nine findings exist with evidence; five of them are backed by probe results (F-0001 R1, F-0002 V1, F-0003 V2, F-0006 G2, F-0008 V3).
- The probe counts are equal on SQLite, PostgreSQL and DuckDB.
- CI runs both gates and the comparison.

## 4. Spec, vocabulary and plan edits across the run

Spec (`spec/SPEC.md`):
- The reference engines gain DuckDB, and the `sql` fallback to standard views is noted.
- Profile: a subject (bound by the model, D-012) that may be absent (D-015); examples gain `statistics`.
- The layout gains `profiles/statistics/` and `examples/qcew/`.
- The toolset gains `fact migrate`.

Vocabulary (`spec/VOCABULARY.md`):
- `engine_enforces_foreign_keys` gains `duckdb`, with the measuring test.
- `value_set` returns `outside_values` and `outside_rows`.
- Subject scope and profiles follow D-015.
- `join` accepts expressions (D-017); `join_match` notes how expressions render.
- `model-config` explains `framework_version`.

Algorithms (`spec/ALGORITHMS.md`):
- Algorithm 2 gains "No anchor (D-015)", the expression-join rule for `unique_target` (D-017), and `reachable` `-`.

Plan (`spec/IMPLEMENTATION_PLAN.md`):
- Ground rule 3 gains the D-016 exception.
- WP2.1 deliverables are listed, and the adopter run is owner-pending.
- WP2.2 names QCEW, and its acceptance gains the QCEW criteria.
- WP2.3 records the round-18 state.

New: `spec/CORE-CHANGES-M2.md`, `spec/VERSIONING.md`, `docs/adopters/bigquery.md`, `docs/adapters/packaging.md`.

## 5. Decisions

| ID | Decision | Platform |
| --- | --- | --- |
| D-015 | A profile may have no subject; then no anchor, every scope `none`, scope facts are errors | QCEW |
| D-016 | Public-domain code lists under 1 MB as committed fixtures, with source line and citation | QCEW |
| D-017 | Join expressions over the two ends; one-end conjuncts filter; `unique_target` needs a target key | QCEW |

The three were recorded in round 16 before any core change. No D-018 was invented.

## 6. Core-change ledger summary

`spec/CORE-CHANGES-M2.md` lists 26 changes since `74013ed`:
- 6 under D-011 (rounds 8, 9, 11, 14, 15);
- 1 under D-012, 1 under D-013 and 2 under D-014;
- 1 under D-015, 1 under D-016 and 2 under D-017;
- several that implement spec v0.1 (sync, drift, triggers, `outside_rows`), or are implementation only (in-place YAML edits, `fact init` templates, `fact migrate`).

Without a record:

| # | Change | Round |
| --- | --- | --- |
| 7 | Snapshot `pin` and per-object `pin` | 8 |
| 11 | Probe `expected` optional; probe keys `entity`, `note` | 11 |
| 17 | Field key `values` (declared value domain) | 14 |

All three are additive (minor), and no platform forced them. They hold the freeze.

## 7. Confirmed / inferred / unknown

**Confirmed**

- QCEW needed exactly the three changes the brief predicted; every core change in rounds 16 and 17 falls under D-015 or D-017.
- On the same rows, SQLite, PostgreSQL 16 and DuckDB 1.5.6 agree on every neutral snapshot part and every probe count, for both examples (Chinook 45 probes, QCEW 46).
- DuckDB enforces declared foreign keys (measured). Its SQLAlchemy dialect cannot reflect, so the `sql` adapter falls back to the standard `INFORMATION_SCHEMA` views.
- A third-party adapter package installed in the environment is listed by `fact adapters` and used by `fact snapshot`.
- The committed BLS code lists are byte-identical to the published files, also in a fresh clone (from `0da3bdc` on).
- Measured on the real code lists:
  - the area list repeats 4,649 codes;
  - 53 industry codes have no prefix parent (the three sector ranges and the 50 three-digit codes under them);
  - every numeric county code finds its state.
- The cross-engine comparison caught a collation-dependent join filter (`< 'A'`), now `<= '9'`.
- No credentials were used and no query ran against a remote platform. Network use was package installs only (DuckDB, duckdb-engine, the local test package); the owner's files were read only, and the zip, CSV singlefiles and `qcew.duckdb` were never copied.

**Inferred**

- The area title file is two lists one after the other. The second starts with a repeated header line, which loads as a row with code `area_fips`, so the owner's "4,809 distinct codes" include it.
- Relationships to the area list are `many_to_many` as published (F-0001).
- The `agglvl_code` discriminator lives in meanings, because a single-target relationship cannot carry one.
- Unresolved relationships carry a placeholder join, because the schema requires a `join`.
- The `statistics` profile orders mechanism rules before class rules, as `retail` does.

**Unknown**

- The BigQuery paths on a real project: owner-pending.
- The GitHub Actions run with the new DuckDB and QCEW steps: CI has not run (nothing pushed); the same commands passed locally and in a fresh clone.

## 8. Divergences

- **Round 18 stopped at the freeze** (stop condition: changes without a record). The schemas stay at 0.1.0, and the commit message says "freeze stopped".
- **Round 17's commit stored the code lists with LF line endings** (global `core.autocrlf=input`). Round 18 fixed it with `.gitattributes`; no amend.
- **Intake defect left in place.** Intake writes a field reference into a finding's `about`, which the gate rejects. Fixing it would be a core change no decision covers; the QCEW example works around it.
- **Round 15:**
  - The plugin test package is installed as a dev path dependency, not inside a test.
  - DuckDB needed an adapter fallback, not only a recorded finding.
- **Round 16:** the statistics profile's rule order differs from its label list; one-end conjuncts as filters were specified inside D-017 before it was committed.
- **Round 17:**
  - A fourth document source, `owner-profile` (rank 20).
  - Two hand-written `null_rate` probes.
  - Finding ids renumbered after intake.
  - The seed has 282 annual and 1,136 quarterly rows.
  - The DDL declares no keys.

## 9. Questions for the owner

**Blocking the freeze**

1. Record (platform: none) or revert the three changes without a record: snapshot pins, the optional probe keys, field `values`. With records, the freeze is `SCHEMA_VERSION = "1.0.0"` and a schema re-render.
2. Fix the intake `about` defect before the freeze? It needs a record, or an agreement that a fix that makes code obey the existing schema is not a core change.

**Can wait**

3. Does an owner brief that answers a question count as a decision record?
4. Should a single-target relationship allow a discriminator (QCEW's `agglvl_code`)?
5. Should `unresolved` relationships be allowed without a `join`?
6. A DuckDB `dialect_runner` line and JSON wrap, for owner-run scripts?
7. The BigQuery adopter run: who, and on which project?

## 10. Suggested next brief: M3 on QCEW

Preconditions: the answers to questions 1 and 2, then the freeze at 1.0.0 (a short round 19), and a push so CI runs once.

- **WP3.1 Semantic layer contract.**
  - Layers reference physical relationship keys only.
  - QCEW is the hard case: a layer must encode
    - the disclosure filter (F-0002, F-0003, F-0006);
    - the join to distinct area codes (F-0001);
    - the `(agglvl_code, industry_code)` level discriminator (F-0008).
  - Measures must be defined from monthly levels and the documented formulas (H-0001, H-0002), never as sums of annual averages.
- **WP3.2 Equivalence harness.** Offline on DuckDB fixture data, as the plan says. Comparison modes `same_rows`, `same_count`, `same_predicate`.
- **WP3.3 Reference consumer and corpus.**
  - QCEW questions about employment and wages by industry, area and time are the corpus candidates. Examples:
    - "private employment in Delaware construction, 2025 Q1, month 3";
    - "average weekly wage in New Castle County retail, 2025";
    - "over-the-year change in Maryland manufacturing employment";
    - "counties whose share of suppressed cells exceeds half".
  - At least 30 requests, with reference SQL hand-written against the seed.
  - Expected failures become findings: suppressed parents, rollups across the geography lattice.
  - Chinook stays the second consumer.
- **New probe kind for rollups:** parent against the sum of its children, with suppression counted. It closes F-0007 (H5) and checks M5 and H-0001. This is a core change, so it needs a decision record naming QCEW.
- **Owner inputs:** the threshold decision for equivalence (plan open question), and whether the BLS County-MSA-CSA crosswalk and NAICS hierarchy crosswalk may be committed under D-016 (they would resolve F-0009 and `to-supersector`).

The local PostgreSQL container from `compose.yaml` was stopped at the end of this run (`docker compose down`).

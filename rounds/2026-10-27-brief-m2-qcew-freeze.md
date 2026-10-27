# Brief - Rounds 15 to 18: M2 on QCEW, core freeze (continuous run)

Date: 2026-10-27 · Owner: Oleksandr Sluchyk · Status: approved
Repository: `~/AI/semantic/factmodel`, branch `main`, start at `04c296f`.
Read first: `AGENTS.md`, `spec/SPEC.md`, `spec/VOCABULARY.md`, `spec/ALGORITHMS.md`, `spec/IMPLEMENTATION_PLAN.md` (section 7), `decisions/D-011` to `D-014`, `rounds/2026-10-23-report-m1-close-final.md`, `rounds/2026-10-23-report-m1-residue.md`.

Owner material, read-only, outside this repository: `~/AI/semantic/qcew-semantic-model/qcew-model/` (`README.md`, `profile.md`, `scripts/load.sh`, `scripts/profile.sql`, `data/raw/*_titles.csv`). It is the owner's own work on public data; it is not an employer or client source. Never copy the `.zip`, `.csv` singlefiles or `qcew.duckdb`.

## 0. Goal

M2 answers one question: does the core survive a second domain with a different shape, with every forced change written down? The second example is the BLS Quarterly Census of Employment and Wages (QCEW) with NAICS. It is public domain (BLS: everything it publishes is public domain; cite BLS as the source), and it has no subject: a row is an aggregate over (area, ownership, industry, size, year, quarter). That is the shape Chinook does not have. After the example is green, the schemas freeze at 1.0.0.

What QCEW is expected to force (each becomes a decision record naming QCEW as the platform):

- no anchor entity, so subject scope is `none` for every entity and labels come from class and mechanism alone;
- joins that are not field equality (NAICS parent by code prefix, county to state by FIPS prefix);
- public-domain code lists as committed fixtures (the title files), so hierarchies exist in the example.

Known facts about the data the model must reproduce as findings or probe results are listed in section 6. The owner's `profile.md` (read on 2026-10-23) is the document source for them; its query ids (Q01 to Q36) may be cited.

## 1. Mode

Four rounds, one after another, as before: clean tree at each round start; green checks with PostgreSQL through `docker compose`; a round report; a `CHANGELOG.md` entry with the why; one commit per round; no push, no tag, no amend, no attribution lines. `UV_PROJECT_ENVIRONMENT=.venv`. After round 18 write `rounds/<date>-report-m2-final.md` and stop. Network: package installs only. Everything QCEW needs is on disk in the owner's folder.

## 2. Round 15 - WP2.1 Adopter paths, plugin packaging, DuckDB, round-14 leftovers

- `docs/adopters/bigquery.md`: the `export` path (`fact export-sql --source <id>`, the owner runs the SQL with `bq`, `fact snapshot --from-export`), then the `sql` path (`sqlalchemy-bigquery` dialect, DSN from `dsn_env`), what the adopter sends back (snapshot files, `fact check` output, no credentials). The adopter run itself is the owner's and is not part of this run; the plan's WP2.1 acceptance line for it becomes "owner-pending".
- `docs/adapters/packaging.md`: how a third-party package registers an adapter in `factmodel.adapters`. Prove it with a tiny test package under `tests/fixtures/plugin/` installed in the test session (`uv pip install -e` in a fixture, or an entry-point stub registered through `importlib.metadata` in the test); `fact adapters` must list it.
- DuckDB as a third local engine through the `sql` adapter: extra `[duckdb]` (`duckdb`, `duckdb-engine`), dev dependency so tests have it. Tests: reflection of the same DDL as the SQLite and PostgreSQL tests agrees on the neutral parts; probes execute with the same counts. Measure whether DuckDB enforces foreign keys with a test that inserts a violating row, and record the result in the `engine_enforces_foreign_keys` block with that test as its reason; do not assume.
- Round-14 leftovers: `value_set` reports `outside_values` (distinct) and `outside_rows`; `fact init` writes `treat_synthetic_as_representative: false` explicitly; Chinook's config keeps `true`.

Commit `WP2.1: adopter guides, plugin packaging, DuckDB engine`.

## 3. Round 16 - Decisions and core changes forced by QCEW

Record the three decisions first, then change the core, then add a hard case for each.

**D-015 A profile may have no subject.** `subject` on a profile becomes optional. When absent, `anchor_entity` must be absent from `factmodel.yaml` (the loader fails on either mismatch), `anchor_reference` and `scope_admission` are errors on every entity, and `fact project` writes `none` scope for every entity. Profile rules may not use `subject_scoped` or `any_end_subject_scoped` in such a profile (loader error). Supersedes nothing; refines D-012. Platform: QCEW.

**D-016 Public-domain code lists as fixtures.** Plan ground rule 3 gains an exception: a code list in the public domain may be committed under `examples/<model>/sources/codelists/` when it is under 1 MB, has a `SOURCES.md` line with the URL, the read date and the required citation, and holds no personal data. Everything else stays synthetic. Platform: QCEW (five BLS title files, 511 KB together).

**D-017 Join expressions.** `join` on a relationship accepts, besides `<entity>.<field> = <entity>.<field>`, a boolean SQL expression parsed by sqlglot in its neutral dialect, in which every column is qualified by an entity id and exactly two entity ids occur (the source and the target). Examples: `substr(industry_titles.industry_code, 1, 2) = sector.industry_code`, `concat(substr(area_titles.area_fips, 1, 2), '000') = state.area_fips`. The `references` stage checks the entity ids and fields; `join_match` and `fan_out` probes render the expression per dialect through sqlglot. A relationship with an expression join cannot carry `scope_admission: unique_target` unless a `unique` key of the target is the full right side (document the rule in ALGORITHMS.md). Platform: QCEW.

Core work: schemas, typed models, vocabulary text, loader, projection and scope (D-015), probe rendering (D-017), `fact init` (D-015: a profile without subject gives a config without `anchor_entity`). New profile `profiles/statistics/profile.yaml`: no subject; labels `dimension` (data to reference), `hierarchy` (reference to reference, or data to data at another level), `lineage` (mechanism `derivation`), `representation`, `unresolved`; rules in that order with `unresolved` first; residue must be 0 on the QCEW example. Hard cases: `no-subject` (profile without subject, three entities, expected labels), `expression-join` (prefix hierarchy, expected probe SQL in two dialects), `subject-profile-without-anchor` (loader error).

Commit `WP2.2a: D-015 to D-017, statistics profile, hard cases`.

## 4. Round 17 - WP2.2 The QCEW example

`examples/qcew/`, built with `fact init --profile statistics`, three live sources and one git source:

| Source id | Adapter | Engine | Notes |
|---|---|---|---|
| `qcew-sqlite` | sql | sqlite | `dsn_env: FACT_DSN_QCEW_SQLITE`; snapshot committed |
| `qcew-pg` | sql | postgres | `dsn_env: FACT_PG_DSN`; CI compares with SQLite |
| `qcew-duckdb` | sql | duckdb | `dsn_env: FACT_DSN_QCEW_DUCKDB`; same comparison |
| `qcew-ddl` | git | - | the DDL files below |
| `bls-layout-annual`, `bls-layout-qtrly`, `bls-titles` | document | - | the BLS pages named in the owner's `README.md`, pinned by the read date 2026-10-23; quotes come from `profile.md` sections A2 and A3 |

Tables (DDL in `examples/qcew/sources/ddl/`, SQLite, PostgreSQL and DuckDB): `annual` and `qtrly` with the BLS singlefile layouts as loaded by the owner's `scripts/load.sh` (eight key fields, then the measures; codes as text, counts and money as integers, ratios as doubles), and the five title tables `area_titles`, `industry_titles`, `ownership_titles`, `agglevel_titles`, `size_titles`. One `annual` table with a `year` column, not one table per year.

Code lists: copy the five `*_titles.csv` from the owner's `data/raw/` unchanged into `sources/codelists/` with `SOURCES.md` (D-016). Keep the area file's duplicate rows; they are a finding, not a defect to clean.

Seed (`seed/seed.py`, deterministic): a few hundred `annual` and `qtrly` rows for two years over two states, five counties, one MSA that crosses the state line, ownership codes 0, 1, 2, 3, 5, an industry set with total `10`, two domains, three supersectors, four sectors (one written as a range, `31-33`), 3-digit and 6-digit children, and agglvl codes consistent with the matrix in `profile.md` A4. The seed must reproduce: suppressed rows with `disclosure_code = 'N'` and zero measures but a populated establishment count (V2); the undocumented `'-'` padding rows with all zeros in `qtrly` (V1, G2); a parent disclosed while a child is suppressed and the reverse (H5); keys that never repeat (G1); annual values that are averages of the quarterly ones (M5 where nothing is suppressed).

Model content, to be confirmed by evidence, not assumed:

| Entity | Class | Relationships (label expected) |
|---|---|---|
| annual, qtrly | data | to each title table on its code (`dimension`); `annual` to `qtrly` by derivation (`lineage`); the `oty_*` fields to the prior-year rows of the same entity by derivation (`lineage`, self-reference) |
| area_titles | reference | county to state by FIPS prefix (`hierarchy`, D-017); county to MSA and CSA: `status: unresolved` (the crosswalk is not in the example) |
| industry_titles | reference | NAICS child to parent by prefix (`hierarchy`); sector to supersector: `status: unresolved` (the BLS hierarchy crosswalk was not verified, `profile.md` C12) |
| ownership_titles, agglevel_titles, size_titles | reference | none |

Probes: generated for every relationship and for the value domains `disclosure_code` (blank, N) and `own_code`; run on SQLite by the agent, committed as evidence (`treat_synthetic_as_representative: true` in the example, as Chinook); PostgreSQL and DuckDB compared in CI and locally. The code-list probes run on real public data, so the area duplicate shows up as a measured fact.

Registers: the findings below must exist in `examples/qcew/registers/findings/`, each with its evidence (a probe result, a document quote from `profile.md` with the query id, or both):

1. `area_titles` repeats 4,649 codes (R1): `key_duplicates` on the committed code list, out of range, opens it.
2. `disclosure_code` holds an undocumented `-` (V1): `value_set` on the seed finds values outside the documented domain.
3. Suppressed measures are 0, not NULL, and establishment counts stay populated (V2): document quote; a `null_rate` probe shows the zero null rate.
4. The annual layout page names field 14 `annual_avg_estabs_count`; the file header says `annual_avg_estabs` (A2): two document records, ranks decide, finding stays open for BLS.
5. The CSV-slice page lists quarterly field 14 twice (A2).
6. The quarterly file pads every key to four quarters with `-` rows (G2).
7. Suppression breaks every rollup (H5): `inferred` from the document; the seed reproduces it and a `join_match`-style rollup probe is deferred to M3 with a note.
8. `industry_code` mixes NAICS codes, ranges, domains and supersectors; code length does not give the level (V3): document quote; the `agglvl_code` discriminator is recorded on the relationship to `industry_titles`.
9. Geography is a lattice, not a tree (H1), and `US000` excludes PR and VI (H2): document quotes, `status: unresolved` relationships.

Hazards register: one entry that annual averages are not additive (M4) and one that `avg_wkly_wage` has a documented formula (M1), both pointing at M3.

Acceptance (M2 example gate): `fact check` green on `examples/qcew`; residue 0; every entity scope `none`; the nine findings present with evidence; probe counts equal on SQLite, PostgreSQL and DuckDB; CI runs the gate and the comparison for both examples. Commit `WP2.2: QCEW example on SQLite, PostgreSQL and DuckDB`.

## 5. Round 18 - WP2.3 Core freeze

- `spec/CORE-CHANGES-M2.md`: every core change since `74013ed` with its decision record and the platform that forced it (D-014 none, D-015 to D-017 QCEW). Anything without a record is a stop condition.
- Schemas to `1.0.0`; `spec/VERSIONING.md` (removing or renaming a key is major; adding an optional key is minor; fixing a description is patch; the framework version and the schema version are separate numbers); `framework_version` handling in `factmodel.yaml` documented.
- `fact migrate`: reports the schema version a model uses and whether the installed framework reads it; no migrations yet.
- Both examples green on the frozen schemas; the hard cases too.
- Final report with a suggested M3 brief (semantic layer contract, equivalence harness, reference consumer: QCEW questions about employment and wages by industry, area and time are the corpus candidates).

Commit `WP2.3: core freeze, schemas 1.0.0`.

## 6. Facts the model must not contradict (from `profile.md`, read 2026-10-23)

- Grain of `annual` and `qtrly`: (area_fips, own_code, industry_code, size_code, year, qtr); `agglvl_code` is derived from the key (G1, Q05).
- `size_code` 1 to 9 never occurs in the singlefiles (G4); the example seed uses 0 only.
- `own_code` 4 does not occur in the data although the title file lists it (Q03).
- The data.bls.gov area title file has 9,458 rows and 4,809 distinct codes (A3, Q22).
- `agglvl_code` is a two-digit matrix with special codes 91 to 96 (A4).

## 7. Stop conditions

- A step needs credentials, network beyond package installs, or a query against any remote platform.
- A core change that no decision in section 3 covers: stop and report it; do not invent D-018.
- Any check cannot be made green without weakening a test or a rule.
- The working tree is not clean at a round start.
- The owner's folder is missing a file this brief names: report which and continue with what exists.

Not stop conditions: Docker absent (PostgreSQL "CI only"); DuckDB reflection missing a neutral part (record it as a finding on the `sql` adapter and compare what it gives).

## 8. Final report

`rounds/<date>-report-m2-final.md`: outcome, git log, acceptance per round, spec and vocabulary edits, decisions, confirmed / inferred / unknown, divergences, questions, the core-change ledger summary, and the suggested M3 brief.

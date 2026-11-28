# Changelog

Newest first. Every entry says what changed and why.

## Unreleased

After the 0.3.0 tag. The QCEW example, its documentation and its tests only; the framework and the schemas are unchanged.

- QCEW finding F-0012: the MSA levels 41 to 48 hold no record after 2025 Q2. BLS publishes an MSA for its total only from third quarter 2025 data on; the quarterly rows at these levels are padding in 2025 Q3 and Q4 and the annual file of 2025 has none (`measurements/msa-levels-by-quarter.txt`). The `level_matrix` concept of the layer gains the column `records_through`, and F-0002, F-0003, F-0006 and F-0007 say how much of their counts are these rows. Found on the way and recorded in F-0007: the rollup probes know withheld rows only and count a padding row as a parent with the value 0 (15,233 of the 116,277 NAICS parents with nothing withheld). No verdict changes; a way to name the rows that are records in a rollup declaration is open for the core.
- `examples/qcew/measurements/` holds 41 queries: `msa-levels-by-quarter`, `rollup-padding-parents` and `parent-child-msa-by-quarter` are new; `suppression-by-geography` gains the withheld share of the rows that are not padding (86.6 percent for the MSA rows, against 64.7 percent of all rows), and `padding-by-quarter` the rows that are not padding per quarter.
- `docs/article-support-part3.md`: section 5 shows the MSA levels per quarter, rows and records, with the annual file beside them.

## 0.3.0 - 2026-11-28

Schemas 2.4.0: three optional keys on an entity (D-025, D-026). The CLI gains one flag and one kind of output line (D-024).

- D-024: `fact propose keys --key <table>:<column>,<column>,...` measures a named column list of any length: unique or not, duplicate rows, row count, written under `named` in `drafts/<source>/keys.yaml` with a measurement record (`inferred`). Why: the search stops at pairs, and the documented QCEW key has six fields, so the command found nothing for the two tables that matter. A key of more than two columns is still never discovered; it is measured when a person names it.
- D-024: `fact propose joins` names the targets it could not use. For a table with no unique column and no unique pair, each column close to a key is printed as `skipped target` with its duplicate count and written under `targets_not_unique` in `joins.yaml`; no query is added. Why: the two missing joins to the QCEW area list are now explained by the tool. Proposal files without such targets are unchanged.
- D-025: a relationship may carry `expected: {orphans_left, reason}` and `keys` may carry `expected: {duplicate_keys, reason}`; `fact probe generate` writes the number as the probe's `max` instead of 0. The reason is required and the number is at least 1. Why: a fact with a known, explained exception was out of range for ever. The QCEW industry hierarchy has 53 codes without a parent by construction (F-0008); its probe is now in range at 53 and out of range at 54. Without `expected` every probe is as before.
- D-026: a relationship may carry `first_period: <field>`. For a self-reference the probe generator leaves out the source rows of the first period, which the probe reads from the data. Why: the QCEW prior-year joins held the literal `year > 2024`, which is wrong the day 2023 is loaded. The join grammar of D-017 is unchanged: the subquery is written by the generator, never in a join.
- The QCEW example is built on the rows BLS publishes. `examples/qcew/scripts/fetch.sh` downloads 440 open data area slices (the U.S. total, Delaware, Maryland, their county codes and the metropolitan and micropolitan areas around them; 2024 and 2025; annual and four quarters) and compares them with `scripts/checksums.sha256`; `scripts/load.sh` and `load.sql` build `qcew.duckdb`; `sources/SOURCES.md` lists every URL with the time it was read and its checksum. The slices and the database stay out of git and out of the sdist. Why: Part 2 of the article promised a public dataset with real keys and real dates, and synthetic rows never confirm a fact (D-014).
- A new source, `qcew-duckdb-real`, and the seven QCEW entities are bound to it; `qcew-duckdb` stays the seeded fixture. Why a new source and not a repointed one: the seeded DuckDB file is what the parity test compares with SQLite and PostgreSQL, and its counts are not those of the published rows.
- `examples/qcew/factmodel.yaml` sets `treat_synthetic_as_representative: false`. The probe results on the published rows are taken in as `confirmed` evidence (49 probes, 47 in range; the two out of range are the findings F-0001 and F-0002); the seeded results of 2026-10-27 are taken in again and are now `inferred`. Why: with real rows in the model, a seeded count must not confirm a fact (D-014).
- QCEW findings F-0001 to F-0009 and hazards H-0001 and H-0002 carry the numbers measured on the published rows; all of them hold. F-0009 now says what adding two state rows and the MSA row counts twice: the two counties of the MSA that lie in the two states. Two findings were opened and resolved in the same release, F-0010 and F-0011: the prior-year joins tested for NULL, but a published row without an over-the-year value holds 0 with `oty_disclosure_code` N. The joins now compare rows with a blank `oty_disclosure_code`, and their probes leave out the first year in the source (D-026); no row is left without its prior row.
- `examples/qcew/measurements/`: 38 measurement queries with their outputs on the published rows, run by `scripts/measure.py`; `scripts/reproduce.sh` rebuilds every artifact of the read and changes no file on the same slices. Why: every number in the README, the registers, the tutorial and the article support page is in a committed file. `scripts/check_load.py` counts the raw slices with the csv module against the loaded tables: rows, withheld rows and padding rows are equal in all 12 groups of table, year and state (`measurements/load-check.txt`).
- QCEW suppression by year. The withheld share is measured per quarter and per ownership, and the gap between a parent and the sum of its children per year: the median county-to-state gap is 34.9 percent in 2024 and 43.1 in 2025, 38.7 over both years. The withheld share rises in the first quarter of 2025; the load is ruled out, and no BLS page states a change of the disclosure rules, so F-0003 records the cause as not known. A new document source, `bls-notices`, holds the BLS notice that an MSA is published for its total only from third quarter 2025 data on (F-0006).
- QCEW corpus: every item names the published BLS row it reads. Two references that only fitted the seed are corrected: `msa-detail-from-counties-2025q3` now sums the seven counties of an MSA that lies in one state (Baltimore-Columbia-Towson), and `nation-from-states-2025q1` reads the published national row. Both stay known gaps. The accepted run stays the seeded SQLite run, which CI reproduces; the run on the published rows is kept as `equivalence/qcew-duckdb-real@2026-11-28.md`.
- `docs/article-support-part3.md`: the commands and outputs Part 3 of the article shows, in the form of the Part 2 page; `tests/docs/test_article_support_part3.py` checks every block against its file and runs every measurement command on the seeded tables. The page is not in the site navigation.
- `docs/tutorial/qcew.md`: fetch, load, snapshot, probe, check and one corpus question on the published rows, about five minutes.
- Tests: `tests/examples/test_qcew_real.py` runs `fetch.sh` against a local folder, `load.sql` on seeded rows written as slices and every measurement query on the seeded tables, and checks that every count in the QCEW documents is in a committed file. No test downloads from BLS. `tests/probes/test_bounds.py` covers the stated bound, its required reason, and the first period on a table that gains an earlier year.
- Corrected in `examples/qcew/README.md`: the example has 47 generated probes and 2 written by hand, not 44 and 2.
- The `level` concept of the QCEW layer no longer says that the first digit of `agglvl_code` is always the geography: levels 94, 95 and 96 are special totals whose digits mean neither.
- The BLS County-MSA-CSA crosswalk spreadsheet is committed unchanged under `examples/qcew/sources/codelists/` (D-016), with its URL, read date and checksum in the `SOURCES.md` beside it. `examples/qcew/scripts/crosswalk.py` reads it with the standard library, and two measurements list the counties of an MSA from it. The two evidence records that rested on a transcription of the BLS page are now `confirmed`.

## 0.2.0 - 2026-11-22

- D-023: an element of a reviewed layer that no passing corpus item uses carries a recorded reason. Layers gain the optional key `untested` (`kind`, `id`, `reason`; vocabulary block `layer_element_kind`), schemas 2.3.0. The gate stage `layers` fails a reviewed layer whose accepted run holds no coverage (`no_coverage`), an enforced element without a passing item and without an entry (`missing_reason`), and an entry for an element a passing item uses (`stale_untested`); every layer's entries must name its elements once (`unknown_untested`). Enforced: entities, joins the trace evaluates, field concepts, measures. `fact migrate` names reviewed layers to run and accept again; the Ossie export carries the entries, the dbt export names them as not held; the `layer-build` skill describes the step. Why: a layer could be proven and reviewed while part of it was never tested. The threshold, the share and the regression rule of D-021 do not change.
- Examples: Chinook's layer drops `album` and `track.to-album`; QCEW's drops `ownership_titles`, `qtrly.to-ownership`, `annual.to-ownership` and `annual.to-industry`, and records reasons for `industry_titles`, `qtrly.to-industry` and `annual.to-area`. Both examples are run and accepted again (2026-11-22); no item changes outcome. Why: nothing read the removed elements (D-023).
- Defect fix: `fact init` failed with `UnicodeDecodeError` when a Finder `.DS_Store` sat under the shipped `agent/skills/`. Walks over shipped templates, skills and profiles skip dot files and files that are not UTF-8.
- `fact equivalence run` reports what the corpus exercises of a layer. A new trace (`factmodel.equivalence.trace`) reads each reference's SQL and names the entities, fields, joins, concepts and measures it uses; only what the query reads counts (a CTE or derived table nothing reads uses nothing), and a table may be named by its entity id or its physical name. Joins count as declared or otherwise, shown apart, otherwise labelled weak; concepts count in the `field` form and in the `predicate` form as written; measures count by a weak match. `generated/equivalence-<layer>.md` gains a coverage table and the lists "Not exercised", "No passing item", "Not found as written" (predicate concepts) and "Not evaluated" (target-set or unreadable joins, concepts in other forms; never a zero), and every item that does not pass gets the line "differs from the reference in". Each layer in `equivalence/last-run.json` gets a `coverage` key (`elements`, `exercised`, `not_exercised`, `not_found_as_written`, `no_passing_item`, `tested`, `not_evaluated`, `unresolved_items`), which `fact equivalence accept` copies into `accepted.json`. Both the local run and the owner-run path give it; a test keeps the trace's aggregate map equal to `measure_aggregation`. `proven` keeps its D-021 meaning; the gate reads coverage from the accepted run (D-023). The outputs hold model identifiers and counts, never a literal or SQL text. Why: a layer could be proven while part of it was never tested; Chinook's `album` and QCEW's `industry_titles` and `ownership_titles` and their joins were used by no corpus item.
- The site gives every decision record its own page (`/decisions/D-NNN/`); `/decisions/` is the index, the only entry in the navigation, and says that D-003 and D-008 were withdrawn before the first release. Why: one page of twenty records had no address per record. The records are unchanged.
- CI and the site build use `actions/checkout@v7` and `astral-sh/setup-uv@v10.3.2` (setup-uv publishes no major tag since v8). Why: the v4 and v6 releases run on Node.js 20, which GitHub's runners are retiring.
- `docs/article-support.md`: the commands and outputs Part 2 of the article shows, copied from `examples/tpch` and the quickstart, one block per article section, each with the file it was taken from; `tests/docs/test_article_support.py` checks every block against the repository. Why: the article and the repository cannot drift. The page is not in the site navigation and nothing links to it.

## 0.1.0 - 2026-11-03

The first public release: a model of a data platform built from evidence, checked by a gate, kept current by sync and probes, and served to consumers through semantic layers that a consumer proves.

### Proposals measured on data

- `fact propose keys` and `fact propose joins`: for a source with a `dsn_env`, measure which columns and column pairs are unique and never null, and which column pairs across tables include one another, and write the candidates to `drafts/<source>/keys.yaml` and `drafts/<source>/joins.yaml` with a measurement record each (`status: inferred`, data quality from the flag). Why: a catalog without declared keys, such as the TPC-H tables DuckDB's extension builds, leaves an agent nothing to draft relationships from; the rows know. Candidates never become keys or relationships by themselves; a person does that. Column names are reported, never used as a criterion. `spec/ALGORITHMS.md` section 4 names the method and its limits; vocabulary block `key_type_class` names the type classes a key may have.

### Snapshots

- More than one snapshot per source and day. A second, different read of a day is written as `<source>@<date>_2.yaml` and its pin gets `_2` (then `_3`, and so on); an identical read is kept, not duplicated; `fact draft` and `fact sync` order snapshots by date, then sequence. Why: the TPC-H example reads the catalog twice on one day, before and after the kit's constraints, and the second read used to overwrite the first or had to borrow a date.

### Examples and documentation

- `examples/tpch`: TPC-H on DuckDB, the example of Part 2 of the article. `scripts/generate.sh` builds the database with the tpch extension (fallback: the reference kit's `.tbl` files and `scripts/schema.sql`); `scripts/apply-constraints.sql` holds the kit's 8 primary and 8 foreign keys translated from `dss.ri`; `scripts/reproduce.sh` rebuilds every committed artifact: the snapshot without keys, the proposals on it, the snapshot with keys, the drift between them and the probe run that confirms the foreign keys.
- The quickstart walks through TPC-H (`docs/quickstart.md`) at scale factor 0.1 and shows the measured propose lines; the doc test asserts their counts, seconds dropped. The SQLite walk stays in `docs/quickstart-sqlite.md`.
- CI runs `tests/examples/test_tpch.py` at scale factor 0.01 (`FACT_TPCH_SF`). Why: scale factor 1 is the example's documented run and is reproduced locally; the test checks the keys, the foreign keys and the listed coincidences at any scale, and the small build keeps the job short.
- README: a "Start here" block of three commands, one sentence per capability, the 0.1.0 contents below.
- D-022: example models keep `AGENTS.md`, `agent/` and `.claude/skills/`; a test keeps the skill copies identical to `agent/skills/`.
- The `model-onboard` skill proposes keys and joins where a source can be measured.

### Specification and vocabulary

- `spec/SPEC.md` and `spec/VOCABULARY.md` define every term, file kind and enumeration once; enumerations are machine-readable blocks that code and schemas load (`factmodel.vocabulary`), so no list is copied by hand.
- `spec/ALGORITHMS.md` defines projection with rule 0, subject scope closure with admission rejections and reachability, and the release partition, with 21 hand-written test vectors, so the code is checked against the specification and not the other way round.
- JSON Schemas for every file kind and the metadata snapshot, rendered from templates and the vocabulary; schemas are at 2.2.0. Versioning rules separate schema and framework versions (`spec/VERSIONING.md`).
- Decision records in `decisions/` record what shapes the framework; D-018 sets when a change needs one: a removal, rename, meaning change or algorithm-result change needs a record, an additive change a ledger line in `spec/CORE-CHANGES.md`.
- Relationship identity is an author-set key, never a list position (D-002); `data_quality` replaces a representative flag (D-006); subject scope is derived, never authored (D-007); one review status serves entities and layers (D-009).

### Core and gate

- One model loader validates every file against its schema, checks every reference between files and reports each problem with file, line, column, gate stage and a fix hint, so agents get errors they can act on.
- `fact project` computes the derived values (labels, scope, residue, scope rejections, per-layer join tables) into `generated/`; nothing derived is ever authored.
- `fact check` runs the gate: yaml, schema, references, evidence, derived-not-authored, projection, scope, layers, registers, triggers, generated-fresh and privacy. Each stage is proven by a model that fails it alone (19 hard cases).
- The core is engine-blind: it reads model files and metadata snapshots only (D-011). The model binds the anchor and the profile names the subject (D-012); a profile may have no subject, as for statistics (D-015).
- Joins may be equality joins or boolean SQL expressions over the two ends, such as a code prefix (D-017); a single-target relationship may carry a discriminator, and an unresolved one may omit its join.
- `fact init`, `fact source add`, `fact status`, `fact migrate` and `fact --version` (package and schema version). `fact check` warns, never fails, when a model's `schema_version` differs from the installed schemas while every file validates.
- A literal connection string in a model file fails the `privacy` stage; connection strings live only in environment variables.

### Adapters and engines

- An adapter protocol with an entry-point registry (`factmodel.adapters`), so engines arrive as plugins; `docs/adapters/packaging.md` shows how a third party packages one, and a test plugin proves it.
- `export` adapter: the owner of a platform runs the export SQL (`fact export-sql`) and the model reads the files (`fact snapshot --from-export`); flavours for generic `INFORMATION_SCHEMA`, PostgreSQL and BigQuery.
- `sql` adapter: SQLAlchemy reflection with the connection string from the environment; falls back to `INFORMATION_SCHEMA` views for engines whose dialect cannot reflect (DuckDB). Tested on SQLite, PostgreSQL and DuckDB.
- `git` adapter: `CREATE TABLE` and `CREATE VIEW` read from DDL at a commit or in the working tree, pinned to file and line; `fact quote` turns a text file into a pinned quote.
- Neutral type classes on snapshot fields (D-013); engines that enforce foreign keys are a vocabulary block, measured by tests.
- `fact draft` turns a snapshot into entity drafts: declared keys become relationships with `inferred` evidence, constraint names are kept, and DDL comments become proposed meanings.

### Probes, sync and drift

- `fact probe generate|render|run|intake`: probe kinds (key duplicates, join match, fan-out, null rate, row count, current-row ties, value set, rollup) as sqlglot ASTs rendered per dialect, returning counts only. A probe a dialect cannot express is marked unsupported, never rendered wrong. Dialect knowledge lives in vocabulary maps, so a new dialect needs a vocabulary line, not code.
- Intake confirms a fact only on representative data; results on synthetic data attach as `inferred` (D-014). Out-of-range results open findings.
- `rollup` probes measure whether a hierarchy adds up and where suppression breaks it (D-020).
- Volatile probes (`fact probe generate --set volatile`) for scheduled re-measuring.
- `fact sync` classifies the drift between snapshots and the model in eight kinds, writes drafts for new facts and findings for lost ones, fires `source_pin_moved` triggers and writes a drift report; the `triggers` stage fails on a fired trigger without follow-up.

### Semantic layers and equivalence

- The semantic layer contract (D-019): a layer is built only on physical facts by id and carries the filters every query applies, discriminators, distinct rules, value tables, measures with expressions, documented formulas, rollups and hazards. The `layers` stage checks it.
- The equivalence harness: a consumer compiles each corpus request into SQL, and the harness compares it with the reference answer in `same_rows`, `same_count` or `same_predicate` mode, keeping outcomes and counts, never rows. `fact equivalence run|accept|script`; the script lets the owner of a platform run the comparison where the data lives.
- A layer is proven when its consumer passes at least the threshold share (0.9 by default), nothing regresses and every failure has a known gap or a finding (D-021); only a proven, accepted layer may be `reviewed`.
- Fix: the owner-run comparison script no longer writes `EXCEPT WITH ...` when a reference starts with a CTE, which no engine accepts.

### Release and exports

- `fact release` builds the readable copy of a model: a complete partition of every file (export, project, refuse), internal-note markers stripped, a `VERSION` file and append-only `RELEASE_NOTES.md` kept in the model repository. It is refused on a failing gate, an equivalence drop or any partition failure. `fact check --release` is the reduced release gate.
- `fact lookup` prints a layer with its joins resolved, an entity or a hazard, from a model or a release.
- `fact export --target dbt`: MetricFlow semantic models and metrics, filters for the layer's default filters, derived metrics for formula measures, evidence status in `meta`; validated with `dbt parse`.
- `fact export --target ossie`: Apache Ossie core specification 0.1.1 by default, 0.2.0.dev0 with `--spec-version`; only keys the pinned document names, the rest in `ai_context` and `custom_extensions`.
- Every export writes `EXPORT_NOTES.md`, the list of what the target cannot hold; nothing is dropped silently (`docs/exporters/round-trip-notes.md`).

### Agent layer

- A model-repository `AGENTS.md` template, brief and report templates, and skills an agent runs with `fact` commands only: `model-onboard`, `entity-scaffold`, `evidence-gather`, `probe-write`, `probe-intake`, `model-lookup`, `release`, `drift-review`, `layer-build`, `escalation-draft` and `maintenance-pack`. `fact init` copies them into a new model.
- A test follows `model-onboard` command by command and reproduces the Chinook drafts exactly.
- The agent never widens its own access and never runs queries against a real platform; the owner of the platform does.

### Examples

- `examples/chinook`: the Chinook schema on SQLite and PostgreSQL with synthetic rows, the `retail` profile, 45 probes, and the layer `customer-purchases` proven by consumer `filter-sql` on a 31-question corpus.
- `examples/qcew`: BLS QCEW with the `statistics` profile, the real BLS code lists (D-016), findings and hazards from measured probes, and the layer `employment-wages` proven by consumer `measure-sql` on a 38-question corpus, including six questions whose naive SQL gives a different answer.

### Packaging and documentation

- `uv build` gives a wheel and an sdist that pass `twine check`; extras `[sql]`, `[postgres]` and `[duckdb]`. A test installs the wheel alone outside the repository and runs the Chinook loop.
- A documentation site (MkDocs Material) assembled from the repository: specification, decisions, guides, one page per skill, a CLI reference generated from the code and a schema reference generated from the schemas. A strict build runs in CI.
- A quickstart and a Chinook tutorial from an empty folder to a release and two exports; tests run every command of both on the installed package.
- Package metadata names the homepage, repository, documentation site and changelog, and the status is Alpha; the site sets its own URL. Readers of the package index can find the project.
- The decision records were curated once for this release (`decisions/README.md`): the record about the earlier working name is removed, and wording that named the development process, work packages or milestones is gone. The specification, the roadmap and the examples name milestones only in the roadmap, and their open questions are the two that are still open, so a reader sees the product, not a to-do list.

## 0.0.1 - 2026-10-23

Repository bootstrap: Python project, license (Apache 2.0, D-001), core vocabulary and the name FactModel (D-010).

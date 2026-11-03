# Changelog

Newest first. Every entry says what changed and why.

## 0.1.0 - 2026-11-03

The first public release: a model of a data platform built from evidence, checked by a gate, kept current by sync and probes, and served to consumers through semantic layers that a consumer proves.

### Proposals measured on data

- `fact propose keys` and `fact propose joins`: for a source with a `dsn_env`, measure which columns and column pairs are unique and never null, and which column pairs across tables include one another, and write the candidates to `drafts/<source>/keys.yaml` and `drafts/<source>/joins.yaml` with a measurement record each (`status: inferred`, data quality from the flag). Why: a catalog without declared keys, such as the TPC-H tables DuckDB's extension builds, leaves an agent nothing to draft relationships from; the rows know. Candidates never become keys or relationships by themselves; a person does that. Column names are reported, never used as a criterion. `spec/ALGORITHMS.md` section 4 names the method and its limits; vocabulary block `key_type_class` names the type classes a key may have.

### Snapshots

- More than one snapshot per source and day. A second, different read of a day is written as `<source>@<date>_2.yaml` and its pin gets `_2` (then `_3`, and so on); an identical read is kept, not duplicated; `fact draft` and `fact sync` order snapshots by date, then sequence. Why: the TPC-H example reads the catalog twice on one day, before and after the kit's constraints, and the second read used to overwrite the first or had to borrow a date.

### Examples and documentation

- `examples/tpch`: TPC-H on DuckDB, the example of Part 2 of the article. `scripts/generate.sh` builds the database with the tpch extension (fallback: the reference kit's `.tbl` files and `scripts/schema.sql`); `scripts/apply-constraints.sql` holds the kit's 8 primary and 8 foreign keys translated from `dss.ri`; `scripts/reproduce.sh` rebuilds every committed artifact: the snapshot without keys, the proposals on it, the snapshot with keys, the drift between them and the probe run that confirms the foreign keys.
- The quickstart walks through TPC-H (`docs/quickstart.md`); the SQLite walk stays in `docs/quickstart-sqlite.md`.
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

# Brief - Rounds 8 to 13: close M1 with an engine-neutral core (continuous run)

Date: 2026-10-23 · Owner: Oleksandr Sluchyk · Status: approved
Repository: `~/AI/semantic/factmodel`, branch `main`, start at `1d88638`.
Read first: `AGENTS.md`, `spec/SPEC.md`, `spec/VOCABULARY.md`, `spec/ALGORITHMS.md`, `spec/IMPLEMENTATION_PLAN.md`, `rounds/2026-10-23-report-m0-m1-core-final.md`, `rounds/2026-10-23-report-wp1.5-stopped.md`.

This brief replaces `rounds/2026-10-23-brief-wp1.5-wp1.5b.md`. That draft, and its D-011, are withdrawn.

## 0. Goal

FactModel is a platform-agnostic framework. It must work with many data sources and, ideally, any. The plan's "M1 - Core on BigQuery" and the `thelook_ecommerce` example contradict that: they tie the first milestone to one cloud engine and to credentials the agent must not have. This run removes that dependency and closes M1 on an engine-neutral core, with two local reference engines (SQLite and PostgreSQL) and one reference dataset (Chinook) that ships for many engines.

How "any data source" is realised, and what every round must respect:

1. The core never names an engine. It reads model files and snapshot files; it never imports an adapter and never branches on `engine`.
2. The snapshot (`schemas/snapshot.schema.json`) is the only contract between an adapter and the core. Engine-specific facts go to `options` or `extensions`; the core reads neither.
3. Adapters are plugins. Built-in and third-party adapters register through the same entry-point group, so an adopter adds an engine without touching the core.
4. Three universal adapters cover the long tail in 1.0: `export` (owner-exported standard `INFORMATION_SCHEMA` tables, any engine that has them), `sql` (live reflection through SQLAlchemy, any engine with a SQLAlchemy dialect), `git` (DDL and text in a repository, any dialect sqlglot parses).
5. Probes are generated from a neutral AST and rendered per dialect. Execution is owner-run by default; a local engine seeded with synthetic rows is a test fixture, not a platform, so tests and the agent may query it.
6. No cloud credentials in the repository or in the agent's environment. BigQuery, Snowflake, Databricks and the rest are reached through `export` or `sql` by adopters with their own credentials; the repository proves the path on local engines.

## 1. Mode

Six rounds, one after another, as in the previous run: clean tree at each round start; every check green (`ruff check`, `ruff format --check`, `mypy src`, `pytest -q`); a round report `rounds/<date>-report-<topic>.md`; a `CHANGELOG.md` entry with the why; one commit per round (`WPx.y: <one line>` plus a body); no push, no tag, no amend, no attribution lines. After round 13 write `rounds/<date>-report-m1-close-final.md` (same sections as the previous final report) and stop.

Run every `uv` command with `UV_PROJECT_ENVIRONMENT=.venv`.

Round 8 starts with `git stash pop`. Keep what fits the protocol in section 3, delete the rest (`decisions/D-011-agent-reads-public-metadata.md`, its index line, the `google-cloud-bigquery` extra, `src/factmodel/adapters/bigquery/live.py`, the ground-rule-7 exception notes in the spec and plan). Then `git stash drop` is not needed; the pop removes it.

If `docker` is available on this machine, use `docker compose` for the PostgreSQL parts. If it is not, that is not a stop condition: write the PostgreSQL tests so they skip without `FACT_PG_DSN`, run everything else, and say in the report that the PostgreSQL path is verified only by CI after the owner pushes.

## 2. Decisions (record in round 8, before any adapter code)

**D-011 Engine-blind core, universal adapters, local reference engines.** Supersedes the "core on BigQuery" framing of the plan (sections 4 and 6). Content: the six points of section 0, plus: reference engines are SQLite (standard library) and PostgreSQL (Docker in CI); the reference dataset is Chinook, schema only, with synthetic rows generated at test time; the agent runs no query against any remote platform and the repository holds no credentials; an adopter verifies a cloud engine on their own project and reports back. The draft D-011 of the withdrawn brief is not recorded; this record takes its number.

**D-012 The model binds the anchor, the profile names the subject.** A profile is a domain, not a platform, so `anchor_entity: users` does not belong in it. The profile gets `subject: <role>` (free text, for example `customer`); `factmodel.yaml` gets `anchor_entity: <entity-id>`. The loader requires `anchor_entity` in the model config; the `references` gate stage checks it names an existing entity of class `data`. Migrate the retail profile, the `fact init` template, the hard cases, the vectors and every fixture that carries the profile key.

**D-013 Neutral type class on snapshot fields.** Snapshot fields get an optional `type_class` from a new vocabulary block (`integer, decimal, float, boolean, text, date, time, timestamp, interval, binary, json, array, struct, geography, other`); `type` keeps the engine's own text. Each adapter maps engine types to a class; unknown types map to `other`. Drift (round 10) treats a change of `type_class` as a type change and a change of `type` text within the same class as "no effect, listed".

Also in round 8:

- `AGENTS.md`: rule 1 example datasets become "Chinook on SQLite and PostgreSQL"; new rule 10: "The agent never drafts or records a decision that widens its own access (credentials, remote platforms, network). Such requests go in the report's questions."
- Plan ground rule 7 stays as written; add one sentence: "A local engine seeded with synthetic rows is a test fixture, not a platform."

## 3. Round 8 - WP1.5 Adapter protocol, `export` and `sql` adapters

Plan reference: WP1.5, rewritten by this brief (see section 9).

Deliverables:

- `src/factmodel/adapters/base.py`:

  ```python
  class Adapter(Protocol):
      name: str                      # adapter id, for example "sql"
      def engines(self) -> list[str]: ...                 # engines it can read, or ["*"]
      def snapshot(self, source: Source, model_root: Path) -> Snapshot: ...
      def default_dialect(self, engine: str) -> str: ...   # sqlglot dialect name
  ```

  `to_facts(snapshot) -> list[EntityDraft]` is one core function, not an adapter method: drafts are engine-neutral by construction. Declared constraints become relationships with `mechanism: declared_fk`, evidence `inferred` when `enforced: false` and `confirmed` when `enforced: true`; nothing else is guessed; class is `data` as a placeholder marked `review_status: draft`.
- Registry: `src/factmodel/adapters/registry.py` reads the entry-point group `factmodel.adapters`; the built-ins are registered in `pyproject.toml` the same way. `fact adapters` lists them with engines and default dialects.
- `export` adapter: reads a directory of files exported by the owner from the standard views `TABLES`, `COLUMNS`, `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `REFERENTIAL_CONSTRAINTS` (CSV or JSON, one file per view, standard column names). Flavours are pure functions in `adapters/export/flavours/<engine>.py` that read optional extra files: `bigquery` (`COLUMN_FIELD_PATHS` for nested and repeated fields, `TABLE_OPTIONS` for partitioning and clustering, constraints always `enforced: false`), `postgres` (enforced foreign keys), `generic` (nothing extra). `fact export-sql --source <id>` prints the SQL the owner runs to produce the export for that engine ("agents read, people run").
- `sql` adapter: SQLAlchemy 2 `inspect()` reflection (tables, views, columns, primary keys, unique constraints, foreign keys, comments). Optional extra `[sql]` (`sqlalchemy>=2.0`); drivers are further extras (`[postgres]`: `psycopg[binary]>=3`). The DSN comes from the environment variable named by the source's `dsn_env`; a literal DSN in any model file fails the `privacy` gate stage (pattern: a URL with `://` and `@`, or `password=`). `enforced` is `true` for engines that enforce foreign keys (PostgreSQL, MySQL with InnoDB, SQL Server, Oracle) and `false` otherwise (SQLite, BigQuery, Snowflake, Databricks); the table lives in the vocabulary, not in code.
- Vocabulary: `source` gains `adapter` (slug) and `dsn_env` (optional); `engine` stays a free slug; new block `engine_dialect` (known engine to default sqlglot dialect: bigquery, postgres, sqlite, mysql, mssql to tsql, snowflake, databricks, duckdb, trino, redshift, oracle) with the rule that an unknown engine needs an explicit `dialect` on the source; new block `engine_enforces_foreign_keys`; new block `type_class` (D-013).
- `fact snapshot --source <id> [--from-export <dir>]` writes `sources/snapshots/<source-id>@<date>.yaml`, valid against `schemas/snapshot.schema.json`, and sets `current_pin`. `fact draft --source <id> [--snapshot <path>]` writes drafts to `drafts/`, never to `physical/`. Both idempotent (ground rule 8).
- Dependencies: `sqlglot` becomes a runtime dependency (D-005 planned it for M1); `sqlalchemy` in dev dependencies so tests always have it.
- Tests: `export` on committed synthetic exports for the three flavours; `sql` on an in-memory SQLite built in the test (DDL with a declared foreign key, a unique constraint, a view); a PostgreSQL test behind `FACT_PG_DSN` that reflects the same DDL and asserts the neutral parts agree with the SQLite snapshot (names, nullability, constraints, `type_class`), while `type` text and `enforced` differ as expected; `to_facts` golden tests; registry test with a fake third-party entry point.

Acceptance: `fact adapters` lists `export`, `sql`, `git` (git lands in round 9; list it as "not installed" until then or add it in round 9); every test above passes; D-011 to D-013 recorded; AGENTS.md updated; no `google-cloud-bigquery` anywhere; `grep -rn thelook spec AGENTS.md profiles CONTRIBUTING.md` prints nothing.

## 4. Round 9 - WP1.5b `git` adapter

Plan reference: WP1.5b, unchanged in substance.

- `src/factmodel/adapters/git/`: read files at a commit; parse `CREATE TABLE` (and `CREATE VIEW`) with sqlglot in the dialect the source names into the same snapshot format; any text file quotable as evidence with pin `<repo>@<sha>:<path>[:<line>]`; `fact snapshot` for a git source stores parsed DDL plus a file list with hashes, never the repository.
- Tests build a small repository in a temporary folder with the same tables in two dialects (SQLite and PostgreSQL DDL); a DDL snapshot and a catalog snapshot (round 8, SQLite in memory) of the same table produce matching entity drafts.

Acceptance: as the plan says, plus `fact adapters` shows all three.

## 5. Round 10 - WP1.6 Sync, drift and triggers

Plan reference: WP1.6, unchanged, engine-neutral by construction (it compares snapshots and model files only).

- `fact sync --source <id>`: compare the latest snapshot with the model; classes new fact / changed fact / lost fact / no effect; drift kinds: new object, dropped object, new field, dropped field, type class change, type text change (no effect, listed), nullability change, constraint change; drafts for new facts into `drafts/`; lost facts open findings; `generated/drift.md`.
- `maintenance/triggers.yaml` format and the `triggers` gate stage (a fired trigger with no follow-up fails the gate); `fact status` lists fired triggers.
- Golden tests with two snapshots that differ in every kind; a trigger fixture that fails the gate until a follow-up is recorded; idempotency test for `fact sync`.

## 6. Round 11 - WP1.7 Probe generator v1, rendering per dialect, intake

Plan reference: WP1.7, with execution added.

- `src/factmodel/probes/`: probe kinds `key_duplicates`, `join_match` (both directions), `fan_out`, `null_rate`, `row_count`, `current_row_ties`, `value_set` (counts of distinct values only, never the values); each probe has a stable ID, the fact it tests, an expected range, and an AST built with sqlglot; identifiers are always quoted (`identify=True`), so mixed-case names survive on PostgreSQL.
- `fact probe generate [--source <id>]` writes `probes/<probe-id>.yaml`; `fact probe render --dialect <d>` writes one script per source (`set -uo pipefail`, each query prints `QUERY FAILED` and continues, results as JSON with a pin); `fact probe run --source <id>` executes through the `sql` adapter when the source has a `dsn_env`, counts only; `fact probe intake <results>` writes `evidence/probes/<probe-id>@<date>.yaml`, moves `inferred` to `confirmed` when in range, opens a finding when out of range, strips anything that looks like an email or a personal identifier.
- A probe that needs a construct the dialect lacks (nested paths outside BigQuery, for example) is marked `unsupported_on_dialect` with a note; never rendered wrong.
- Tests: rendering snapshots for `bigquery`, `postgres`, `sqlite`, `snowflake`, `duckdb`, `tsql`, `mysql`; execution on SQLite in memory for every kind; execution on PostgreSQL behind `FACT_PG_DSN`; intake with in-range, out-of-range and malformed results; idempotency of intake.

## 7. Round 12 - WP1.8 Retail profile and the Chinook example

Plan reference: WP1.8, rewritten.

- Before copying anything: check the Chinook license in the upstream repository (`lerocha/chinook-database`). If it is permissive (MIT or similar), copy the schema statements only (no `INSERT`) for SQLite and PostgreSQL into `examples/chinook/sources/ddl/` with the license file and a `SOURCES.md` naming the commit. If it is not, write the DDL by hand from the public schema description (eleven tables: Artist, Album, Track, Genre, MediaType, Playlist, PlaylistTrack, Customer, Employee, Invoice, InvoiceLine) in both dialects, and say so in the report. Neither case is a stop condition.
- `examples/chinook/seed/seed.py`: deterministic synthetic rows (fixed seed; a few hundred customers, invoices and lines; a few employees; a small catalog) loaded into SQLite and PostgreSQL by the tests and by `docker compose`. Names and emails are generated strings that do not look like real people (`customer-0042`, `c0042@example.invalid`).
- `examples/chinook/` is a full model repository (`fact init --profile retail`, `anchor_entity: customer` per D-012) with three sources: `chinook-sqlite` (adapter `sql`, engine `sqlite`, `dsn_env: FACT_DSN_CHINOOK_SQLITE`), `chinook-pg` (adapter `sql`, engine `postgres`, `dsn_env: FACT_PG_DSN`), `chinook-ddl` (adapter `git`, this repository, the DDL files). Snapshots committed: SQLite catalog and DDL. The PostgreSQL snapshot is taken in CI and compared with the SQLite one on the neutral parts; it is not committed unless the owner takes it (not a stop condition).
- Expected shape, to be confirmed by evidence, not assumed: Customer anchor; Invoice direct; InvoiceLine transitive through Invoice (tests which basis wins); Employee administrative (SupportRepId; ReportsTo self-reference); Artist, Album, Track, Genre, MediaType, Playlist, PlaylistTrack reference (Track to Album to Artist is a reference chain; PlaylistTrack is a bridge between reference entities); InvoiceLine to Track is customer data joined to reference data.
- Probes generated for every relationship, run on SQLite (agent, local), results committed as evidence; the same probes run on PostgreSQL in CI and must return the same counts (same seed).
- `.github/workflows/ci.yml`: add a `postgres:16` service, `FACT_PG_DSN`, and a job step that runs `fact check` and the probe comparison on `examples/chinook`.

Acceptance (M1 gate): `fact check` green on `examples/chinook`; residue 0; scopes match the expected shape or differ with a decision record; every relationship confirmed by a probe or explicitly inferred with a reason; the PostgreSQL job is green in CI after the owner pushes (report it as "CI only" if Docker is absent locally).

## 8. Round 13 - WP1.9 Agent layer v1

Plan reference: WP1.9.

- `agent/AGENTS.md` template and skills `model-onboard`, `entity-scaffold`, `evidence-gather`, `probe-write`, `probe-intake` under `agent/skills/<name>/SKILL.md`; `agent/templates/brief.md`, `agent/templates/report.md`. Skills name `fact` commands, never an engine.
- Dogfood: in this session, following only the skill text, redo WP1.8 steps 1 and 2 (snapshot and draft) for `examples/chinook` into a temporary folder and compare with the committed drafts; record the result in `docs/dogfood/2026-10-23-chinook-onboard.md`. A fresh-session run stays with the owner.

## 9. Spec and plan edits (round 8, with D-011)

- `spec/IMPLEMENTATION_PLAN.md`: section 3 baseline rows for BigQuery and PostgreSQL access become "Generic SQL access: SQLAlchemy 2 (extra `sql`); drivers as extras (`postgres`: psycopg 3)" and "Reference engines: SQLite (standard library), PostgreSQL (Docker in CI)"; section 4: M1 becomes "Core, engine-neutral" with the Chinook gate, M2 becomes "Cloud engines by adopters and a second domain" (BigQuery `export` and `sql` paths verified by an adopter on their own project; third-party adapter packaging guide; second domain profile with a dataset chosen then); section 6 heading, expected-model table and WP1.5, WP1.7, WP1.8 as this brief says; WP2.1 and WP2.2 reworded; WP3.3 "reference consumer for the Chinook example".
- `spec/SPEC.md`: add to the principles "The core never names an engine; adapters are plugins behind one snapshot contract"; toolset gains `fact adapters`, `fact export-sql`, `fact draft`, `fact probe run`; repository layout gains `examples/`; "Later, not in 1.0" keeps Snowflake and Databricks as adapters to verify, and adds dbt manifest, OpenMetadata and DataHub as candidate adapter plugins.
- `spec/VOCABULARY.md`: blocks and fields from sections 2 and 3; example pins stop naming `thelook` (use a neutral example such as `postgres:chinook@2026-10-23` and `bigquery:my-project.sales@2026-10-23`). Fixture files may keep existing example values.
- `profiles/README.md`, `CONTRIBUTING.md`, `AGENTS.md`: no `thelook`, no Pagila.

## 10. Stop conditions

- A step needs credentials for, or a query against, any remote platform.
- A step needs network beyond package installs and the Chinook license check (one read of the upstream repository page).
- Any check cannot be made green without weakening a test or a rule.
- Doing the work would change a decision or a spec principle beyond D-011 to D-013.
- The working tree is not clean at a round start, or `git stash pop` conflicts (report the conflict; do not resolve it by discarding `main`).

Not stop conditions: Docker absent (skip PostgreSQL tests locally, report "CI only"); Chinook license not permissive (write the DDL by hand); a vocabulary block needs one more value to express an engine (add it, record it in the round report).

## 11. Final report

As in the previous run: outcome, git log, acceptance per round, spec and vocabulary edits, decisions, confirmed / inferred / unknown, divergences, questions, and a suggested next brief (M2). State explicitly which parts are verified only by CI.

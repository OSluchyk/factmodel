# FactModel - Implementation Plan

Author: Oleksandr Sluchyk · Version 0.1 (draft) · 2026-10-23
Companion to `spec/SPEC.md`. Where the two disagree, the spec wins and this plan is fixed.

## 1. How to use this plan

- Work is split into **milestones** (M0-M4) and **work packages** (WP). One work package is one agent round: one brief in, one report out, one commit by the agent (D-008).
- Every work package lists: goal, deliverables (exact paths), tasks, acceptance checks, dependencies.
- A work package is done only when its acceptance checks pass in CI and its round is committed.
- Effort is given in agent rounds. It is a rough estimate, not a commitment.
- Anything that changes the core after M2 needs a decision record (`decisions/D-NNN.md`) naming the platform that forced it.

## 2. Ground rules

1. **Clean room.** No code, schema names, tickets, data or documents from any employer or client. Concepts only, written from scratch. Examples use public datasets.
2. **English everywhere:** code, comments, docs, commit messages.
3. **No data in the repository.** Test fixtures are synthetic or exported metadata from public datasets. Probe outputs are counts only. One exception (D-016): a public-domain code list under 1 MB may be committed unchanged under `examples/<model>/sources/codelists/`, with a `SOURCES.md` line giving its URL, read date and required citation, when it holds no personal data.
4. **Deterministic core.** The core package does no network or database I/O. Adapters do I/O and write files; the core reads files.
5. **Schemas are normative.** JSON Schema files in `schemas/` define every file kind. Python models are checked against them in tests, never the other way round.
6. **Every gate stage has a failing fixture.** A check that has never failed is not trusted.
7. **Agents never push or run queries against real platforms.** The owner does. On this repository the agent commits once per round (D-008). A local engine seeded with synthetic rows is a test fixture, not a platform.
8. **Every write command is idempotent.** A second run of `fact sync`, `fact project`, `fact probe intake` or any migration produces zero diff. Tests check it.
9. **Services are authored by hand in 1.0**, with evidence from code read through the git adapter. Automatic extraction of services from pipeline configuration is platform-specific and out of scope.

## 3. Technical baseline

| Area | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12+ | Ecosystem for SQL parsing, YAML, warehouses |
| Packaging and runs | `uv`, `pyproject.toml`, PEP 621 | Fast, reproducible, one tool |
| CLI | Typer | Typed commands, generated help |
| YAML | ruamel.yaml in strict mode | Fails on duplicate keys, keeps comments and order on round-trip |
| Schema validation | jsonschema (Draft 2020-12) | Standard, language-neutral |
| Typed models | pydantic v2 | Fast typed access in Python; parity-tested against JSON Schema |
| SQL generation and parsing | sqlglot | One AST, many dialects; transpile probes per engine |
| Generic SQL access | SQLAlchemy 2 (extra `sql`); drivers as extras (`postgres`: psycopg 3) | One adapter for any engine with a SQLAlchemy dialect (D-011) |
| Reference engines | SQLite (standard library), PostgreSQL (Docker, locally and in CI) | Local, free, no credentials; synthetic rows only (D-011) |
| Tests | pytest, hypothesis for projection rules | Unit, golden-file, property tests |
| Quality | ruff (lint and format), mypy (strict on core) | Same rules for agents and people |
| CI | GitHub Actions | Lint, types, tests, gate on every example model |
| Docs | Markdown in repo; MkDocs Material from M4 | No site until there is something to publish |
| License | Apache 2.0 (D-001) | Public repository; explicit patent grant |

## 4. Milestone overview

| Milestone | Outcome | Gate to pass | Rounds (rough) |
| --- | --- | --- | --- |
| M0 - Specification | Repository bootstrapped; every file kind specified with JSON Schema and worked examples; algorithms written as pseudo-code with test vectors | Spec review; schema test suite green | 3-4 |
| M1 - Core, engine-neutral | Core package, gate, CLI, adapter protocol and registry, `export`, `sql` and `git` adapters, sync, probe generator v1 rendered per dialect, hard-case fixtures, retail profile, `examples/chinook` on SQLite and PostgreSQL | Gate green on `examples/chinook` and on every hard-case fixture; expected scopes hold; residue 0; the same probes give the same counts on SQLite and PostgreSQL | 12-14 |
| M2 - Cloud engines by adopters and a second domain | BigQuery `export` and `sql` paths verified by an adopter on their own project; third-party adapter packaging guide; second domain profile with a dataset chosen then; core frozen at schema 1.0.0 | No core change, or each change has a decision record naming the platform that forced it | 4-5 (done: rounds 15 to 19; BigQuery adopter run owner-pending) |
| M3 - Semantic layers | Layer contract, consumer equivalence harness, reference consumer, exports (OSI, dbt), release projection | One consumer meets its threshold on a corpus | 6-8 (done: rounds 20 to 25, synthetic corpora) |
| M4 - Release 1.0 | Packaging, docs site, tutorial, upgrade policy, external pilot | Someone else sets up a model from scratch using only the docs | 3-4 |

Dependencies: M0 before everything. Within M1, WP1.1-WP1.4 come first; adapters and probes after. M3 needs M2's frozen core.

---

## 5. M0 - Specification

### WP0.1 Repository bootstrap (1 round)

**Goal.** An empty but working repository.

**Deliverables.**

```text
pyproject.toml               name, version 0.0.1, dev dependency group; engine extras come with their adapters (D-005)
LICENSE                      Apache 2.0 (D-001)
README.md                    one-paragraph pitch, status, link to spec
CONTRIBUTING.md              round workflow, commit rules, how to run checks
CHANGELOG.md                 newest first, "why" for every entry
decisions/README.md          decision record template (context, decision, consequences, platform)
.github/workflows/ci.yml     ruff, mypy, pytest, fact check on examples (later)
.pre-commit-config.yaml      ruff, end-of-file, trailing whitespace, YAML duplicate-key check
src/factmodel/__init__.py
tests/test_smoke.py
```

**Tasks.** Create the tree; `uv sync` works; CI runs on push; choose the license (record as D-001).

**Acceptance.** `uv run pytest` and `uv run ruff check` pass locally and in CI.

### WP0.2 Core vocabulary and identifiers (1 round, with WP0.3)

**Goal.** Fix names and IDs before any schema exists.

**Decisions to write down (`spec/VOCABULARY.md`):**

- File kinds: `source`, `entity`, `service`, `tenants`, `evidence`, `finding`, `escalation`, `hazard`, `decision`, `profile`, `layer`, `consumer`, `release-allowlist`, `probe`, `probe-result`, `trigger`, `model-config`.
- IDs: lowercase slugs, `[a-z0-9][a-z0-9_-]{0,63}`; entity IDs keep the platform's table name in a separate `physical_name`.
- Relationship identity: a `key` the author sets, unique within its source entity; full reference `<entity-id>.<relationship-key>` (D-002). Positions move, so a position is never an identity.
- Register IDs: `F-0001`, `E-0001`, `H-0001`, `D-0001`; never reused, never deleted.
- Evidence status: `confirmed | inferred | unresolved | retracted`.
- Entity class: `data | configuration | administrative | reference`.
- Subject scope: `direct | transitive | none`, derived (D-007); scope basis on a relationship's `scope_admission`: `unique_target | current_row_rule | measured_fanout`.
- Relationship mechanism: `declared_fk | inferred_join | derivation | representation`.
- Cardinality: `one_to_one | many_to_one | one_to_many | many_to_many | unknown`.
- Source access mode: `agent_read | owner_read | export_file`; source kinds: `git | warehouse | api | document | ticket | person`.
- Pin formats per source kind: git `<repo>@<sha>:<path>[:<line>]`; warehouse `<engine>:<project>.<dataset>@<date>`; api `<host><path>@<date>`; document `<title>@<version or date>`; ticket `<system>:<key>@<date>`; person `<role>@<date>` (never a name).
- Entity and layer status (`review_status`, D-009): `draft | reviewed | deprecated`.
- Field path: dotted path for nested fields (`processing.request_id`); `repeated: true` for arrays.
- Relationship `meaning` (free text) and optional `discriminator` (the field that selects the target in a target set).
- Service kind: `pipeline | scheduled_job | application | manual`.
- Tenant facts on two axes: `ingest` (from configuration: which streams or objects the loader accepts) and `presence` (measured: which objects hold rows), per environment. They are never merged into one value.
- Evidence from probes carries `probe`, `environment` and `data_quality: representative | synthetic | unknown` (D-006).
- A retraction names its error: `retracted` status requires `named_error` (one sentence) and `superseded_by`.

**Acceptance.** Vocabulary reviewed by the owner; every term used in the spec appears here once.

### WP0.3 JSON Schemas for every file kind (1-2 rounds)

**Goal.** One schema per file kind, plus valid and invalid fixtures.

**Deliverables.** `schemas/<kind>.schema.json` for every kind in WP0.2; `tests/fixtures/schemas/<kind>/valid/*.yaml` and `invalid/*.yaml` (at least 3 invalid per kind, each failing for one named reason).

**Key shapes (normative examples to include in the spec):**

```yaml
# physical/entities/orders.yaml
kind: entity
id: orders
physical_name: sales.orders
grain: one row per order
class: data
status: draft
keys:
  primary: [order_id]
  current_row_rule: null
anchor_reference:            # makes orders direct; scope itself is derived (D-007)
  field: user_id
  evidence: [ev-orders-users-match]
evidence: [ev-orders-ddl]    # metadata evidence; fields without their own evidence inherit it
fields:
  - name: order_id
    type: INT64
    nullable: false
    meaning: Order identifier.
    evidence: [ev-orders-ddl]
  - name: user_id
    type: INT64
    nullable: true
    meaning: The customer who placed the order.
    evidence: [ev-orders-ddl]
relationships:
  - key: placed-by
    to: users
    join: orders.user_id = users.id
    meaning: The customer who placed the order.
    mechanism: inferred_join
    cardinality: many_to_one
    evidence: [ev-orders-users-match]
records:                     # inline evidence records; `evidence` keys hold IDs only
  - id: ev-orders-ddl
    source: bq-public
    pin: postgres:sales@2026-11-01
    quote: INFORMATION_SCHEMA.COLUMNS for orders
    status: confirmed
    read_on: 2026-11-01
  - id: ev-orders-users-match
    source: bq-public
    pin: postgres:sales@2026-11-02
    measurement: {match_rate: 1.0, orphans_left: 0}
    status: confirmed
    read_on: 2026-11-02
    probe: join-orders-users
    environment: prod
    data_quality: representative
```

```yaml
# profiles/retail/profile.yaml
kind: profile
id: retail
anchor_entity: users
labels: [customer_scoped, configuration, administrative, lineage, representation, unresolved]
rules:              # evaluated in order; first match wins
  - when: {evidence_status: unresolved}
    label: unresolved
  - when: {mechanism: derivation}
    label: lineage
  - when: {mechanism: representation}
    label: representation
  - when: {any_end_class: administrative}
    label: administrative
  - when: {any_end_class: configuration}
    label: configuration
  - when: {all_ends_match: [{class: data, subject_scoped: true}, {class: reference}], any_end_subject_scoped: true}
    label: customer_scoped
```

**Rules for schemas.**

- `additionalProperties: false` everywhere except `extensions:` (a free map for adopters, never read by the core).
- Derived keys (`label`, `subject_scope`, `subject_scoped`, `scope_basis`, `reachable`, `residue`, `withheld`) are forbidden in authored files; the schema rejects them.
- Every authored fact that can carry evidence has an `evidence` list with at least one ID, except when `status: unresolved` is explicit.
- A field without its own `evidence` inherits the entity's metadata evidence (the DDL or catalog snapshot). The example above shows per-field evidence only to make the shape visible; the fixture set must include the inherited form.
- Nested fields use `path`; the example set includes one STRUCT and one ARRAY field.

**Acceptance.** `pytest tests/schemas` validates every valid fixture and rejects every invalid one with the expected error path.

### WP0.4 Algorithms with test vectors (1 round)

**Goal.** The three algorithms the core runs, written precisely before code.

**Deliverables.** `spec/ALGORITHMS.md` and `tests/vectors/<algorithm>/<case>.yaml` (input model files + expected output).

1. **Projection.** Input: relationships, entity facts, profile. For each relationship: if it has a target set, project per target (rule 0) and keep the label if all agree, else `withheld`; otherwise apply ordered rules, first match wins; no match = residue. Output: label per relationship, residue list. Test vectors: at least one per rule, one per tie case, one residue case, one target-set agreement, one disagreement.
2. **Subject scope closure** (D-007). Direct: the entity has `anchor_reference`. Transitive: fixed point over relationships with mechanism in `{declared_fk, inferred_join}`, evidence confirmed or inferred-with-citation, target scoped, and a `scope_admission` with its basis (`unique_target`, `current_row_rule`, `measured_fanout`). Reference entities never propagate. Direct wins. Output: scope, via-path, basis per entity. Vectors: chain of three, cycle, reference blocking, missing basis rejected.
3. **Release partition.** Every file in the model repository gets exactly one disposition: `export`, `project` (allowlisted keys only), `refuse`. Undeclared key in a projected file = failure. Vectors: complete, residue file, undeclared key.

**Acceptance.** Owner review; vectors load against the schemas from WP0.3.

### WP0.5 Spec review and freeze of v0.1 (part of WP0.4 round)

Update `spec/SPEC.md` with links to the vocabulary, schemas and algorithms; record `spec-v0.1` in `CHANGELOG.md`. The owner creates the git tag.

---

## 6. M1 - Core, engine-neutral

Target (D-011): the core never names an engine; adapters are plugins behind one snapshot contract. `examples/chinook/` models the Chinook schema end to end on two local reference engines, SQLite and PostgreSQL, with synthetic rows generated at test time. Cloud engines are reached through the `export` and `sql` adapters by adopters with their own credentials (M2).

Expected model (to be confirmed by evidence, not assumed):

| Table | Class | Scope | Note |
| --- | --- | --- | --- |
| Customer | data | anchor | `anchor_entity: customer` in `factmodel.yaml` (D-012) |
| Invoice | data | direct | `CustomerId` |
| InvoiceLine | data | transitive | through Invoice; tests which basis wins |
| Employee | administrative | none | `SupportRepId` on Customer; `ReportsTo` self-reference |
| Artist, Album, Track, Genre, MediaType | reference | none | Track to Album to Artist is a reference chain |
| Playlist, PlaylistTrack | reference | none | PlaylistTrack bridges two reference entities |

### WP1.1 Model loader and strict YAML (1 round)

**Deliverables.** `src/factmodel/io/yaml_strict.py`, `src/factmodel/model/loader.py`, `src/factmodel/model/types.py` (pydantic).

**Tasks.**

- Load a model repository from `factmodel.yaml`: discover files by kind, validate each against its schema, build an in-memory `Model`.
- Fail on duplicate keys, unknown kinds, broken references (relationship to a missing entity, evidence ID not found, source not registered).
- Errors carry file, line, column and a short fix hint.

**Acceptance.** Loader tests cover every reference error; a parity test checks that every pydantic model accepts exactly what its JSON Schema accepts on the fixture set.

### WP1.2 Projection and scope library (1-2 rounds)

**Deliverables.** `src/factmodel/core/projection.py`, `src/factmodel/core/scope.py`, `src/factmodel/core/derived.py`.

**Tasks.** Implement WP0.4 algorithms 1 and 2 as pure functions over `Model` + `Profile`. Write derived values to `generated/` (`labels.tsv`, `scope.tsv`, `residue.tsv`) with the header line from `spec/VOCABULARY.md` section 6. `subject_scope`, its via-path and basis are computed here, never authored (D-007).

**Acceptance.** All test vectors pass; hypothesis tests: projection is deterministic, order of files does not change output, adding an unrelated entity does not change existing labels.

### WP1.3 Gate runner (1 round)

**Deliverables.** `src/factmodel/gate/runner.py`, `src/factmodel/gate/stages/*.py`, `src/factmodel/gate/gate.yaml` (the stage list the framework ships), `tests/fixtures/gate/<stage>/fail/`.

**Stages in M1:**

| Stage | Fails when |
| --- | --- |
| `yaml` | duplicate key, invalid YAML |
| `schema` | a file does not match its schema |
| `references` | any broken reference |
| `evidence` | an authored fact without evidence, unless explicitly unresolved |
| `derived-not-authored` | a derived key appears in an authored file |
| `projection` | residue > 0 |
| `scope` | a transitive admission without a basis; a consumer-declared entity unreachable without an owner decision |
| `layers` (M3, D-019) | a semantic layer breaks its contract: wrong current-row rule, unresolved or outside join, expression outside the layer, unlisted inherited hazard, missing companion, reviewed without an accepted equivalence run |
| `registers` | closed escalation without answer source and evidence; reused or missing register ID |
| `generated-fresh` | `generated/` differs from a fresh `fact project` |
| `privacy` | an evidence or probe-result file contains a value that looks like an email, a personal identifier or a row sample |

**Tasks.** Declarative stage list in `gate.yaml` (name, module, enabled); one verdict line per stage; exit code 0 only if all pass; `--stage` to run one.

**Acceptance.** Each stage has a fixture model that fails it and only it; the clean fixture passes all.

### WP1.4 CLI skeleton (1 round, can merge with WP1.3)

**Deliverables.** `src/factmodel/cli.py` with `fact init`, `fact source add`, `fact check`, `fact project`, `fact status`.

**Tasks.**

- `fact init --profile retail <dir>`: writes `factmodel.yaml`, folder layout, `AGENTS.md` and skills from `agent/` templates, an empty source registry.
- `fact init` also writes `.github/workflows/fact-check.yml` for the model repository (runs `fact check` on push) and a `CHANGELOG.md` with the format from the spec.
- `fact status`: open findings, open escalations, fired triggers without follow-up, evidence older than its source pin, next actions.

**Acceptance.** End-to-end test: `init` → add a source → `check` passes on the empty model.

### WP1.5 Adapter protocol, `export` and `sql` adapters (1-2 rounds)

**Deliverables.** `src/factmodel/adapters/base.py` (protocol), `src/factmodel/adapters/registry.py` (entry-point group `factmodel.adapters`), `src/factmodel/adapters/export/` (with flavours `bigquery`, `postgres`, `generic`), `src/factmodel/adapters/sql/`, `fact adapters`, `fact export-sql`, `fact snapshot`, `fact draft`.

**Adapter protocol.**

```python
class Adapter(Protocol):
    name: str                                            # adapter id, for example "sql"
    def engines(self) -> list[str]: ...                  # engines it can read, or ["*"]
    def snapshot(self, source: Source, model_root: Path) -> Snapshot: ...
    def default_dialect(self, engine: str) -> str: ...   # sqlglot dialect name
```

**Tasks.**

- `to_facts(snapshot)` is one core function, not an adapter method: declared constraints become `declared_fk` relationships, `confirmed` when the engine enforces them and `inferred` otherwise; nothing else is guessed.
- `export` reads owner-exported standard `INFORMATION_SCHEMA` views (CSV or JSON); `fact export-sql` prints the SQL the owner runs ("agents read, people run").
- `sql` reflects any engine with a SQLAlchemy dialect; the connection string comes from the environment variable the source names in `dsn_env`, never from a file.
- Engine knowledge (default dialect, which engines enforce foreign keys) lives in the vocabulary, not in code.

**Acceptance.** `export` tests on committed synthetic exports for every flavour; `sql` tests on SQLite in memory; a PostgreSQL test behind `FACT_PG_DSN` that agrees with SQLite on the neutral parts; registry test with a fake third-party entry point.

### WP1.5b Git source adapter (1 round)

**Deliverables.** `src/factmodel/adapters/git/`.

**Tasks.**

- Read files from a repository at a commit: DDL (`CREATE TABLE`, parsed with sqlglot into the same snapshot format as a warehouse read), and any text file as a quotable source for evidence (configuration, schema definitions, pipeline code).
- Pins are `<repo>@<sha>:<path>[:<line>]`; `fact snapshot` for a git source stores the parsed DDL plus the file list with hashes, never the whole repository.
- Rank: a git source normally outranks a warehouse catalog for intent (what was meant) and loses to it for presence (what exists). The profile or `factmodel.yaml` sets ranks; the adapter only reports them.

**Acceptance.** Tests on a small fixture repository (created in the test) with two DDL dialects; a DDL and a catalog snapshot of the same table produce matching entity drafts.

### WP1.6 Sync, drift and triggers (1 round)

**Deliverables.** `src/factmodel/sync/`, `fact sync`, `generated/drift-<source-id>.md` (one report per source, so syncing one source never overwrites another's), triggers as `kind: trigger` files in `maintenance/` (one per trigger, like register entries), gate stage `triggers` (a fired trigger has no follow-up entry).

`fact sync` stays offline: it reads the latest committed snapshot; taking a new one is `fact snapshot`.

**Tasks.** Compare adapter facts with the model: new table, dropped table, new column, dropped column, type change, nullability change, constraint change. Classify each as new fact / changed fact / lost fact / no effect. Write drafts for new facts into `drafts/` (never straight into `physical/`). Lost facts open findings.

**Acceptance.** Golden tests with two snapshots that differ in every way listed; a trigger fixture that fires and fails the gate until a follow-up is recorded.

### WP1.7 Probe generator v1 and intake (1-2 rounds)

**Deliverables.** `src/factmodel/probes/` (`spec.py`, `generate.py`, `intake.py`), `fact probe generate`, `fact probe intake`.

**Probe kinds in M1:** key duplicates, join match rate and orphans (both directions), fan-out per source row, null rate per field, row count per object, ties after a current-row rule, count of distinct values (never the values).

**Tasks.**

- Each probe has a stable ID, the fact it tests, expected range, and a neutral sqlglot AST rendered per dialect with quoted identifiers; a construct a dialect lacks is marked `unsupported_on_dialect`, never rendered wrong.
- `fact probe run --source <id>` executes through the `sql` adapter when the source has a `dsn_env` (counts only); a local engine with synthetic rows is a test fixture.
- Output is a shell script per run: `set -uo pipefail`, defaults via `${PROJECT:-...}`, each query prints `QUERY FAILED` and continues on error, results saved as JSON with a pin. No identifiers or values are ever selected; only counts and rates.
- Intake reads results, writes `evidence/probes/<probe-id>@<date>.yaml`, updates fact status (inferred → confirmed when in range), opens a finding when out of range, strips anything that looks like an email or personal identifier.

**Acceptance.** Rendering snapshots per kind for `bigquery`, `postgres`, `sqlite`, `snowflake`, `duckdb`, `tsql`, `mysql`; execution on SQLite for every kind and on PostgreSQL behind `FACT_PG_DSN`; intake tests with in-range, out-of-range and malformed results.

### WP1.8 Retail profile and the Chinook example (1-2 rounds)

**Deliverables.** `profiles/retail/`, `examples/chinook/` (full model repository with sources `chinook-sqlite`, `chinook-pg`, `chinook-ddl`), the Chinook DDL for SQLite and PostgreSQL, a deterministic synthetic seed, probes, and probe results from SQLite committed as evidence; a CI job with a `postgres:16` service.

**Tasks.**

1. Agent: snapshot metadata (SQLite catalog and DDL), draft entities.
2. Agent: classify every table with evidence; write relationships; generate probes.
3. Agent: run probes on the local SQLite engine (a test fixture, D-011); CI runs the same probes on PostgreSQL and compares counts.
4. Agent: intake; resolve residue; record decisions.

**Acceptance (M1 gate).** `fact check` green on `examples/chinook`; projection residue 0; scopes match the table above or differ with a decision record; every relationship confirmed by a probe or explicitly inferred with a reason; the PostgreSQL job green in CI.

### WP1.8b Hard-case fixtures (1 round)

**Goal.** Public datasets are too clean. These synthetic models exercise what the framework exists for.

**Deliverables.** `tests/fixtures/hard-cases/<case>/` - each a tiny model repository with an expected-output file.

| Case | What it contains | Expected |
| --- | --- | --- |
| soft-delete | an entity with `deleted` flag and a current-row rule | rule required for transitive admission; probe for ties generated |
| key-not-unique | a target whose key repeats per owner | `cardinality: many_to_many`; transitive admission only with `current_row_rule` or `measured_fanout` |
| polymorphic | a relationship with a discriminator and three targets | per-target projection; `withheld` when labels disagree |
| per-tenant-target | one relationship, two targets, choice by tenant | rule 0 agreement case and disagreement case |
| nullable-fk | optional reference to the anchor | scope `direct` with coverage note; probe for null rate |
| reference-chain | data -> reference -> data | reference never propagates scope |
| nested-field | STRUCT and ARRAY fields with a reference inside | field path resolves; join on a nested path renders per dialect |
| stale-evidence | evidence pin older than the source | `fact status` flags it; gate passes (staleness is not an error) |
| retraction | a fact retracted with `named_error` | registers stage accepts; a retraction without the error fails |

**Acceptance.** `fact check` and `fact project` run on every case in CI with the expected output; every gate stage has at least one hard case that fails it.

**Done in round 7 (gate and projection parts).** Cases live in `tests/fixtures/hard-cases/`, with variants that fail a stage (for example `soft-delete-without-rule`, `key-not-unique-unique-basis`). `key-not-unique` added the admission rejection `non_unique_target`, and `nested-field` lets `anchor_reference` name a nested path. Deferred to WP1.7: the probe for ties (`soft-delete`), the null-rate probe (`nullable-fk`) and rendering a nested-path join per dialect (`nested-field`).

### WP1.9 Agent layer v1 (1 round)

**Deliverables.** `agent/AGENTS.md` (template), `agent/skills/{model-onboard,entity-scaffold,evidence-gather,probe-write,probe-intake}/SKILL.md`, `agent/templates/brief.md`, `agent/templates/report.md`.

**Content rules.**

- `AGENTS.md`: invariants only (evidence rules, derived-never-authored, stop conditions, never commit, report shape with confirmed / inferred / unknown).
- Each skill: when to use it, inputs, steps, which `fact` commands to run, acceptance checks, what to put in the report.
- Report template ends with the exact `git add` list by name.

**Acceptance.** Following only the skill text, an agent reproduces WP1.8 steps 1 and 2 for `examples/chinook` and gets the committed drafts. Record the result in `docs/dogfood/`. A fresh-session run stays with the owner.

---

## 7. M2 - Cloud engines by adopters and a second domain

Target: show that the universal adapters reach cloud engines without core changes, verified by adopters on their own projects (the repository holds no cloud credentials, D-011), and that a second domain fits the core.

### WP2.1 Cloud engines through `export` and `sql` (1-2 rounds)

**Tasks.** An adopter runs the `export` path (`fact export-sql`, then `fact snapshot --from-export`) and the `sql` path on BigQuery with their own project and reports back; differences become findings or decision records naming the platform. Write a guide for packaging a third-party adapter as an entry point in `factmodel.adapters`.

**Deliverables (round 15).** `docs/adopters/bigquery.md` (the `export` path, then the `sql` path through `sqlalchemy-bigquery`); `docs/adapters/packaging.md` with the test package `tests/fixtures/plugin/` (`factmodel-csvdir`); DuckDB as a third local engine through `sql` (extra `[duckdb]`), its foreign-key enforcement measured by a test.

**Acceptance.** An adopter report for BigQuery with snapshots that validate: owner-pending (the adopter run is the owner's, outside the agent's runs). The packaging guide followed once by a test package: done in round 15.

### WP2.2 Second domain profile and example (1-2 rounds)

**Deliverables.** A second domain profile (or `retail` reused if it fits without change - the preferred outcome) and an example on a dataset chosen then.

Chosen (rounds 16 and 17): the BLS QCEW with NAICS, public domain. `retail` does not fit (QCEW has no subject), so `profiles/statistics/` was added, with D-015 to D-017. `examples/qcew/` runs on SQLite, PostgreSQL and DuckDB with a synthetic seed of its two data tables and the real BLS code lists (D-016).

**Acceptance.** `fact check` green; residue 0. For QCEW also: every entity scope `none`; nine findings with evidence; the same probe counts on the three engines.

### WP2.3 Core freeze review (1 round)

**Tasks.**

- List every core change made since M1 with its decision record.
- Bump schemas to `1.0.0`; write `spec/VERSIONING.md` (semver for schemas: removing or renaming a key is major; adding an optional key is minor; fixing a description is patch).
- Add `fact migrate` stub that reports which schema version a model uses.

Round 18: `spec/CORE-CHANGES-M2.md` (the ledger), `spec/VERSIONING.md` and `fact migrate` are done. The bump to 1.0.0 waited: the ledger found three contract changes without a decision record (snapshot pins, optional probe keys, field `values`), which the brief made a stop condition.

Round 19: D-018 records the three retroactively and sets the rule for what a change needs; the schemas froze at 1.0.0. **M2 done.**

**Acceptance (M2 gate).** No core change without a decision record naming the platform that forced it; both examples green on the frozen schemas.

---

## 8. M3 - Semantic layers, equivalence, release, export

### WP3.1 Semantic layer contract (1 round)

**Deliverables.** `schemas/layer.schema.json`, `schemas/consumer.schema.json`, spec section.

**Shape.** A layer has: id, purpose, consumer id, concepts (named filters over physical fields with a value vocabulary), measures (aggregations with grain and time column), joins (references to physical relationship keys only, never free SQL), hazards it inherits, status from `review_status` (`draft | reviewed | deprecated`, D-009).

**Rule.** A layer can only reference physical facts by ID. The gate fails on a join or field not in the physical layer.

Round 20 (D-019): the v1 shape is in `spec/VOCABULARY.md` section 9 (entities with current-row rules and default filters, concepts in three forms, measures with expression, grain, time, formula source, hazards and suppressed handling; consumer `interface`); the gate stage `layers`; schemas 2.0.0.

### WP3.2 Equivalence harness (1-2 rounds)

**Deliverables.** `src/factmodel/equivalence/`, corpus format `corpus/*.yaml`, `fact equivalence run`.

**Design.**

- Corpus item: id, request (consumer input), reference (the platform's own answer: SQL or result file), comparison mode.
- Privacy: corpus items in the repository are synthetic or redacted. A real corpus stays outside the repository and is referenced by pin; the harness reads it from a path the owner gives at run time.
- Comparison modes: `same_rows` (result sets equal), `same_count`, `same_predicate` (normalised SQL AST equal via sqlglot).
- Runner calls the consumer through a small interface (`compile(request) -> sql`), executes both sides offline (DuckDB on fixture data) or prints a probe script for the owner (live).
- Report: counts per mode and per outcome; any drop vs the last accepted run blocks release.

**Acceptance.** Harness tests with a toy consumer that is right, wrong and partially right.

Round 21: `src/factmodel/equivalence/` (corpus, compare, harness), `fact equivalence run|accept|script`; tables are named by entity id in consumer and reference SQL and bound to physical names by the harness; executed offline on SQLite and DuckDB; outcomes and counts only.

Round 22: layers `employment-wages` (QCEW) and `customer-purchases` (Chinook) at `status: draft`; probe kind `rollup` (D-020), declared on layer measures; the QCEW seed generated bottom-up.

### WP3.3 Reference consumer for the Chinook example (1-2 rounds)

**Goal.** Prove the loop end to end with a real consumer.

**Deliverables.** `examples/chinook/consumers/filter-sql/`: a small generator that turns a filter request ("customers who bought tracks of genre X in the last 90 days") into SQL using only the semantic layer; a corpus of at least 30 requests with hand-written reference SQL.

**Acceptance (M3 gate).** Equivalence at or above the threshold chosen in the open question (record it as a decision); every failure explained as a finding.

Round 23 (D-021): reference consumers `examples/qcew/consumers/measure-sql/` and `examples/chinook/consumers/filter-sql/`; corpora of 38 and 31 items; both layers proven on SQLite and DuckDB and `reviewed`; the owner's accept simulated once.

### WP3.4 Release projection and model-lookup skill (1 round)

**Deliverables.** `release/allowlist.yaml` format, `fact release --out`, `agent/skills/model-lookup/`, `agent/skills/release/`.

**Tasks.** Complete partition (export / project / refuse); per-kind key allowlist; fail-closed on undeclared keys; internal notes marked with explicit markers; release notes are an append-only log, one section per version, never edited. The release carries a `VERSION` file with the release version, the source commit and the schema version, so consumers can pin.

**Acceptance.** Tests for partition residue, undeclared key, marker stripping; release of `examples/chinook` reads cleanly with no derived-key leaks.

Round 24: `src/factmodel/release/` (`fact release`, `fact check --release`), `fact lookup`, skills `model-lookup` and `release`; allowlists for both examples; both release into `release/out/` (gitignored) in tests.

### WP3.5 Exporters (1-2 rounds)

**Deliverables.** `src/factmodel/export/osi.py`, `src/factmodel/export/dbt.py`; Cube optional.

**Tasks.** Check the current OSI / Apache Ossie spec version at start and pin it in the exporter. Map layer concepts and measures; carry evidence status as metadata where the target allows, otherwise drop with a warning list.

**Acceptance.** Exported files validate against the target's published schema or loader; round-trip notes list what cannot be expressed.

Round 25: `src/factmodel/export/{dbt,ossie}.py`, `fact export`; dbt-core 1.12.6 validates the dbt export with `dbt parse`; the Ossie page was read once (no version stated) and the export keeps to the structure it shows (`docs/exporters/round-trip-notes.md`). Round 28 read the core specification once and pinned the export to 0.2.0.dev0. Round 29 read the released 0.1.1 once and made it the default; 0.2.0.dev0 stays behind `--spec-version`.

### WP3.6 Drift-review, layer-build, escalation skills (1 round)

**Deliverables.** `agent/skills/{drift-review,layer-build,escalation-draft,maintenance-pack}/`; `fact probe generate --set volatile` for the maintenance pack.


Round 25: skills `drift-review`, `layer-build`, `escalation-draft`, `maintenance-pack`; vocabulary block `volatile_probe_kind` and `fact probe generate --set volatile`. **M3 done** (the owner-run live comparison and a real corpus are M4's pilot).
---

## 9. M4 - Release 1.0

Round 26 (WP4.1): `uv build` gives wheel and sdist (`twine check` passes); a clean-room test installs the wheel alone outside the repository and runs the Chinook loop; the M3 answers (layer join tables, value tables, dbt derived metrics, committed release notes, a migration registry slot).

**Status: kit done, pilot pending.** Rounds 26 to 28 built the kit; the M4 gate waits on the owner's pilot on real QCEW data and the release round after it.

Round 27 (WP4.2): the documentation site (MkDocs Material), assembled from the repository by `docs/_site/hooks.py`: spec, decisions on one page, guides, one page per skill, a CLI reference generated from the Typer app, a schema reference generated from the JSON Schemas, a quickstart (tested) and a FAQ; `mkdocs build --strict` in CI; `pages.yml` deploys on push to `main` once the owner enables GitHub Pages.

Round 28 (WP4.3): the Chinook tutorial (`docs/tutorial/chinook.md`), from an empty folder to a release and two exports, tested on the installed wheel alone; the pilot kit (`docs/pilot/qcew-real-data.md`) for the owner's run on the real QCEW files, dry-run on the seed in per-year tables; the Ossie export pinned to the core specification 0.2.0.dev0.

### WP4.1 Packaging (1 round)

Re-check the name (D-010); publish `factmodel` with extras `[sql]`, `[postgres]` and further drivers; `fact --version` shows package and schema versions.

### WP4.2 Documentation site and tutorial (1-2 rounds)

MkDocs Material site from `docs/`: concepts, quickstart, "model a platform in a day" tutorial on Chinook, CLI reference (generated from Typer), schema reference (generated from JSON Schema), skills reference, FAQ.

### WP4.3 External pilot (1 round, mostly waiting)

One person outside the project sets up a model of a platform of their choice using only the docs. Their notes become issues; blocking issues are fixed before 1.0.

**Acceptance (M4 gate).** Pilot succeeds; CI green; release notes for 1.0.0.

---

## 10. Testing strategy

| Layer | Kind of test | Where |
| --- | --- | --- |
| Schemas | valid/invalid fixtures per kind | `tests/schemas/` |
| Loader | reference errors, line/column reporting | `tests/model/` |
| Projection and scope | test vectors, property tests | `tests/core/` |
| Gate | one failing fixture per stage, one clean fixture | `tests/gate/` |
| Adapters | offline snapshots; live tests behind env flags | `tests/adapters/` |
| Probes | SQL snapshot per kind and dialect; intake cases | `tests/probes/` |
| CLI | end-to-end in a temp directory | `tests/cli/` |
| Examples | `fact check` on every example in CI | CI job |
| Equivalence | toy consumer right / wrong / partial | `tests/equivalence/` |

Coverage target for `src/factmodel/core` and `gate`: 90 % lines. Adapters and CLI: 70 %.

## 11. Working with agents on this repository

- **Brief template** (`agent/templates/brief.md`): context, decisions already made, work items with deliverables, acceptance checks, stop conditions, out of scope, report shape.
- **Report template**: outcome, files changed, checks run with results, confirmed / inferred / unknown, divergences from the brief, questions for the next round, exact `git add` list.
- **Round rhythm:** brief → agent works → report → agent commits → owner reviews and pushes → next brief. One work package per round; two only when they are small and share files.
- **Dogfooding:** from M1 onward the repository's own `AGENTS.md` follows the template it ships. A rule that is awkward for us is awkward for users.

## 12. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Core shaped by one platform | Second platform needs breaking changes | Freeze only after M2; decision records for every core change |
| Public datasets too clean | Hazards, current-row rules and target sets never tested | WP1.8b hard-case fixtures, one per gate stage at least |
| Agents drift from rules | Authored derived values, missing evidence | The gate enforces rules; skills only describe them |
| Scope creep into a semantic-layer runtime | Competes with dbt/Cube | Non-goal in spec; exporters instead |
| Name conflict | Rename after publishing | Name check before M1 (WP0.1 open item) |
| OSI spec changes | Exporter breaks | Pin spec version; exporter is a plugin |
| One-person project | Slow reviews | Small rounds; owner reviews reports, not diffs |

## 13. Open decisions mapped to work packages

| Decision | Needed by |
| --- | --- |
| License: Apache 2.0 (D-001); MIT possible before the first public push | WP0.1 |
| Name: FactModel, package `factmodel`, command `fact` (D-010); GitHub and trademark check still open | WP0.1 |
| Relationship identity: key only (D-002) | WP0.2 |
| Fact format: YAML only, or YAML plus generated graph (JSON-LD) | WP0.3 |
| Second domain dataset (chosen in M2: QCEW) | WP2.2 |
| Equivalence threshold: global or per layer | WP3.2 |
| Export priority: OSI first or dbt first | WP3.5 |

## 14. First three briefs

1. **WP0.1 + WP0.2:** bootstrap the repository, write `spec/VOCABULARY.md`, record D-001 (license).
2. **WP0.3:** JSON Schemas for all file kinds with valid and invalid fixtures.
3. **WP0.4 + WP0.5:** algorithms with test vectors; update and tag the spec `spec-v0.1`.

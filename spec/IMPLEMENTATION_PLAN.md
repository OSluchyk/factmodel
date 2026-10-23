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
3. **No data in the repository.** Test fixtures are synthetic or exported metadata from public datasets. Probe outputs are counts only.
4. **Deterministic core.** The core package does no network or database I/O. Adapters do I/O and write files; the core reads files.
5. **Schemas are normative.** JSON Schema files in `schemas/` define every file kind. Python models are checked against them in tests, never the other way round.
6. **Every gate stage has a failing fixture.** A check that has never failed is not trusted.
7. **Agents never push or run queries against real platforms.** The owner does. On this repository the agent commits once per round (D-008).
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
| BigQuery access | google-cloud-bigquery (optional extra) | Only in the adapter, only in live mode |
| PostgreSQL access | psycopg 3 (optional extra) | Only in the adapter, only in live mode |
| Tests | pytest, hypothesis for projection rules | Unit, golden-file, property tests |
| Quality | ruff (lint and format), mypy (strict on core) | Same rules for agents and people |
| CI | GitHub Actions | Lint, types, tests, gate on every example model |
| Docs | Markdown in repo; MkDocs Material from M4 | No site until there is something to publish |
| License | Apache 2.0 (D-001) | Public repository; explicit patent grant |

## 4. Milestone overview

| Milestone | Outcome | Gate to pass | Rounds (rough) |
| --- | --- | --- | --- |
| M0 - Specification | Repository bootstrapped; every file kind specified with JSON Schema and worked examples; algorithms written as pseudo-code with test vectors | Spec review; schema test suite green | 3-4 |
| M1 - Core on BigQuery | Core package, gate, CLI, BigQuery and git adapters, probe generator v1, hard-case fixtures, retail profile, `examples/thelook` | Gate green on `examples/thelook` and on every hard-case fixture; expected scopes hold; residue 0 | 10-12 |
| M2 - Second engine | PostgreSQL adapter, second domain profile, `examples/pagila`; core frozen at schema 1.0.0 | No core change, or each change has a decision record | 4-5 |
| M3 - Semantic layers | Layer contract, consumer equivalence harness, reference consumer, exports (OSI, dbt), release projection | One consumer meets its threshold on a corpus | 6-8 |
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
physical_name: thelook_ecommerce.orders
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
    pin: bigquery:bigquery-public-data.thelook_ecommerce@2026-11-01
    quote: INFORMATION_SCHEMA.COLUMNS for orders
    status: confirmed
    read_on: 2026-11-01
  - id: ev-orders-users-match
    source: bq-public
    pin: bigquery:bigquery-public-data.thelook_ecommerce@2026-11-02
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

## 6. M1 - Core on BigQuery

Target: `examples/thelook/` models the public dataset `bigquery-public-data.thelook_ecommerce` end to end. Verify the dataset exists and list its tables before WP1.6.

Expected model (to be confirmed by evidence, not assumed):

| Table | Class | Scope | Note |
| --- | --- | --- | --- |
| users | data | anchor | |
| orders | data | direct | `user_id` |
| order_items | data | direct or transitive | carries `user_id` and `order_id`; tests which basis wins |
| events | data | direct, partial coverage | `user_id` nullable (anonymous sessions) |
| products | reference | none | never propagates scope |
| distribution_centers | reference | none | |
| inventory_items | data | none | stock, not about a customer |

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

### WP1.5 BigQuery adapter (1-2 rounds)

**Deliverables.** `src/factmodel/adapters/base.py` (adapter protocol), `src/factmodel/adapters/bigquery/`.

**Adapter protocol.**

```python
class Adapter(Protocol):
    engine: str
    def snapshot(self, target: str) -> MetadataSnapshot: ...      # live read
    def load_snapshot(self, path: Path) -> MetadataSnapshot: ...   # offline, from exported JSON
    def to_facts(self, snap: MetadataSnapshot) -> list[FactDraft]: ...
    def dialect(self) -> str: ...                                  # sqlglot dialect name
```

**Tasks.**

- Live mode reads `INFORMATION_SCHEMA.TABLES`, `COLUMNS`, `COLUMN_FIELD_PATHS`, `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `TABLE_OPTIONS` (partitioning, clustering).
- Offline mode reads the same as exported JSON; `fact snapshot --source <id>` writes that export to `sources/snapshots/` so tests and agents never need credentials. The snapshot format is engine-neutral and has its own schema (`schemas/snapshot.schema.json`): objects, fields with paths and types, declared constraints, partitioning, options.
- `to_facts` produces drafts with evidence pins; declared keys become `declared_fk`; nothing else is guessed.
- Note in docs: BigQuery constraints are `NOT ENFORCED`; a declared key needs a probe before it is `confirmed`.

**Acceptance.** Offline tests on a committed metadata snapshot of `thelook_ecommerce` (metadata only, no rows); live test behind `FACT_LIVE_BQ=1`.

### WP1.5b Git source adapter (1 round)

**Deliverables.** `src/factmodel/adapters/git/`.

**Tasks.**

- Read files from a repository at a commit: DDL (`CREATE TABLE`, parsed with sqlglot into the same snapshot format as a warehouse read), and any text file as a quotable source for evidence (configuration, schema definitions, pipeline code).
- Pins are `<repo>@<sha>:<path>[:<line>]`; `fact snapshot` for a git source stores the parsed DDL plus the file list with hashes, never the whole repository.
- Rank: a git source normally outranks a warehouse catalog for intent (what was meant) and loses to it for presence (what exists). The profile or `factmodel.yaml` sets ranks; the adapter only reports them.

**Acceptance.** Tests on a small fixture repository (created in the test) with two DDL dialects; a DDL and a catalog snapshot of the same table produce matching entity drafts.

### WP1.6 Sync, drift and triggers (1 round)

**Deliverables.** `src/factmodel/sync/`, `fact sync`, `generated/drift.md`, `maintenance/triggers.yaml` format, gate stage `triggers` (a fired trigger has no follow-up entry).

**Tasks.** Compare adapter facts with the model: new table, dropped table, new column, dropped column, type change, nullability change, constraint change. Classify each as new fact / changed fact / lost fact / no effect. Write drafts for new facts into `drafts/` (never straight into `physical/`). Lost facts open findings.

**Acceptance.** Golden tests with two snapshots that differ in every way listed; a trigger fixture that fires and fails the gate until a follow-up is recorded.

### WP1.7 Probe generator v1 and intake (1-2 rounds)

**Deliverables.** `src/factmodel/probes/` (`spec.py`, `generate.py`, `intake.py`), `fact probe generate`, `fact probe intake`.

**Probe kinds in M1:** key duplicates, join match rate and orphans (both directions), fan-out per source row to anchor, null rate per field, row count per object.

**Tasks.**

- Each probe has a stable ID, the fact it tests, expected range, and SQL built with sqlglot and rendered in the adapter dialect.
- Output is a shell script per run: `set -uo pipefail`, defaults via `${PROJECT:-...}`, each query prints `QUERY FAILED` and continues on error, results saved as JSON with a pin. No identifiers or values are ever selected; only counts and rates.
- Intake reads results, writes `evidence/probes/<probe-id>@<date>.yaml`, updates fact status (inferred → confirmed when in range), opens a finding when out of range, strips anything that looks like an email or personal identifier.

**Acceptance.** Snapshot tests of generated SQL per probe kind; intake tests with in-range, out-of-range and malformed results.

### WP1.8 Retail profile and the thelook example (2 rounds)

**Deliverables.** `profiles/retail/`, `examples/thelook/` (full model repository), `examples/thelook/probes/` (generated), owner-run probe results committed as evidence.

**Tasks.**

1. Agent: snapshot metadata (owner exports if needed), run sync, draft entities.
2. Agent: classify every table with evidence; write relationships; write probe scripts.
3. Owner: run probes on the public dataset, return output.
4. Agent: intake; resolve residue; record decisions.

**Acceptance (M1 gate).** `fact check` green on `examples/thelook`; projection residue 0; scopes match the table above or differ with a decision record; every relationship confirmed by a probe or explicitly inferred with a reason.

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

### WP1.9 Agent layer v1 (1 round)

**Deliverables.** `agent/AGENTS.md` (template), `agent/skills/{model-onboard,entity-scaffold,evidence-gather,probe-write,probe-intake}/SKILL.md`, `agent/templates/brief.md`, `agent/templates/report.md`.

**Content rules.**

- `AGENTS.md`: invariants only (evidence rules, derived-never-authored, stop conditions, never commit, report shape with confirmed / inferred / unknown).
- Each skill: when to use it, inputs, steps, which `fact` commands to run, acceptance checks, what to put in the report.
- Report template ends with the exact `git add` list by name.

**Acceptance.** A fresh agent session, given only the repository and the brief "onboard thelook", reproduces WP1.8 step 1-2 without extra instructions. Record the session transcript summary in `docs/dogfood/`.

---

## 7. M2 - Second engine and domain

Target: `examples/pagila/` on PostgreSQL. Pagila is the PostgreSQL port of the Sakila DVD-rental sample; check its license and availability before WP2.2. Fallback: Chinook.

Expected shape: anchor `customer`; direct `rental`, `payment`; reference `film`, `category`, `language`; configuration `store`, `staff`-related tables to be classified by evidence; unanchored `inventory`.

### WP2.1 PostgreSQL adapter (1-2 rounds)

**Tasks.** Read `information_schema.tables`, `columns`, `table_constraints`, `key_column_usage`, `referential_constraints`, plus `pg_catalog` for enforced foreign keys and indexes. Enforced FKs become `declared_fk` with `confirmed` status (enforced by the engine) - unlike BigQuery. Offline snapshot format identical to BigQuery's.

**Acceptance.** Offline tests on a committed Pagila metadata snapshot; live test behind `FACT_LIVE_PG=1` against a local Docker database (`docker compose` file in `examples/pagila/`).

### WP2.2 Second domain profile and the Pagila example (1-2 rounds)

**Deliverables.** `profiles/rental/` (or reuse `retail` if it fits without change - that is the preferred outcome), `examples/pagila/`.

**Acceptance.** `fact check` green; residue 0.

### WP2.3 Core freeze review (1 round)

**Tasks.**

- List every core change made since M1 with its decision record.
- Bump schemas to `1.0.0`; write `spec/VERSIONING.md` (semver for schemas: removing or renaming a key is major; adding an optional key is minor; fixing a description is patch).
- Add `fact migrate` stub that reports which schema version a model uses.

**Acceptance (M2 gate).** No core change without a decision record naming the platform that forced it; both examples green on the frozen schemas.

---

## 8. M3 - Semantic layers, equivalence, release, export

### WP3.1 Semantic layer contract (1 round)

**Deliverables.** `schemas/layer.schema.json`, `schemas/consumer.schema.json`, spec section.

**Shape.** A layer has: id, purpose, consumer id, concepts (named filters over physical fields with a value vocabulary), measures (aggregations with grain and time column), joins (references to physical relationship keys only, never free SQL), hazards it inherits, status from `review_status` (`draft | reviewed | deprecated`, D-009).

**Rule.** A layer can only reference physical facts by ID. The gate fails on a join or field not in the physical layer.

### WP3.2 Equivalence harness (1-2 rounds)

**Deliverables.** `src/factmodel/equivalence/`, corpus format `corpus/*.yaml`, `fact equivalence run`.

**Design.**

- Corpus item: id, request (consumer input), reference (the platform's own answer: SQL or result file), comparison mode.
- Privacy: corpus items in the repository are synthetic or redacted. A real corpus stays outside the repository and is referenced by pin; the harness reads it from a path the owner gives at run time.
- Comparison modes: `same_rows` (result sets equal), `same_count`, `same_predicate` (normalised SQL AST equal via sqlglot).
- Runner calls the consumer through a small interface (`compile(request) -> sql`), executes both sides offline (DuckDB on fixture data) or prints a probe script for the owner (live).
- Report: counts per mode and per outcome; any drop vs the last accepted run blocks release.

**Acceptance.** Harness tests with a toy consumer that is right, wrong and partially right.

### WP3.3 Reference consumer for thelook (1-2 rounds)

**Goal.** Prove the loop end to end with a real consumer.

**Deliverables.** `examples/thelook/consumers/filter-sql/`: a small generator that turns a filter request ("customers who ordered in category X in the last 90 days") into SQL using only the semantic layer; a corpus of at least 30 requests with hand-written reference SQL.

**Acceptance (M3 gate).** Equivalence at or above the threshold chosen in the open question (record it as a decision); every failure explained as a finding.

### WP3.4 Release projection and model-lookup skill (1 round)

**Deliverables.** `release/allowlist.yaml` format, `fact release --out`, `agent/skills/model-lookup/`, `agent/skills/release/`.

**Tasks.** Complete partition (export / project / refuse); per-kind key allowlist; fail-closed on undeclared keys; internal notes marked with explicit markers; release notes are an append-only log, one section per version, never edited. The release carries a `VERSION` file with the release version, the source commit and the schema version, so consumers can pin.

**Acceptance.** Tests for partition residue, undeclared key, marker stripping; release of `examples/thelook` reads cleanly with no derived-key leaks.

### WP3.5 Exporters (1-2 rounds)

**Deliverables.** `src/factmodel/export/osi.py`, `src/factmodel/export/dbt.py`; Cube optional.

**Tasks.** Check the current OSI / Apache Ossie spec version at start and pin it in the exporter. Map layer concepts and measures; carry evidence status as metadata where the target allows, otherwise drop with a warning list.

**Acceptance.** Exported files validate against the target's published schema or loader; round-trip notes list what cannot be expressed.

### WP3.6 Drift-review, layer-build, escalation skills (1 round)

**Deliverables.** `agent/skills/{drift-review,layer-build,escalation-draft,maintenance-pack}/`; `fact probe generate --set volatile` for the maintenance pack.

---

## 9. M4 - Release 1.0

### WP4.1 Packaging (1 round)

Re-check the name (D-010); publish `factmodel` with extras `[bigquery]`, `[postgres]`, `[duckdb]`; `fact --version` shows package and schema versions.

### WP4.2 Documentation site and tutorial (1-2 rounds)

MkDocs Material site from `docs/`: concepts, quickstart, "model a platform in a day" tutorial on thelook, CLI reference (generated from Typer), schema reference (generated from JSON Schema), skills reference, FAQ.

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
| Second domain dataset (Pagila or Chinook) | WP2.2 |
| Equivalence threshold: global or per layer | WP3.2 |
| Export priority: OSI first or dbt first | WP3.5 |

## 14. First three briefs

1. **WP0.1 + WP0.2:** bootstrap the repository, write `spec/VOCABULARY.md`, record D-001 (license).
2. **WP0.3:** JSON Schemas for all file kinds with valid and invalid fixtures.
3. **WP0.4 + WP0.5:** algorithms with test vectors; update and tag the spec `spec-v0.1`.

# FactModel - Vocabulary

Author: Oleksandr Sluchyk · Version 0.1 · 2026-10-23
Companion to `spec/SPEC.md`. Every term the schemas use is defined here once.

## How to read this file

- Each term has a one-sentence meaning, its allowed values when it is an enumeration, and one example.
- Every enumeration is also given as a fenced block that opens with `yaml vocabulary:<name>`. The code loads these blocks (`src/factmodel/vocabulary.py`), and later schemas import them, so the list here is the only source. Change a value here, and the code follows.
- All values are slugs (see Identifiers). Where the spec used two words for one thing, one is chosen and the other is listed under "Not used".
- Examples use a small shop schema (`users`, `orders`, `order_items`, `products`); the reference example of the framework is Chinook on SQLite and PostgreSQL (D-011).

## General terms

| Term | Meaning |
| --- | --- |
| platform | The data system being modelled: its engines, pipelines, configuration and documents together. |
| engine | One database or warehouse product that stores data on a platform, for example BigQuery or PostgreSQL. |
| model | The set of YAML and Markdown files in a model repository that describe one platform. |
| model repository | A git repository that holds one model (`<platform>-model/`). |
| core | The framework schemas and code; it holds no domain word. |
| owner | The person who approves decisions, runs probes, commits and publishes releases. |
| agent | An AI agent that gathers evidence, drafts model changes and probes, and reports. |
| authored | Written by a person or an agent, and therefore needing evidence. |
| derived | Computed by deterministic code from authored facts, and never authored (see Derived values). |
| gate | The set of checks run by `fact check`; one command, one verdict. |
| round | One unit of agent work: one brief in, one report out, the owner commits. |

Not used: "neutral core" as a name for the physical layer (the core is the framework; the physical layer is model content), "readable copy" (use release), "model owner" outside the users table (use owner).

## 1. File kinds

Every model file declares its kind in a top-level `kind:` key. One kind, one schema.

| Kind | Meaning | Lives in (model repository) |
| --- | --- | --- |
| `model-config` | The root file: framework version, profile, adapters, consumers. `framework_version` is the release that created or last migrated the model; the schema version is separate (`spec/VERSIONING.md`, `fact migrate`). | `factmodel.yaml` |
| `source` | One entry in the source registry. | `sources/` |
| `entity` | One table, view or object on the platform, with its fields and outgoing relationships. | `physical/entities/` |
| `service` | One process that reads or writes entities. | `physical/services/` |
| `tenants` | Tenants and environments, with ingest and presence per pair. | `physical/tenants.yaml` |
| `evidence` | A standalone evidence record (quotes, probe measurements) referenced by ID. | `evidence/` |
| `finding` | A register entry for a problem to fix. | `registers/` |
| `escalation` | A register entry for a question to people. | `registers/` |
| `hazard` | A register entry for permanent behaviour a reader must know. | `registers/` |
| `decision` | A register entry for why the model is the way it is. | `registers/` |
| `profile` | The domain layer: anchor entity, label vocabulary, ordered rules. | framework `profiles/<name>/` |
| `layer` | One semantic layer for one use case. | `semantic/<layer>/` |
| `consumer` | The agent, SQL generator or knowledge base that proves a layer. | `semantic/<layer>/` |
| `release-allowlist` | The per-kind key allowlist and file dispositions for a release. | `release/` |
| `probe` | One generated data check: the fact it tests, its expected range, its SQL. | `probes/` |
| `probe-result` | The counts a probe returned, with its pin; it becomes evidence. | `evidence/probes/` |
| `trigger` | An event and the follow-up it requires. | `maintenance/` |

Example: `kind: entity` at the top of `physical/entities/orders.yaml`.

```yaml vocabulary:file_kind
- model-config
- source
- entity
- service
- tenants
- evidence
- finding
- escalation
- hazard
- decision
- profile
- layer
- consumer
- release-allowlist
- probe
- probe-result
- trigger
```

## 2. Identifiers

**Slug.** Every authored ID is a slug: lowercase letters, digits, hyphen and underscore, starting with a letter or digit, at most 64 characters. Pattern: `^[a-z0-9][a-z0-9_-]{0,63}$`. Example: `order-items`.

**Entity `id` and `physical_name`.** The `id` is the slug the model uses everywhere; `physical_name` is the name the engine uses, kept exactly as the engine writes it. Example: `id: orders`, `physical_name: sales.orders`; for Chinook, `id: invoice_line`, `physical_name: InvoiceLine`.

**Relationship key.** A slug the author sets, unique within its source entity (D-002). The position of a relationship in a list is never its identity, because lists get reordered. Example: `key: placed-by`.

**Relationship reference.** The full reference is `<entity-id>.<relationship-key>`. Example: `orders.placed-by`.

**Register IDs.** Register entries use a prefix and a four-digit number: `F-0001` (finding), `E-0001` (escalation), `H-0001` (hazard), `D-0001` (decision). They are never reused and never deleted; a mistaken entry is closed or superseded, not removed. Example: `H-0003`.

Register IDs are not slugs (they use uppercase), so the slug rule does not apply to them. Model register IDs (`D-0001`) are distinct from the framework's own decision records (`D-001` in `decisions/`).

Not used: positional relationship identity such as `orders#1`.

## 3. Evidence

**Evidence** is the record that proves an authored fact. Every authored fact names at least one evidence ID, unless its status is explicitly `unresolved`.

| Field | Meaning | Example |
| --- | --- | --- |
| `id` | Slug, unique within the model. | `ev-orders-ddl` |
| `source` | ID of a registered source. | `bq-public` |
| `pin` | The exact version read, in the pin format of the source kind (see Sources). | `postgres:chinook@2026-10-23` |
| `quote` | A verbatim quote from the source, at most 40 words. | `INFORMATION_SCHEMA.COLUMNS for orders` |
| `measurement` | A map of counts or rates, never values or identifiers. | `{match_rate: 1.0, orphans_left: 0}` |
| `status` | See below. | `confirmed` |
| `read_on` | The date the source was read, `YYYY-MM-DD`. | `2026-11-01` |
| `probe` | For evidence from a probe only: the ID of the probe that produced it. | `join-orders-users` |
| `environment` | Required with `probe`: the environment the probe ran in. | `prod` |
| `data_quality` | Required with `probe`: what kind of data the probe ran on (see below). | `representative` |
| `named_error` | Required when `retracted`: one sentence on what was wrong. | `The join used users.email, which is not unique.` |
| `superseded_by` | Required when `retracted`: the ID of the record that replaces it. | `ev-orders-users-match-2` |

An evidence record has a `quote` or a `measurement`, not both.

**Where evidence lives.** Evidence records have one schema. A record sits inline in the file of the fact it proves (under the top-level key `records:`), or standalone in `evidence/` (file kind `evidence`, also under `records:`) when several files share it. Evidence IDs are unique across the whole model; the loader checks it. A fact points to records by ID with an `evidence:` list. The key `evidence` always holds IDs; the key `records` always holds evidence records.

**Probe evidence.** A `probe-result` file is the raw output of one probe run. Intake turns it into an evidence record that carries `probe: <probe-id>`, the warehouse source and pin, `environment` and `data_quality`.

### Evidence status

| Status | Meaning | Who may set it |
| --- | --- | --- |
| `confirmed` | The fact is proven by a source that can prove it. | An adapter reading engine metadata; a probe whose result on representative data is in its expected range (D-014); the owner, for evidence the owner read. |
| `inferred` | The fact is believed, with a cited reason, but not proven. | Anyone. Every agent-authored fact starts here. |
| `unresolved` | The fact is not known; the record says what is missing. | Anyone. A fact with this status needs no evidence ID. |
| `retracted` | The fact was wrong. The record stays, names the error and points to its replacement. | The owner, or an agent with owner approval in the round report. |

```yaml vocabulary:evidence_status
- confirmed
- inferred
- unresolved
- retracted
```

**Retraction.** A `retracted` record requires `named_error` (one sentence that says what was wrong) and `superseded_by` (the ID of the record that replaces it). Example: `named_error: The join used users.email, which is not unique.`, `superseded_by: ev-orders-users-match-2`.

**Data quality.** What kind of data a probe ran on (D-006). Only a result on `representative` data confirms a fact (D-014); a result on `synthetic` or `unknown` data is recorded as `inferred` evidence and cited, so the probe stays attached and the fact stays `inferred`. Superseded by D-014: "a zero-violation result carries over to production". A model whose platform is itself synthetic (an example or test model) may set `treat_synthetic_as_representative: true` in `factmodel.yaml`; intake then treats its results as representative.

| Value | Meaning |
| --- | --- |
| `representative` | Real data that stands for production use. |
| `synthetic` | Generated or seeded test data. |
| `unknown` | Not known; treated like `synthetic` for shares. |

```yaml vocabulary:data_quality
- representative
- synthetic
- unknown
```

**Inheritance.** A field without its own `evidence` inherits the entity's `evidence` (the metadata evidence: the DDL or catalog snapshot).

Not used: "date read" (use `read_on`), "probe output" for the stored result (use probe result).

## 4. Sources

A **source** is one place facts come from. The source registry records how to obtain access, never the secret.

### Source kinds

| Kind | Meaning | Pin format | Example pin |
| --- | --- | --- | --- |
| `git` | A git repository: DDL, configuration, pipeline code. | `<repo>@<sha>:<path>[:<line>]`; the sha is a commit, or the file's blob hash for a read of the working tree | `etl-config@3f2a9c1:loaders/orders.yaml:12` |
| `warehouse` | An engine's catalog or data, read through an adapter or a probe. | `<engine>:<target>@<YYYY-MM-DD>`, where the target is what was read (a database, a schema, `<project>.<dataset>`) | `postgres:chinook@2026-10-23`, `bigquery:my-project.sales@2026-10-23` |
| `api` | An HTTP API that describes or serves platform objects. | `<host><path>@<YYYY-MM-DD>` | `api.example.com/v2/objects@2026-11-01` |
| `document` | A vendor or internal document with a version or date. | `<title>@<version or YYYY-MM-DD>` | `Loader guide@4.2` |
| `ticket` | An issue or change ticket. | `<system>:<key>@<YYYY-MM-DD>` | `tracker:DATA-12@2026-11-01` |
| `person` | A verbal or written answer from a person, recorded by role. | `<role>@<YYYY-MM-DD>` | `data-platform-lead@2026-11-01` |

A person pin names a role, never a person's name.

```yaml vocabulary:source_kind
- git
- warehouse
- api
- document
- ticket
- person
```

### Access modes

| Mode | Meaning |
| --- | --- |
| `agent_read` | The agent reads the source directly with the access it is given. |
| `owner_read` | Only the owner reads the source; the agent works from what the owner quotes or measures. |
| `export_file` | The owner exports the source to a file (for example a metadata snapshot), and the agent reads the file. |

Example: a production warehouse is `owner_read`; its metadata snapshot in `sources/snapshots/` is read as `export_file`.

**Adapter and access fields.** A source that an adapter reads names it:

| Field | Meaning | Example |
| --- | --- | --- |
| `adapter` | The adapter that reads the source (an entry point in the group `factmodel.adapters`). | `sql` |
| `engine` | A free slug for the engine. Engines in `engine_dialect` below have a default SQL dialect. | `postgres` |
| `dialect` | The sqlglot dialect, required when the engine is not in `engine_dialect`. | `tsql` |
| `dsn_env` | The name of the environment variable that holds the connection string. The string itself is never written in a model file; the `privacy` gate stage fails on one. | `FACT_PG_DSN` |
| `location` | Where the source is: a schema or `<project>.<dataset>` for a warehouse, the repository path (absolute or relative to the model root) for git. | `../schema-repo` |
| `revision` | For git: the commit, branch or tag to read (default `HEAD`); `worktree` reads the files as they are. | `main` |
| `include` | For git: path globs of the DDL files to parse. | `[ddl/*.sql]` |

```yaml vocabulary-map:engine_dialect
bigquery: bigquery
postgres: postgres
sqlite: sqlite
mysql: mysql
mssql: tsql
snowflake: snowflake
databricks: databricks
duckdb: duckdb
trino: trino
redshift: redshift
oracle: oracle
```

**Engines that enforce foreign keys.** A declared foreign key read from one of these engines is `enforced: true` and its draft evidence is `confirmed`; from any other engine (SQLite by default, BigQuery, Snowflake, Databricks) it is `enforced: false` and `inferred` until a probe confirms it.

```yaml vocabulary:engine_enforces_foreign_keys
- postgres
- mysql
- mssql
- oracle
- duckdb
```

DuckDB is in the list because it was measured, not assumed: `tests/adapters/test_duckdb.py::test_duckdb_enforces_foreign_keys` inserts a row that violates a declared foreign key and the engine rejects it.

**Current pin.** A source may record `current_pin`, the version of the source as last read (`fact sync` will update it). Evidence from that source pinned to another version is stale: `fact status` lists it, and the gate does not fail on it.

```yaml vocabulary:access_mode
- agent_read
- owner_read
- export_file
```

### Rank

**Rank** is an integer; when two sources disagree, the lower rank wins. A model may set its own ranks in `factmodel.yaml`; these are the defaults.

| Kind | Default rank | Reason |
| --- | --- | --- |
| `git` | 10 | Configuration and DDL state what the platform is set up to do. |
| `warehouse` | 20 | The catalog and data state what exists, but not what was meant. |
| `api` | 30 | A live interface, but often a view over configuration. |
| `document` | 40 | Written intent that may lag the configuration. |
| `ticket` | 50 | A record of a change request, not of what shipped. |
| `person` | 60 | A verbal answer is the weakest form of evidence. |

Example: a loader configuration in git (rank 10) beats a vendor document (rank 40).

## 5. Physical layer

The **physical layer** describes what exists on the platform: entities, fields, relationships, services, tenants and environments.

### Entity class

What kind of rows an entity holds.

| Class | Meaning | Example |
| --- | --- | --- |
| `data` | Rows that record events or things the platform is about. | `orders` |
| `configuration` | Rows that control how the platform behaves. | a loader settings table |
| `administrative` | Rows about operating the platform: users of the tool, audit, jobs. | a job run log |
| `reference` | Shared lookup rows that are not about any one subject. | `products` |

```yaml vocabulary:entity_class
- data
- configuration
- administrative
- reference
```

### Review status

Entities and layers both carry `status` from this block (D-009).

| Status | Meaning |
| --- | --- |
| `draft` | Written, not yet reviewed by the owner. |
| `reviewed` | The owner reviewed it in a round report. |
| `deprecated` | Still on the platform, but no longer to be used; kept so references resolve. |

Example: `status: draft` on an entity an agent just scaffolded.

```yaml vocabulary:review_status
- draft
- reviewed
- deprecated
```

### Subject scope

The **anchor entity** is the entity whose rows are the subjects of the domain (customers, patients, accounts); the model binds it (D-012). A domain may have no subject (statistics, where every row is an aggregate): its profile names none, the model binds no anchor, every entity is `none`, and `anchor_reference` and `scope_admission` are errors (D-015). **Subject scope** says how an entity's rows reach the anchor. It is derived, never authored (D-007): `fact project` computes it from two authored facts and writes it to `generated/scope.tsv`.

- **`anchor_reference`** on an entity: `{field: <field name or nested path>, evidence: [...]}` when that field holds the anchor's key. It makes the entity `direct`. Example: `anchor_reference: {field: user_id, evidence: [ev-orders-users-match]}` on `orders`.
- **`scope_admission`** on a relationship: `{basis: <scope basis>, evidence: [...]}`. It lets scope pass from the target to the source entity. Example: `scope_admission: {basis: unique_target, evidence: [ev-orders-pk]}` on `order_items.part-of`.

| Scope | Meaning | Example |
| --- | --- | --- |
| `direct` | Each row references the anchor key itself (the entity has `anchor_reference`). The anchor entity is `direct` by definition. | `orders` (has `user_id`) |
| `transitive` | Each row reaches exactly one anchor through admitted relationships. | `order_items` through `orders` |
| `none` | Rows are not about a subject. | `products` |

```yaml vocabulary:subject_scope
- direct
- transitive
- none
```

### Scope basis

Why a relationship may carry scope, given in its `scope_admission`. Every `transitive` scope is reached through admitted relationships, and the computed basis is the basis of the first step. A `direct` scope has no basis; `anchor_reference` expresses it.

| Basis | Meaning |
| --- | --- |
| `unique_target` | Each step of the path joins to a unique key, so a row reaches at most one anchor. |
| `current_row_rule` | The target key repeats, and the target's current-row rule picks one row. |
| `measured_fanout` | A probe measured that no source row reaches more than one anchor. |

Example: `order_items` is `transitive` with basis `unique_target` (`order_id` is unique in `orders`).

```yaml vocabulary:scope_basis
- unique_target
- current_row_rule
- measured_fanout
```

### Relationship

A **relationship** is an authored link from one entity (the one whose file holds it) to a target.

| Attribute | Meaning | Example |
| --- | --- | --- |
| `key` | Slug, unique within the source entity (D-002). | `placed-by` |
| `to` | One target entity, or a **target set**: a list of at least two targets, chosen per row by a discriminator or per tenant. | `users` |
| `discriminator` | A field of the source. With a target set, it selects the target per row; without it, the target is chosen per tenant. With a single target, it names the source field the target's meaning depends on (QCEW: `agglvl_code` gives the level of `industry_code`). The loader checks that the field exists on the source. | `owner_type`, `agglvl_code` |
| `join` | The join condition, in `<entity>.<field> = <entity>.<field>` form (`AND` for composite keys), or a boolean SQL expression in sqlglot's neutral dialect whose columns are all `<entity>.<field>` of the source and the target (D-017); for a self-reference, the left operand of each top-level comparison is the source row. For a target set, a map from each target to its join. Required, except on an `unresolved` relationship, which may omit it when the join is not known. | `orders.user_id = users.id`; `substr(industry.industry_code, 1, 2) = sector.industry_code` |
| `meaning` | One sentence on what the link means. | `The customer who placed the order.` |
| `mechanism` | How the link exists (see below). | `inferred_join` |
| `cardinality` | Rows on each side (see below). | `many_to_one` |
| `scope_admission` | Optional: lets scope pass through this relationship (see Subject scope). | `{basis: unique_target, evidence: [ev-orders-pk]}` |
| `status` | Optional, only `unresolved`: the link is not known yet. Then `evidence` may be absent. | `unresolved` |
| `evidence` | Evidence IDs; required unless `status: unresolved`. | `[ev-orders-users-match]` |

**Mechanism.**

| Mechanism | Meaning |
| --- | --- |
| `declared_fk` | The engine or DDL declares a foreign key. Some engines do not enforce it; a probe confirms it. |
| `inferred_join` | No declaration; names, types or documents suggest the join, and a probe confirms it. |
| `derivation` | The target is computed from the source (lineage), not joined to it. |
| `representation` | The target is another representation of the same thing (a copy, an export, a view). |

```yaml vocabulary:mechanism
- declared_fk
- inferred_join
- derivation
- representation
```

**Cardinality.** Written from the source entity to the target: `many_to_one` means many source rows per target row.

```yaml vocabulary:cardinality
- one_to_one
- many_to_one
- one_to_many
- many_to_many
- unknown
```

Example: `orders.placed-by` is `many_to_one`.

Not used: "declared key" for a mechanism (use `declared_fk`; "declared key" means a primary or unique key the engine or DDL declares).

### Field

| Attribute | Meaning | Example |
| --- | --- | --- |
| `name` | The engine's column name. | `user_id` |
| `path` | Dotted path for a nested field; absent for a top-level field. | `processing.request_id` |
| `type` | The engine's type name. | `INT64` |
| `nullable` | Whether the engine allows null. | `true` |
| `repeated` | `true` for an array field. | `false` |
| `meaning` | One sentence on what the value means. | `The customer who placed the order.` |
| `values` | Optional declared value domain (codes or categories, never personal data); a `value_set` probe counts values outside it. | `[open, shipped, returned]` |
| `hazards` | Register IDs of hazards that apply to this field. | `[H-0002]` |
| `evidence` | Optional evidence IDs; without them the field inherits the entity's `evidence`. | `[ev-orders-ddl]` |

A nested field has both `name` (its last segment) and `path` (the full dotted path). Example: `name: request_id`, `path: processing.request_id`.

**Drafts.** `fact draft` writes engine-neutral drafts: relationship keys are `to-<target>`, and the engine's own constraint names are kept under `extensions.draft.constraint_name` (key to name). A comment or description the source declares (`COMMENT ON`, an inline column comment, a description option) becomes the proposed meaning, cited by an `inferred` record that quotes it: a comment is a claim, not proof.

### Entity keys

An entity file has `id`, `physical_name`, `grain`, `class`, `status`, `keys` (`primary`, optional `unique`, `current_row_rule`), optional `anchor_reference`, `fields`, `relationships`, `evidence` (the IDs of the metadata evidence - the DDL or catalog read - for the entity itself and for every field without its own evidence) and optional inline `records`.

Keys that hold a vocabulary kind are named after the block, because `kind` is the file kind: a source has `source_kind`, a service `service_kind`, a probe `probe_kind`.

### Grain and current-row rule

**Grain.** One sentence that says what one row is. Example: `one row per order`.

**Current-row rule.** A condition that picks the one current row per key when an entity keeps history, versions or soft-deleted rows. It is required when the key repeats (history, soft delete) and the entity is a target of a transitive admission or is read by a consumer. Every consumer applies it; a layer lists it so nothing is applied from memory. Example: `deleted_at IS NULL`. When the key does not repeat, the rule is `null`.

### Service

A **service** is a process that reads or writes entities, with when it runs. Services are authored by hand in 1.0, with evidence from code.

| Kind | Meaning | Example |
| --- | --- | --- |
| `pipeline` | A data pipeline or loader that moves data in or between entities. | a nightly load of orders |
| `scheduled_job` | A job that runs on a schedule and changes data in place. | a cleanup of expired sessions |
| `application` | An application that writes rows as users act. | a web shop backend |
| `manual` | A person who loads or edits data by hand. | a monthly price upload |

```yaml vocabulary:service_kind
- pipeline
- scheduled_job
- application
- manual
```

## 5a. Tenants and environments

**Environment.** A slug that names one copy of the platform, for example `dev`, `test`, `prod`. Any slug is allowed.

**Tenant.** A slug that names one customer, brand or partition of the platform that shares the same structure. Example: `brand-a`.

For each tenant and environment pair the model records two separate facts:

- **`ingest`**: what the configuration accepts - which streams or objects the loader takes in. Evidence comes from configuration (git, api, document).
- **`presence`**: what the data shows - which objects hold rows. Evidence comes from a probe in that environment.

These two facts are never merged into one value. Configuration that accepts an object does not prove rows exist, and rows that exist do not prove the configuration still accepts them.

Example: tenant `brand-a` in `prod` has `ingest` for `orders` (from the loader configuration) and `presence` for `orders` (row count above zero, from a probe).

## 6. Derived values

Derived values are computed by `fact project` and written to `generated/`. Every generated file starts with the header line `# generated by fact project - do not edit`. The schema rejects derived keys in authored files.

| Value | Meaning | Written to |
| --- | --- | --- |
| `label` | The domain label the profile assigns to a relationship. | `generated/labels.tsv` |
| `subject_scope` | `direct`, `transitive` or `none` per entity, with its via-path (D-007). | `generated/scope.tsv` |
| `subject_scoped` | Whether an entity's subject scope is not `none`. | `generated/scope.tsv` |
| `scope_basis` | The basis of the first admitted step of a transitive scope. | `generated/scope.tsv` |
| `reachable` | Whether an entity a consumer declares is reachable from the anchor. | `generated/scope.tsv` |
| `residue` | The relationships no profile rule matched. The gate fails when it is not empty. | `generated/residue.tsv` |
| `withheld` | The label given to a target-set relationship whose targets do not agree. | `generated/labels.tsv` |

```yaml vocabulary:derived_value
- label
- subject_scope
- subject_scoped
- scope_basis
- reachable
- residue
- withheld
```

The exact columns of each generated file are in `spec/ALGORITHMS.md`.

**Admission rejection.** Why a `scope_admission` cannot carry scope; written to `generated/scope-rejections.tsv` (`spec/ALGORITHMS.md`, algorithm 2). Any row fails the gate's `scope` stage.

| Reason | Meaning |
| --- | --- |
| `target_set` | The relationship has several targets; scope never passes through a target set. |
| `wrong_mechanism` | The mechanism is not `declared_fk` or `inferred_join`. |
| `reference_end` | One end is a `reference` entity (also used for `anchor_reference` on a reference entity). |
| `weak_evidence` | The relationship or its admission is `unresolved` or `retracted`. |
| `no_current_row_rule` | The basis is `current_row_rule`, but the target has no rule. |
| `non_unique_target` | The basis is `unique_target`, but the cardinality is not `many_to_one` or `one_to_one`. |

```yaml vocabulary:admission_rejection
- target_set
- wrong_mechanism
- reference_end
- weak_evidence
- no_current_row_rule
- non_unique_target
```

Example: `orders.placed-by	customer_scoped` is a row in `generated/labels.tsv`.

## 7. Profiles

A **profile** is the domain layer over the core.

- **Subject**: the role of the rows the domain is about, in plain words. Example: `subject: customer`. Optional: a profile without a subject (for example `statistics`) labels from class and mechanism alone and may not use the facets `any_end_subject_scoped`, `all_ends_subject_scoped` or `subject_scoped` (D-015).
- **Anchor entity**: the entity that holds the subjects. A model binds it in `factmodel.yaml`, not in the profile, so one profile fits many platforms (D-012). Example: `anchor_entity: customer`. Required when the profile names a subject, absent when it names none (D-015).
- **Label vocabulary**: the labels the profile may assign. Example: `[customer_scoped, configuration, administrative, lineage, representation, unresolved]`. `withheld` is reserved by the core and is never in a label vocabulary.
- **Facet**: a property of a relationship or its ends that a rule can test: evidence status, mechanism, the class of each end, whether each end is subject-scoped.
- **Rules**: an ordered list of `when` (facets) and `label`. Rules are evaluated in order; the first match wins.
- **Target set**: each target is projected on its own. If all targets get the same label, the relationship keeps it; if not, it is `withheld`.
- **Residue**: a relationship that no rule matches. Residue must be 0 for the gate to pass.

Example: `- when: {mechanism: derivation}` then `label: lineage`.

## 8. Registers

Registers keep the model's history of problems, questions, permanent behaviour and reasons. Entries are never deleted.

| Register | For | Statuses | What closes it |
| --- | --- | --- | --- |
| finding (`F-`) | A problem in the model or the platform to fix. | `open`, `resolved`, `wont_fix` | A change with evidence (`resolved`), or an owner decision (`wont_fix`). |
| escalation (`E-`) | A question for people that the evidence cannot answer. | `open`, `answered`, `withdrawn` | An answer with a named answer source and evidence (`answered`), or an owner note that the question no longer matters (`withdrawn`). |
| hazard (`H-`) | Permanent behaviour of the platform a reader must know. | `active`, `retired` | Evidence that the behaviour no longer exists (`retired`). |
| decision (`D-`) | Why the model is the way it is, including retractions. | `accepted`, `superseded` | A later decision that replaces it (`superseded`). |

**Hazards are not issues.** A hazard is permanent semantics, not a defect. Hazards are never counted as open issues, in `fact status` or anywhere else.

```yaml vocabulary:register_kind
- finding
- escalation
- hazard
- decision
```

```yaml vocabulary:finding_status
- open
- resolved
- wont_fix
```

```yaml vocabulary:escalation_status
- open
- answered
- withdrawn
```

```yaml vocabulary:hazard_status
- active
- retired
```

```yaml vocabulary:decision_status
- accepted
- superseded
```

Example: `H-0001` "Order status `Returned` is set after refund, so a returned order still counts in revenue for that day."

## 9. Semantic layers and consumers

A **semantic layer** is a named set of concepts and measures for one use case, built only on physical facts referenced by ID (D-019). It lives in `semantic/<layer-id>/layer.yaml`, next to its consumer.

| Key | Meaning | Example |
| --- | --- | --- |
| `entities` | The physical entities the layer reads, each with its `current_row_rule` (copied; the gate checks it equals the entity's) and `default_filters` (concept ids applied by default). | `{entity: qtrly, current_row_rule: null, default_filters: [disclosed]}` |
| `joins` | Relationship keys only, never SQL; never an `unresolved` relationship; both ends among `entities`. | `qtrly.to-industry` |
| `concepts` | Named filters. One of: `field` with `values` (a value vocabulary); `predicate` (a D-017 expression over the layer's entities); `distinct` (fields on which an entity's rows are made distinct before the layer joins to it). `required: true`: every query applies it. | `{id: disclosed, predicate: "qtrly.disclosure_code IS NULL", required: true}` |
| `measures` | `expression` over `<entity>.<field>` columns (sqlglot, neutral dialect), `aggregation`, `grain` (`entity`, `fields`), `time` (`field`, `granularity`), `formula_source` (evidence id), `hazards`, `suppressed` and `companion`; `rollups` (D-020): the hierarchy relationships the measure must add up over, each with the grain field that holds the code and the concept that marks a suppressed row. | `{id: total_wages, expression: qtrly.total_qtrly_wages, aggregation: sum}` |
| `hazards` | Every active hazard the layer inherits: one that applies to an entity or relationship the layer reads, or is listed on a field it uses. | `[H-0001, H-0002]` |

```yaml vocabulary:measure_aggregation
- sum
- count
- count_distinct
- avg
- min
- max
- none
```

`none`: the expression is already an aggregate or a ratio of aggregates (for example a weekly wage computed from summed wages and summed employment).

```yaml vocabulary:time_granularity
- day
- month
- quarter
- year
```

**Suppressed cells.** What a measure does with rows the platform withheld (QCEW `disclosure_code = 'N'`): `exclude` (the measure applies a concept that leaves them out; `companion` names the measure that counts them), `include` (they count as stored), `not_applicable` (the platform withholds nothing).

```yaml vocabulary:suppressed_handling
- exclude
- include
- not_applicable
```

A **consumer** is the agent, SQL generator or knowledge base that reads a layer or a release (`semantic/<layer-id>/consumer.yaml`): `layers`, `corpus` (`location` relative to the layer folder, or a `pin` for a corpus kept outside the repository), `threshold` (default 0.9, D-021) and `interface` (`<path>:<function>`, the `compile(request, layer) -> sql` entry point, path relative to the model root). The layer is correct when the consumer gives the same answers as the platform at its threshold.

The gate stage `layers` checks every rule in this section; a layer at `status: reviewed` needs an accepted equivalence run.

**Equivalence corpus.** One YAML file per item in the layer's corpus folder (`semantic/<layer-id>/corpus/`, never read as a model file): `id`, `request` (the consumer's input, a map), `reference` (the platform's own answer: SQL in the neutral dialect that names tables by entity id), `mode`, `note`, `tags`, and for an item the consumer may fail, `known_gap` (the reason) or `finding` (the finding that records it, D-021). `fact equivalence run` compiles each request with the consumer, binds entity ids to physical names, runs both sides and compares; it writes `generated/equivalence-<layer>.md` and `equivalence/last-run.json`, outcomes and counts only. `fact equivalence accept` copies the last run into `equivalence/accepted.json`; an item that passed there and does not pass now is a regression.

```yaml vocabulary:equivalence_mode
- same_rows
- same_count
- same_predicate
```

**Threshold (D-021).** A consumer proves its layer when the share of items that pass in `same_rows` or `same_predicate`, over items not marked `known_gap`, is at least its `threshold` (0.9 by default); no item regresses against `equivalence/accepted.json`; and every item that does not pass has a `known_gap` or a `finding`. A layer may be `status: reviewed` only when its accepted run proved it.

`same_rows`: equal result sets as multisets (order ignored, duplicates kept). `same_count`: equal row counts. `same_predicate`: equal normalised ASTs (lower-case identifiers, no quoting, sorted conjunctions, literals kept); nothing runs.

**Release.** The readable copy of a model for consumers. Every file in the model repository gets exactly one disposition; a projected file keeps only allowlisted keys, and an undeclared key fails the release.

```yaml vocabulary:release_disposition
- export
- project
- refuse
```

A `project` file keeps only the top-level keys its kind lists under `keep` in the allowlist; keys under `drop` leave the copy. A key in neither list fails the release.

**Release failure.** Why a file stops a release (`spec/ALGORITHMS.md`, algorithm 3).

| Reason | Meaning |
| --- | --- |
| `unmatched` | No pattern matches the file. |
| `no_key_list` | The file is projected, but its kind has no key list. |
| `undeclared_key` | A projected file has a key in neither `keep` nor `drop`. |

```yaml vocabulary:release_failure
- unmatched
- no_key_list
- undeclared_key
```

**Building a release** (`fact release --out <dir> --version <v>`). The model's gate must pass, and no `reviewed` layer may have dropped against its accepted equivalence run (D-021). Every file of the repository is partitioned (built releases under `release/out/` and `.git` are not part of it). Exported text files lose every block between a line holding `internal:begin` and a line holding `internal:end`; an unclosed block refuses the release. Markers are explicit; prose is never pattern-matched. The release folder holds `VERSION` (`release`, `source_commit`, `schema_version`, `framework_version`) and `RELEASE_NOTES.md`, one section per version, newest last, never edited. `fact check --release <dir> --previous <dir>` runs yaml, schema, references and privacy on the release, and a `release` stage: `VERSION` and the notes exist, no derived key leaked, and every earlier section of the notes is unchanged.

**Export targets.** Other tools a layer can be exported to.

```yaml vocabulary:export_target
- osi
- dbt
- cube
```

## 10. Probes

A **probe** is a data check generated from the model, written as a readable script for a person or CI with credentials to run. Probes return counts and rates only, never values, identifiers or rows. A result is saved with a pin and becomes evidence; a result outside its expected range opens a finding.

Probe kinds:

| Kind | Tests | Returns |
| --- | --- | --- |
| `key_duplicates` | A declared key. | Number of key values with more than one row. |
| `join_match` | A join, in both directions. An expression join (D-017) is rendered through sqlglot; its one-end conjuncts filter the rows of that end. | Match rate and orphan count per side. |
| `fan_out` | Cardinality and transitive scope. | Rows per source row; source rows that reach more than one anchor. |
| `null_rate` | A field. | Share of null values. |
| `row_count` | Presence per tenant and environment. | Number of rows. |
| `current_row_ties` | A current-row rule. | Keys with more than one row after the rule. |
| `value_set` | A field against its declared `values`. | Count of distinct values, of distinct values outside the declared set (`outside_values`), and of rows holding one (`outside_rows`); nulls are never outside; never the values. |
| `rollup` | A hierarchy relationship and a layer measure (D-020): each parent row against the sum of its children at one level, other key fields equal. | `parents_compared`, `exact`, `within_rounding` (at most one unit per child), `beyond` (among parents with nothing suppressed), `parents_with_suppressed_child`, `suppressed_parents_disclosed_children`. Confirms a hierarchy for aggregation. |

All seven are built in M1 (WP1.7). Each probe is a sqlglot AST rendered per dialect with quoted identifiers; a probe that needs a construct a dialect lacks (a nested path outside BigQuery) lists it under `unsupported_on_dialect` and is never rendered for it.

**Dialect knowledge for probes.** Which dialects can read a nested path, how a query is wrapped to print one JSON object, and which shell command runs a statement: all of it lives here, not in code (D-011). A dialect missing from a block gets the neutral behaviour: nested-path probes are not rendered for it, the SQL is not wrapped, and the owner must set `RUN_SQL`. The code implements two wrap strategies: `json_object_pairs` (`SELECT json_object('k', "k", ...) FROM (<sql>) AS q`) and `row_to_json` (`SELECT row_to_json(q) FROM (<sql>) AS q`).

```yaml vocabulary-map:dialect_nested_paths
bigquery: true
```

```yaml vocabulary-map:dialect_json_wrap
sqlite: json_object_pairs
postgres: row_to_json
duckdb: json_object_pairs
```

```yaml vocabulary-map:dialect_runner
sqlite: 'sqlite3 "${SQLITE_DB:?set SQLITE_DB to the database file}"'
postgres: 'psql "${FACT_PG_DSN:?set FACT_PG_DSN}" -At -v ON_ERROR_STOP=1'
duckdb: 'duckdb -noheader -list "${DUCKDB_DB:?set DUCKDB_DB to the database file}"'
```

**Running probes.** `fact probe generate` writes `probes/<probe-id>.yaml`. The owner runs them from `fact probe render --dialect <d>` (a plain shell script per source), or `fact probe run --source <id>` runs them through the `sql` adapter where the source names a `dsn_env`; a local engine seeded with synthetic rows is a test fixture, not a platform (D-011). Both write JSON lines: a header `{source, pin, environment, data_quality, ran_on}`, then `{probe, measurement}` or `{probe, error}` per probe. `fact probe intake <file>` keeps numbers only, writes `evidence/probes/<probe-id>@<date>.yaml`, cites an in-range result from the fact it tests and opens a finding for an out-of-range one. The record is `confirmed`, and so the fact, only on representative data; on synthetic or unknown data it is `inferred` (D-014). Rates (`match_rate`, `null_rate`) are computed at intake, never in SQL.

```yaml vocabulary:probe_kind
- key_duplicates
- join_match
- fan_out
- null_rate
- row_count
- current_row_ties
- value_set
- rollup
```

Example probe result: `probe: join-orders-users`, `measurement: {match_rate: 1.0, orphans_left: 0}`.

## 11. Keeping the model current

**Drift class.** Each item in a sync drift report gets one class.

| Class | Meaning | What follows |
| --- | --- | --- |
| `new_fact` | Something the model does not have yet. | An agent drafts it in `drafts/`. |
| `changed_fact` | A fact whose source changed. | Its evidence must be renewed. |
| `lost_fact` | A fact the source no longer supports. | A finding opens. |
| `no_effect` | A source change that touches no fact. | Nothing. |

```yaml vocabulary:drift_class
- new_fact
- changed_fact
- lost_fact
- no_effect
```

**Drift kind.** What changed between two snapshots of a source, or between a snapshot and the model (`fact sync`, written to `generated/drift.md`).

| Kind | Meaning | Class when the object is modelled |
| --- | --- | --- |
| `new_object` | An object the previous snapshot did not have. | `new_fact` (draft), `no_effect` if already modelled |
| `dropped_object` | A modelled object, or one in the previous snapshot, that the latest does not have. | `lost_fact` (finding) |
| `new_field` | A field the previous snapshot did not have. | `new_fact` (draft) |
| `dropped_field` | A field that is gone. | `lost_fact` (finding) |
| `type_class_change` | The field's `type_class` changed (D-013). | `changed_fact` |
| `type_text_change` | The type text changed within the same class. | `no_effect`, listed |
| `nullability_change` | The field became nullable or not nullable. | `changed_fact` |
| `constraint_change` | A declared key or foreign key appeared, disappeared or changed. | `changed_fact` |

A change to an object nobody has modelled yet is `no_effect`; the object's draft carries it.

```yaml vocabulary:drift_kind
- new_object
- dropped_object
- new_field
- dropped_field
- type_class_change
- type_text_change
- nullability_change
- constraint_change
```

**Trigger.** An event with the follow-up it requires, one `kind: trigger` file per trigger in `maintenance/`. When the event happens, a `fired` entry records the date; its `follow_up_ref` records where the follow-up is (a register ID, a commit, a file). The `triggers` gate stage fails on any fired entry without `follow_up_ref`. `fact sync` fires `source_pin_moved` triggers when a source's snapshot pin changes.

```yaml vocabulary:trigger_event
- new_tenant
- source_pin_moved
- escalation_answered
- ticket_shipped
- probe_out_of_range
```

Example: `source_pin_moved` on the loader repository requires the evidence pinned to the old commit to be re-read.

## 12. Metadata snapshots

A **snapshot** is an engine-neutral export of a source's metadata (`fact snapshot --source <id>`), stored in `sources/snapshots/`, so adapters, agents and tests work without credentials. It holds objects, fields with paths and types, declared constraints, partitioning and options - never rows. It is not a model file kind: the gate does not read it. It is the only contract between an adapter and the core (D-011): `fact draft` and `fact sync` read snapshots, and the core never reads `options` or `extensions`, where engine-specific facts go. Its schema is `schemas/snapshot.schema.json`.

A snapshot may carry a `pin` (the version read) and each object may carry its own `pin` (for example a DDL file at a commit); drafts cite the object's pin, else the snapshot's.

**Object type.**

```yaml vocabulary:object_type
- table
- view
- materialized_view
- external
```

**Constraint type.** Constraints the engine or DDL declares. `enforced: false` marks a constraint the engine does not check.

```yaml vocabulary:constraint_type
- primary_key
- unique
- foreign_key
```

Example: a BigQuery primary key on `orders.order_id` is `{constraint_type: primary_key, fields: [order_id], enforced: false}`.

**Type class.** A neutral class for a field's type (D-013). `type` keeps the engine's own text; `type_class` lets snapshots from different engines, or reads before and after a cosmetic change, be compared. Each adapter maps engine types; an unknown type is `other`.

```yaml vocabulary:type_class
- integer
- decimal
- float
- boolean
- text
- date
- time
- timestamp
- interval
- binary
- json
- array
- struct
- geography
- other
```

Example: `INT64` (BigQuery), `integer` (PostgreSQL) and `INTEGER` (SQLite) are all `integer`.

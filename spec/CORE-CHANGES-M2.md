# Core changes since WP1.8b (M2 freeze review)

The ledger behind the M2 gate: "No core change without a decision record naming the platform that forced it" (`IMPLEMENTATION_PLAN.md`, WP2.3). It lists every change to the core from WP1.8b (the last core round before M1 was closed) to round 19 (the freeze), and the record that covers it.

Written in round 18 (2026-10-27); closed in round 19 with D-018.

**Rule (D-018).** A decision record is required when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result. Adding an optional key, a vocabulary value or a probe kind needs a `CHANGELOG.md` entry and a line in this ledger, nothing more. A fix that makes code obey the existing schema is a defect fix, not a core change; it needs a `CHANGELOG.md` entry only. An owner brief is not a decision record.

## What counts as core

The contract a model and an adapter rely on, and the code that applies it:

- the schemas (`schemas/`, rendered from `src/factmodel/schemas/templates/`) and the typed models;
- the vocabulary (`spec/VOCABULARY.md`) and the algorithms (`spec/ALGORITHMS.md`);
- the loader, scope closure, projection, derived values, the gate, probes, sync, intake, `fact init` and the CLI commands.

Not core: adapters (plugins behind the snapshot contract, D-011), profiles, examples, hard cases, agent skills and templates, documentation, tests and CI.

A change either changes the contract (a schema key, a vocabulary block, an algorithm rule or a file a command writes), or implements what the contract already said. Implementing spec v0.1 (before WP1.8b) is not a core change; it is listed here so nothing is left out.

## Ledger

| # | Round | Change | Kind | Record | Platform |
| --- | --- | --- | --- | --- | --- |
| 1 | round 8 | Adapter protocol and registry, entry-point group `factmodel.adapters`; `fact adapters` | contract | D-011 | none |
| 2 | round 8 | The snapshot is the only adapter-core contract; drafts from one core function (`to_facts`); `fact snapshot`, `fact draft`, `fact export-sql` | contract | D-011 | none |
| 3 | round 8 | Source keys `adapter`, `dialect`, `dsn_env`, `revision`, `include`; blocks `engine_dialect`, `engine_enforces_foreign_keys`; loader check `missing_dialect` | contract | D-011 | none |
| 4 | round 8 | `privacy` stage fails on a literal connection string | contract | D-011 (no credentials) | none |
| 5 | round 8 | `type_class` on snapshot fields, its vocabulary block | contract | D-013 | none |
| 6 | round 8 | `anchor_entity` in `factmodel.yaml`, `subject` on a profile; loader anchor checks; scope reads the model's anchor | contract | D-012 | none |
| 7 | round 8 | Snapshot `pin`, and `pin` per snapshot object | contract, additive | D-018 (retroactive) | none |
| 8 | round 9 | `fact quote` (quotable text through the git adapter); git pins by blob hash for working-tree reads | contract | D-011 (git adapter: DDL and text) | none |
| 9 | round 10 | `fact sync`, the drift report, block `drift_kind`; the `triggers` stage enabled | implements spec v0.1 (sync, drift classes, triggers) | D-013 for the type-class rule of drift | none |
| 10 | round 11 | `fact probe generate`, `render`, `run`, `intake`; probes as neutral ASTs rendered per dialect; probe key `unsupported_on_dialect` | contract | D-011 (probes from a neutral AST, rendered per dialect) | none |
| 11 | round 11 | Probe key `expected` becomes optional; new keys `entity` and `note` | contract, additive | D-018 (retroactive) | none |
| 12 | round 12 | In-place YAML edits that keep the author's line breaks (sync, intake) | implementation | - | none |
| 13 | round 13 | `fact source add` options for the D-011 source keys; `fact init` copies the skills | implementation | D-011 | none |
| 14 | round 14 | Map blocks (`vocabulary-map:`) with text or boolean values; `dialect_nested_paths`, `dialect_json_wrap`, `dialect_runner` | contract | D-011 (engine knowledge is vocabulary) | none |
| 15 | round 14 | Intake confirms only on representative data; `treat_synthetic_as_representative` | contract | D-014 | none |
| 16 | round 14 | Drafts keep constraint names in `extensions.draft` and turn comments into meanings with `inferred` evidence | implementation of `to_facts` (`extensions` is a free map) | D-011 | none |
| 17 | round 14 | Field key `values` (a declared value domain); `value_set` generated for it | contract, additive | D-018 (retroactive) | none |
| 18 | round 14 | `fact init` copies the brief and report templates | implementation | - | none |
| 19 | round 15 | `value_set` also returns `outside_rows` | implements spec v0.1 ("count of rows whose value is outside") | - | none |
| 20 | round 15 | `fact init` writes `treat_synthetic_as_representative: false` | implementation | D-014 | none |
| 21 | round 15 | `duckdb` in `engine_enforces_foreign_keys`, measured by a test | vocabulary data | D-011 (engine facts are vocabulary) | DuckDB |
| 22 | round 16 | `subject` optional; no anchor without a subject; `anchor_reference`, `scope_admission` and subject facets are errors without one; scope `none` and `reachable` `-`; `fact init` writes no anchor | contract | D-015 | QCEW |
| 23 | round 16 | Public-domain code lists as committed fixtures (plan ground rule 3) | plan rule | D-016 | QCEW |
| 24 | round 16 | Join expressions: parsing and reference checks, per-dialect `join_match` and `fan_out`, one-end filters, the `unique_target` rule | contract | D-017 | QCEW |
| 25 | round 17 | A self-reference conjunct may be a negated comparison | contract | D-017 | QCEW |
| 26 | round 18 | `fact migrate` reports the model's framework version, the schema version and compatibility; it writes nothing | implementation (plan WP2.3) | - | none |
| 27 | round 19 | D-018: what a contract change needs; rows 7, 11 and 17 recorded retroactively | rule | D-018 | none |
| 28 | round 19 | Schemas frozen: `SCHEMA_VERSION` 1.0.0, `$id` URNs at 1.0.0 | version | D-018 (the M2 gate) | none |
| 29 | round 19 | Optional `schema_version` in `factmodel.yaml`, written by `fact init`; `fact migrate` reads it and names the difference to the installed schemas | contract, additive | ledger line (D-018) | none |
| 30 | round 19 | A single-target relationship may carry a `discriminator` (a source field the target's meaning depends on); the loader checks the field exists | contract, additive (a rule relaxed) | ledger line (D-018); owner answer Q4 | QCEW |
| 31 | round 19 | An `unresolved` relationship may omit `join`; `to` is still checked | contract, additive (a required key relaxed) | ledger line (D-018); owner answer Q5 | QCEW |
| 32 | round 19 | `duckdb` in `dialect_json_wrap` (`json_object_pairs`) and `dialect_runner` | vocabulary values | ledger line (D-018); owner answer Q6 | DuckDB |

Not core, listed for completeness: the `export`, `sql` and `git` adapters and their flavours (rounds 8, 9 and 15, including the `sql` fallback to standard views for engines whose SQLAlchemy dialect cannot reflect), the retail and statistics profiles, both examples, the hard cases and the agent skills.

## Changes without a decision record

None since round 19. Round 18 found three (rows 7, 11 and 17), all additive and forced by no platform; D-018 records them retroactively and sets the rule above, and the schemas froze at 1.0.0 in round 19.

## Defect fixes (D-018: CHANGELOG entry only)

- Round 19: `fact probe intake` wrote a field reference into a finding's `about` when a probe on a field was out of range; the schema allows an entity or a relationship there. Intake now names the entity and keeps the field in `extensions.fact`.

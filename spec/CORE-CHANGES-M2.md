# Core changes since WP1.8b (M2 freeze review)

The ledger behind the M2 gate: "No core change without a decision record naming the platform that forced it" (`IMPLEMENTATION_PLAN.md`, WP2.3). It lists every change to the core from commit `74013ed` (WP1.8b, the last core round before M1 was closed) to `e137bb7` (round 17), and the record that covers it.

Written in round 18 (2026-10-27).

## What counts as core

The contract a model and an adapter rely on, and the code that applies it:

- the schemas (`schemas/`, rendered from `src/factmodel/schemas/templates/`) and the typed models;
- the vocabulary (`spec/VOCABULARY.md`) and the algorithms (`spec/ALGORITHMS.md`);
- the loader, scope closure, projection, derived values, the gate, probes, sync, intake, `fact init` and the CLI commands.

Not core: adapters (plugins behind the snapshot contract, D-011), profiles, examples, hard cases, agent skills and templates, documentation, tests and CI.

A change either changes the contract (a schema key, a vocabulary block, an algorithm rule or a file a command writes), or implements what the contract already said. Implementing spec v0.1 (`b8b3f61`, before `74013ed`) is not a core change; it is listed here so nothing is left out.

## Ledger

| # | Commit | Change | Kind | Record | Platform |
| --- | --- | --- | --- | --- | --- |
| 1 | `3bbe8db` round 8 | Adapter protocol and registry, entry-point group `factmodel.adapters`; `fact adapters` | contract | D-011 | none |
| 2 | `3bbe8db` | The snapshot is the only adapter-core contract; drafts from one core function (`to_facts`); `fact snapshot`, `fact draft`, `fact export-sql` | contract | D-011 | none |
| 3 | `3bbe8db` | Source keys `adapter`, `dialect`, `dsn_env`, `revision`, `include`; blocks `engine_dialect`, `engine_enforces_foreign_keys`; loader check `missing_dialect` | contract | D-011 | none |
| 4 | `3bbe8db` | `privacy` stage fails on a literal connection string | contract | D-011 (no credentials) | none |
| 5 | `3bbe8db` | `type_class` on snapshot fields, its vocabulary block | contract | D-013 | none |
| 6 | `3bbe8db` | `anchor_entity` in `factmodel.yaml`, `subject` on a profile; loader anchor checks; scope reads the model's anchor | contract | D-012 | none |
| 7 | `3bbe8db` | Snapshot `pin`, and `pin` per snapshot object | contract | **none** | none |
| 8 | `4302b06` round 9 | `fact quote` (quotable text through the git adapter); git pins by blob hash for working-tree reads | contract | D-011 (git adapter: DDL and text) | none |
| 9 | `93238ab` round 10 | `fact sync`, the drift report, block `drift_kind`; the `triggers` stage enabled | implements spec v0.1 (sync, drift classes, triggers) | D-013 for the type-class rule of drift | none |
| 10 | `b78afdc` round 11 | `fact probe generate`, `render`, `run`, `intake`; probes as neutral ASTs rendered per dialect; probe key `unsupported_on_dialect` | contract | D-011 (probes from a neutral AST, rendered per dialect) | none |
| 11 | `b78afdc` | Probe key `expected` becomes optional; new keys `entity` and `note` | contract | **none** | none |
| 12 | `b2f23b4` round 12 | In-place YAML edits that keep the author's line breaks (sync, intake) | implementation | - | none |
| 13 | `20e1072` round 13 | `fact source add` options for the D-011 source keys; `fact init` copies the skills | implementation | D-011 | none |
| 14 | `04c296f` round 14 | Map blocks (`vocabulary-map:`) with text or boolean values; `dialect_nested_paths`, `dialect_json_wrap`, `dialect_runner` | contract | D-011 (engine knowledge is vocabulary) | none |
| 15 | `04c296f` | Intake confirms only on representative data; `treat_synthetic_as_representative` | contract | D-014 | none |
| 16 | `04c296f` | Drafts keep constraint names in `extensions.draft` and turn comments into meanings with `inferred` evidence | implementation of `to_facts` (`extensions` is a free map) | D-011 | none |
| 17 | `04c296f` | Field key `values` (a declared value domain); `value_set` generated for it | contract | **none** | none |
| 18 | `04c296f` | `fact init` copies the brief and report templates | implementation | - | none |
| 19 | `f525716` round 15 | `value_set` also returns `outside_rows` | implements spec v0.1 ("count of rows whose value is outside") | - | none |
| 20 | `f525716` | `fact init` writes `treat_synthetic_as_representative: false` | implementation | D-014 | none |
| 21 | `f525716` | `duckdb` in `engine_enforces_foreign_keys`, measured by a test | vocabulary data | D-011 (engine facts are vocabulary) | DuckDB |
| 22 | `98d8dc5` round 16 | `subject` optional; no anchor without a subject; `anchor_reference`, `scope_admission` and subject facets are errors without one; scope `none` and `reachable` `-`; `fact init` writes no anchor | contract | D-015 | QCEW |
| 23 | `98d8dc5` | Public-domain code lists as committed fixtures (plan ground rule 3) | plan rule | D-016 | QCEW |
| 24 | `98d8dc5` | Join expressions: parsing and reference checks, per-dialect `join_match` and `fan_out`, one-end filters, the `unique_target` rule | contract | D-017 | QCEW |
| 25 | `e137bb7` round 17 | A self-reference conjunct may be a negated comparison | contract | D-017 | QCEW |
| 26 | round 18 | `fact migrate` reports the model's framework version, the schema version and compatibility; it writes nothing | implementation (plan WP2.3) | - | none |

Not core, listed for completeness: the `export`, `sql` and `git` adapters and their flavours (rounds 8, 9 and 15, including the `sql` fallback to standard views for engines whose SQLAlchemy dialect cannot reflect), the retail and statistics profiles, both examples, the hard cases and the agent skills.

## Changes without a decision record

Three contract changes have no decision record. The brief makes this a stop condition, so the schemas are not frozen at 1.0.0 in round 18; the owner decides.

| # | Change | Where it came from | Compatible with 0.1.0 models |
| --- | --- | --- | --- |
| 7 | Snapshot `pin` and per-object `pin` | Round 8 implementation of the D-011 contract; the D-011 brief describes git pins for round 9 but not the snapshot keys | yes: optional keys |
| 11 | Probe `expected` optional; `entity`, `note` | Round 11 implementation (a probe that only measures; the entity whose table it reads) | yes: optional keys, one required key relaxed |
| 17 | Field `values` | Owner answer Q7 in `rounds/2026-10-23-brief-m1-residue.md` (spec v0.1 compared `value_set` against a profile vocabulary instead) | yes: optional key |

All three are additive (minor under `spec/VERSIONING.md`), and none was forced by a platform. Each needs either a decision record (platform: none) or a revert before the freeze.

## Known defect (not a change)

`fact probe intake` writes a field reference into a finding's `about` when a probe on a field is out of range; the schema allows an entity or a relationship there, so the gate then fails `references`. Found in round 17 (`examples/qcew`, F-0002). Fixing it changes what intake writes, so it waits for the owner with the three entries above.

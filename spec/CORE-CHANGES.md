# Core changes

The ledger of every change to the core contract, with the record that covers it, ordered by schema version.

**Rule (D-018).** A decision record is required when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result. Adding an optional key, a vocabulary value or a probe kind needs a `CHANGELOG.md` entry and a line in this ledger, nothing more. A fix that makes code obey the existing schema is a defect fix, not a core change; it needs a `CHANGELOG.md` entry only.

## What counts as core

The contract a model and an adapter rely on, and the code that applies it:

- the schemas (`schemas/`, rendered from `src/factmodel/schemas/templates/`) and the typed models;
- the vocabulary (`spec/VOCABULARY.md`) and the algorithms (`spec/ALGORITHMS.md`);
- the loader, scope closure, projection, derived values, the gate, probes, sync, intake, `fact init` and the CLI commands.

Not core: adapters (plugins behind the snapshot contract, D-011), profiles, examples, hard cases, agent skills and templates, documentation, tests and CI.

Kinds: **contract** changes a schema key, a vocabulary block, a gate rule or a file a command writes; **algorithm** changes what an algorithm computes or what a status means; **additive** adds an optional key, a vocabulary value or a probe kind and breaks no model; **implementation** implements what the contract already said, listed so nothing is left out. Record: a decision id, or **ledger** when D-018 asks for this line only.

Schema version 0.1.0 covers the specification as first written and every change before the freeze; the specification itself is not listed.

## Ledger

| Schema | Change | Kind | Record | Platform |
| --- | --- | --- | --- | --- |
| 0.1.0 | Adapter protocol and registry, entry-point group `factmodel.adapters`; `fact adapters` | contract | D-011 | none |
| 0.1.0 | The snapshot is the only adapter-core contract; drafts from one core function (`to_facts`); `fact snapshot`, `fact draft`, `fact export-sql` | contract | D-011 | none |
| 0.1.0 | Source keys `adapter`, `dialect`, `dsn_env`, `revision`, `include`; blocks `engine_dialect`, `engine_enforces_foreign_keys`; loader check `missing_dialect` | contract | D-011 | none |
| 0.1.0 | `privacy` stage fails on a literal connection string | contract | D-011 | none |
| 0.1.0 | `type_class` on snapshot fields, its vocabulary block | contract | D-013 | none |
| 0.1.0 | `anchor_entity` in `factmodel.yaml`, `subject` on a profile; loader anchor checks; scope reads the model's anchor | contract | D-012 | none |
| 0.1.0 | Snapshot `pin`, and `pin` per snapshot object | additive | D-018 (retroactive) | none |
| 0.1.0 | `fact quote` (quotable text through the git adapter); git pins by blob hash for working-tree reads | contract | D-011 | none |
| 0.1.0 | `fact sync`, the drift report, block `drift_kind`; the `triggers` stage enabled | implementation (sync, drift classes and triggers as specified) | D-013 for the type-class rule of drift | none |
| 0.1.0 | `fact probe generate`, `render`, `run`, `intake`; probes as neutral ASTs rendered per dialect; probe key `unsupported_on_dialect` | contract | D-011 | none |
| 0.1.0 | Probe key `expected` becomes optional; new keys `entity` and `note` | additive | D-018 (retroactive) | none |
| 0.1.0 | In-place YAML edits that keep the author's line breaks (sync, intake) | implementation | - | none |
| 0.1.0 | `fact source add` options for the source keys; `fact init` copies the skills | implementation | D-011 | none |
| 0.1.0 | Map blocks (`vocabulary-map:`) with text or boolean values; `dialect_nested_paths`, `dialect_json_wrap`, `dialect_runner` | contract | D-011 | none |
| 0.1.0 | Intake confirms only on representative data; `treat_synthetic_as_representative` | algorithm | D-014 | none |
| 0.1.0 | Drafts keep constraint names in `extensions.draft` and turn comments into meanings with `inferred` evidence | implementation of `to_facts` (`extensions` is a free map) | D-011 | none |
| 0.1.0 | Field key `values` (a declared value domain); `value_set` generated for it | additive | D-018 (retroactive) | none |
| 0.1.0 | `fact init` copies the brief and report templates | implementation | - | none |
| 0.1.0 | `value_set` also returns `outside_rows` | implementation (the count the specification names) | - | none |
| 0.1.0 | `fact init` writes `treat_synthetic_as_representative: false` | implementation | D-014 | none |
| 0.1.0 | `duckdb` in `engine_enforces_foreign_keys`, measured by a test | additive | D-011 | DuckDB |
| 0.1.0 | `subject` optional; no anchor without a subject; `anchor_reference`, `scope_admission` and subject facets are errors without one; scope `none` and `reachable` `-`; `fact init` writes no anchor | contract | D-015 | QCEW |
| 0.1.0 | Public-domain code lists as committed fixtures (roadmap ground rule 3) | rule | D-016 | QCEW |
| 0.1.0 | Join expressions: parsing and reference checks, per-dialect `join_match` and `fan_out`, one-end filters, the `unique_target` rule | contract | D-017 | QCEW |
| 0.1.0 | A self-reference conjunct may be a negated comparison | contract | D-017 | QCEW |
| 0.1.0 | `fact migrate` reports the model's framework version, the schema version and compatibility; it writes nothing | implementation | - | none |
| 1.0.0 | D-018: what a contract change needs; the three additive changes above recorded retroactively | rule | D-018 | none |
| 1.0.0 | Schemas frozen: `SCHEMA_VERSION` 1.0.0, `$id` URNs at 1.0.0 | version | D-018 | none |
| 1.0.0 | Optional `schema_version` in `factmodel.yaml`, written by `fact init`; `fact migrate` reads it and names the difference to the installed schemas | additive | ledger | none |
| 1.0.0 | A single-target relationship may carry a `discriminator` (a source field the target's meaning depends on); the loader checks the field exists | additive (a rule relaxed) | ledger | QCEW |
| 1.0.0 | An `unresolved` relationship may omit `join`; `to` is still checked | additive (a required key relaxed) | ledger | QCEW |
| 1.0.0 | `duckdb` in `dialect_json_wrap` (`json_object_pairs`) and `dialect_runner` | additive | ledger | DuckDB |
| 2.0.0 | Layer contract v1: `entities` (current-row rule, default filters), concepts in three forms (`field`/`values`, `predicate`, `distinct`) with `required`, measures with `expression`, `grain`, `time`, `formula_source`, `hazards`, `suppressed`, `companion`; `filters`, measure `field` and `time_field` removed; consumer `interface` | contract, breaking | D-019 | QCEW, Chinook |
| 2.0.0 | Schemas 2.0.0 | version | D-019 | QCEW, Chinook |
| 2.0.0 | Vocabulary blocks `measure_aggregation`, `time_granularity`, `suppressed_handling` | contract | D-019 | QCEW, Chinook |
| 2.0.0 | Gate stage `layers` | contract | D-019 | QCEW, Chinook |
| 2.0.0 | `fact check` warns (never fails) on a `schema_version` difference when every file validates | implementation | - | none |
| 2.0.0 | Framework version 0.1.0 | version | - | none |
| 2.0.0 | Equivalence corpus item format (`id`, `request`, `reference`, `mode`, `note`, `tags`) and vocabulary block `equivalence_mode` | additive | ledger | none |
| 2.0.0 | `fact equivalence run`, `accept`, `script`; `equivalence/last-run.json`, `equivalence/accepted.json`, `generated/equivalence-<layer>.md` | implementation | - | none |
| 2.1.0 | Probe kind `rollup` (counts per parent against the sum of its children); a hierarchy is confirmed for aggregation only by a rollup in range; intake cites it on the hierarchy relationship | algorithm (meaning of confirmed) | D-020 | QCEW |
| 2.1.0 | Optional layer measure key `rollups` (hierarchy, field, suppressed concept); the `layers` stage checks it; `fact probe generate` reads layers | additive | D-020 | QCEW |
| 2.1.0 | Schemas 2.1.0 | version | D-018 (additive) | QCEW |
| 2.1.0 | Equivalence threshold: share in `same_rows`/`same_predicate` over non-gap items, no regression, every failure explained; corpus keys `known_gap`, `finding`; run summary `threshold`, `share`, `proven`, `unexplained`; `reviewed` needs a proven accepted run | algorithm (meaning of reviewed) | D-021 | none |
| 2.1.0 | Release folder format: `VERSION` keys, append-only `RELEASE_NOTES.md`, internal-note markers `internal:begin` / `internal:end` | additive | ledger | none |
| 2.1.0 | `fact release`, `fact check --release` (reduced gate plus a `release` stage), `fact lookup`; the loader skips `release/out/` | implementation | - | none |
| 2.1.0 | Vocabulary value `ossie` in `export_target` (`osi` kept) | additive | ledger | none |
| 2.1.0 | Vocabulary block `volatile_probe_kind`; generated probes of those kinds carry `volatile: true`; `fact probe generate --set volatile` | additive | ledger | none |
| 2.1.0 | `fact export --target ossie|dbt`, `EXPORT_NOTES.md` | implementation | - | none |
| 2.2.0 | Derived file `semantic/<layer>/generated/joins.tsv`, written by `fact project`, checked by `derived-not-authored` | additive | ledger | QCEW, Chinook |
| 2.2.0 | Concept form `values_table` (`columns`, `rows` or `entity`); the `layers` stage checks it | additive | ledger | QCEW |
| 2.2.0 | Schemas 2.2.0 | version | D-018 (additive) | QCEW |
| 2.2.0 | dbt export: derived metrics for formula measures over exported metrics | implementation | - | QCEW |
| 2.2.0 | `RELEASE_NOTES.md` kept in the model repository (`release/RELEASE_NOTES.md`); `fact release` appends and copies | additive | ledger | none |
| 2.2.0 | `fact migrate` registry with one documented slot (1.0.0 to 2.0.0, no automatic step) | implementation | - | none |
| 2.2.0 | `fact --version` prints the schema version | implementation | - | none |
| 2.2.0 | Ossie export: the released core specification 0.1.1 by default, 0.2.0.dev0 with `fact export --spec-version`; only keys each document names | implementation (the target's format, no framework key) | - | QCEW, Chinook |
| 2.2.0 | More than one snapshot per source and day: the second different read of a day is `<source>@<date>_2.yaml` with `_2` on its warehouse pin (then `_3`, ...); `fact draft` and `fact sync` order snapshots by date, then sequence | additive (a file name and a pin suffix; the first read of a day keeps its name and pin) | ledger | TPC-H |

## Defect fixes (D-018: CHANGELOG entry only)

- `fact probe intake` wrote a field reference into a finding's `about` when a probe on a field was out of range; the schema allows an entity or a relationship there. Intake now names the entity and keeps the field in `extensions.fact`.
- `fact equivalence script` wrote `EXCEPT WITH ...` when a reference starts with a CTE; each side of the `EXCEPT` is now a plain `SELECT * FROM (...)`.

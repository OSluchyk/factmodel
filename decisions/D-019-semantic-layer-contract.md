# D-019 Semantic layer contract v1

Date: 2026-10-27 · Status: accepted
Platform that forced it: QCEW and Chinook (`examples/qcew`, `examples/chinook`)

## Context

The layer and consumer schemas of 1.0.0 were placeholders ("details come in M3"): a layer had flat `filters`, concepts on one field, measures on one field with an aggregation name. QCEW cannot be served by that shape. A correct QCEW answer applies the disclosure filter and the level discriminator on every query, joins to distinct area codes, and computes measures from monthly levels by a documented formula, never as a sum of annual averages. Chinook needs measures over joined entities (revenue is price times quantity). A consumer must be able to read all of this from the layer, and the gate must be able to check it.

## Decision

A layer (`semantic/<layer-id>/layer.yaml`) has:

- `id`, `purpose`, `consumer`, `status` (`review_status`), `evidence`, `records`, `extensions`, as before.
- `entities`: the physical entities the layer reads, each with `current_row_rule` copied by reference (the gate checks it equals the entity's) and `default_filters` (ids of the layer's concepts applied by default).
- `joins`: relationship keys only (`<entity>.<key>`), never SQL. The gate fails on an unknown key, on a relationship with `status: unresolved`, and on a join whose ends the layer does not read.
- `concepts`: named filters, each one of three forms:
  - a field with a value vocabulary (`field`, `values`);
  - a predicate in the D-017 expression form over the layer's entities (`predicate`);
  - a distinct rule (`distinct`): the fields on which rows of an entity are made distinct before the layer joins to it, for a code list that repeats its rows.
  `required: true` marks a concept every query must apply.
- `measures`: `id`, `meaning`, `expression` over physical fields (parsed by sqlglot, neutral dialect, columns `<entity>.<field>`), `aggregation` (vocabulary `measure_aggregation`), `grain` (the entity and the key fields a result row is at), `time` (the field that carries time and its `granularity`, vocabulary `time_granularity`), `formula_source` (the evidence id of a documented formula), `hazards` (hazard ids the measure inherits), and `suppressed` (vocabulary `suppressed_handling`: what the measure does with cells the platform withheld; `companion` names the measure that counts them).
- `hazards`: the hazards the layer inherits. The gate fails when an active hazard applies to an entity or relationship the layer reads, or is listed on a field the layer uses, and the layer does not list it.

A consumer (`semantic/<layer-id>/consumer.yaml`) has `id`, `meaning`, `layers`, `corpus` (`location` relative to the layer folder, or `pin` for a corpus outside the repository), `threshold` (default 0.9, D-021) and `interface` (the `compile` entry point, `<path>:<function>` relative to the model root).

The flat `filters` list is removed (its job moves to `entities[].current_row_rule` and `default_filters`); a concept's `field` becomes optional (one of three forms); a measure's `field` and `time_field` are replaced by `expression` and `time`. These remove and rename keys, so under D-018 the schemas go from 1.0.0 to **2.0.0**.

The gate gets a stage `layers` that checks all of the above; `status: reviewed` requires an accepted equivalence run for the layer (wired with the harness).

## Consequences

- Schemas 2.0.0; `spec/VERSIONING.md`, `spec/SPEC.md` and `spec/VOCABULARY.md` section 9 describe the contract; new vocabulary blocks `measure_aggregation`, `time_granularity`, `suppressed_handling`.
- No model in the repository had a layer, so nothing migrates; `fact migrate` still has no migrations.
- Hard cases: free SQL in `joins`, a missing inherited hazard, a join over an unresolved relationship, a valid minimal layer.

## Evidence

- Owner decision in the owner brief of 2026-10-27 on M3 semantic layers (private working notes), sections 0 and 2 (pre-approved).
- QCEW findings F-0001, F-0002, F-0003, F-0006, F-0008 and hazards H-0001, H-0002 (`examples/qcew/registers/`).

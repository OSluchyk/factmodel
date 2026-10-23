# Brief - Rounds 2 to 7: finish M0 and build the M1 core (continuous run)

Date: 2026-10-23 · Owner: Oleksandr Sluchyk
Repository: `~/AI/semantic/factmodel` (renamed in round 2a), branch `main`, start at the round 2a commit (`b11fa64` + the rename).
Read first: `AGENTS.md`, `spec/SPEC.md`, `spec/VOCABULARY.md`, `spec/IMPLEMENTATION_PLAN.md`, `rounds/2026-10-23-report-wp0.1-wp0.2.md`, `rounds/2026-10-23-report-rename-factmodel.md`.

## 1. Mode: continuous rounds

This brief covers six rounds. Do them one after another without waiting for the owner. The owner reviews the final report and the git log at the end.

Per round:

1. `git status --short` must be empty. If not, stop (section 7).
2. Read the work package in `spec/IMPLEMENTATION_PLAN.md` and the decisions in section 2 of this brief.
3. Do the work. Keep `AGENTS.md` rules.
4. Run every check: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest -q`. All green before you go on.
5. Re-read the work package's acceptance list and tick every item in the report.
6. Write `rounds/<date>-report-<wp>.md` (format in `AGENTS.md`) and a `CHANGELOG.md` entry with the why.
7. Commit: one commit per round, message `WPx.y: <one line>` plus a body with the why. Author is the repository's git identity. No attribution lines, no tags, no amend, no rebase, no push.
8. Next round.

After round 7, write `rounds/<date>-report-m0-m1-core-final.md` (section 8) and stop.

Do not bump `__version__` (stays `0.0.1` until M1 closes).

## 2. Decisions (record each as a decision record in round 2, before any schema work)

**D-006 Data quality instead of a boolean.** Rename the `representative` block to `data_quality` with values `representative | synthetic | unknown`. Probe evidence carries `data_quality`. Reason: a tri-state as strings `"true" | "false"` is a trap in YAML and in code.

**D-007 Subject scope is derived, not authored.** Principle 2 of the spec applies: scope is computed. What is authored:

- on an entity: `anchor_reference: {field: <field name>, evidence: [...]}` when a field holds the anchor key (this is what makes `direct`); absent otherwise;
- on a relationship: optional `scope_admission: {basis: unique_target | current_row_rule | measured_fanout, evidence: [...]}` that lets scope pass through this relationship.

`fact project` computes per entity `subject_scope` (`direct | transitive | none`), the via-path and the basis, into `generated/scope.tsv`. `subject_scope` and `scope_basis` are removed from authored entity files and added to the derived-value list. `declared_reference` leaves the `scope_basis` block (it is the direct case, expressed by `anchor_reference`). Update `spec/VOCABULARY.md` sections 5, 6 and the derived block, the plan (WP0.4 algorithm 2, the `orders.yaml` example, WP1.2), and the spec's entity row. Reason: an authored claim checked against a computed closure is a second source for one fact; the mismatch class of errors disappears when only the facts are authored.

**D-008 The agent commits per round.** Already recorded in round 2a; apply it: one commit at the end of each round, never push, never amend or rewrite history, no attribution lines.

**D-009 One review status for entities and layers.** Rename the `entity_status` block to `review_status` (`draft | reviewed | deprecated`); entities and layers both use it. WP3.1's `draft | reviewed` is corrected in the plan.

Names after round 2a: product FactModel, package `factmodel`, command `fact`, config `factmodel.yaml`.

**Answers to the round-1 questions (no decision record needed; apply them):**

- Q1: an evidence record from a probe carries `probe: <probe-id>`; the `probe-result` file is the raw output, intake writes the evidence record.
- Q5: evidence records are one schema. Inline in the file of the fact they prove, or standalone in `evidence/` when several facts share them. IDs are unique across the model; the loader checks it.
- Q6: register statuses and default ranks from your report are accepted as written.
- Q7: add `current_row_ties` and `value_set` to `probe_kind` now.
- Q8: `environment` and `tenant` stay free slugs.

## 3. Round 2 - WP0.3 JSON Schemas

Plan reference: WP0.3, with D-006, D-007, D-009 applied first.

Deliverables: `schemas/<kind>.schema.json` for every file kind in `vocabulary:file_kind` plus `schemas/snapshot.schema.json` (engine-neutral metadata snapshot: objects, fields with paths and types, declared constraints, partitioning, options); `schemas/README.md` (how enumerations are kept in sync with the vocabulary); `tests/fixtures/schemas/<kind>/valid/` and `invalid/` (at least 3 invalid per kind, each failing for one named reason, the reason in the file name); `tests/test_schemas.py`.

Rules:

- Draft 2020-12. `additionalProperties: false` everywhere except `extensions:` (free map, never read by the core).
- Every enumeration in a schema is generated from `factmodel.vocabulary`, never typed: write `src/factmodel/schemas/build.py` that renders the schemas from templates plus the vocabulary, and a test that the committed schemas equal a fresh render.
- Derived keys (`label`, `subject_scope`, `subject_scoped`, `scope_basis`, `reachable`, `residue`, `withheld`) are rejected in authored files; one invalid fixture per derived key on the entity schema.
- Evidence: `quote` or `measurement`, not both; `retracted` requires `named_error` and `superseded_by`; `data_quality` and `environment` required when `probe` is set.
- Relationship: `key` required; `to` is a string or a list of at least two strings; `discriminator` allowed only with a list.
- Field: `path` and `name` both present for nested fields; `repeated` boolean.
- Nested-field fixture (one STRUCT, one ARRAY) and an inherited-evidence fixture (fields without `evidence`) are in the valid set.

Acceptance: `pytest tests/test_schemas.py` validates every valid fixture and rejects every invalid one at the expected JSON path; the render test passes; `fact --version` still works.

## 4. Round 3 - WP0.4 Algorithms and WP0.5 spec freeze

Plan reference: WP0.4, WP0.5.

Deliverables: `spec/ALGORITHMS.md` (projection with rule 0; scope closure per D-007; release partition), `tests/vectors/<algorithm>/<case>.yaml` (input model files + expected output), `tests/test_vectors.py` that loads every vector against the schemas (no algorithm code yet - the vectors are data, the test checks they are valid input).

Vectors to include at least: projection - one per rule, a tie, a residue, a target-set agreement, a target-set disagreement, a discriminator case; scope - direct, chain of three, cycle, reference blocks propagation, missing admission rejected, two paths with different bases; release - complete partition, residue file, undeclared key.

Spec freeze: update `spec/SPEC.md` links (vocabulary, algorithms, schemas), set its version line to `0.1`, record `spec-v0.1` in `CHANGELOG.md`. Do not create a git tag; the owner tags.

Acceptance: every vector validates; `spec/ALGORITHMS.md` has a worked example per rule.

## 5. Round 4 - WP1.1 Model loader

Plan reference: WP1.1.

Deliverables: `src/factmodel/io/yaml_strict.py`, `src/factmodel/model/loader.py`, `src/factmodel/model/types.py`, `tests/model/`.

Acceptance: as in the plan, plus a parity test over `tests/fixtures/schemas/*/valid` (pydantic accepts exactly what the JSON Schema accepts), error messages with file, line, column and a fix hint, and a loader test for every reference error (missing entity, missing evidence ID, duplicate evidence ID, duplicate relationship key, unregistered source).

## 6. Rounds 5 to 7

**Round 5 - WP1.2 Projection and scope library.** `src/factmodel/core/{projection,scope,derived}.py`; `fact project` writes `generated/{labels,scope,residue}.tsv` with the header the vocabulary names. All vectors from round 3 pass as executable tests. Hypothesis tests: determinism, file order does not matter, an unrelated entity changes nothing.

**Round 6 - WP1.3 Gate runner + WP1.4 CLI skeleton.** Stages from the plan table, each with a failing fixture in `tests/fixtures/gate/<stage>/`; `gate.yaml`; `fact check`, `fact init --profile <name> <dir>` (writes `factmodel.yaml`, layout, `AGENTS.md` and skills placeholders from `agent/` templates - create minimal templates now, the full skills come in WP1.9 - `CHANGELOG.md`, `.github/workflows/fact-check.yml`), `fact source add`, `fact status`. The `triggers` stage is not in this round (WP1.6). End-to-end test: `init` → `source add` → `check` passes on the empty model. A first `profiles/retail/profile.yaml` is needed for `init` and `check`; write it from the plan's example and validate it against the profile schema.

**Round 7 - WP1.8b Hard-case fixtures, gate and projection parts.** Every case in the plan table except the probe expectations (`probe for ties generated`, `probe for null rate`), which are deferred to WP1.7 and noted in the report. Each case: a tiny model repository, `expected/` with the generated files and the gate verdict, a test that runs `fact project` and `fact check` on it. Every gate stage must have at least one hard case that fails it.

## 7. Stop conditions (stop the run, write the final report with what is done)

- A check cannot be made green inside the round after a reasonable attempt; do not weaken a test or a rule to pass.
- Doing the work would require changing a decision in `decisions/` or a principle in the spec.
- A dependency is missing and `uv add` cannot get it.
- Anything needs credentials or network beyond package installs.
- The working tree is not clean at a round start.

On a stop: finish the report for the current round with the state as it is, do not commit a red round, and write the final report.

## 8. Final report (`rounds/<date>-report-m0-m1-core-final.md`)

1. Outcome: which rounds completed, which stopped and why.
2. The git log for the run (`git log --oneline b11fa64..HEAD`).
3. Per round: acceptance checklist ticked, with the report path.
4. Spec, vocabulary and plan edits across the run (old → new, one line each).
5. Decisions created (D-006 to D-009 and any the run forced, each naming what forced it).
6. Confirmed / inferred / unknown across the run.
7. Divergences from this brief and from the plan.
8. Questions for the owner, grouped: blocking the next milestone / can wait.
9. Suggested next brief: WP1.5 BigQuery adapter and WP1.5b git adapter - what the owner must provide (a metadata snapshot of `thelook_ecommerce` exported with credentials, or confirmation that the agent may query the public dataset).

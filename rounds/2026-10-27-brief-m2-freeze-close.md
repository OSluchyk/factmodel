# Brief - Round 19: close the M2 freeze (one round)

Date: 2026-10-27 · Owner: Oleksandr Sluchyk · Status: approved
Repository: `~/AI/semantic/factmodel`, branch `main`, start at `3851c95`.
Read first: `rounds/2026-10-27-report-m2-final.md` (sections 7 to 10), `spec/CORE-CHANGES-M2.md`, `spec/VERSIONING.md`.

Rounds 15 to 18 are accepted. The stop in round 18 was correct. This round records the owner's answers and freezes the schemas. Same mode: clean tree, green checks with PostgreSQL through `docker compose`, round report, CHANGELOG entry with the why, one commit `WP2.3: core freeze, schemas 1.0.0 (D-018)`, no push, no tag, no amend, no attribution lines. `UV_PROJECT_ENVIRONMENT=.venv`. Leave the untracked `.claude/` folder alone.

## 1. D-018 Additive keys need a ledger line, not a decision record

Record D-018 first. Two parts:

1. Retroactive record for the three contract changes in `spec/CORE-CHANGES-M2.md` without a record: snapshot `pin` keys (round 8), optional probe `expected` plus `entity` and `note` (round 11), field `values` (round 14). All three add optional keys; none removes, renames or changes the meaning of an existing key. They stand. Platform that forced them: none (the framework's own probes and adapters).
2. The rule from here on, written into `spec/VERSIONING.md` and `AGENTS.md` rule 6: a decision record is required when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result. Adding an optional key, a vocabulary value or a probe kind needs a CHANGELOG entry and a line in the current core-change ledger, nothing more. A fix that makes code obey the existing schema is a defect fix, not a core change; it needs a CHANGELOG entry only.

Update the ledger: the three rows get D-018; add the rule as a note at the top.

## 2. Intake defect

Fix `fact probe intake` under the rule above (defect fix): for a probe on a field, the finding's `about` names the entity (or the relationship) and the field goes to `extensions.fact`, exactly as the QCEW example's F-0002 does by hand. Golden test with an out-of-range `value_set` and an out-of-range `null_rate`; the gate must pass on the result. Re-run intake on the QCEW example and check it is idempotent (zero diff).

## 3. The freeze

- `SCHEMA_VERSION = "1.0.0"`, schemas re-rendered, `$id` URNs at `1.0.0`; `VERSIONING.md` says the current version is 1.0.0 and that the next removal or rename is 2.0.0.
- `fact migrate` reports 1.0.0 for both examples; models at 0.1.0 are reported as compatible when every file validates (no migration exists yet) and the report names the version difference.
- Both examples and all hard cases green on the frozen schemas.
- The plan's M2 row becomes "done"; `spec/SPEC.md` roadmap line for M2 updated.

## 4. Answers to the "can wait" questions of the final report

- Q3: an owner brief is not a decision record. When a brief decides something that D-018's rule classes as a decision, the round records it (as this brief does with D-018).
- Q4: yes, a single-target relationship may carry a discriminator when the target's meaning depends on a field of the source (QCEW `agglvl_code`). Additive: vocabulary text, loader check that the discriminator field exists on the source; ledger line.
- Q5: yes, `status: unresolved` relationships may omit `join`; the `references` stage still checks `to`. Additive; ledger line.
- Q6: yes, add the DuckDB `dialect_runner` and JSON wrap entries to the vocabulary maps, with a test that the rendered script runs through the `duckdb` CLI when it is installed (skip otherwise).
- Q7: the BigQuery adopter run is the owner's, later; nothing to do.

## 5. Stop conditions

As before. A contract change that D-018's rule classes as a decision and that this brief does not name: stop.

## 6. Report

`rounds/<date>-report-m2-freeze.md`, the usual sections, with `fact migrate` output for both examples and the test counts before and after.

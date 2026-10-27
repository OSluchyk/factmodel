# Report - Round 19: WP2.3 core freeze, schemas 1.0.0 (D-018)

Date: 2026-10-27 · Brief: `rounds/2026-10-27-brief-m2-freeze-close.md` · Branch `main`, from `3851c95`

## 1. Outcome

D-018 was recorded first. The intake defect is fixed as a defect fix, the schemas are frozen at 1.0.0, and both examples and every hard case are green on them, so M2 is done.

The section 4 answers are in: single-target discriminators, join-less unresolved links and the DuckDB probe maps. No stop condition was hit.

Tests: **678 before, 694 + 1 skipped after** (with PostgreSQL; the skip is the `duckdb` CLI test, the CLI is not installed). Without `FACT_PG_DSN`: 672 + 6 skipped before, 688 + 7 skipped after.

## 2. Files

Created:

- `decisions/D-018-additive-keys-ledger.md` (first, before any other change)
- `tests/probes/test_intake_findings.py` and golden findings `tests/fixtures/probes/intake-findings/{value-set-customer-email-hash,null-rate-order-customer-id}.yaml`
- `tests/model/test_relationship_options.py` (5 tests)
- `tests/probes/test_duckdb_script.py` (3 tests)
- Schema fixtures `entity/valid/unresolved-without-join.yaml` and `entity/invalid/join-missing-when-resolved.yaml`
- `rounds/2026-10-27-brief-m2-freeze-close.md` (the owner's brief), this report

Updated:

- D-018 text: `AGENTS.md` (rule 6), `decisions/README.md`, `spec/VERSIONING.md`, `spec/CORE-CHANGES-M2.md`
- Intake: `src/factmodel/probes/intake.py`
- Freeze:
  - `src/factmodel/schemas/build.py` (`SCHEMA_VERSION = "1.0.0"`) and all 18 `schemas/*.schema.json` re-rendered
  - `src/factmodel/schemas/templates/model-config.yaml`, `model/types.py`, `repo.py` (`schema_version`)
  - `src/factmodel/migrate.py`
  - `examples/{chinook,qcew}/factmodel.yaml` (`schema_version: 1.0.0`)
  - `spec/IMPLEMENTATION_PLAN.md`, `spec/SPEC.md`
- Section 4:
  - Schema and code: `src/factmodel/schemas/templates/entity.yaml`, `model/types.py`, `model/loader.py`
  - `spec/VOCABULARY.md`
  - QCEW: `physical/entities/{annual,qtrly,area_titles,industry_titles}.yaml`, `registers/findings/F-0008.yaml`
- Tests:
  - `tests/fixtures/schemas/entity/{invalid → valid}/discriminator-with-single-target.yaml`
  - `tests/fixtures/schemas/model-config/valid/full.yaml`
  - `tests/gate/test_cli.py`, `tests/test_migrate.py`
  - `tests/probes/test_dialect_maps.py` (Trino replaces DuckDB as the unmapped example dialect)
- `CHANGELOG.md`

## 3. Verification

```text
Before (at 3851c95):
$ uv run pytest -q
672 passed, 6 skipped in 26.47s
$ FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
678 passed in 27.49s

After:
$ uv run ruff check .
All checks passed!
(exit 0)
$ uv run ruff format --check .
100 files already formatted
(exit 0)
$ uv run mypy src
Success: no issues found in 53 source files
(exit 0)
$ uv run pytest -q
688 passed, 7 skipped in 28.74s
$ FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
694 passed, 1 skipped in 30.20s
$ uv run python -m factmodel.schemas.build --check schemas
(exit 0)
$ uv run fact check --root examples/chinook
gate: pass
$ uv run fact migrate --root examples/chinook
model framework_version: 0.0.1
model schema_version: 1.0.0
installed framework: 0.0.1
installed schemas: 1.0.0
schema difference: same
compatible: every model file validates against the installed schemas
migrations: none needed
$ uv run fact check --root examples/qcew
gate: pass
$ uv run fact migrate --root examples/qcew
model framework_version: 0.0.1
model schema_version: 1.0.0
installed framework: 0.0.1
installed schemas: 1.0.0
schema difference: same
compatible: every model file validates against the installed schemas
migrations: none needed
$ for each hard case: uv run fact check (expected verdicts)
52 passed in 1.76s
```

Intake re-run on the examples (idempotence, zero diff):

```text
$ uv run fact probe intake --root examples/qcew examples/qcew/probes/results/qcew-sqlite@2026-10-27.jsonl
43 in range, 3 out of range, 0 failed, 0 rejected; 0 files written
$ uv run fact probe intake --root examples/chinook examples/chinook/probes/results/chinook-sqlite@2026-10-23.jsonl
45 in range, 0 out of range, 0 failed, 0 rejected; 0 files written
```

A model at 0.1.0 (`tests/test_migrate.py`, QCEW copy with `schema_version: 0.1.0`): exit 0. The output includes `schema difference: 0.1.0 -> 1.0.0 (major)` and `compatible: every model file validates against the installed schemas`. A model without the key (hard case `no-subject`): `not recorded (the model was written before schemas 1.0.0)`, compatible.

Acceptance:

- [x] **1.** D-018 recorded first: the three changes are retroactive, platform none. The rule is in `spec/VERSIONING.md`, `AGENTS.md` rule 6 and `decisions/README.md`. The ledger rows 7, 11 and 17 cite D-018, with the rule as a note at the top.
- [x] **2.** Intake names the entity for a field probe, with the field in `extensions.fact`; a relationship probe keeps the relationship. Golden test with out-of-range `value_set` and `null_rate`; the gate passes on the result. A second intake writes nothing, on the test model and on both examples.
- [x] **3.** `SCHEMA_VERSION` is 1.0.0; the schemas are re-rendered, the `$id` URNs end in `1.0.0`, and `--check` is clean. `VERSIONING.md` gives 1.0.0 as current and 2.0.0 as the next removal or rename. `fact migrate` reports 1.0.0 for both examples and names the difference for a 0.1.0 model. Examples and hard cases are green. The plan's M2 row says done, and so does the SPEC roadmap line.
- [x] **4.**
  - Q3: in D-018 and `AGENTS.md`.
  - Q4: single-target discriminator, with vocabulary text and the loader field check (existing check, now tested). QCEW uses `agglvl_code`.
  - Q5: an unresolved link may omit `join`, and `to` is still checked. QCEW's four placeholders are removed.
  - Q6: DuckDB in `dialect_json_wrap` and `dialect_runner`. The wrap is checked through the `duckdb` module; the CLI script test skips here.
  - Q7: nothing to do.

## 4. Spec edits

- `spec/VERSIONING.md`:
  - "After the freeze (M2), every minor or major change needs a decision record that names the platform that forced it" becomes the D-018 rule in three bullets, plus "An owner brief is not a decision record."
  - "Current schema version: **0.1.0**. The freeze to 1.0.0 is the M2 gate. It waits for ..." → "Current schema version: **1.0.0** (frozen in round 19, the M2 gate). The next removal or rename of a key is **2.0.0**; additive changes move it to 1.1.0 and on."
  - The `framework_version` section gains `schema_version` and the difference `fact migrate` reports.
- `spec/CORE-CHANGES-M2.md`:
  - A D-018 rule note at the top.
  - Rows 7, 11 and 17: "**none**" → "D-018 (retroactive)".
  - "Changes without a decision record" → "None since round 19 ...".
  - "Known defect" → "Defect fixes (D-018: CHANGELOG entry only)".
  - New rows 27 to 32 for round 19.
- `spec/VOCABULARY.md`:
  - `discriminator`: "Only with a target set: the field that selects the target per row. Without it, the target is chosen per tenant." → "A field of the source. With a target set, it selects the target per row; without it, the target is chosen per tenant. With a single target, it names the source field the target's meaning depends on (QCEW: `agglvl_code` gives the level of `industry_code`). The loader checks that the field exists on the source."
  - `join` gains "Required, except on an `unresolved` relationship, which may omit it when the join is not known."
  - `dialect_json_wrap` gains `duckdb: json_object_pairs`; `dialect_runner` gains `duckdb: 'duckdb -noheader -list "${DUCKDB_DB:?set DUCKDB_DB to the database file}"'`.
- `spec/IMPLEMENTATION_PLAN.md`: the M2 row's estimate gains "(done: rounds 15 to 19; BigQuery adopter run owner-pending)"; WP2.3 gains "Round 19: D-018 records the three retroactively and sets the rule for what a change needs; the schemas froze at 1.0.0. **M2 done.**"
- `spec/SPEC.md`, roadmap M2 row: title gains "(done: schemas 1.0.0)", the BigQuery item "(owner-pending)", the domain item "(`statistics`, QCEW)". The gate becomes "every core change in the ledger with its record (D-018: removals, renames and meaning changes need a decision; additions a ledger line)".
- `AGENTS.md` rule 6 gains the D-018 rule and "An owner brief is not a record."

## 5. Confirmed / inferred / unknown

**Confirmed**

- The frozen schemas validate every file of both examples and every hard case, with the expected verdicts.
- Intake output now passes the `references` stage for field probes; relationship and entity probes are unchanged.
- The DuckDB JSON wrap gives the expected counts for all 10 probes of the probe test model.

**Inferred**

- `schema_version` in `factmodel.yaml` is a new optional key, not named in the brief. Without it a model cannot say it is at 0.1.0, so `fact migrate` could not name a version difference. D-018 classes it as additive: ledger row 29, no decision record.
- 0.1.0 to 1.0.0 is reported as "major" by the number, although no key was removed. A model at 0.1.0 that validates is compatible, as the brief asks.
- A resolved relationship without a join now fails `schema` and `references` (`bad_join`); both are kept.

**Unknown**

- The DuckDB CLI runner line (`-noheader -list`, SQL on stdin) is untested here: the `duckdb` CLI is not installed, so that test skips.

## 6. Divergences

- Added the optional `schema_version` key (see section 5); it has a ledger line and no decision record.
- `tests/probes/test_dialect_maps.py` now uses Trino as the example of a dialect absent from the maps, since DuckDB is in them now.

## 7. Questions for the next round

1. Should `fact init` and `fact migrate --apply` keep `schema_version` current, and should the loader warn when it is newer than the installed schemas?
2. Should the framework version move to 1.0.0 with the schemas, or stay 0.x until M4 (release 1.0)?
3. M3: start with WP3.1 on QCEW as the final M2 report suggests?

## 8. Commit

Committed on `main` as `WP2.3: core freeze, schemas 1.0.0 (D-018)` with every file in section 2. The owner's untracked `.claude/` folder is not committed.

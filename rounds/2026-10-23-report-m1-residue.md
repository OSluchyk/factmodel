# Report - Round 14: M1 residue

Date: 2026-10-23 · Brief: `rounds/2026-10-23-brief-m1-residue.md` · Branch `main`, from `969a2f8`

## 1. Outcome

Probe dialect knowledge now lives in three vocabulary-map blocks instead of code. D-014 is recorded and applied: synthetic probe results attach to facts but no longer confirm them, unless an example model opts out. Q4, Q5, Q7, Q8 and Q9 are answered in code, spec and tests.

Tests: **608 before, 625 after** (with PostgreSQL through `docker compose`); without `FACT_PG_DSN`, 605 + 3 skipped before and 621 + 4 skipped after. All checks are green.

## 2. Files

Created:

- `decisions/D-014-synthetic-never-confirms.md`
- `tests/probes/test_dialect_maps.py`, `tests/probes/test_d014.py`
- `tests/fixtures/probes/intake-golden/{synthetic,unknown,treated,representative}.yaml`
- `examples/chinook/agent/{brief,report}.md`
- `rounds/2026-10-23-brief-m1-residue.md` (the owner's brief, committed with this round), this report

Updated:

- Section 1: `spec/VOCABULARY.md` (blocks `dialect_nested_paths`, `dialect_json_wrap`, `dialect_runner`); `src/factmodel/vocabulary.py` (map values may be text or booleans; `text_map`, `flag_map`); `src/factmodel/probes/__init__.py`, `probes/script.py` (read the maps; `WRAPS` holds the two strategies); `src/factmodel/adapters/export/__init__.py` (flavour chosen by module name, not a list of engines); `adapters/base.py`, `cli.py`, `model/loader.py` (use `text_map`)
- Section 2: `spec/SPEC.md`, `spec/VOCABULARY.md`, `schemas/templates/model-config.yaml` and `schemas/model-config.schema.json`, `model/types.py`, `probes/intake.py`, `examples/chinook/factmodel.yaml`, `agent/skills/probe-intake/SKILL.md` and its copy in the example, `decisions/README.md`
- Section 3:
  - Q4, Q9: `core/drafts.py`, `adapters/git/__init__.py`, regenerated `tests/fixtures/drafts/bigquery/` and `examples/chinook/drafts/`.
  - Q7: `schemas/templates/entity.yaml`, `schemas/entity.schema.json`, `model/types.py`, `probes/build.py`, `probes/__init__.py`.
  - Q8: `repo.py`, `agent/AGENTS.md`, `agent/README.md`, `examples/chinook/AGENTS.md`.
  - Q5: `spec/IMPLEMENTATION_PLAN.md`.
- Tests: `tests/test_vocabulary.py`, `tests/probes/test_probes.py`, `tests/adapters/test_git.py`, `tests/gate/test_cli.py`
- `CHANGELOG.md`

## 3. Verification

```text
Before (at 969a2f8):
$ FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
608 passed in 11.69s
$ uv run pytest -q
605 passed, 3 skipped in 11.03s

After:
$ uv run ruff check .
All checks passed!
(exit 0)
$ uv run ruff format --check .
88 files already formatted
(exit 0)
$ uv run mypy src
Success: no issues found in 51 source files
(exit 0)
$ uv run pytest -q
621 passed, 4 skipped in 13.94s
(exit 0)
$ FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
625 passed in 14.58s
(exit 0)
$ uv run fact check --root examples/chinook
...
gate: pass
(exit 0)
$ grep -rn 'NESTED_DIALECTS\|DEFAULT_RUN_SQL' src
(no output)
```

PostgreSQL 16 ran through `docker compose up -d --wait` and was stopped after the commit.

Acceptance:

- [x] **1.** Blocks `dialect_nested_paths`, `dialect_json_wrap` (strategies `json_object_pairs`, `row_to_json`), `dialect_runner`. The code keeps the strategies and reads the maps; a dialect absent from a map gets the neutral behaviour. A test adds a dialect to the maps only and sees rendering, the script runner and nested-path generation change. `grep -rn 'NESTED_DIALECTS\|DEFAULT_RUN_SQL' src` prints nothing, and the probes package names no dialect.
- [x] **2.** D-014 recorded before intake changed. Intake confirms only on `representative` data; `synthetic` and `unknown` results are `inferred` evidence, cited, and the fact stays `inferred`. `treat_synthetic_as_representative` added to the schema, typed model and vocabulary, and set in `examples/chinook/factmodel.yaml`. Old rule recorded as superseded in the spec's evidence paragraph and the vocabulary. Golden tests for both settings (plus `unknown` and `representative`).
- [x] **Q4.** Drafts keep the engine's constraint names in `extensions.draft.constraint_name` (relationship key to name).
- [x] **Q5.** Plan WP1.6: "`fact sync` stays offline: it reads the latest committed snapshot; taking a new one is `fact snapshot`." No code change.
- [x] **Q7.** A field may declare `values`; `fact probe generate` adds a `value_set` probe that returns `distinct_values` and `outside_values` (distinct values outside the set), never the values; expected `outside_values` at most 0. Verified on SQLite and PostgreSQL.
- [x] **Q8.** `fact init` copies `agent/templates/brief.md` and `report.md` into the model's `agent/` folder.
- [x] **Q9.** The git adapter reads `COMMENT ON TABLE|VIEW|COLUMN`, inline column comments and description options (tested in PostgreSQL, MySQL, Snowflake and BigQuery DDL). Drafts turn each description into the proposed meaning with an `inferred` record quoting it.

## 4. Spec edits

- `spec/SPEC.md`, Evidence paragraph: "Shares measured on test data do not carry over to production; a zero-violation result does." → "Only a result on representative data confirms a fact; a result on synthetic or unknown data is kept as `inferred` evidence (D-014). Superseded: the earlier rule that a zero-violation result on test data carries over to production. Example models whose platform is itself synthetic may set `treat_synthetic_as_representative: true`."
- `spec/VOCABULARY.md`:
  - Evidence status table: `confirmed` by "a probe whose result on representative data is in its expected range (D-014)".
  - Data-quality paragraph rewritten for D-014, with the superseded sentence quoted.
  - Field table: new `values` row.
  - New "Drafts" paragraph (constraint names, comments as `inferred` evidence).
  - `value_set` row now counts values outside the declared set.
  - New "Dialect knowledge for probes" paragraph and three map blocks; the intake sentence follows D-014.
- `spec/IMPLEMENTATION_PLAN.md`, WP1.6: the Q5 sentence.

## 5. Confirmed / inferred / unknown

**Confirmed**

- Behaviour is unchanged for SQLite and PostgreSQL after the move to maps: the golden renderings and the rendered SQLite script test pass as before.
- `value_set` gives the same counts on SQLite and PostgreSQL.
- The Chinook gate stays green with the flag set; its committed evidence did not change.

**Inferred**

- D-014 treats `unknown` like `synthetic`: only `representative` confirms.
- Comments become `inferred` evidence for every adapter that reports descriptions (`sql` reflection comments, BigQuery descriptions in exports), not only for git DDL, since `to_facts` is one core function; a field with a comment cites both the catalog record and the comment record.
- `extensions.draft.constraint_name` is a map from relationship key to the engine's name, because an entity may have several foreign keys.
- `outside_values` counts distinct values outside the domain, not rows; nulls are not counted as outside.
- `values` items may be text or numbers, so integer codes compare as numbers.

**Unknown**

- How `json_object_pairs` behaves for dialects added later with different JSON functions; adding a third strategy is a code change, choosing among existing ones is not.

## 6. Divergences

- The export adapter's flavour choice also left the code (it listed `bigquery` and `postgres`); it now imports the flavour module named after the engine, else `generic`. Same rule as section 1, one more place.
- Mapping blocks now allow text and boolean values (keys stay slugs); `engine_dialect` is read through `text_map`, which requires text values.
- No hard case relies on intake (their probe evidence is written by hand with `data_quality: representative`), so no hard case needed the flag.

## 7. Questions for the next round

1. Should `outside_values` also report a row count (rows with a value outside the domain), or are distinct values enough?
2. Should `fact init` write `treat_synthetic_as_representative: false` explicitly, so the setting is visible?

## 8. Commit

Committed on `main` as `Round 14: M1 residue` with every file in section 2.

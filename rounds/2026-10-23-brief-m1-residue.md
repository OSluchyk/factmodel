# Brief - Round 14: M1 residue (one round)

Date: 2026-10-23 · Owner: Oleksandr Sluchyk · Status: approved
Repository: `~/AI/semantic/factmodel`, branch `main`, start at `969a2f8`.
Read first: `AGENTS.md`, `rounds/2026-10-23-report-m1-close-final.md` (sections 6 to 8), `decisions/D-011-engine-blind-core.md`.

Rounds 8 to 13 are accepted. This round closes what the review found and answers the "can wait" questions, so M2 starts from a clean core. Same mode as before: clean tree, green checks, round report, CHANGELOG entry with the why, one commit `Round 14: M1 residue`, no push, no tag, no amend, no attribution lines. `UV_PROJECT_ENVIRONMENT=.venv`. PostgreSQL through `docker compose` as in rounds 8 to 13.

## 1. Dialect knowledge leaves the code (review finding)

D-011 says engine knowledge lives in vocabulary blocks, not in code. Three places in `src/factmodel/probes/` break that: `NESTED_DIALECTS`, the `sqlite` / `postgres` branches in `json_wrapped`, and `DEFAULT_RUN_SQL` in `script.py`.

- Add `vocabulary-map` blocks: `dialect_nested_paths` (dialect to `true`), `dialect_json_wrap` (dialect to a strategy name from a small set the code implements: `json_object_pairs`, `row_to_json`), `dialect_runner` (dialect to the shell command that reads one statement on stdin and prints one JSON object).
- The code keeps the strategies and reads the maps. A dialect absent from a map gets the neutral behaviour it gets today (raw SQL, `RUN_SQL` required).
- Test: a new dialect added to the maps in a test fixture changes rendering without a code change; the three names above no longer appear in `src/` (`grep -rn 'NESTED_DIALECTS\|DEFAULT_RUN_SQL' src` prints nothing).

## 2. Decision D-014: synthetic data never confirms a fact about a platform

A probe result with `data_quality: synthetic` proves that the mechanism works, not that the platform holds the fact. Intake moves a fact to `confirmed` only when `data_quality` is `representative`; a `synthetic` result attaches the probe and leaves the fact `inferred`. Example and test models may set `treat_synthetic_as_representative: true` in `factmodel.yaml` (schema, typed model, vocabulary text); then intake behaves as today. Set it in `examples/chinook/factmodel.yaml` and in any hard case that relies on probe evidence. Record the old behaviour as superseded in the spec paragraph on probe evidence. Golden tests for both settings.

## 3. Answers to the "can wait" questions of the final report

- Q4 yes: drafts keep the engine's constraint name in `extensions.draft.constraint_name`.
- Q5 `fact sync` stays offline and reads the latest committed snapshot; taking one is `fact snapshot`. Write that sentence into the plan at WP1.6; no code change.
- Q7 yes: generate `value_set` for a field that declares a value domain; the probe returns the count of distinct values and the count of values outside the declared set, never the values.
- Q8 yes: `fact init` copies `agent/templates/brief.md` and `report.md` into the model's `agent/` folder.
- Q9 yes: DDL `COMMENT ON` (and inline column comments where the dialect has them) become field and entity descriptions in the git adapter, with an `inferred` evidence record quoting the comment.

## 4. Not in this round

- Marking the Chinook entities `reviewed`: owner review, later.
- The second domain and the BigQuery adopter run: M2 brief.
- Fixture example values that still say `thelook`: leave them.

## 5. Stop conditions

As in the previous brief. Doing the work would change a decision or a spec principle beyond D-014: stop.

## 6. Report

`rounds/<date>-report-m1-residue.md`, the usual sections. State the test count before and after.

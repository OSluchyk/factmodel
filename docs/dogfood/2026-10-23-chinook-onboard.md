# Dogfood: onboarding Chinook with the `model-onboard` skill

Date: 2026-10-23 · Round 13 (WP1.9) · Who: the agent of the framework run, in the same session that built the skill

## Goal

Redo WP1.8 steps 1 and 2 (snapshot and draft) for `examples/chinook`, following only the text of `agent/skills/model-onboard/SKILL.md`, into a temporary folder, and compare the result with what is committed in `examples/chinook`.

## What was done

Each step names the skill step it followed.

1. `fact adapters` (step 1 hint): listed `export`, `git`, `sql`.
2. `fact init <tmp>/chinook-model --profile retail` (step 1): 27 files; `anchor_entity: customer` from the profile's subject.
3. `fact source add --root <tmp>/chinook-model --id chinook-sqlite --title "Chinook on a local SQLite file" --kind warehouse --access-mode agent_read --adapter sql --engine sqlite --location chinook --dsn-env FACT_DSN_CHINOOK_SQLITE` (step 2).
4. The owner's part: a local engine seeded with synthetic rows (`examples/chinook/seed/seed.py`), and `FACT_DSN_CHINOOK_SQLITE` set in the environment. A test fixture, not a platform (D-011).
5. `fact snapshot --root <tmp>/chinook-model --source chinook-sqlite --date 2026-10-23` (step 3, live reflection): 11 objects.
6. `fact draft --root <tmp>/chinook-model --source chinook-sqlite` (step 4): 11 drafts.
7. `fact check --root <tmp>/chinook-model` (step 5): `gate: pass`.
8. Steps 5 and 6 again: snapshot unchanged, 0 drafts written.

## Result

- `drafts/chinook-sqlite/` is identical to `examples/chinook/drafts/chinook-sqlite/` (`diff -r`: no difference).
- `sources/snapshots/chinook-sqlite@2026-10-23.yaml` is identical to the committed snapshot.
- The acceptance list of the skill holds: one snapshot, `current_pin` set, one draft per object with its placeholders listed, `fact check` passes, a second run changes no file.

## Gaps found and fixed

- `fact source add` could not set `adapter`, `dsn_env`, `dialect`, `revision` or `include`, so step 2 could not be done with commands alone. The options were added in round 13 before the run.

## Limits

- The agent that ran this also wrote the skill; a fresh session with only the repository and the brief "onboard chinook" is the stronger test and stays with the owner.
- `tests/examples/test_dogfood.py` repeats this run on every test run, so the skill's commands and the committed drafts cannot drift apart unnoticed.

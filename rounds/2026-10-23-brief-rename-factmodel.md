# Brief - Round 2a: rename Plumbline to FactModel

Date: 2026-10-23 · Owner: Oleksandr Sluchyk
Repository: `~/AI/semantic/plumbline`, branch `main`, start at `b11fa64`.
Run this round before `rounds/2026-10-23-brief-m0-m1-core.md`.

## 1. Decision

**D-010 Name: FactModel.** The product is FactModel; the Python distribution and import name is `factmodel`; the command is `fact`; the model-config file is `factmodel.yaml`. `plumbline-model` and `plb` are retired before any public push. Supersedes the name part of D-003 (D-003's PyPI and GitHub findings stay valid history). Reason: a name that says what the thing is - a model made of proven facts - beats a metaphor that needs a paragraph. `factmodel` was free on PyPI on 2026-10-23 (`https://pypi.org/project/factmodel/` returned 404); GitHub is not checked, the owner checks before the first push.

**D-008 The agent commits per round.** Record it in this round (it was planned for round 2): one commit at the end of each round on the branch the brief names, never push, never amend or rewrite history, no attribution lines. `AGENTS.md` rule 4 changes accordingly. The owner reviews the log and pushes.

## 2. Scope of the rename

Rename everywhere except history: `decisions/*` (unchanged; D-010 says that paths in earlier records read as `src/factmodel/` from this commit on), `rounds/*-report-*` and `rounds/2026-10-23-brief-wp0.1-wp0.2.md` (unchanged), past `CHANGELOG.md` entries (unchanged).

Mapping:

| From | To |
| --- | --- |
| `Plumbline` (prose) | `FactModel` |
| `plumbline` (package, paths, config key names) | `factmodel` |
| `plumbline-model` (distribution) | `factmodel` |
| `plb` (command) | `fact` |
| `plumbline.yaml` | `factmodel.yaml` |
| `src/plumbline/` | `src/factmodel/` (use `git mv`) |

Files to touch: `pyproject.toml` (name, script `fact = "factmodel.cli:app"`, hatch wheel package and force-include paths, mypy files), `src/factmodel/*` (module docstrings, `resources.files("factmodel")`), `tests/*`, `AGENTS.md` (rule 4 per D-008, rule 7 import path), `README.md`, `NOTICE` ("FactModel - Copyright 2026 Oleksandr Sluchyk"), `CONTRIBUTING.md`, `spec/SPEC.md`, `spec/VOCABULARY.md`, `spec/IMPLEMENTATION_PLAN.md`, `rounds/2026-10-23-brief-m0-m1-core.md` (names, commands, paths; its start commit becomes "the round 2a commit"; its D-008 paragraph becomes "already recorded in round 2a, apply it"), `uv.lock` (regenerate with `uv lock`).

`spec/SPEC.md`: replace the "Why the name" and "Alternatives" paragraphs with one paragraph: FactModel is a model made of facts about a data platform, each with its evidence; semantic layers stand on it. Open question "Name: trademark check before the first public push" stays, now for FactModel.

Decisions `decisions/D-008-agent-commits.md` and `decisions/D-010-name-factmodel.md` in the format of `decisions/README.md`; add both to the index table there.

## 3. Verification

```bash
uv lock && uv sync
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q
uv run fact --version          # prints: fact 0.0.1
grep -rIn -i 'plumbline' --exclude-dir=.git --exclude-dir=.venv . | grep -v -E '^\./(decisions/|rounds/2026-10-23-(report|brief-wp0\.1)|CHANGELOG\.md)'   # must print nothing
grep -rInw 'plb' --exclude-dir=.git --exclude-dir=.venv . | grep -v -E '^\./(decisions/|rounds/2026-10-23-(report|brief-wp0\.1)|CHANGELOG\.md)'       # must print nothing
grep -rnP '\x{2014}' --include='*.md' --include='*.py' --include='*.toml' . | grep -v '^\./\.venv'   # must print nothing
```

## 4. Report and commit

`rounds/2026-10-23-report-rename-factmodel.md`: outcome, files changed, verification output pasted as is, divergences, questions. `CHANGELOG.md` entry with the why. Then one commit: `Rename Plumbline to FactModel (D-010); agent commits per round (D-008)` with a body. No push.

After the commit, the owner renames the folder: `mv ~/AI/semantic/plumbline ~/AI/semantic/factmodel` and starts the next brief from the new path.

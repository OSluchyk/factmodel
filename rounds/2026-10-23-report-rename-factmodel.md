# Report - Round 2a: rename Plumbline to FactModel

Date: 2026-10-23 · Brief: `rounds/2026-10-23-brief-rename-factmodel.md` · Branch `main`, from `b11fa64`

## 1. Outcome

The project is renamed to FactModel everywhere outside history: distribution and import `factmodel`, command `fact`, model config `factmodel.yaml`, package in `src/factmodel/`. D-008 (the agent commits per round) and D-010 (the name) are recorded, `AGENTS.md` rule 4 and the round workflow docs follow D-008, and all checks pass.

## 2. Files changed

Moved with `git mv`:

- `src/plumbline/` to `src/factmodel/` (`__init__.py`, `cli.py`, `py.typed`, `vocabulary.py`)

Created:

- `decisions/D-008-agent-commits.md`
- `decisions/D-010-name-factmodel.md`
- this report

Updated:

- `pyproject.toml` - name `factmodel`, script `fact = "factmodel.cli:app"`, wheel package and force-include paths, mypy files.
- `uv.lock` - regenerated with `uv lock`.
- `src/factmodel/__init__.py`, `cli.py`, `vocabulary.py` - docstrings, command name, `resources.files("factmodel")`.
- `tests/test_smoke.py`, `tests/test_vocabulary.py` - imports, expected `fact 0.0.1`.
- `AGENTS.md` - product name; rule 4 per D-008; rule 7 import path; report item 8 lists the commit instead of a `git add` list.
- `README.md`, `NOTICE`, `CONTRIBUTING.md` - name, command; round workflow and commit rules per D-008.
- `rounds/README.md` - round steps per D-008 (agent commits, owner reviews and pushes).
- `spec/SPEC.md` - name, commands, layout, `factmodel.yaml`; "Why the name" and "Alternatives" replaced by one paragraph; package-name open question now points to D-010.
- `spec/VOCABULARY.md` - name, commands, `factmodel.yaml`, source path.
- `spec/IMPLEMENTATION_PLAN.md` - name, commands, paths; D-008 wording in sections 1, 2 and 11; `PLB_LIVE_*` flags renamed `FACT_LIVE_*`; name rows point to D-010.
- `rounds/2026-10-23-brief-m0-m1-core.md` - removed the sentence that mapped old names ("Every `plumbline` and `plb` below is to be read with those names"); there were no old names below it. Its start line and D-008 paragraph already had the wording the brief asks for.
- `decisions/README.md` - D-008 and D-010 added to the index; D-003's index status reads "name part superseded by D-010" (the D-003 file is unchanged).
- `CHANGELOG.md` - new entry with the why.

Unchanged as history: `decisions/D-001` to `D-005`, `rounds/2026-10-23-brief-wp0.1-wp0.2.md`, `rounds/2026-10-23-report-wp0.1-wp0.2.md`, the round 1 `CHANGELOG.md` entry, and this round's brief.

## 3. Verification

```text
$ uv lock && uv sync
Resolved 42 packages in 295ms
Added factmodel v0.0.1
Removed plumbline-model v0.0.1
Resolved 42 packages in 4ms
   Building factmodel @ file:///Users/Oleksandr_Sluchyk/AI/semantic/plumbline
      Built factmodel @ file:///Users/Oleksandr_Sluchyk/AI/semantic/plumbline
Prepared 1 package in 456ms
Uninstalled 1 package in 1ms
Installed 1 package in 1ms
 + factmodel==0.0.1 (from file:///Users/Oleksandr_Sluchyk/AI/semantic/plumbline)
 - plumbline-model==0.0.1 (from file:///Users/Oleksandr_Sluchyk/AI/semantic/plumbline)
(exit 0)
$ uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest -q
All checks passed!
5 files already formatted
Success: no issues found in 3 source files
...............                                                          [100%]
15 passed in 0.39s
(exit 0)
$ uv run fact --version
fact 0.0.1
(exit 0)
```

The two name greps as written in the brief print every match in the repository on this machine: `grep` here is ugrep 7.8.4, which prints paths without the `./` prefix, so the filter `^\./(...)` never matches. With the filter changed to `^(\./)?(...)`, the output is:

```text
$ grep -rIn -i 'plumbline' --exclude-dir=.git --exclude-dir=.venv . | grep -v -E '^(\./)?(decisions/|rounds/2026-10-23-(report|brief-wp0\.1)|CHANGELOG\.md)'
rounds/2026-10-23-brief-rename-factmodel.md:1:# Brief - Round 2a: rename Plumbline to FactModel
rounds/2026-10-23-brief-rename-factmodel.md:4:Repository: `~/AI/semantic/plumbline`, branch `main`, start at `b11fa64`.
rounds/2026-10-23-brief-rename-factmodel.md:9:**D-010 Name: FactModel.** ... `plumbline-model` and `plb` are retired before any public push. ...
rounds/2026-10-23-brief-rename-factmodel.md:21:| `Plumbline` (prose) | `FactModel` |
rounds/2026-10-23-brief-rename-factmodel.md:22:| `plumbline` (package, paths, config key names) | `factmodel` |
rounds/2026-10-23-brief-rename-factmodel.md:23:| `plumbline-model` (distribution) | `factmodel` |
rounds/2026-10-23-brief-rename-factmodel.md:25:| `plumbline.yaml` | `factmodel.yaml` |
rounds/2026-10-23-brief-rename-factmodel.md:26:| `src/plumbline/` | `src/factmodel/` (use `git mv`) |
rounds/2026-10-23-brief-rename-factmodel.md:40:grep -rIn -i 'plumbline' ...   # must print nothing
rounds/2026-10-23-brief-rename-factmodel.md:47:... Then one commit: `Rename Plumbline to FactModel (D-010); agent commits per round (D-008)` with a body. No push.
rounds/2026-10-23-brief-rename-factmodel.md:49:After the commit, the owner renames the folder: `mv ~/AI/semantic/plumbline ~/AI/semantic/factmodel` ...
(exit 0)
$ grep -rInw 'plb' --exclude-dir=.git --exclude-dir=.venv . | grep -v -E '^(\./)?(decisions/|rounds/2026-10-23-(report|brief-wp0\.1)|CHANGELOG\.md)'
rounds/2026-10-23-brief-rename-factmodel.md:9:**D-010 Name: FactModel.** ... `plumbline-model` and `plb` are retired before any public push. ...
rounds/2026-10-23-brief-rename-factmodel.md:24:| `plb` (command) | `fact` |
rounds/2026-10-23-brief-rename-factmodel.md:41:grep -rInw 'plb' ...       # must print nothing
(exit 0)
$ grep -rnP '\x{2014}' --include='*.md' --include='*.py' --include='*.toml' . | grep -v -E '^(\./)?\.venv'
(exit 1, no output)
```

Long lines are shortened with `...` here. The only remaining matches are in this round's brief, which describes the rename and must keep the old names; the brief's filter does not exclude it.

Extra check: `uv build --wheel` into a scratch directory gives `factmodel-0.0.1-py3-none-any.whl` with `factmodel/VOCABULARY.md` and the entry point `fact = factmodel.cli:app`.

## 4. Divergences

- The name greps need `^(\./)?` instead of `^\./` on this machine (ugrep), and this round's brief still matches; both are explained in section 3.
- `PLB_LIVE_BQ` and `PLB_LIVE_PG` in the plan became `FACT_LIVE_BQ` and `FACT_LIVE_PG`. The brief's mapping does not list them, but they are the old command name in uppercase.
- D-008 wording was also applied to `CONTRIBUTING.md`, `rounds/README.md` and the plan (sections 1, 2 and 11), not only `AGENTS.md`, so no file says "the owner commits".
- The plan's WP1.9 line about the model-repository `AGENTS.md` template ("never commit") was left unchanged: D-008 covers this repository, not model repositories. D-008 says so.
- `decisions/README.md` changed the D-003 index status to "name part superseded by D-010"; the D-003 file itself is unchanged.
- I deleted the local `.mypy_cache`, `.ruff_cache` and `.pytest_cache` folders (ignored by git, rebuilt by the checks) because they held the old package name.
- `.idea/plumbline-model.iml` (the IDE's project file, ignored by git) still has the old name; I left it alone.

## 5. Questions

1. Should the brief's grep checks use `^(\./)?` so they work with both GNU grep and ugrep, and also exclude the rename brief?
2. Should the model-repository agent template (WP1.9) also let the agent commit per round, or keep "never commit"?
3. GitHub check for `factmodel` is still open (D-010); do you want it done in the next round?

## 6. Commit

One commit on `main`, no push:

```text
Rename Plumbline to FactModel (D-010); agent commits per round (D-008)

Rename the product, distribution, import, command and model-config
file: FactModel, factmodel, fact, factmodel.yaml. The package moves
to src/factmodel/. A name that says what the thing is beats a
metaphor that needs a paragraph, and nothing was public yet.

The agent now makes one commit per round and never pushes, amends
or adds attribution lines. AGENTS.md rule 4, CONTRIBUTING.md,
rounds/README.md and the plan follow.

Decision records, earlier round reports and past changelog entries
keep the old names as history.
```

After this commit, the owner renames the folder: `mv ~/AI/semantic/plumbline ~/AI/semantic/factmodel`.

# Agent layer templates

Files that `fact init` copies into a new model repository. This is a minimal version; the full skills and the brief and report templates come in WP1.9.

| Template | Copied to | Purpose |
| --- | --- | --- |
| `AGENTS.md` | `AGENTS.md` | Invariants for agents working on a model repository. |
| `skills/` | `.claude/skills/` | One folder per skill with a `SKILL.md`. |
| `templates/CHANGELOG.md` | `CHANGELOG.md` | The model's changelog, newest first, with the why. |
| `templates/fact-check.yml` | `.github/workflows/fact-check.yml` | Runs `fact check` on every push. |

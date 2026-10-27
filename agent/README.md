# Agent layer templates

Files that `fact init` copies into a new model repository: the agent rules, the skills and the brief and report templates for agent rounds.

| Template | Copied to | Purpose |
| --- | --- | --- |
| `AGENTS.md` | `AGENTS.md` | Invariants for agents working on a model repository. |
| `skills/` | `.claude/skills/` | One folder per skill with a `SKILL.md`. |
| `templates/brief.md`, `templates/report.md` | `agent/brief.md`, `agent/report.md` | The shape of a round brief and report. |
| `templates/CHANGELOG.md` | `CHANGELOG.md` | The model's changelog, newest first, with the why. |
| `templates/fact-check.yml` | `.github/workflows/fact-check.yml` | Runs `fact check` on every push. |

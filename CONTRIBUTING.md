# Contributing

## Round workflow

Work happens in rounds:

1. The owner writes a brief. Briefs are working notes and stay out of the repository.
2. An agent or contributor does the work and writes a report to `_work/` (ignored by git); the owner keeps it.
3. The agent commits once at the end of the round (D-008); the owner reviews the report and the log, and pushes.

Agents never push. Rules for agents are in [AGENTS.md](AGENTS.md).

## Rules

- English only, plain and short. Use a hyphen, not an em dash.
- Clean room: write from the spec and general knowledge only. Examples use Chinook on SQLite and PostgreSQL.
- No data and no secrets in the repository.
- Every change has a `CHANGELOG.md` entry that says why.
- A decision that shapes the framework gets a record in `decisions/` (see [decisions/README.md](decisions/README.md)).

## Running checks

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
```

Optional: `uv run pre-commit install` runs ruff and the file hygiene hooks on every commit.

CI (`.github/workflows/ci.yml`) runs the same steps on every push and pull request.

## Commit messages

- First line: imperative mood, at most 72 characters, with the work package when there is one. Example: `WP0.2: add core vocabulary and loader`.
- Body: what changed and why, wrapped at 72 characters.
- One round, one commit, unless the brief says otherwise.
- No attribution trailers (no co-author or tool lines).

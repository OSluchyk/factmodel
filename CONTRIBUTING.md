# Contributing

## How to contribute

1. Fork the repository, or create a branch if you have write access. Never push to `main` directly.
2. Set up the environment: `uv sync` (Python 3.12+ and [uv](https://docs.astral.sh/uv/)).
3. Make the change, with tests. The example models (`examples/chinook`, `examples/qcew`, `examples/tpch`) and the hard cases (`tests/fixtures/hard-cases/`) must stay green.
4. Run the checks below until they pass.
5. Open a pull request with the description below.

## Running checks

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src
docker compose up -d --wait
FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
uv run fact check --root examples/chinook
uv run fact check --root examples/qcew
uv run fact check --root examples/tpch
```

`compose.yaml` starts a local PostgreSQL that holds only synthetic rows; without `FACT_PG_DSN`, the PostgreSQL tests are skipped. For the documentation site, run `uv run mkdocs build --strict`.

Optional: `uv run pre-commit install` runs ruff and the file hygiene hooks on every commit.

CI (`.github/workflows/ci.yml`) runs the same steps on every push and pull request.

## Rules

- Clean room: write from the specification and general knowledge only. Never copy code, names, data or documents from an employer, a client or another private project. Examples use public datasets.
- English only, plain and short. Use a hyphen, not an em dash.
- No data and no secrets in the repository. Connection strings live in environment variables only.
- Every change has a `CHANGELOG.md` entry that says why.
- The vocabulary has one source, `spec/VOCABULARY.md`; code reads it through `factmodel.vocabulary`.
- A contract change that removes or renames a key, changes the meaning of a key or value, or changes an algorithm's result needs a decision record in `decisions/` (see [decisions/README.md](decisions/README.md)). An additive change needs a CHANGELOG entry and a line in `spec/CORE-CHANGES.md`. A defect fix needs a CHANGELOG entry (D-018).

## Pull request description

1. Outcome in two sentences.
2. Files created and updated.
3. Verification output, pasted as is.
4. Spec edits, with old and new text.
5. Confirmed / inferred / unknown, kept apart.

## Commit messages

- First line: imperative mood, at most 72 characters. Example: `Add the rollup probe kind`.
- Body: what changed and why, wrapped at 72 characters.
- No attribution trailers (no co-author or tool lines).

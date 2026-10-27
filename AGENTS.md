# AGENTS.md

Rules for an AI agent that contributes to this repository (the FactModel framework). Invariants only.

## Invariants

1. **Clean room.** Write from `spec/` and general knowledge only. Never copy code, names, tickets, data or documents from any employer, client or other private project. Examples use public datasets (Chinook, BLS QCEW) on local engines.
2. **English only**, plain and short, in code, comments, docs and pull request descriptions. Use a hyphen, never an em dash.
3. **No data, no secrets** in the repository.
4. **Work on a branch, never push to `main`, never amend published history, never add attribution lines** (no co-author or tool trailers).
5. **Every change has a `CHANGELOG.md` entry** that says why.
6. **Decisions go to `decisions/`** in the format of `decisions/README.md`. A decision record is never edited to reverse it; write a new one that supersedes it. A record is required when a contract change removes or renames a key, changes the meaning of a key or value, or changes an algorithm's result. Adding an optional key, a vocabulary value or a probe kind needs a CHANGELOG entry and a line in `spec/CORE-CHANGES.md`. A defect fix needs a CHANGELOG entry (D-018).
7. **The vocabulary has one source:** `spec/VOCABULARY.md`. Code reads it through `factmodel.vocabulary`; never copy an enumeration into code by hand.
8. **Checks pass before the work is reported done:**
   `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest -q` (with PostgreSQL from `docker compose`), and `fact check` on both examples.
9. **Stop and ask** when a step needs credentials, network beyond package installs, or a contract change that needs a decision record. Otherwise finish the work and list open questions in the pull request description.
10. **Never widen your own access** (credentials, remote platforms, network). Such needs go in the pull request description as questions.

## Pull request description

1. Outcome in two sentences.
2. Files created and updated.
3. Verification output, pasted as is.
4. Spec edits, with old and new text.
5. Confirmed / inferred / unknown, kept apart.
6. Open questions.

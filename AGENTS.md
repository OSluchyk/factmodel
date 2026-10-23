# AGENTS.md

Rules for agents working on this repository (the FactModel framework). Invariants only.

## Invariants

1. **Clean room.** Write from `spec/` and general knowledge only. Never copy code, names, tickets, data or documents from any employer, client or other private project. Examples use Chinook on SQLite and PostgreSQL.
2. **English only**, plain and short, in code, comments, docs and reports. Use a hyphen, never an em dash.
3. **No data, no secrets** in the repository.
4. **One commit per round, never push** (D-008). At the end of a round, commit once on the branch the brief names. Never push, never amend or rewrite history, never add attribution lines (no co-author or tool trailers). The owner reviews the log and pushes.
5. **Every change has a `CHANGELOG.md` entry** that says why.
6. **Decisions go to `decisions/`** in the format of `decisions/README.md`. A decision record is never edited to reverse it; write a new one that supersedes it.
7. **The vocabulary has one source:** `spec/VOCABULARY.md`. Code reads it through `factmodel.vocabulary`; never copy an enumeration into code by hand.
8. **Checks pass before a round is reported done:**
   `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src`, `uv run pytest -q`.
9. **Stop and ask** only for the stop conditions in the brief. Otherwise finish the work and record questions in the report.
10. **The agent never drafts or records a decision that widens its own access** (credentials, remote platforms, network). Such requests go in the report's questions.

## Report

Write `rounds/<date>-report-<topic>.md` with:

1. Outcome in two sentences.
2. Files created and updated.
3. Verification output, pasted as is.
4. Spec edits, with old and new text.
5. Confirmed / inferred / unknown, kept apart.
6. Divergences from the brief, one line each.
7. Questions for the next round.
8. The files committed and the commit message; the report is part of the commit.

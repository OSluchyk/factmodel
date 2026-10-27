# D-022 Round reports are private

Date: 2026-10-27 · Status: accepted
Platform that forced it: none

## Context

D-008 says the round commit holds "the work and the round report". Briefs and reports are working notes of the development process: they quote the owner's local paths and setup, and they cite commits. When the repository went public (round 30), they moved to a folder the owner keeps outside the repository, and `AGENTS.md` began sending reports to `_work/`, which git ignores. D-008 still said the report is committed.

## Decision

Round reports are private working notes. The owner keeps them outside the repository; an agent writes its report to `_work/` (ignored by git), never into the tree.

This supersedes only the part of D-008 that says the round commit holds the round report. The rest of D-008 stands: one commit per round, on the branch the brief names, with the work; never push, never amend or rewrite history, no attribution lines.

## Consequences

- `AGENTS.md` rule 4 and its Report section, and `CONTRIBUTING.md`, already say this (round 30); they now rest on this record.
- A round report lists the commit it describes; the commit no longer contains the report.
- D-008's own text is not edited. The index marks the superseded part.

## Evidence

- Owner decision in the owner brief of 2026-10-27 on round 31 (private working notes).
- `AGENTS.md` rule 4 and section "Report"; `.gitignore` (`_work/`).

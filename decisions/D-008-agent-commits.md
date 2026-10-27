# D-008 The agent commits per round

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

In round 1 the agent wrote a `git add` list and a suggested message, and the owner committed by hand. That step adds work for the owner without adding review: the owner reads the report and the log either way. The repository has no remote yet, so a local commit cannot leak anything.

## Decision

At the end of each round the agent makes one commit on the branch the brief names, with the work and the round report. The agent never pushes, never amends or rewrites history, and adds no attribution lines (no co-author or tool trailers). The owner reviews the log and pushes.

## Consequences

- `AGENTS.md` rule 4 changes from "never commit" to "one commit per round, never push"; the report lists the commit instead of a `git add` list.
- `CONTRIBUTING.md`, the round workflow notes (private working notes) and `spec/IMPLEMENTATION_PLAN.md` (sections 1, 2 and 11) say the same.
- A mistake in a round is fixed by a new commit in a later round, never by rewriting history.
- This applies to the framework repository. The agent template for model repositories (`agent/AGENTS.md`, WP1.9) keeps "never commit" until a decision says otherwise.

## Evidence

- Owner decision in the owner brief of 2026-10-23 on the rename to FactModel (private working notes), section 1.

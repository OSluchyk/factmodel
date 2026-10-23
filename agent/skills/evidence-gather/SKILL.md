---
name: evidence-gather
description: Find and quote the highest-ranked source that supports or refutes one claim, and record it as an evidence record. Use whenever a fact needs evidence or its evidence is weak or stale.
---

# evidence-gather

## When to use

A fact has no evidence, only `inferred` evidence, or evidence that `fact status` lists as stale.

## Inputs

- The claim, in one sentence, and the fact it belongs to (an entity, field, relationship or register entry).
- The source registry (`sources/`); ranks decide which source wins (lower rank wins).

## Steps

1. Pick the sources that could hold the answer, lowest rank first.
2. Read the source you are allowed to read:
   - A text file in a git source: `fact quote --root <dir> --source <id> --path <path> --line <n> [--lines <k>]` prints an evidence record pinned to the file's version.
   - A metadata snapshot: quote the object and constraint it lists; the pin is the snapshot's (or the object's) pin.
   - Anything only the owner can read: ask the owner for the quote and record `access_mode: owner_read` on the source.
3. Write the record under `records:` of the fact's file (or in `evidence/` when several files share it): `id`, `source`, `pin`, a `quote` of at most 40 words, `status` (`inferred` for your reading; `confirmed` only from an adapter, a probe in range, or the owner), `read_on`.
4. Add the record's ID to the fact's `evidence:` list.
5. If the evidence contradicts the fact: stop, report it, and propose a retraction (`named_error`, `superseded_by`) for the owner to approve.
6. `fact check --root <dir>`.

## Acceptance

- The quote is verbatim and short; no personal data, no row values (the `privacy` stage checks).
- The pin names the exact version read.

## Report

The claim, the record ID, the source and pin, the status, and any contradiction found.

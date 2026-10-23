---
name: probe-write
description: Generate data probes for the facts data can confirm, explain each, and render scripts the owner can read and run. Use when facts are inferred and a probe could confirm them.
---

# probe-write

## When to use

Entities and relationships exist in `physical/` with `inferred` evidence, or `fact sync` reported changed facts.

## Steps

1. Generate: `fact probe generate --root <dir> [--source <id>]`. Each probe in `probes/<probe-id>.yaml` names the fact it tests, its expected range and its SQL in the source's dialect. Skipped facts are listed with the reason.
2. Read every probe you report; explain in one line what it counts and what range is expected. Probes return counts only.
3. Render for the owner: `fact probe render --root <dir> --dialect <dialect> [--source <id>]` writes `probes/scripts/<source>.<dialect>.sh`. A probe a dialect cannot express is left out with a note; never edit SQL by hand to force it.
4. Only when the source is a local engine seeded with synthetic rows and the owner has set its environment variable, you may run it yourself: `fact probe run --root <dir> --source <id> --environment <env> --data-quality synthetic`.
5. `fact check --root <dir>`.

## Acceptance

- One probe per fact that data can confirm; no probe selects values.
- The script header says how to run it and what the owner must set (`PIN`, `RUN_SQL` or the variables it names).

## Report

The probes by kind, the facts skipped and why, the script paths, and exactly what the owner must run. Next skill: `probe-intake` once results come back.

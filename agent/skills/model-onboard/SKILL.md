---
name: model-onboard
description: First pass on a new platform - register its sources, take metadata snapshots, and draft one entity per table. Use when the owner asks to onboard, start or bootstrap a model of a platform.
---

# model-onboard

## When to use

The owner wants a first model of a platform, or of one more source of it. You end with snapshots in `sources/snapshots/` and drafts in `drafts/`; nothing in `physical/` yet.

## Inputs

- The model repository (or a folder for a new one) and the profile to use.
- For each source: what it is, which adapter reads it, and how access works. Ask the owner if any of this is missing; never guess a connection string.

## Steps

1. **Create the repository** if there is none:
   `fact init <dir> --profile <profile> [--anchor <entity-id>]`
   The anchor defaults to the profile's subject. `fact adapters` lists the adapters you can use and their default dialects.
2. **Register each source**, recording how access works, never the secret:
   `fact source add --root <dir> --id <id> --title <title> --kind <kind> --access-mode <mode> --adapter <adapter> --engine <engine> [--location <location>] [--dsn-env <ENV_VAR>] [--revision <rev>] [--include <glob>]`
   An engine without a default dialect also needs `--dialect`.
3. **Take a snapshot** of each source, by the path its adapter allows:
   - The owner exports metadata: `fact export-sql --root <dir> --source <id>` prints the SQL; the owner runs it and gives you the folder; then `fact snapshot --root <dir> --source <id> --from-export <folder>`.
   - Live reflection, only where the owner has set the environment variable the source names: `fact snapshot --root <dir> --source <id>`.
   - DDL in a repository: `fact snapshot --root <dir> --source <id>`.
   Add `--date <YYYY-MM-DD>` when the date read must be fixed.
4. **Draft entities**: `fact draft --root <dir> --source <id>`. Drafts go to `drafts/<source>/entities/`.
5. **Check**: `fact check --root <dir>` passes (drafts are not read by the gate).

## Acceptance

- One snapshot per source in `sources/snapshots/`, each source's `current_pin` set.
- One draft per object; every draft lists its placeholders under `extensions.draft`.
- `fact check` passes. Running steps 3 and 4 again changes no file.

## Report

The sources registered (without secrets), the snapshot files, the number of drafts, the placeholders still open, and what the owner must provide next (exports, environment variables, reviews). Next skill: `entity-scaffold` for each draft.

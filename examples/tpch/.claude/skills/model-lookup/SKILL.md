---
name: model-lookup
description: Find an entity, a layer's concepts and measures, a join or a hazard in a model release, with the commands that print them. Use when writing or debugging a consumer of a layer, or when someone asks what a field, measure or hazard means.
---

# model-lookup

## When to use

You read a release (or a model repository) as a consumer: you write SQL, a prompt or a report on top of a semantic layer and need the facts behind it. A layer lists relationship keys and concept ids; this skill turns them into joins, predicates, formulas and hazards without opening the model's working files.

## Inputs

- The release folder (from `fact release`), or the model repository. Every command takes `--root <dir>`.
- The layer id (the folder name under `semantic/`).

## Steps

1. Check what you read: `fact check --release <dir>` must pass; `cat <dir>/VERSION` gives the release, the source commit and the schema version to pin.
2. The layer, resolved: `fact lookup --root <dir> --layer <id>`. It prints:
   - each entity with its physical name, current-row rule and default filters;
   - each relationship key with its join condition, cardinality and mechanism;
   - each concept (required ones marked) with its predicate, value list or distinct rule;
   - each measure with aggregation, expression, grain, time, suppressed handling, companion, and the quote of its formula source;
   - the hazards with their text.
3. An entity: `fact lookup --root <dir> --entity <id>`: fields with types, value domains and meanings; relationships with joins, unresolved ones marked.
4. A hazard: `fact lookup --root <dir> --hazard H-NNNN`, and the findings that mention a fact: `grep -l "<entity>.<key>" <dir>/registers/findings/*.yaml`.
5. How well the layer is proven: `<dir>/generated/equivalence-<layer>.md` (share, threshold, failures and their reasons) and `<dir>/equivalence/accepted.json`.
6. Evidence behind a fact: the ids in its `evidence` list are records in `<dir>/evidence/` or in the file's own `records`; read the `quote` or the `measurement`, the `source` and the `pin`.

## Rules

- Apply every required concept and every default filter the layer lists; a measure with `suppressed: exclude` reports its companion next to it.
- Never join through an `unresolved` relationship and never sum a measure whose aggregation is `none`.
- A fact you cannot find in the release is not in the model: ask the owner, never guess.

## Report

The facts you used (ids), the release version you read them from, and anything you could not find.

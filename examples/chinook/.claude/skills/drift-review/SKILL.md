---
name: drift-review
description: Review what changed on a platform since the last snapshot, classify every drift item, and turn each into the follow-up it needs. Use after fact sync, or when the owner says a source changed.
---

# drift-review

## When to use

`fact sync` wrote `generated/drift-<source>.md`, a trigger fired (`source_pin_moved`), or the owner reports a change on the platform.

## Inputs

- The new snapshot (`fact snapshot --root <dir> --source <id>`, taken by whoever has access) and the drift report.
- The layers that read the changed entities (`fact lookup --root <dir> --layer <id>`).

## Steps

1. `fact sync --root <dir> --source <id>`: read `generated/drift-<source>.md`. Every item has a kind (`new_object`, `dropped_field`, `type_class_change`, ...) and a class (`new_fact`, `changed_fact`, `lost_fact`, `no_effect`).
2. `new_fact`: scaffold it with `entity-scaffold` from the draft sync wrote; never edit `physical/` from the snapshot directly.
3. `changed_fact`: renew the evidence (`evidence-gather`); if a type class changed, re-run the probes of the fact (`probe-write`, `probe-intake`).
4. `lost_fact`: sync opened a finding; decide with the owner whether the fact is retracted (new record with `named_error` and `superseded_by`) or the source is wrong.
5. For every `reviewed` layer that reads a changed entity: `fact equivalence run --root <dir> --layer <id>`. A drop blocks the next release; record it as a finding.
6. `fact project --root <dir>`, then `fact check --root <dir>`.

## Report

The drift items by class, what each became (draft, renewed evidence, finding, retraction), the layers re-run and their verdicts, and the open questions for the owner.

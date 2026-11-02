---
name: entity-scaffold
description: Turn one entity draft into a reviewed model entity - class, grain, meanings, keys, relationships, anchor reference, scope admissions, all with evidence. Use when the owner asks to model, scaffold or review one table or entity.
---

# entity-scaffold

## When to use

A draft exists in `drafts/<source>/entities/<id>.yaml` (from `model-onboard` or `fact sync`), or the owner names a table to model.

## Inputs

- The draft, the snapshot it came from, the profile (`factmodel.yaml` names it) and the model's `anchor_entity` (absent when the profile names no subject, D-015).

## Steps

1. Copy the draft to `physical/entities/<id>.yaml`. Work through every placeholder in `extensions.draft.placeholders`, then delete `extensions.draft`.
2. **Class** (`data`, `configuration`, `administrative`, `reference`) and **grain** (one sentence): cite evidence for each that is not obvious from the catalog (`evidence-gather`).
3. **Meanings**: one sentence per field and per relationship. A field without its own `evidence` inherits the entity's.
4. **Keys**: keep the declared primary key; add `unique` keys and a `current_row_rule` only with evidence.
5. **Anchor**: if a field holds the anchor's key, add `anchor_reference: {field, evidence}`. A model without an anchor (its profile names no subject) has no `anchor_reference` and no `scope_admission`.
6. **Relationships**: declared foreign keys arrive as `declared_fk`. Add other joins as `inferred_join` with evidence; a join that is not field equality (a code prefix, for example) is written as a condition over `<entity>.<field>` columns (D-017). Add `scope_admission: {basis, evidence}` only where scope may pass, with the basis that holds (`unique_target` for a join to a unique key, `current_row_rule` when the target needs its rule, `measured_fanout` with probe evidence).
7. Leave `status: draft`; the owner sets `reviewed`.
8. `fact project --root <dir>`, then `fact check --root <dir>`. Fix residue with evidence, not by changing labels; a missing profile rule is a question for the owner.

## Acceptance

- No placeholder left; every fact cites evidence or says `status: unresolved`.
- `fact check` passes, including `projection` (residue 0) and `scope`.

## Report

The entity, its class and scope as computed (from `generated/scope.tsv`), relationships and their labels, evidence still `inferred`, and the probes to write next (`probe-write`).

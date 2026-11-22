---
name: layer-build
description: Build a semantic layer for one consumer from reviewed physical facts, with its required concepts, measures, hazards and an equivalence corpus, up to an accepted run whose untested elements each carry a reason (D-023). Use when the owner names a use case and a consumer.
---

# layer-build

## When to use

The owner names a use case ("employment by area and industry"), the consumer that serves it, and where its reference answers come from.

## Inputs

- Reviewed entities and resolved relationships the use case needs (`fact lookup --root <dir> --entity <id>`).
- The hazards and findings on those entities (`registers/`).
- Reference answers: SQL the platform's owners trust, or result files, for at least 30 requests.

## Steps

1. Create `semantic/<layer-id>/layer.yaml` (D-019):
   - `entities`, each with the entity's `current_row_rule` copied exactly and its `default_filters`;
   - `joins` by relationship key only; never an `unresolved` relationship;
   - `concepts`: every filter a correct answer needs is `required: true`. Use a predicate (D-017 form), a field with `values`, or a `distinct` rule for a code list that repeats rows;
   - `measures`: `expression`, `aggregation`, `grain`, `time`; `formula_source` for a documented formula; `suppressed` and its `companion`; `rollups` for hierarchies the measure must add up over (D-020);
   - `hazards`: every hazard the layer inherits (the gate lists any you missed).
2. Create `semantic/<layer-id>/consumer.yaml`: `layers`, `corpus.location`, `threshold` (0.9 unless the owner says otherwise), `interface`.
3. Write the corpus: one file per item under `corpus/`, with `request`, `reference` (tables by entity id), `mode` (`same_rows` for answers, `same_predicate` for filters) and `note`. Keep a naive query in `note` where a plausible shortcut gives a different answer. Mark an item the consumer cannot answer yet with `known_gap` and a reason, or a `finding`.
4. `fact check --root <dir>` (the `layers` stage), then `fact probe generate` and `fact probe run`/`intake` for the rollups.
5. `fact equivalence run --root <dir> --layer <id>`: it must say `proven` (D-021). Fix the layer, not the references.
6. Read the coverage in `generated/equivalence-<layer-id>.md` (D-023). For every element under "Not exercised" or "No passing item": remove it if nothing needs it, propose a corpus item that would test it, or add an `untested` entry to the layer with `kind`, `id` and a `reason` that says what needs the element and what would test it (cite a probe or an evidence id where one exists). A rollup that names an element is not a reason by itself. Predicate concepts under "Not found as written" and elements under "Not evaluated" need no entry.
7. The owner runs `fact equivalence accept`; only then the layer may become `status: reviewed`. The gate refuses a reviewed layer whose accepted run holds no coverage, misses a reason, or keeps a stale `untested` entry; after any change to the layer or the corpus, run and accept again.

## Report

The layer's concepts and measures, the inherited hazards, the corpus counts per mode and outcome, the share and verdict, every known gap with its reason, and every `untested` entry with its reason.

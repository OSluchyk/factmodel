# D-009 One review status for entities and layers

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

The plan gave entities and layers `draft | reviewed | deprecated` in WP0.2, but WP3.1 gave layers `draft | reviewed`. The vocabulary called the block `entity_status`, which did not fit layers.

## Decision

The `entity_status` block is renamed `review_status`, with the values `draft | reviewed | deprecated`. Entities and layers both use it, under the key `status`.

## Consequences

- One block for every reviewed file kind; a layer can be deprecated like an entity.
- `spec/VOCABULARY.md`, the vocabulary tests and the plan (WP0.2, WP3.1) are updated.

## Evidence

- Owner decision in `rounds/2026-10-23-brief-m0-m1-core.md`, section 2.

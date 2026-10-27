# D-002 Relationship identity: an author-set key

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

Generated labels, probes, layers and findings all point at relationships. An earlier draft proposed a positional ID (`<entity>#<n>`) plus a stable key. Lists in YAML files get reordered and edited, so a positional ID changes when nothing about the relationship changed, and every reference to it breaks silently.

## Decision

A relationship is identified by an author-set `key`, a slug unique within its source entity. The full reference is `<entity-id>.<relationship-key>`, for example `orders.placed-by`. The position of a relationship in a list is never its identity.

## Consequences

- The entity schema requires `key` on every relationship and the loader rejects duplicate keys within an entity.
- Generated files (`generated/labels.tsv` and others) and every register entry use the full reference.
- Reordering relationships produces no diff in generated files.
- Renaming a key is a breaking change for references; it needs a migration or a decision in the model.
- The roadmap (`spec/ROADMAP.md`) is updated to match.

## Evidence

- Maintainer decision, 2026-10-23.

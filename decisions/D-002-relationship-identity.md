# D-002 Relationship identity: an author-set key

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

Generated labels, probes, layers and findings all point at relationships. The plan proposed a positional ID (`<entity>#<n>`) plus a stable key. Lists in YAML files get reordered and edited, so a positional ID changes when nothing about the relationship changed, and every reference to it breaks silently.

## Decision

A relationship is identified by an author-set `key`, a slug unique within its source entity. The full reference is `<entity-id>.<relationship-key>`, for example `orders.placed-by`. The position of a relationship in a list is never its identity.

## Consequences

- The entity schema (WP0.3) requires `key` on every relationship and the loader rejects duplicate keys within an entity.
- Generated files (`generated/labels.tsv` and others) and every register entry use the full reference.
- Reordering relationships produces no diff in generated files.
- Renaming a key is a breaking change for references; it needs a migration or a decision in the model.
- `spec/IMPLEMENTATION_PLAN.md` (WP0.2 and section 13) is updated to match.

## Evidence

- Owner decision in `rounds/2026-10-23-brief-wp0.1-wp0.2.md`, section 3.

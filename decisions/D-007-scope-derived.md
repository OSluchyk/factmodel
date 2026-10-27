# D-007 Subject scope is derived, not authored

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

The first draft of the vocabulary let an entity declare `subject_scope` and `scope_basis`, and planned a gate check that compared the claim with a computed closure. That is two sources for one fact, and it creates a class of errors (claim and closure disagree) that exists only because the claim is authored. Spec principle 2 says scopes are computed.

## Decision

Only the facts that scope is computed from are authored:

- On an entity: `anchor_reference: {field: <field name>, evidence: [...]}` when a field holds the anchor key. This is what makes an entity `direct`. Absent otherwise.
- On a relationship: optional `scope_admission: {basis: unique_target | current_row_rule | measured_fanout, evidence: [...]}`, which lets scope pass through that relationship.

`fact project` computes per entity `subject_scope` (`direct | transitive | none`), the via-path and the basis, into `generated/scope.tsv`. `subject_scope` and `scope_basis` are derived values and are rejected in authored files. `declared_reference` leaves the `scope_basis` block; the direct case is expressed by `anchor_reference`.

## Consequences

- The scope closure (`spec/ALGORITHMS.md`, algorithm 2) reads `anchor_reference` and `scope_admission` only.
- The entity schema rejects `subject_scope`, `subject_scoped` and `scope_basis`.
- The plan's `orders.yaml` example, WP0.4 algorithm 2 and WP1.2, the spec's entity row and `spec/VOCABULARY.md` sections 5 and 6 are updated.
- The `scope` gate stage checks admissions and reachability, not a claim against the closure.

## Evidence

- Maintainer decision, 2026-10-23.
- `spec/SPEC.md`, principle 2.

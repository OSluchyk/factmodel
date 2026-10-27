# D-012 The model binds the anchor, the profile names the subject

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

The retail profile said `anchor_entity: users`, the name of a table in one dataset. A profile is a domain (retail, healthcare payer, banking), not a platform: the same retail profile must fit a model whose customer table is `users`, `customer` or `Customer`.

## Decision

- A profile names the role of its subjects: `subject: <role>` (free text, for example `customer`). It no longer names an entity.
- `factmodel.yaml` binds the anchor: `anchor_entity: <entity-id>`. The loader requires it.
- The `references` gate stage checks that `anchor_entity` names an existing entity of class `data` (once the model has entities; an empty model created by `fact init` has none yet).
- `fact init` writes `anchor_entity`, by default the slug of the profile's `subject`; `--anchor` overrides it.

## Consequences

- The scope closure and the projection read the anchor from the model config.
- The retail profile, the `fact init` template, the schema fixtures, the test vectors, the gate fixtures and the hard cases are migrated.
- A profile can be shared between models of different platforms without change.

## Evidence

- Owner decision in the owner brief of 2026-10-23 on closing M1 engine-neutral (private working notes), section 2.

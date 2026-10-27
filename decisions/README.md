# Decision records

Decisions that shape the framework are recorded here, one file per decision: `D-NNN-<slug>.md`. A record is never edited to reverse it. A reversal is a new record, and the old one gets `Status: superseded by D-NNN`.

These are decisions about the framework itself. A model repository keeps its own decisions in its `registers/` with four-digit IDs (`D-0001`).

Since schema 1.0.0 the core is frozen: a change that removes or renames a key, changes the meaning of a key or value, or changes an algorithm's result needs a record that names the platform that forced it. Adding an optional key, a vocabulary value or a probe kind needs a CHANGELOG entry and a ledger line; a defect fix needs a CHANGELOG entry (D-018).

## Format

```markdown
# D-NNN Title

Date: YYYY-MM-DD · Status: accepted | superseded by D-NNN
Platform that forced it: none | <example or engine>

## Context
## Decision
## Consequences
## Evidence
```

The records were curated once, for the first public release; the development history before that release is not public. From that release on, a record is never edited to reverse it.

## Index

| ID | Title | Status | Date |
| --- | --- | --- | --- |
| [D-001](D-001-license.md) | License: Apache 2.0 | accepted | 2026-10-23 |
| [D-002](D-002-relationship-identity.md) | Relationship identity: an author-set key | accepted | 2026-10-23 |
| [D-004](D-004-source-layout.md) | Source layout: `src/factmodel/` | accepted | 2026-10-23 |
| [D-005](D-005-toolchain.md) | Toolchain | accepted | 2026-10-23 |
| [D-006](D-006-data-quality.md) | Data quality instead of a boolean | accepted | 2026-10-23 |
| [D-007](D-007-scope-derived.md) | Subject scope is derived, not authored | accepted | 2026-10-23 |
| [D-009](D-009-review-status.md) | One review status for entities and layers | accepted | 2026-10-23 |
| [D-010](D-010-name-factmodel.md) | Name: FactModel | accepted | 2026-10-23 |
| [D-011](D-011-engine-blind-core.md) | Engine-blind core, universal adapters, local reference engines | accepted | 2026-10-23 |
| [D-012](D-012-model-binds-anchor.md) | The model binds the anchor, the profile names the subject | accepted | 2026-10-23 |
| [D-013](D-013-type-class.md) | Neutral type class on snapshot fields | accepted | 2026-10-23 |
| [D-014](D-014-synthetic-never-confirms.md) | Synthetic data never confirms a fact about a platform | accepted | 2026-10-23 |
| [D-015](D-015-profile-without-subject.md) | A profile may have no subject | accepted | 2026-10-27 |
| [D-016](D-016-public-domain-code-lists.md) | Public-domain code lists as fixtures | accepted | 2026-10-27 |
| [D-017](D-017-join-expressions.md) | Join expressions | accepted | 2026-10-27 |
| [D-018](D-018-additive-keys-ledger.md) | Additive keys need a ledger line, not a decision record | accepted | 2026-10-27 |
| [D-019](D-019-semantic-layer-contract.md) | Semantic layer contract v1 | accepted | 2026-10-27 |
| [D-020](D-020-rollup-probe.md) | Rollup probe kind | accepted | 2026-10-27 |
| [D-021](D-021-equivalence-threshold.md) | Equivalence threshold | accepted | 2026-10-27 |

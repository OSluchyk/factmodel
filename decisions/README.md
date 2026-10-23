# Decision records

Decisions that shape the framework are recorded here, one file per decision: `D-NNN-<slug>.md`. A record is never edited to reverse it. A reversal is a new record, and the old one gets `Status: superseded by D-NNN`.

These are decisions about the framework itself. A model repository keeps its own decisions in its `registers/` with four-digit IDs (`D-0001`).

After M2 the core is frozen: any change to it needs a record that names the platform that forced it.

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

## Index

| ID | Title | Status | Date |
| --- | --- | --- | --- |
| [D-001](D-001-license.md) | License: Apache 2.0 | accepted | 2026-10-23 |
| [D-002](D-002-relationship-identity.md) | Relationship identity: an author-set key | accepted | 2026-10-23 |
| [D-003](D-003-name-check.md) | Name check: distribution name `plumbline-model` | name part superseded by D-010 | 2026-10-23 |
| [D-004](D-004-source-layout.md) | Source layout: `src/plumbline/` | accepted | 2026-10-23 |
| [D-005](D-005-toolchain.md) | Toolchain | accepted | 2026-10-23 |
| [D-006](D-006-data-quality.md) | Data quality instead of a boolean | accepted | 2026-10-23 |
| [D-007](D-007-scope-derived.md) | Subject scope is derived, not authored | accepted | 2026-10-23 |
| [D-008](D-008-agent-commits.md) | The agent commits per round | accepted | 2026-10-23 |
| [D-009](D-009-review-status.md) | One review status for entities and layers | accepted | 2026-10-23 |
| [D-010](D-010-name-factmodel.md) | Name: FactModel | accepted | 2026-10-23 |

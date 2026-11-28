# D-025 A bound that is not zero carries its reason

Date: 2026-11-28 · Status: accepted
Platform that forced it: QCEW (published rows)

## Context

The probe schema accepts any range per metric, but `fact probe generate` wrote `max: 0` for every `join_match` and `key_duplicates` probe, and nothing in an entity could say otherwise. A fact with a known, explained exception was therefore out of range for ever. In QCEW the hierarchy `industry_titles.parent` has 53 codes without a parent, by construction of the BLS list: the three sector ranges and the 50 three-digit codes under them. The probe measured 53, the bound was 0, and the relationship could never be confirmed by its own probe.

## Decision

- A relationship may carry `expected: {orphans_left: <n>, reason: <text>}`; `keys` may carry `expected: {duplicate_keys: <n>, reason: <text>}`. The number is at least 1 and the reason is required.
- `fact probe generate` writes the number as the probe's `max` instead of 0. Everything else is unchanged: a result at or under the bound is in range and is cited by the fact; a result above it opens a finding.
- The bound is an upper limit, not a tolerance in percent. It is the measured count of rows a person has explained; when the data moves above it, someone has to look again.
- Without `expected` the bound stays 0.

## Consequences

- Schemas 2.4.0: two optional objects in the entity schema; typed model, generator and tests follow. Models written for 2.3.0 are valid as they are.
- A bound without a reason fails the gate at the schema stage.
- QCEW: `industry_titles.parent` states 53 with its reason; its probe is in range on the published rows and on the seed.

## Evidence

- `examples/qcew/evidence/probes/join-match-industry-titles-parent@2026-11-28.yaml`: 2,659 source rows, 53 without a parent.
- `tests/probes/test_bounds.py`.

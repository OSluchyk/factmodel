# D-015 A profile may have no subject

Date: 2026-10-27 · Status: accepted
Platform that forced it: QCEW (`examples/qcew`, BLS Quarterly Census of Employment and Wages)

## Context

Every profile so far named a subject (`customer`), and every model bound an anchor entity that holds those subjects (D-012). Subject scope (D-007) is then computed outward from the anchor.

QCEW has no subject. A row of `annual` or `qtrly` is an aggregate over (area, ownership, industry, size, year, quarter): no row is about a person, a customer or any other individual. Naming an anchor would be false, and leaving one out was not allowed: `subject` was required on a profile and `anchor_entity` on `factmodel.yaml`.

## Decision

- `subject` on a profile becomes optional.
- When the model's profile has no subject, `anchor_entity` must be absent from `factmodel.yaml`. When the profile has a subject, `anchor_entity` stays required. The loader reports either mismatch (stage `references`).
- In a model whose profile has no subject, `anchor_reference` and `scope_admission` are errors on every entity: there is nothing to scope to.
- `fact project` writes `subject_scope: none` for every entity of such a model, with no basis and no via path; reachability is not applicable and is written as `-`.
- A profile without a subject may not use the facets `any_end_subject_scoped`, `all_ends_subject_scoped`, or `subject_scoped` in an end pattern (loader error): they would always read false.
- `fact init` with a profile without a subject writes no `anchor_entity`; `--anchor` is then an error.

Supersedes nothing; refines D-012.

## Consequences

- Schemas: `profile.subject` and `model-config.anchor_entity` become optional; the cross-file rule is a loader check.
- Typed models, scope closure, projection, `fact project`, `fact init`, the gate's scope stage and the vocabulary text follow.
- Labels in such a model come from entity class and mechanism alone. The new `statistics` profile is the first of this kind.
- Hard cases `no-subject` and `subject-profile-without-anchor`.

## Evidence

- Owner decision in `rounds/2026-10-27-brief-m2-qcew-freeze.md`, section 3.
- QCEW grain (area_fips, own_code, industry_code, size_code, year, qtr): owner's `profile.md`, G1 and Q05, read 2026-10-23.

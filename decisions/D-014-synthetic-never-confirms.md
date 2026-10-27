# D-014 Synthetic data never confirms a fact about a platform

Date: 2026-10-23 · Status: accepted
Platform that forced it: none (review of rounds 8 to 13)

## Context

Until now intake moved a fact to `confirmed` whenever a probe result was in range, whatever the data it ran on. The spec allowed it: "a zero-violation result carries over to production". On synthetic rows that is not true. Zero orphans in seeded data shows that the probe and the join work, not that the platform's own rows have no orphans.

## Decision

- A probe result moves a fact to `confirmed` only when its `data_quality` is `representative`.
- A result on `synthetic` or `unknown` data is still taken in: intake writes its evidence record with status `inferred` and cites it from the fact it tests, so the fact stays `inferred` and the probe stays attached. A result out of range still opens a finding.
- An example or test model may set `treat_synthetic_as_representative: true` in `factmodel.yaml`. Intake then treats every result as representative, as before this decision. The flag is for models whose platform is itself synthetic, such as the framework's examples; a model of a real platform never sets it.

## Consequences

- `factmodel.yaml` gains the optional boolean `treat_synthetic_as_representative` (schema, typed model, vocabulary).
- `examples/chinook/factmodel.yaml` sets it; its committed evidence is unchanged.
- The spec's evidence paragraph and the vocabulary's data-quality paragraph record the earlier rule ("a zero-violation result carries over") as superseded by this record.
- Golden tests cover intake with and without the flag.

## Evidence

- Owner decision in the owner brief of 2026-10-23 on M1 residue (private working notes), section 2.

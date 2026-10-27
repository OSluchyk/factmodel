# D-021 Equivalence threshold

Date: 2026-10-27 · Status: accepted
Platform that forced it: none

## Context

The harness (round 21) says per item whether a consumer answered like the platform. A layer still needs a rule for when the consumer has proven it: how many items must pass, in which modes, what a failure must carry, and what an earlier accepted run protects. The open question in `spec/SPEC.md` was "one global number or per layer".

## Decision

A consumer proves a layer when all of these hold:

1. At least the threshold share of corpus items pass in `same_rows` or `same_predicate`. The default threshold is 0.9; the owner may set another per consumer in `consumer.yaml` (`threshold`). The share is taken over the items that are not marked `known_gap`. A pass in `same_count` does not count towards it: equal counts do not show equal answers.
2. No item regresses against the last accepted run (`equivalence/accepted.json`, committed).
3. Every item that does not pass has a finding (`finding: F-NNNN`) or a `known_gap` entry with a reason, so no failure goes unexplained.

`fact equivalence run` reports the share, the threshold and the verdict, and exits 1 when the layer is not proven. `fact equivalence accept` records the verdict with the run. A layer may be `status: reviewed` only when its accepted run proved it.

## Consequences

- Corpus items gain the optional keys `known_gap` (a reason) and `finding` (a finding id). The run summary gains `threshold`, `share`, `proven` and `unexplained`.
- The gate's `layers` stage reads `proven` from the accepted run.
- `spec/SPEC.md` closes the open question: one default, per consumer when the owner says so.

## Evidence

- Owner decision in the owner brief of 2026-10-27 on M3 semantic layers (private working notes), sections 0 and 5 (pre-approved).

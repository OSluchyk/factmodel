# D-020 Rollup probe kind

Date: 2026-10-27 · Status: accepted
Platform that forced it: QCEW (`examples/qcew`)

## Context

QCEW is a lattice of aggregates: a state row is the sum of its county rows, a NAICS parent the sum of its children, as long as nothing is suppressed (profile.md M5). Suppression breaks that: a parent can be disclosed over suppressed children and the reverse (H5, finding F-0007), and annual averages differ from sums by rounding (H-0001). A `join_match` probe only shows that a child finds its parent; it says nothing about whether the numbers add up, so a hierarchy relationship was "confirmed" without its arithmetic ever being measured. F-0007 was left open with "a rollup probe is deferred to M3".

## Decision

- New probe kind `rollup`: for a hierarchy relationship and a measure, each parent row is compared with the sum of its children at one level (the children the relationship joins to it, with every other key field equal). It returns counts only:
  - `parents_compared`: parents where neither the parent nor any child is suppressed;
  - `exact`, `within_rounding` (the difference is at most one unit per child) and `beyond` among them;
  - `parents_with_suppressed_child`;
  - `suppressed_parents_disclosed_children`.
- Rollups are declared on a layer measure (`rollups`: the hierarchy relationship, the grain field that holds the code, and the concept that marks a suppressed row). `fact probe generate` writes one probe per declaration, expected `beyond` at most 0.
- What "confirmed" means for a hierarchy changes: a hierarchy relationship is confirmed for aggregation only by a `rollup` probe in range. A `join_match` in range confirms the link, not the arithmetic. Intake cites a rollup result on the hierarchy relationship.

## Consequences

- Vocabulary: `rollup` in `probe_kind`, with its row in the probe table; the layer schema gains the optional measure key `rollups`; the `layers` stage checks it.
- The QCEW seed is generated bottom-up, so its parents are sums of their children, as in the real files.
- F-0007 cites the measured result; M5 is confirmed where nothing is suppressed, and H-0001 is measured on annual averages.

## Evidence

- Owner decision in `rounds/2026-10-27-brief-m3-semantic-layers.md`, sections 0 and 4 (pre-approved).
- `examples/qcew/registers/findings/F-0007.yaml`; profile.md M4, M5, H5, Q13, Q16, Q17.

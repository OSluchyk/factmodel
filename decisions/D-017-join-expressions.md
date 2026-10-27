# D-017 Join expressions

Date: 2026-10-27 · Status: accepted
Platform that forced it: QCEW (`examples/qcew`)

## Context

A relationship's `join` was field equality only: `<entity>.<field> = <entity>.<field>`, joined with `AND`. QCEW's hierarchies are not equalities of fields. A NAICS code's parent is the code with a shorter prefix (`substr(industry_code, 1, 2)`); a county's state is the state code padded with `000` (`concat(substr(area_fips, 1, 2), '000')`). Without expressions these relationships cannot be written, probed or labelled.

## Decision

- `join` accepts, besides the equality form, a boolean SQL expression parsed by sqlglot in its neutral dialect.
- In an expression, every column is qualified by an entity id, and exactly two entity ids occur: the source and the target. For a self-reference (source equals target) the convention of the equality form holds: in each top-level comparison, the left operand is the source row and the right operand the target row.
- A top-level conjunct that reads one end only is a filter on that end's rows (for example `substr(areas.area_fips, 3, 3) <> '000'`: the source row is a county).
- The `references` stage checks that the expression parses, that its entity ids are the source and the target, and that every field exists.
- `join_match` and `fan_out` probes render the expression per dialect through sqlglot, with each entity id replaced by the probe's table alias. Filters restrict the rows each end contributes. `fan_out` groups the target by the target side of each equality between the ends; a join that compares the ends in any other way gets no `fan_out`.
- A relationship with an expression join may carry `scope_admission` with basis `unique_target` only when every conjunct that compares the two ends is an equality whose target operand is a bare column, and those columns are exactly the primary key or a `unique` key of the target. Filters do not count.

## Consequences

- Schema: the `join` string pattern is relaxed; the parse and reference checks move to the loader.
- Typed models, the loader, probe generation and rendering, `spec/ALGORITHMS.md` (the `unique_target` rule) and the vocabulary text follow.
- Hard case `expression-join` with expected probe SQL in two dialects.

## Evidence

- Owner decision in `rounds/2026-10-27-brief-m2-qcew-freeze.md`, section 3.
- NAICS and area code structure: owner's `profile.md`, sections H1, V3 and A3, read 2026-10-23.

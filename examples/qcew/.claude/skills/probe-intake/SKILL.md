---
name: probe-intake
description: Take probe results in as evidence - confirm facts in range, open findings for results out of range, and report. Use when the owner returns probe output or a local run finished.
---

# probe-intake

## When to use

A results file exists: the output of a rendered script, or `probes/results/<source>@<date>.jsonl` from `fact probe run`.

## Steps

1. Check the header line names the source, pin, environment, data quality and date. Ask the owner if any is missing; never invent them.
2. Intake: `fact probe intake --root <dir> <results-file>`. It keeps numbers only, writes `evidence/probes/<probe-id>@<date>.yaml`, cites in-range results from the fact they test (the fact becomes `confirmed` on representative data) and opens a finding for each result out of range.
3. For each finding: read the probe, the fact and the measurement. If the fact is wrong, propose a retraction; if the platform is wrong, keep the finding open for the owner.
4. Only a result on `representative` data confirms a fact. A result on `synthetic` or `unknown` data is kept as `inferred` evidence and the fact stays `inferred`, unless the model sets `treat_synthetic_as_representative` (example and test models only). Say which results were which in the report.
5. `fact project --root <dir>`, then `fact check --root <dir>`.

## Acceptance

- Running intake again on the same file changes nothing.
- `fact check` passes; open findings are listed by `fact status`.

## Report

Counts in range and out of range, the findings opened, failed queries, rejected lines, and facts still `inferred`.

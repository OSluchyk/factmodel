---
name: maintenance-pack
description: Re-measure the volatile probes on a schedule, take the results in, and report what moved. Use when the owner schedules maintenance or a release is due.
---

# maintenance-pack

## When to use

On the owner's schedule (for example monthly), before a release, or when a trigger asks for a re-measure.

## Steps

1. `fact probe generate --root <dir> --set volatile`: the probes whose results change as the platform loads data (key duplicates, row counts, value sets, rollups; vocabulary block `volatile_probe_kind`).
2. Render them for whoever has access: `fact probe render --root <dir> --dialect <dialect> --source <id>`; on a local fixture engine only, `fact probe run --root <dir> --source <id> --environment <env> --data-quality <quality>`.
3. `fact probe intake --root <dir> <results file>`: results in range renew their evidence; results out of range open findings (`probe-intake`).
4. For each `reviewed` layer: `fact equivalence run --root <dir> --layer <id>`. A drop is a finding and blocks the next release.
5. `fact project --root <dir>`, `fact check --root <dir>`, and `fact status --root <dir>` for stale evidence.

## Report

Probes re-run, in range and out of range; new findings; layer verdicts; stale evidence that still needs a source read.

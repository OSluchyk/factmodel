# Skills

Procedures an agent follows in a model repository. Each skill names the `fact` commands to run and never names an engine: the source's adapter and dialect carry everything engine-specific.

| Skill | Started by | Does |
| --- | --- | --- |
| [`model-onboard`](model-onboard/SKILL.md) | owner | First pass on a new platform: register sources, snapshot, draft entities |
| [`entity-scaffold`](entity-scaffold/SKILL.md) | owner | Turn one draft into a reviewed entity with keys, relationships and evidence |
| [`evidence-gather`](evidence-gather/SKILL.md) | agent | Find and quote the highest-rank source for a claim |
| [`probe-write`](probe-write/SKILL.md) | agent | Generate and render probes for a set of facts |
| [`probe-intake`](probe-intake/SKILL.md) | owner | Read probe results, update evidence, open findings |

Planned later: `drift-review`, `layer-build`, `escalation-draft`, `maintenance-pack`, `release`, `model-lookup`.

# Skills

Procedures an agent follows in a model repository. Each skill names the `fact` commands to run and never names an engine: the source's adapter and dialect carry everything engine-specific.

| Skill | Started by | Does |
| --- | --- | --- |
| [`model-onboard`](model-onboard/SKILL.md) | owner | First pass on a new platform: register sources, snapshot, draft entities |
| [`entity-scaffold`](entity-scaffold/SKILL.md) | owner | Turn one draft into a reviewed entity with keys, relationships and evidence |
| [`evidence-gather`](evidence-gather/SKILL.md) | agent | Find and quote the highest-rank source for a claim |
| [`probe-write`](probe-write/SKILL.md) | agent | Generate and render probes for a set of facts |
| [`probe-intake`](probe-intake/SKILL.md) | owner | Read probe results, update evidence, open findings |
| [`model-lookup`](model-lookup/SKILL.md) | consumer | Find an entity, a layer's concepts and measures, a join or a hazard in a release |
| [`release`](release/SKILL.md) | owner | Build and check a release with the allowlist, VERSION and append-only notes |

Planned later: `drift-review`, `layer-build`, `escalation-draft`, `maintenance-pack`.

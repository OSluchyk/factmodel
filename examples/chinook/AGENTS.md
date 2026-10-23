# AGENTS.md

Rules for agents working on this model repository. Invariants only; procedures live in `.claude/skills/`.

1. **Evidence or it does not exist.** Every authored fact names evidence IDs (`evidence:`), unless it says `status: unresolved`. Evidence records hold a source, a pin, a quote (at most 40 words) or a measurement, a status and `read_on`.
2. **Agent-authored facts start as `inferred`.** Only an adapter, a probe in range, or evidence the owner read makes a fact `confirmed`.
3. **Derived values are never authored.** Labels, subject scope, reachability and residue are computed by `fact project` into `generated/`. Never edit `generated/`.
4. **No data, no secrets, no names.** Probes return counts and rates only. Never write credentials, row values or personal data. A person is recorded by role.
5. **Mistakes stay visible.** Retract evidence with `named_error` and `superseded_by`; never delete register entries.
6. **Agents read, people run.** Never run queries against production. Write the probe; the owner runs it.
7. **Never commit, push or publish.** The owner does.
8. **Stop and ask** when a measurement contradicts a documented fact, or when a change cannot be undone.
9. **`fact check` passes** before you report a round done.

Report each round with: outcome, files changed, `fact check` output, confirmed / inferred / unknown kept apart, open questions, and the exact `git add` list.

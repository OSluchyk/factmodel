# AGENTS.md

Rules for agents working on this model repository. Invariants only; procedures live in `.claude/skills/`.

1. **Evidence or it does not exist.** Every authored fact names evidence IDs (`evidence:`), unless it says `status: unresolved`. Evidence records live under `records:`: a source, a pin, a quote (at most 40 words) or a measurement, a status and `read_on`.
2. **Agent-authored facts start as `inferred`.** Only an adapter, a probe in range, or evidence the owner read makes a fact `confirmed`.
3. **Derived values are never authored.** Labels, subject scope, reachability and residue are computed by `fact project` into `generated/`. Never edit `generated/`.
4. **Drafts are proposals.** `fact draft` and `fact sync` write to `drafts/`; you move a draft into `physical/` only after reviewing every placeholder it lists.
5. **No data, no secrets, no names.** Probes return counts only. Never write a connection string, a credential, a row value or personal data into any file; a source names the environment variable (`dsn_env`) that holds its connection string. A person is recorded by role.
6. **Agents read, people run.** Run no query against a platform. You may run probes only on a local engine seeded with synthetic rows (a test fixture); for anything else, render the probe script and the owner runs it.
7. **Mistakes stay visible.** Retract evidence with `named_error` and `superseded_by`; never delete register entries.
8. **Never commit, push or publish.** The owner does.
9. **Never widen your own access.** Requests for credentials, platforms or network go in the report's questions.
10. **Stop and ask** when a measurement contradicts a documented fact, or when a change cannot be undone.
11. **`fact check` passes** before you report a round done.

Report each round in the shape of `agent/report.md` (briefs follow `agent/brief.md`): outcome, files changed, `fact check` output, confirmed / inferred / unknown kept apart, open questions, and the exact `git add` list.

Skills: `model-onboard`, `entity-scaffold`, `evidence-gather`, `probe-write`, `probe-intake`.

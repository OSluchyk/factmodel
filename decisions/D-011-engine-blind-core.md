# D-011 Engine-blind core, universal adapters, local reference engines

Date: 2026-10-23 · Status: accepted
Platform that forced it: none (supersedes the plan's "M1 - Core on BigQuery" framing)

## Context

FactModel must work with many data sources, ideally any. The plan tied M1 to one cloud engine (BigQuery) and one dataset (`thelook_ecommerce`), and therefore to cloud credentials the agent must not have. A withdrawn draft brief tried to solve that with an access exception; this record replaces that draft and takes its number.

## Decision

1. **The core never names an engine.** It reads model files and snapshot files. It never imports an adapter and never branches on `engine`.
2. **The snapshot is the only contract** between an adapter and the core (`schemas/snapshot.schema.json`). Engine-specific facts go to `options` or `extensions`; the core reads neither.
3. **Adapters are plugins.** Built-in and third-party adapters register through the same entry-point group, `factmodel.adapters`, so an adopter adds an engine without touching the core.
4. **Three universal adapters** cover the long tail in 1.0: `export` (owner-exported standard `INFORMATION_SCHEMA` views, for any engine that has them), `sql` (live reflection through SQLAlchemy, for any engine with a SQLAlchemy dialect) and `git` (DDL and text in a repository, for any dialect sqlglot parses).
5. **Probes are generated from a neutral AST** and rendered per dialect. Running them is owner-run by default. A local engine seeded with synthetic rows is a test fixture, not a platform, so tests and the agent may query it.
6. **No cloud credentials** in the repository or in the agent's environment. BigQuery, Snowflake, Databricks and the rest are reached through `export` or `sql` by adopters with their own credentials; the repository proves the path on local engines.
7. **Reference engines:** SQLite (standard library) and PostgreSQL (Docker, locally and in CI). **Reference dataset:** Chinook, schema only, with synthetic rows generated at test time.
8. The agent runs no query against any remote platform. An adopter verifies a cloud engine on their own project and reports back.

## Consequences

- M1 becomes "Core, engine-neutral", gated on the Chinook example; M2 becomes "Cloud engines by adopters and a second domain" (`spec/IMPLEMENTATION_PLAN.md`, sections 4 and 6).
- WP1.5 is rewritten: an adapter protocol, a registry, the `export` and `sql` adapters; drafts are made by one core function (`to_facts`), not by adapters.
- Engine knowledge that the framework needs (default dialects, which engines enforce foreign keys) lives in vocabulary blocks, not in code.
- Plan ground rule 7 stays; it gains one sentence about local test engines.
- Every `thelook` reference leaves the spec, the profiles and the agent rules; fixtures may keep old example values.

## Evidence

- Owner decision in `rounds/2026-10-23-brief-m1-close-engine-neutral.md`, sections 0 and 2.

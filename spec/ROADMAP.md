# FactModel - Roadmap

Author: Oleksandr Sluchyk · 2026-10-27
Companion to `spec/SPEC.md`. Where the two disagree, the spec wins and this roadmap is fixed.

## 1. Ground rules

1. **Clean room.** No code, schema names, tickets, data or documents from any employer or client. Concepts only, written from scratch. Examples use public datasets.
2. **English everywhere:** code, comments, docs, commit messages.
3. **No data in the repository.** Test fixtures are synthetic or exported metadata from public datasets. Probe outputs are counts only. One exception (D-016): a public-domain code list under 1 MB may be committed unchanged under `examples/<model>/sources/codelists/`, with a `SOURCES.md` line giving its URL, read date and required citation, when it holds no personal data.
4. **Deterministic core.** The core package does no network or database I/O. Adapters do I/O and write files; the core reads files.
5. **Schemas are normative.** JSON Schema files in `schemas/` define every file kind. Python models are checked against them in tests, never the other way round.
6. **Every gate stage has a failing fixture.** A check that has never failed is not trusted.
7. **Agents never push or run queries against real platforms.** People with access do. A local engine seeded with synthetic rows is a test fixture, not a platform.
8. **Every write command is idempotent.** A second run of `fact sync`, `fact project`, `fact probe intake` or any migration produces zero diff. Tests check it.
9. **Services are authored by hand in 1.0**, with evidence from code read through the git adapter. Automatic extraction of services from pipeline configuration is platform-specific and out of scope.

## 2. Technical baseline

| Area | Choice | Why |
| --- | --- | --- |
| Language | Python 3.12+ | Ecosystem for SQL parsing, YAML, warehouses |
| Packaging and runs | `uv`, `pyproject.toml`, PEP 621 | Fast, reproducible, one tool |
| CLI | Typer | Typed commands, generated help |
| YAML | ruamel.yaml in strict mode | Fails on duplicate keys, keeps comments and order on round-trip |
| Schema validation | jsonschema (Draft 2020-12) | Standard, language-neutral |
| Typed models | pydantic v2 | Fast typed access in Python; parity-tested against JSON Schema |
| SQL generation and parsing | sqlglot | One AST, many dialects; probes rendered per engine |
| Generic SQL access | SQLAlchemy 2 (extra `sql`); drivers as extras (`postgres`, `duckdb`) | One adapter for any engine with a SQLAlchemy dialect (D-011) |
| Reference engines | SQLite (standard library), PostgreSQL (Docker, locally and in CI), DuckDB | Local, free, no credentials; synthetic rows only (D-011) |
| Tests | pytest, hypothesis for projection rules | Unit, golden-file, property tests |
| Quality | ruff (lint and format), mypy (strict) | Same rules for agents and people |
| CI | GitHub Actions | Lint, types, tests, the gate on every example model, package build, strict site build |
| Docs | Markdown in the repository; MkDocs Material site | Generated from the files that define the framework |
| License | Apache 2.0 (D-001) | Public repository; explicit patent grant |

## 3. Milestones

| Milestone | Outcome | Gate | Status |
| --- | --- | --- | --- |
| M0 - Specification | Every file kind specified with JSON Schema and worked examples; algorithms with test vectors | Schema test suite green; every rule has a worked example | done |
| M1 - Core, engine-neutral | Core package, gate, CLI, adapter protocol, `export`, `sql` and `git` adapters, sync, probes rendered per dialect, hard cases, retail profile, Chinook on SQLite and PostgreSQL | Gate green on Chinook and every hard case; expected scopes hold; residue 0; the same probes give the same counts on both engines | done |
| M2 - Cloud engines and a second domain | BigQuery `export` and `sql` paths, adapter packaging guide, DuckDB, the `statistics` profile and the QCEW example; schemas frozen at 1.0.0 | Every core change in the ledger with its record (D-018) | done; BigQuery verified by an adopter on their own project: not yet |
| M3 - Semantic layers | Layer contract, equivalence harness, reference consumers, release projection, dbt and Ossie exports | One consumer meets its threshold on a corpus | done on synthetic corpora; a consumer proven on a real corpus: not yet |
| M4 - Release 1.0 | Packaging, documentation site, tutorial, upgrade policy | Someone outside the project sets up a model from the docs alone | in progress |

**M4 in detail.** Packaging (wheel, sdist, a clean-room install test), the documentation site and the Chinook tutorial are done. Not yet: the QCEW model run on the real BLS files with a real corpus, and a model set up from the docs alone by someone outside the project. Version 1.0.0 follows them.

### M0 - Specification

The vocabulary, the specification and JSON Schemas for every file kind, rendered from templates and the vocabulary so enumerations have one source. `spec/ALGORITHMS.md` defines projection with rule 0, subject scope closure and the release partition, with hand-written test vectors that the code runs against.

### M1 - Core, engine-neutral

The model loader, the projection and scope library, the gate runner and the CLI. The core reads only model files and metadata snapshots; engines come through adapters (`export`, `sql`, `git`) behind an entry-point registry (D-011). Probes are generated as ASTs and rendered per dialect; sync classifies drift and fires triggers. Hard-case fixtures make every gate stage fail at least once, and the Chinook example proves the whole loop on SQLite and PostgreSQL.

### M2 - Cloud engines and a second domain

A written path to BigQuery that never hands the agent a credential, a guide and a tested example for third-party adapters, and DuckDB as a third local engine. QCEW, a statistics domain with no subject, code-prefix hierarchies and public code lists, forced three decisions (D-015 to D-017) before the schemas froze at 1.0.0 under the D-018 rule.

### M3 - Semantic layers

The semantic layer contract (D-019), the rollup probe (D-020), the equivalence harness and its threshold (D-021), and reference consumers with corpora for Chinook and QCEW, both proven on SQLite and DuckDB. Releases give consumers a pinned, checked copy of a model; exporters write layers for dbt and Apache Ossie, listing what each target cannot hold.

### M4 - Release 1.0

The package builds and installs alone; a documentation site is generated from the repository with a CLI and a schema reference; a quickstart and a tutorial are tested on the installed package. What remains is listed above.

## 4. Testing strategy

| Layer | Kind of test | Where |
| --- | --- | --- |
| Schemas | valid and invalid fixtures per kind | `tests/test_schemas.py`, `tests/fixtures/schemas/` |
| Loader | reference errors, line and column reporting | `tests/model/` |
| Projection and scope | test vectors, property tests | `tests/core/`, `tests/test_vectors.py` |
| Gate | one failing fixture per stage, one clean fixture; hard cases | `tests/gate/`, `tests/hard_cases/` |
| Adapters | offline snapshots; live tests behind environment flags | `tests/adapters/` |
| Probes | SQL per kind and dialect; intake cases | `tests/probes/` |
| Sync | drift kinds, triggers, idempotence | `tests/sync/` |
| Equivalence | toy consumer right, wrong and partly right | `tests/equivalence/` |
| Release and export | partition, refusals, release gate; dbt parse, Ossie structure | `tests/release/`, `tests/export/` |
| Examples | the gate and cross-engine counts on every example | `tests/examples/`, CI |
| Package and docs | clean-room install; quickstart and tutorial run on the installed package; strict site build | `tests/install/`, `tests/docs/` |

Coverage target for `src/factmodel/core` and the gate: 90 % lines. Adapters and CLI: 70 %.

## 5. Risks

| Risk | Effect | Mitigation |
| --- | --- | --- |
| Core shaped by one platform | A second platform needs breaking changes | Frozen only after a second engine and a second domain; a decision record for every contract change |
| Public datasets too clean | Hazards, current-row rules and target sets never tested | Hard-case fixtures, at least one per gate stage |
| Agents drift from rules | Authored derived values, missing evidence | The gate enforces rules; skills only describe them |
| Scope creep into a semantic-layer runtime | Competes with dbt or Cube | A non-goal in the spec; exporters instead |
| Ossie specification changes | The exporter breaks | Each supported version pinned and tested; the exporter lists what it cannot hold |
| One-person project | Slow reviews | Small, checked changes; a gate that catches what review misses |

## 6. Open questions

| Question | Status |
| --- | --- |
| Format of facts: YAML only, or YAML plus a generated graph file (for example JSON-LD) for graph consumers | open |
| Ossie: move to 0.2.0 when it is released, or when a JSON Schema is published | open |

# Changelog

Newest first. Every entry says why, not only what.

## Unreleased - 2026-10-23 - Round 11: WP1.7 Probes

**Why.** An inferred join or key is a claim until data confirms it. Probes generated from the model, rendered for whichever engine holds the data and returning counts only, turn those claims into evidence without moving a single row into the repository.

- Add `fact probe generate|render|run|intake`: seven probe kinds as sqlglot ASTs with quoted identifiers, rendered per dialect; owner-run shell scripts or a run through the `sql` adapter; intake writes evidence, confirms facts in range and opens findings out of range.
- A probe a dialect cannot express is marked `unsupported_on_dialect` and never rendered wrong.
- Counts agree on SQLite and PostgreSQL; the soft-delete, nullable-fk and nested-field hard cases now get their probes.

## Unreleased - 2026-10-23 - Round 10: WP1.6 Sync, drift and triggers

**Why.** A model goes stale when the platform changes. Sync turns every change into a classified fact (new, changed, lost, no effect) with a concrete follow-up, and triggers make sure a change that needs work cannot be forgotten.

- Add `fact sync --source <id>`: drift between the latest snapshot, the previous one and the model, in eight kinds; drafts for new facts, findings for lost facts, a `source_pin_moved` firing, and `generated/drift-<source>.md`. Idempotent.
- Add the `triggers` gate stage: a fired trigger without `follow_up_ref` fails the gate.
- New vocabulary block `drift_kind`.

## Unreleased - 2026-10-23 - Round 9: WP1.5b git adapter

**Why.** Much of what a platform means is written down before it exists: DDL, configuration, pipeline code. Reading it from git, at a pinned commit, gives intent evidence for any dialect sqlglot parses, without credentials.

- Add the `git` adapter: `CREATE TABLE` and `CREATE VIEW` at a commit or in the working tree become snapshot objects pinned `<repo>@<sha>:<path>:<line>`; the snapshot lists the files read with their blob hashes.
- Add `fact quote`: an evidence record quoting a text file, pinned to its version.
- DDL in two dialects agrees on the neutral parts, and DDL and a catalog of the same tables give the same drafts.

## Unreleased - 2026-10-23 - Round 8: WP1.5 Adapter protocol, export and sql adapters

**Why.** FactModel must work with any data source. Tying M1 to one cloud engine meant credentials the agent must not have and a core shaped by one platform. The core now reads only snapshots and model files; engines arrive as plugins.

- Record D-011 (engine-blind core, universal adapters, local reference engines), D-012 (the model binds the anchor, the profile names the subject) and D-013 (neutral type class), and apply them to the spec, plan, vocabulary, schemas, fixtures and code.
- Add the adapter protocol, the entry-point registry (`factmodel.adapters`), the `export` adapter (generic, PostgreSQL and BigQuery flavours) and the `sql` adapter (SQLAlchemy reflection, DSN only from the environment).
- Add core `to_facts`, and `fact adapters`, `fact export-sql`, `fact snapshot`, `fact draft`.
- A literal connection string in a model file fails the privacy stage.
- AGENTS.md rule 10: the agent never widens its own access.

## Unreleased - 2026-10-23 - Round 7: WP1.8b Hard-case fixtures

**Why.** Public datasets are too clean to show what the framework exists for: soft deletes, keys that repeat, polymorphic links, per-tenant targets, nullable anchors, reference chains, nested fields, stale and retracted evidence. Small synthetic models make each one a regression test.

- Add 19 hard cases in `tests/fixtures/hard-cases/` (the nine plan cases plus variants), each with the expected generated files and gate verdict; a test runs `fact check` and `fact project` on all of them, and every gate stage fails on at least one.
- Scope: a `unique_target` admission on a link whose target key repeats is rejected (`non_unique_target`).
- An `anchor_reference` may name a nested field path.
- Deferred to WP1.7: probes for ties and null rates, and per-dialect rendering of nested-path joins.

## Unreleased - 2026-10-23 - Round 6: WP1.3 Gate runner, WP1.4 CLI skeleton

**Why.** Rules that only live in documents drift. The gate turns every rule into a check with one verdict, and each check is proven by a model that fails it alone. The CLI makes a new model repository in one command, so the first thing an adopter sees is a passing gate.

- Add `fact check`: ten stages from `gate.yaml` (yaml, schema, references, evidence, derived-not-authored, projection, scope, registers, generated-fresh, privacy), one verdict line each, `--stage` to run one.
- Add `fact init`, `fact source add`, `fact status`.
- Ship the `retail` profile and minimal agent templates (`AGENTS.md`, skills placeholder, changelog and CI templates).
- Sources may record `current_pin`, so `fact status` can list stale evidence.

## Unreleased - 2026-10-23 - Round 5: WP1.2 Projection and scope library

**Why.** Derived values are never authored, so something must compute them. Pure functions, checked against hand-written vectors and property tests, make the computation trustworthy before the gate depends on it.

- Add `factmodel.core`: effective evidence status, subject scope closure with rejections and reachability, projection with rule 0, and the release partition as a pure function.
- Add `fact project`: writes `generated/labels.tsv`, `scope.tsv`, `residue.tsv` and `scope-rejections.tsv`; idempotent; refuses a broken model.
- Every round-3 test vector now runs as a test; hypothesis checks determinism, order independence and that an unrelated entity changes nothing.

## Unreleased - 2026-10-23 - Round 4: WP1.1 Model loader

**Why.** The gate, the projection and every command read the same model. One loader that finds every problem at once, and says where and how to fix it, keeps those parts simple and gives agents an error they can act on.

- Add `factmodel.model.loader`: discovers model files, validates them against their schemas, checks references between files (entities, evidence, sources, fields, joins, registers, profile labels) and returns a typed `Model` with every issue.
- Each issue has file, line, column, gate stage and a fix hint.
- Add typed pydantic models for every kind; a parity test checks they agree with the JSON Schemas on every schema fixture.

## Unreleased - 2026-10-23 - Round 3: WP0.4 Algorithms, WP0.5 spec-v0.1

**Why.** The core's three algorithms must be exact before code exists, so that the code is checked against the spec and not the other way round. The test vectors are that check, written by hand from the text.

- Add `spec/ALGORITHMS.md`: projection with rule 0, subject scope closure (D-007) with admission rejections and reachability, release partition.
- Add 21 test vectors in `tests/vectors/` and a test that every vector input is valid and every expected output covers its input.
- Release key lists are `keep` and `drop` per kind, so an undeclared key fails closed.
- New vocabulary blocks `admission_rejection` and `release_failure`.
- **spec-v0.1**: `spec/SPEC.md` and `spec/VOCABULARY.md` are version 0.1, with links to the vocabulary, algorithms and schemas. The owner creates the git tag.

## Unreleased - 2026-10-23 - Round 2: WP0.3 JSON Schemas

**Why.** Every later piece (loader, gate, adapters) needs a normative shape for each file kind, and the shapes must not drift from the vocabulary. Three round-1 choices would have made the schemas awkward: a boolean-or-string field, an authored scope checked against a computed one, and a status block named for entities only.

- Record D-006 (`data_quality` instead of `representative`), D-007 (subject scope is derived; `anchor_reference` and `scope_admission` are authored) and D-009 (`review_status` for entities and layers), and apply them to the vocabulary, spec and plan.
- Add `schemas/` for every file kind plus the metadata snapshot, rendered by `factmodel.schemas.build` from templates and the vocabulary, so enumerations have one source.
- Add valid and invalid fixtures for every kind; each invalid fixture fails for one named reason at one path.
- Add `factmodel.io.yaml_strict`: duplicate keys fail, dates stay strings, nodes keep their positions.
- Inline evidence records move under `records:`; `evidence:` always holds IDs.

## 0.0.1 - 2026-10-23 - Round 2a: rename to FactModel, agent commits per round

**Why.** The name should say what the thing is - a model made of proven facts - instead of a metaphor that needs a paragraph; nothing was public yet, so the rename was cheap now and expensive later. Committing by hand after each round added owner work without adding review.

- Rename Plumbline to FactModel: distribution and import `factmodel`, command `fact`, model config `factmodel.yaml`, package in `src/factmodel/` (D-010). Earlier decision records, round reports and changelog entries keep the old names as history.
- The agent commits once per round and never pushes, amends or adds attribution lines; `AGENTS.md` rule 4 and the round workflow docs changed to match (D-008).

## 0.0.1 - 2026-10-23 - WP0.1 Repository bootstrap, WP0.2 Core vocabulary

**Why.** The repository held only the specification and the plan. Later work packages need a project that installs, lints, type-checks and tests, and a fixed vocabulary that every schema will share, before any schema is written.

- Bootstrap the Python project: `src/plumbline/` layout (D-004), `uv`, Typer, ruamel.yaml, jsonschema and pydantic v2 (D-005), CI and pre-commit hooks, `plb --version`.
- License the framework under Apache 2.0 (D-001).
- Publish under the distribution name `plumbline-model`, keeping the import name `plumbline`, because `plumbline` is taken on PyPI (D-003).
- Add `spec/VOCABULARY.md` with machine-readable enumeration blocks, and `plumbline.vocabulary` to load them, so later schemas have one source for every list.
- Make relationship identity an author-set key, never a list position (D-002).
- Align the spec and plan wording with the vocabulary; see the round report for each edit.

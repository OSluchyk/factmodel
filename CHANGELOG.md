# Changelog

Newest first. Every entry says why, not only what.

## 0.1.0 - 2026-10-27

The first public release. The entries below are the rounds that built it.

## Unreleased - 2026-10-27 - Round 30: public release cleanup

**Why.** The repository goes public. It should hold what a user, a contributor or CI needs, and nothing that only made sense during development or names the owner's machine. The public history will be one commit, so commit hashes in the text would point nowhere.

- Briefs and round reports, the agent's session notes and the owner's pilot kit leave the tree; the owner keeps them privately. Round reports now go to `_work/` (ignored) instead of the tree (`AGENTS.md`, `CONTRIBUTING.md`).
- References to the removed files become plain words. Decision evidence lines cite the owner's brief by date as private working notes; decision text is unchanged.
- Commit hashes leave the core-change ledgers, the changelog and the vocabulary's example pin; the round labels stay.
- The plan drops its "First three briefs" section. The examples' release notes go back to the header, because their 0.1.0 section named a source commit that will not exist; the release test builds on a copy, so the committed notes stay at the header.
- The pilot-kit page and its test leave the site; the skill reproduction test gets a plain name.

## Unreleased - 2026-10-27 - Round 29: D-010 evidence correction, Ossie 0.1.1 pin, kit step

**Why.** Three corrections after review. The round-26 PyPI check read a status code that PyPI returns for every name, so the record said the name was taken when it is free. An export should default to what Ossie has released, not to a draft. The pilot model kept the seed's probe evidence next to the real results, though it describes the seed, not the platform.

- D-010 gains a dated reviewer line after the round-26 line: `/project/` answers 200 for any name (an anti-bot page); `/simple/factmodel/` and `/pypi/factmodel/json` answer 404, so the name is free. Correction notes in the round-26 report and the M4 final report.
- Ossie: one read of the released core specification 0.1.1 (tag `osi-0.1.1-rc1`); the export defaults to it. 0.1.1 has the `semantic_model` list, no `version` and no `datatype`, and closed enumerations for dialects (`ANSI_SQL` for engines it does not list) and vendors (`COMMON`, with the framework's keys under `factmodel`). `fact export --spec-version 0.2.0.dev0` keeps the round-28 shape. Tests cover both.
- Pilot kit, step 4: after the real intake, a block removes the seed's probe evidence (source `qcew-sqlite`, `data_quality: synthetic`) and every citation of it, then runs `fact project` and `fact check`. Catalog and document evidence stay. Dry-run on the stand-in.

## Unreleased - 2026-10-27 - Round 28: WP4.3 Tutorial, pilot kit, Ossie pin

**Why.** M4's test is someone building a model from the docs alone, and the QCEW model proving itself on real data. The tutorial is that path on Chinook, kept honest by a test that runs it on the installed wheel. The pilot kit lets the owner run the real-data step without the agent ever touching the data. The Ossie export followed a project page; it now follows the specification document itself.

- Tutorial `docs/tutorial/chinook.md`: from an empty folder to residue, review, probes, a proven layer, a release and two exports, every step a command. A test runs every block on the installed wheel alone and checks the promised outputs (gate verdicts, residue 0, `proven`).
- Pilot kit (kept with the owner's working notes): the owner's six steps on the real QCEW files (model from `examples/qcew`, sources and two views over the per-year tables, snapshot and drift against a seed-shaped baseline, owner-run probes with the expected counts, a real corpus kept outside the repository, what to send back). Dry-run end to end on the seed split into per-year tables.
- Ossie export pinned to the core specification 0.2.0.dev0 (a draft), read once: the flat document the specification defines (no `semantic_model` list), field expressions and types, relationships for equality joins, metric descriptions, and `custom_extensions` (vendor `factmodel`) for evidence status, required concepts, hazards and suppression. What it does not name stays in `ai_context`.
- Fix: `fact equivalence script` wrote `... EXCEPT WITH ...` when a reference starts with a CTE, a syntax error on every engine, so every such item came back as an error. Each side of the EXCEPT is now a plain `SELECT * FROM (...)`. Found by the pilot dry run; the QCEW references all start with `WITH`.
- The clean-room test and the tutorial test share one wheel build (`tests/install/wheel.py`, a session fixture).
- `spec/SPEC.md` and the plan: M4 "kit done, pilot pending"; the M3 real-corpus caveat points at the pilot kit.

## Unreleased - 2026-10-27 - Round 27: WP4.2 Documentation site

**Why.** A framework others set up from scratch needs one place to read it, generated from the files that define it so it cannot drift from them. The CLI and schema references come straight from the code and the schemas, and a strict build fails on any broken link between pages.

- MkDocs Material (dev dependency). `docs/_site/hooks.py` assembles the site before every build:
  - the spec and the roadmap;
  - the decisions on one page;
  - the guides;
  - one page per skill;
  - a CLI reference with every command, option and one example;
  - a schema reference with one page per file kind;
  - a tested ten-command quickstart, and a FAQ.
- `mkdocs build --strict` runs in tests and CI; `pages.yml` deploys on push to `main` once the owner enables Pages.
- The spec's toolset gains `fact probe render` and `fact quote`, which it had missed.

## Unreleased - 2026-10-27 - Round 26: WP4.1 Packaging, clean-room install, M3 answers

**Why.** Before anyone else can use FactModel, the built package alone has to work with nothing from the source tree. The M3 answers close the gaps the reference consumers found: joins a consumer had to look up, a level matrix it had to derive, a formula dbt could not hold, and release notes that did not survive a fresh build folder.

- Packaging:
  - `uv build` gives wheel and sdist, and `twine check` (dev dependency) passes;
  - the sdist no longer ships the owner's root `.claude/`;
  - `fact --version` prints the schema version.
- A clean-room test installs the wheel into a fresh environment outside the repository and runs the Chinook loop: check, project, probes, equivalence, release, release check, dbt export.
- M3 answers:
  - per-layer derived join tables (Q1);
  - the concept form `values_table`, used by QCEW's `level_matrix` (Q2);
  - dbt derived metrics for formula measures (Q4);
  - committed `release/RELEASE_NOTES.md` (Q5);
  - a migration registry slot (Q6).
- Schemas 2.2.0. D-010 gains a dated PyPI check: the name now has a page (200), and the owner decides.

## Unreleased - 2026-10-27 - Round 25: WP3.5 and WP3.6 Exporters and maintenance skills

**Why.** A proven layer is most useful where teams already work: in dbt's semantic layer and in the open Ossie interchange format. An export that silently loses the disclosure filter or a hazard would carry a wrong answer into those tools, so every exporter lists what its target cannot hold. The maintenance skills close the loop: drift, escalations, scheduled re-measuring and building the next layer.

- `fact export --target dbt`: semantic models and metrics with the disclosure filter as a MetricFlow filter and evidence status in `meta`; validated with `dbt parse` (dbt-core 1.12.6, dev dependency).
- `fact export --target ossie`: pinned to the Apache Ossie page read on 2026-10-27, which states no version. Only the keys that page shows are written, and the rest goes in `ai_context` as text.
- `EXPORT_NOTES.md` per export, and `docs/exporters/round-trip-notes.md`.
- Skills `drift-review`, `layer-build`, `escalation-draft` and `maintenance-pack`.
- Volatile probes: a new vocabulary block, the `volatile: true` mark, and `fact probe generate --set volatile`.

## Unreleased - 2026-10-27 - Round 24: WP3.4 Release projection, model-lookup and release skills

**Why.** Consumers should read a pinned, checked copy of a model, not its working files. A release that leaks internal notes or derived values, or ships a layer that stopped answering like the platform, would undo what the gate and the harness proved. The reference consumers' own run showed that consumers also need joins resolved for them.

- `fact release`:
  - builds the copy: complete partition, internal-note markers, `VERSION`, append-only `RELEASE_NOTES.md`;
  - is refused on a failing gate, an equivalence drop in a reviewed layer, or any partition failure.
- `fact check --release`: the reduced release gate.
- `fact lookup`: a layer with its joins resolved, an entity or a hazard.
- Skills `model-lookup` and `release`, and release allowlists for both examples.
- Defect found and fixed in passing: the model loader no longer reads a built release under `release/out/` as model files.

## Unreleased - 2026-10-27 - Round 23: WP3.3 Reference consumers and corpora, threshold (D-021)

**Why.** A layer is proven only by a consumer that answers like the platform. QCEW shows why that matters: the naive answers (summing suppressed zeros, joining the raw area list, mixing levels, summing annual averages, averaging weekly wages) are all different. D-021 fixes when a run proves a layer, so `reviewed` means something.

- D-021: the threshold, known gaps and findings, and the run verdict. `fact equivalence run` exits 1 when a layer is not proven, and the gate needs a proven accepted run for `reviewed`.
- QCEW: consumer `measure-sql` and a 38-item corpus. It has six naive-versus-correct pairs with the naive SQL in the note, and two known gaps (MSA detail from counties, the national rollup).
- Chinook: consumer `filter-sql` and a 31-item corpus.
- Both layers are proven on SQLite and DuckDB, accepted (the owner's act, simulated once) and `reviewed`.
- A working note (kept privately) lists what the consumers looked up outside their layers.

## Unreleased - 2026-10-27 - Round 22: WP3.3a Layers for QCEW and Chinook, rollup probe (D-020)

**Why.** The layer contract has to carry real cases. For QCEW the layer must make the disclosure filter, the level, distinct area codes and formula-based measures impossible to miss. A hierarchy's arithmetic was never measured, so D-020 adds a probe that shows where QCEW's numbers add up and where suppression breaks them.

- Layers:
  - `examples/qcew/semantic/employment-wages/`, with consumer `measure-sql`;
  - `examples/chinook/semantic/customer-purchases/`, with consumer `filter-sql`.
  Both are at `status: draft`.
- D-020: probe kind `rollup`, declared on layer measures (`rollups`) and cited on the hierarchy relationship. Schemas 2.1.0.
- The QCEW seed is generated bottom-up, so parents are true sums of their children.
- Measured on the seed:
  - monthly levels add up exactly where nothing is suppressed (M5);
  - annual averages add up only within rounding (H-0001);
  - suppression shows in 24 and 8 parents (H5, F-0007).
  F-0007 and H-0001 cite the results.

## Unreleased - 2026-10-27 - Round 21: WP3.2 Equivalence harness

**Why.** A layer is only as good as the answers a consumer gets from it. The harness runs a consumer over a corpus of requests with known answers and compares the two. It keeps outcomes and counts, never rows, so a layer can be proven, accepted and protected against regressions.

- `src/factmodel/equivalence/`: one YAML corpus item per file. Modes `same_rows`, `same_count` and `same_predicate` (normalised AST). Consumers and references name tables by entity id, and the harness binds them to physical names.
- `fact equivalence run` runs offline on SQLite or DuckDB, or reads the output of an owner-run script from `fact equivalence script`. `fact equivalence accept` is the owner's act. A drop against the accepted run is reported as a regression and exits 1.
- Tests with a toy layer and right, wrong and partly right consumers.

## Unreleased - 2026-10-27 - Round 20: WP3.1 Semantic layer contract v1 (D-019)

**Why.** M3 needs layers a consumer can rely on. QCEW shows that a layer must carry more than names: the filters every query applies, the level discriminator, the distinct-codes rule, measures defined by expression and documented formula, and the hazards behind them. The 1.0.0 placeholders could not hold that, so D-019 replaces them and the gate checks the new contract.

- D-019; layer and consumer schemas v1; schemas 2.0.0. New vocabulary blocks `measure_aggregation`, `time_granularity` and `suppressed_handling`.
- Gate stage `layers`, with a failing gate fixture, four hard cases and unit tests for each rule.
- `fact check` warns, never fails, when a model's `schema_version` differs from the installed schemas while every file validates.
- Framework version 0.1.0: M2 is closed, and 1.0.0 is M4.
- `spec/CORE-CHANGES-M3.md` opens the M3 ledger.

## Unreleased - 2026-10-27 - Round 19: WP2.3 core freeze, schemas 1.0.0 (D-018)

**Why.** Round 18 stopped the freeze over three additive keys without a decision record. The owner decided that only removals, renames and meaning changes need a decision record, so the freeze could close M2 without rewriting history or reverting keys that break no model.

- D-018: additive keys need a CHANGELOG entry and a ledger line, a defect fix a CHANGELOG entry, and a removal, rename or meaning change a decision record; the three round-18 gaps are recorded retroactively. `AGENTS.md` rule 6, `decisions/README.md` and `spec/VERSIONING.md` say so.
- Defect fix: `fact probe intake` names the entity in a finding's `about` for a field probe and keeps the field in `extensions.fact`, so the gate reads what intake writes.
- Freeze: `SCHEMA_VERSION` 1.0.0. `factmodel.yaml` may record `schema_version` (written by `fact init`), and `fact migrate` names the difference to the installed schemas. M2 is done.
- Owner answers:
  - a single-target relationship may carry a discriminator (QCEW `agglvl_code`);
  - an unresolved relationship may omit its join (QCEW's placeholders removed);
  - DuckDB has a JSON wrap and a default runner for rendered probe scripts.

## Unreleased - 2026-10-27 - Round 18: WP2.3 core-change ledger, versioning, `fact migrate` (freeze stopped)

**Why.** The schemas may freeze only when every core change since M1 has a decision record naming the platform that forced it. The ledger is how that is checked. It found three contract changes without a record, so the freeze waits for the owner instead of being declared.

- `spec/CORE-CHANGES-M2.md`: 26 changes since WP1.8b, each with its record. Three have none: snapshot pins (round 8), optional probe keys (round 11), field `values` (round 14).
- `spec/VERSIONING.md`: schema and framework versions are separate; semver rules for the schemas; how `framework_version` is used.
- `fact migrate` reports a model's framework version, the installed schema version and whether every file validates. It writes nothing.
- `.gitattributes` keeps the BLS code lists byte for byte. Round 17's commit had stored them with LF line endings (`core.autocrlf=input`), so they were not the published files until this round.
- Schemas stay at 0.1.0.

## Unreleased - 2026-10-27 - Round 17: WP2.2 QCEW example on SQLite, PostgreSQL and DuckDB

**Why.** The core's second domain has to be modelled end to end, defects included, before the schemas freeze. QCEW shows what Chinook cannot: no subject, prefix hierarchies, and real code lists whose flaws must become measured findings.

- Add `examples/qcew/`: DDL for three engines, a deterministic seed, the five BLS code lists (D-016), seven reviewed entities, document evidence, 46 probes with SQLite evidence, findings F-0001 to F-0009 and hazards H-0001, H-0002. Every scope is `none`, residue 0, and PostgreSQL and DuckDB return the same probe counts.
- Join expressions accept a negated comparison in a self-reference (`x IS NOT NULL`), under D-017.
- CI runs the QCEW gate; the examples' cross-engine tests cover PostgreSQL and DuckDB.

## Unreleased - 2026-10-27 - Round 16: WP2.2a D-015 to D-017, statistics profile, hard cases

**Why.** QCEW, the second domain, has a shape Chinook does not: no row is about an individual, its hierarchies are code prefixes rather than equal fields, and its code lists are public data the example needs as they are. The core could not express any of this, so three decisions were recorded first and the core changed only as far as they allow.

- D-015: a profile may have no subject; the model then binds no anchor, every entity is `none`, and `anchor_reference`, `scope_admission` and subject facets are loader errors. `fact init` writes no anchor for such a profile.
- D-016: public-domain code lists under 1 MB may be committed unchanged in an example, with a source line and citation (plan ground rule 3).
- D-017: a join may be a boolean SQL expression over the two ends; the loader parses and checks it, probes render it per dialect with one-end conjuncts as filters, and `unique_target` needs a target key on the target side.
- New `statistics` profile (labels `dimension`, `hierarchy`, `lineage`, `representation`, `unresolved`) and hard cases `no-subject`, `expression-join`, `subject-profile-without-anchor`.

## Unreleased - 2026-10-27 - Round 15: WP2.1 Adopter guides, plugin packaging, DuckDB

**Why.** M2 asks whether the core holds beyond the engines it was built on. Adopters need a written path to BigQuery that never hands the agent a credential, third parties need a proven way to add an adapter, and a third local engine tests the `sql` adapter on a dialect nobody tuned it for.

- `docs/adopters/bigquery.md` (the `export` path, then the `sql` path) and `docs/adapters/packaging.md`; the plan's BigQuery adopter run is owner-pending.
- A test package `tests/fixtures/plugin/` (`factmodel-csvdir`) installed as a path dependency of the dev group: `fact adapters` lists it and `fact snapshot` runs through it.
- DuckDB through `sql` (extra `[duckdb]`). Its SQLAlchemy dialect cannot reflect (it sends PostgreSQL catalog queries DuckDB does not answer), so the `sql` adapter now falls back to the standard `INFORMATION_SCHEMA` views. Neutral parts and Chinook's 45 probe counts agree with SQLite and PostgreSQL. DuckDB joins `engine_enforces_foreign_keys` because a test measured it.
- `value_set` also counts rows outside the domain (`outside_rows`); `fact init` writes `treat_synthetic_as_representative: false` so the setting is visible.

## Unreleased - 2026-10-23 - Round 14: M1 residue

**Why.** The review of rounds 8 to 13 found dialect knowledge still hard-coded in the probes, and a probe rule that let synthetic rows confirm facts about a platform. M2 should start from a core that holds its own rules.

- Probe dialect knowledge moves to vocabulary maps (`dialect_nested_paths`, `dialect_json_wrap`, `dialect_runner`); a new dialect needs a vocabulary line, not code. The export adapter picks its flavour by module name.
- D-014: only representative data confirms a fact; synthetic results attach as `inferred` evidence. Example models may set `treat_synthetic_as_representative` (Chinook does).
- Drafts keep engine constraint names; DDL comments become meanings with `inferred` evidence; fields may declare a value domain checked by `value_set`; `fact init` copies the brief and report templates; `fact sync` stays offline (plan).

## Unreleased - 2026-10-23 - Round 13: WP1.9 Agent layer v1

**Why.** Rules an agent cannot follow by itself do not scale. Skills turn the framework's procedures into steps an agent runs with `fact` commands only, and a run of the agent on its own skills proves they are enough.

- Add five skills (`model-onboard`, `entity-scaffold`, `evidence-gather`, `probe-write`, `probe-intake`), the model-repository `AGENTS.md` template, and brief and report templates; `fact init` copies the skills.
- `fact source add` can set the adapter, dialect, `dsn_env`, revision and include globs.
- Self-test: following only `model-onboard`, the Chinook snapshot and drafts are reproduced exactly; a test repeats it.

## Unreleased - 2026-10-23 - Round 12: WP1.8 Chinook example (M1 gate)

**Why.** The core has to prove itself end to end on a real schema, on more than one engine, without credentials. Chinook on SQLite and PostgreSQL with synthetic rows does that locally and in CI.

- Add `examples/chinook/`: hand-written DDL for SQLite and PostgreSQL (the upstream license is not a recognised permissive one, so nothing was copied), a deterministic synthetic seed, three sources (`sql` on SQLite and PostgreSQL, `git` on the DDL), snapshots, drafts, the reviewed model, 45 probes with their evidence, and generated tables.
- M1 gate: `fact check` green, residue 0, scopes as expected (Invoice direct, InvoiceLine transitive, catalog reference), every relationship confirmed by a probe; PostgreSQL gives the same snapshot parts and probe counts.
- Retail profile: label `reference_data` for links between reference entities.
- CI runs the Chinook gate and the PostgreSQL comparison.

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

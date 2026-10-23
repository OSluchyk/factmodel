# Final report - Rounds 8 to 13: close M1 with an engine-neutral core

Date: 2026-10-23 · Brief: `rounds/2026-10-23-brief-m1-close-engine-neutral.md` · Branch `main`, from `1d88638`

## 1. Outcome

All six rounds completed; none stopped. M1 is closed on an engine-neutral core. The core reads only model files and snapshots, three universal adapters arrive as plugins (`export`, `sql`, `git`), sync and probes work per dialect, and the Chinook example passes the M1 gate on SQLite. PostgreSQL gives the same answers.

Docker was available, so every PostgreSQL path was verified locally against PostgreSQL 16. The only part verified by nothing yet is the GitHub Actions workflow itself, which runs once the owner pushes. The final state passes ruff, ruff format, mypy (strict) and 608 tests with `FACT_PG_DSN` set (605 plus 3 skipped without it).

## 2. Git log for the run

```text
$ git log --oneline 1d88638..HEAD
20e1072 WP1.9: agent layer v1, skills and dogfood
b2f23b4 WP1.8: Chinook example on SQLite and PostgreSQL, M1 gate green
b78afdc WP1.7: probes as ASTs, rendered per dialect, run and intake
93238ab WP1.6: sync, drift report and triggers stage
4302b06 WP1.5b: git adapter for DDL and quotable text
3bbe8db WP1.5: adapter protocol, export and sql adapters, D-011 to D-013
```

This final report is committed on its own after `20e1072`. Nothing was pushed, amended or tagged; no commit carries an attribution line.

## 3. Rounds and acceptance

| Round | Work package | Report | Acceptance |
| --- | --- | --- | --- |
| 8 | WP1.5 adapter protocol, `export`, `sql`; D-011 to D-013 | `rounds/2026-10-23-report-wp1.5.md` | all items ticked; PostgreSQL test run locally |
| 9 | WP1.5b `git` adapter | `rounds/2026-10-23-report-wp1.5b.md` | all items ticked |
| 10 | WP1.6 sync, drift, triggers | `rounds/2026-10-23-report-wp1.6.md` | all items ticked |
| 11 | WP1.7 probes, rendering, run, intake | `rounds/2026-10-23-report-wp1.7.md` | all items ticked; PostgreSQL execution run locally |
| 12 | WP1.8 retail profile and Chinook (M1 gate) | `rounds/2026-10-23-report-wp1.8.md` | M1 gate met; PostgreSQL comparison run locally |
| 13 | WP1.9 agent layer v1 | `rounds/2026-10-23-report-wp1.9.md` | all items ticked; dogfood identical |

M1 gate (brief section 7):

- `fact check` green on `examples/chinook`; residue 0.
- Scopes as expected without a decision record: Customer anchor, Invoice direct, InvoiceLine transitive (`unique_target`), Employee administrative, the catalog reference.
- Every relationship confirmed by a probe (45 probes in range).
- PostgreSQL, seeded with the same rows, gives the same neutral snapshot parts and the same 45 probe counts.

## 4. Spec, vocabulary and plan edits across the run

Spec (`spec/SPEC.md`):

- New principle 9 "The core never names an engine; adapters are plugins behind one snapshot contract".
- Adapters and Profiles rows; "First adapters: BigQuery, PostgreSQL" → the three built-in adapters and the reference engines.
- Toolset gains `fact adapters`, `fact export-sql`, `fact draft`, `fact probe run`; layout `examples/thelook/` → `examples/chinook/`.
- M1 and M2 rows rewritten; reference dataset paragraph → Chinook; "Later, not in 1.0" adds candidate adapter plugins (dbt manifest, OpenMetadata, DataHub).

Vocabulary (`spec/VOCABULARY.md`):

- Neutral example pins (`postgres:chinook@...`, `bigquery:my-project.sales@...`); git pins may use a blob hash for working-tree reads.
- Source fields `adapter`, `engine`, `dialect`, `dsn_env`, `location`, `revision`, `include`.
- Mapping block `engine_dialect` (new fence `vocabulary-map:`); blocks `engine_enforces_foreign_keys`, `type_class` (D-013), `drift_kind`.
- Profile `subject`, model `anchor_entity` (D-012); snapshots are the adapter-core contract and may carry pins.
- Trigger rules and the `triggers` stage; probes rendered per dialect, `unsupported_on_dialect`, the run and intake workflow.

Algorithms (`spec/ALGORITHMS.md`):

- Algorithm 2 reads the anchor from `factmodel.yaml`.
- Projection examples gain rule 6 (`all_ends_class: reference` → `reference_data`, vector `rule-reference-data`); customer-scoped becomes rule 7.

Plan (`spec/IMPLEMENTATION_PLAN.md`):

- Ground rule 7 gains "A local engine seeded with synthetic rows is a test fixture, not a platform".
- Section 3: generic SQL access and reference engines.
- Section 4: M1 "Core, engine-neutral", M2 "Cloud engines by adopters and a second domain".
- Section 6: heading, target, Chinook expected model; WP1.5 rewritten; WP1.6 deliverables; WP1.7 kinds, rendering, run; WP1.8 rewritten for Chinook; WP1.9 acceptance.
- Section 7 (M2) rewritten; WP3.3 and the remaining `thelook` and Pagila mentions replaced.

## 5. Decisions

| ID | Decision | Forced by |
| --- | --- | --- |
| D-011 | Engine-blind core, universal adapters, local reference engines (replaces the withdrawn draft D-011) | Owner decision (brief section 2); supersedes the plan's "core on BigQuery" framing |
| D-012 | The model binds the anchor, the profile names the subject | Owner decision; a profile is a domain, not a platform |
| D-013 | Neutral type class on snapshot fields | Owner decision |

The run forced no further decision record. Changes made along the way, none of which changes a decision or a principle:

- The `non_unique_target` rule and snapshot pins (round 8).
- `fact quote` and working-tree reads (round 9).
- One label and one rule in the retail profile (round 12).
- Five `fact source add` options (round 13).

`AGENTS.md` gained rule 10 (the agent never widens its own access).

## 6. Confirmed / inferred / unknown

**Confirmed**

- Every check is green at `20e1072`, with PostgreSQL 16 running locally in Docker.
- SQLite and PostgreSQL agree on every neutral snapshot part of the test schema and of Chinook (names, nullability, type classes, constraints), and on every probe count; PostgreSQL enforces its constraints and SQLite does not, as the vocabulary says.
- DDL parsed by the git adapter agrees with the SQLite catalog; drafts from DDL and from the catalog match.
- Following only the `model-onboard` skill reproduces the committed Chinook snapshot and drafts exactly.
- No credentials in the repository; no query ran against a remote platform. Network: package installs, the `postgres:16` image pull, and one GitHub API read for the Chinook license.

**Inferred** (choices to review; each is detailed in its round report)

- Drafted relationship keys are `to-<target>`, not constraint names (names differ by engine).
- Entity IDs split camel case (`InvoiceLine` → `invoice_line`).
- Arrays are element type plus `repeated: true`.
- `fan_out` measures the most target rows per join-key value.
- Rates are computed at intake, not in SQL.
- The retail profile labels catalog-to-catalog links `reference_data`.
- The Chinook entities stay `status: draft` until the owner reviews them.
- The `chinook-ddl` source reads the working tree, pinned by blob hash.

**Unknown**

- The GitHub Actions workflow has not run (nothing pushed). Its PostgreSQL service, the Chinook gate step and the comparison step are verified only by running the same commands locally.
- Behaviour of rendered probes on Snowflake, DuckDB, T-SQL and MySQL engines: rendering is tested, execution is not.
- Whether the hand-written Chinook DDL differs from upstream in details.

## 7. Divergences

From the brief:

- **Docker was available**, so PostgreSQL was verified locally as well as wired into CI.
- **Chinook license** `NOASSERTION`: the DDL was written by hand. Reading the license file would have needed a second network request.
- **CI PostgreSQL service** added in round 8, not round 12, because round 8's test needs it.
- **Drift report** is per source: `generated/drift-<source-id>.md`, not `generated/drift.md`.
- **Triggers** stay one file per trigger, not a single `maintenance/triggers.yaml`.
- **Extra commands and options:**
  - `fact quote` (round 9).
  - `fact probe generate` takes a default dialect for entities without a source (round 11).
  - `fact source add` adapter options (round 13).
- **Retail profile** gained `reference_data`, so Chinook's catalog links are not residue.
- **Example refresh:** the Chinook example's `AGENTS.md` and skills were refreshed after round 13.

From the plan:

- **Probe results** are JSON lines in `probes/results/`; the `probe-result` file kind is unused for now.
- **Model AGENTS.md:** the model-repository `AGENTS.md` keeps "never commit" (D-008 is for the framework repository only).

## 8. Questions for the owner

**Blocking M2**

1. Which second domain and dataset for WP2.2 (the plan leaves it open)? It should have a clear anchor, reference data and data with no anchor, and a permissive license.
2. Who verifies BigQuery through `export` and `sql` (WP2.1), on which project? The repository holds no cloud credentials (D-011), so this is an adopter's run.
3. Should the Chinook entities be marked `reviewed`, and is `reference_data` the right label name?

**Can wait**

4. Should drafts keep the engine's constraint name (for example in `extensions.draft`)?
5. Should `fact sync` take a fresh snapshot before comparing, or stay offline?
6. Should probe evidence on `synthetic` data move facts to `confirmed` (today: yes for zero-violation results, as the spec says)?
7. Should `value_set` be generated for fields with a profile vocabulary?
8. Should `fact init` copy the brief and report templates?
9. Should DDL `COMMENT ON` become field descriptions in the git adapter?

## 9. Suggested next brief: M2

- **WP2.1 Cloud engines through `export` and `sql`.** Write the adopter guide: `fact export-sql` for BigQuery, then `fact snapshot --from-export`, then the `sql` path with a SQLAlchemy BigQuery dialect. Write a packaging guide for third-party adapters, with a tiny test package registered in `factmodel.adapters` and installed in CI. The owner or an adopter runs the BigQuery steps on their own project and returns the exports; the agent never sees credentials.
- **WP2.2 Second domain profile and example.** The owner picks the dataset (question 1). The agent checks its license with one read, writes or copies the DDL accordingly, adds a seed, and models it on SQLite and PostgreSQL like Chinook. Reusing `retail` unchanged is the preferred outcome.
- **WP2.3 Core freeze review.** List every core change since M1 with its decision record, bump the schemas to 1.0.0, write `spec/VERSIONING.md`, add a `fact migrate` stub.
- **Owner inputs before it runs:** the answers to questions 1 and 2, and a push of `main` so CI runs once and the "CI only" items in section 6 become confirmed.

The local PostgreSQL container from `compose.yaml` was stopped at the end of this run (`docker compose down`).

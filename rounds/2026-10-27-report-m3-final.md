# Final report - Rounds 20 to 25: M3 semantic layers, equivalence, release, export

Date: 2026-10-27 · Brief: `rounds/2026-10-27-brief-m3-semantic-layers.md` · Branch `main`, from `61f9112`

## 1. Outcome

All six rounds completed; none stopped.

**What M3 built:**
- **Layer contract.** A semantic layer is built only on physical facts by ID (D-019, schemas 2.0.0, then 2.1.0). The gate checks it in a new stage `layers`.
- **Equivalence.** A harness proves a consumer against a corpus, with a threshold (D-021).
- **Rollups.** A probe kind measures whether hierarchies add up (D-020).
- **Release.** `fact release` builds a pinned, checked copy of a model.
- **Export.** Layers export to dbt (validated with `dbt parse`) and to Apache Ossie (structural).

**What the examples now show:**
- **QCEW** makes the semantic layer earn its keep: six naive queries give wrong answers on the seed, and the reference consumer gives the right ones by applying the layer.
- **Both reference consumers** prove their layers on SQLite and DuckDB, and both layers are `reviewed`.

Final state: ruff, ruff format, mypy (strict) and **763 tests + 1 skipped** pass with PostgreSQL 16 through `docker compose` (757 + 7 skipped without it). The skip is the DuckDB CLI script test (the `duckdb` CLI is not installed). Baseline at `61f9112`: 694 + 1 skipped.

## 2. Git log for the run

```text
$ git log --oneline 61f9112..HEAD
4f3a4ee WP3.5, WP3.6: exporters and maintenance skills
b560924 WP3.4: release projection, model-lookup and release skills
2defea1 WP3.3: reference consumers and corpora, threshold (D-021)
e2c12cd WP3.3a: layers for QCEW and Chinook, rollup probe (D-020)
49fa36b WP3.2: equivalence harness
c900f20 WP3.1: semantic layer contract v1 (D-019)
```

This final report is committed on its own after `4f3a4ee`. Nothing was pushed, amended or tagged; no commit carries an attribution line; the untracked `.claude/` folder at the repository root was left alone.

## 3. Rounds and acceptance

| Round | Work | Report | Acceptance |
| --- | --- | --- | --- |
| 20 | WP3.1 layer contract v1 (D-019); framework 0.1.0; `fact check` warns on a `schema_version` difference | `rounds/2026-10-27-report-wp3.1.md` | all items ticked |
| 21 | WP3.2 equivalence harness | `rounds/2026-10-27-report-wp3.2.md` | all items ticked |
| 22 | WP3.3a layers for QCEW and Chinook, rollup probe (D-020) | `rounds/2026-10-27-report-wp3.3a.md` | all items ticked; crosswalks absent, so F-0009 and `to-supersector` stay unresolved |
| 23 | WP3.3 reference consumers, corpora, threshold (D-021) | `rounds/2026-10-27-report-wp3.3.md` | all items ticked; owner's accept simulated once, as briefed |
| 24 | WP3.4 release projection, `model-lookup` and `release` skills | `rounds/2026-10-27-report-wp3.4.md` | all items ticked |
| 25 | WP3.5, WP3.6 exporters and maintenance skills | `rounds/2026-10-27-report-wp3.5-wp3.6.md` | all items ticked; Ossie page states no version (pinned as such) |

## 4. Equivalence results per consumer

Accepted runs (`examples/*/equivalence/accepted.json`). SQLite and DuckDB give the same outcome for every item.

| Consumer | Layer | Items | same_rows pass / fail / error | same_count | same_predicate pass | Known gaps | Share (D-021) | Threshold | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QCEW `measure-sql` | `employment-wages` | 38 | 34 / 0 / 2 | 0 | 2 | 2 (both errors) | 1.000 | 0.9 | proven, `reviewed` |
| Chinook `filter-sql` | `customer-purchases` | 31 | 29 / 0 / 0 | 0 | 2 | 0 | 1.000 | 0.9 | proven, `reviewed` |

QCEW known gaps:
- MSA detail built from counties needs the County-MSA-CSA crosswalk (F-0009);
- the national rollup needs the coverage of US000 (H2, F-0009).

QCEW naive-versus-correct pairs (the naive SQL is in each item's `note`, and a test checks that the two differ):

| Item | Naive mistake | Naive answer | Correct answer |
| --- | --- | --- | --- |
| `de-private-total-2025q1` | mixing levels (F-0008) | 39,820 | 9,219 |
| `de-total-covered-2025q1` | adding own_code 0 to its parts | 368,608 | 184,304 |
| `kent-construction-2025q1` | summing a suppressed zero (F-0003) | 0 | no value, 1 suppressed cell |
| `de-private-weekly-wage-2025q1` | averaging weekly wages (H-0002) | 1,050.0 | 1,051.13 |
| `de-private-annual-2025` | summing annual averages (H-0001) | 8,956 | 8,955 |
| `de-counties-private-2025q1` | joining the raw area list (F-0001) | each county doubled | 2,910 / 3,045 / 3,264 |

Rollups on the QCEW seed (D-020, equal on SQLite, PostgreSQL and DuckDB):

| Measure | Hierarchy | Clean parents: exact / within rounding / beyond | Suppression |
| --- | --- | --- | --- |
| third-month employment | county to state | 296 / 0 / 0 (M5) | 24 parents with a suppressed child (H5) |
| third-month employment | NAICS child to parent | 216 / 0 / 0 | 8 suppressed parents with disclosed children |
| annual average employment | county to state | 47 / 27 / 0 (H-0001) | 6 parents with a suppressed child |

## 5. Spec and vocabulary edits across the run

- **`spec/VOCABULARY.md`**
  - Section 9 rewritten: the layer contract v1, consumers, the corpus format, D-021, and building and checking a release.
  - New blocks: `measure_aggregation`, `time_granularity`, `suppressed_handling`, `equivalence_mode`, `volatile_probe_kind`.
  - `probe_kind` gains `rollup`, and `export_target` gains `ossie`.
  - The probe table gains `rollup`; the export targets and volatile probes are described.
- **`spec/SPEC.md`**
  - The semantic layer paragraph follows D-019.
  - Toolset gains `fact equivalence`, `fact release --version`, `fact check --release`, `fact lookup` and `fact export --target`.
  - Open questions closed: equivalence threshold and export priority.
  - Roadmap: M3 done on synthetic corpora.
- **`spec/ALGORITHMS.md`**: algorithm 3 says what `fact release` writes.
- **`spec/VERSIONING.md`**: current version 2.1.0, with what 2.0.0 and 2.1.0 changed; the `fact check` warning.
- **`spec/IMPLEMENTATION_PLAN.md`**: the gate stage table gains `layers`; a paragraph per round under WP3.1 to WP3.6; M3 marked done.
- **`spec/CORE-CHANGES-M3.md`** (new): the M3 ledger, 17 rows, each with its record.

## 6. Decisions

| ID | Decision | Platform |
| --- | --- | --- |
| D-019 | Semantic layer contract v1 (schemas 2.0.0) | QCEW, Chinook |
| D-020 | Rollup probe kind; a hierarchy is confirmed for aggregation only by a rollup | QCEW |
| D-021 | Equivalence threshold: 0.9 default, per consumer; no regression; every failure explained | none |

Each was recorded in its round before the code that depends on it. No contract change outside D-019 to D-021 needed a decision under D-018, and no D-022 was written. The additive changes (corpus format, `rollups` key, release folder format, `volatile_probe_kind`, `ossie`, `schema_version`) have ledger lines.

## 7. Core-change ledger summary

`spec/CORE-CHANGES-M3.md`:
- 3 breaking or meaning changes, each with its decision: the layer contract (D-019), rollup confirmation (D-020) and the threshold (D-021);
- 5 additive contract changes with ledger lines;
- 2 version bumps (2.0.0, 2.1.0);
- the rest implementation of plan work packages.

## 8. Confirmed / inferred / unknown

**Confirmed**

- **Layers in use.** Both layers pass the `layers` stage; their consumers prove them on SQLite and DuckDB; releases of both examples pass `fact check --release`; exports of both pass `dbt parse`.
- **Engine agreement.** The QCEW rollups and every probe count agree on SQLite, PostgreSQL 16 and DuckDB.
- **Network use.** Package installs (dbt-core, dbt-duckdb), the one read of https://ossie.apache.org/, and one PyPI version check made by `dbt --version` (section 9). No credentials were used, and no query ran against a remote platform.
- **Two defects found and fixed in passing:**
  - the model loader read a built release under `release/out/` as model files;
  - an `EXCEPT` with parenthesised operands, which SQLite rejects, in the owner-run equivalence script.

**Inferred** (details in each round report)

- **Distinct rule.** The concept form `distinct` was written into D-019 for F-0001.
- **Rollups.** They are declared on layer measures.
- **Required concepts.** They are applied to the measure; a companion counts the cells they leave out.
- **Naming.** Consumer and reference SQL name tables by entity id, and the harness binds them to physical names.
- **Ossie.** The export keeps to the structure the pinned page shows.
- **`fact lookup`.** It was added because the `model-lookup` skill needs joins resolved.

**Unknown**

- **A real corpus.** How a consumer scores on a real corpus outside the repository (the SPEC's M3 gate): both corpora here are synthetic. This is the M4 pilot.
- **Ossie fidelity.** The specification document was not read.
- **CI.** The workflow has not run the new steps (nothing pushed).

## 9. Divergences

- **Schema bumps.** Schemas went to 2.0.0 in round 20, as D-019 foresaw for a breaking layer contract, and to 2.1.0 in round 22 for the additive `rollups` key and `rollup` kind.
- **New commands.** `fact lookup`, and a `release` stage in the release gate (VERSION, notes, derived-key leaks), both beyond the brief's list.
- **Optional `schema_version`.** Added in round 19 and carried here: examples are at 2.1.0, and `fact check` warns on any other value.
- **dbt version check.** `dbt --version` made one PyPI version-check request. All later dbt calls run with the version check and tracking off.
- **No Ossie version.** The pinned Ossie version is "not stated": neither the page nor `spec/SPEC.md` names one.
- **Brief concepts split.** The brief's `area_kind` and `period` concepts became three area-kind predicates and a quarter field.
- **Owner's accept.** It was simulated once in round 23, as briefed.

## 10. Questions for the owner

**Can wait**

1. Should a layer carry the join condition of each relationship key it lists, so consumers never need the physical model? Today `fact lookup` and the release give it.
2. Should the A4 level matrix become a layer concept of its own (a table-valued concept), so a consumer does not derive `agglvl_code`?
3. May the agent read the Ossie core specification once more, to pin a version and move the `ai_context` text into real keys?
4. Should the dbt exporter generate derived metrics for formula measures?
5. Should `RELEASE_NOTES.md` also be committed in the model repository, so a fresh CI build carries the history?
6. Should `fact migrate` gain a 1.x to 2.x layer migration? No model needed one here.

## 11. Suggested next brief: M4 (release 1.0)

- **WP4.1 Packaging.**
  - Build and check the wheel and sdist; extras `[sql]`, `[postgres]` and `[duckdb]`, and the plugin example.
  - A clean-room install test in a fresh virtual environment: `fact init`, `fact check` and `fact release` on Chinook from the installed package only.
  - Version 1.0.0 for the framework when M4's gate passes.
- **WP4.2 Docs site.** Built from `spec/`, `docs/` and the skills, with a page per command. Plain Markdown with a static generator chosen by the owner; the content is the spec, not a rewrite.
- **WP4.3 Tutorial.** A from-scratch walk through Chinook: init, onboard, scaffold, probes, a layer with a 30-item corpus, equivalence, release, export. Every step is a command the tutorial test runs.
- **WP4.4 External pilot on the owner's standalone QCEW model with real data.**
  - The owner points FactModel at their own `qcew-model` (DuckDB, real 2024 and 2025 files).
  - The agent never reads the data. It renders probes and equivalence scripts; the owner runs them and returns counts.
  - The corpus is real QCEW questions with the owner's reference SQL, kept outside the repository and referenced by pin.
  - Expected outcome: the nine findings reproduce as measured facts (R1 4,649 duplicates; V1 the `-` counts; G2 the padding), the rollups give real M5 and H5 counts, and the consumer meets 0.9 or the failures become findings. This closes the SPEC's M3 gate on a real corpus.
- **Owner inputs before it runs:**
  - the answers to questions 1 and 3;
  - whether the crosswalks may be placed under D-016;
  - a push of `main`, so CI runs the M2 and M3 steps once.

The local PostgreSQL container from `compose.yaml` is stopped at the end of this run (`docker compose down`).

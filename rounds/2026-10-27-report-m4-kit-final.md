# Final report - Rounds 26 to 28: M4 kit (packaging, documentation, tutorial, pilot kit)

Date: 2026-10-27 · Brief: `rounds/2026-10-27-brief-m4-release.md` · Branch `main`, from `85494ea`

## 1. Outcome

All three rounds completed; none stopped. The framework version stays 0.1.0, the schemas are at 2.2.0, and no decision record was written (no D-022).

**What M4 built:**
- **Packaging.** The wheel and sdist build, `twine check` passes, and the wheel alone runs the Chinook loop outside the repository.
- **Documentation site.** The site builds strictly, with a generated CLI and schema reference, a tested quickstart and a FAQ.
- **Tutorial.** It takes an empty folder to a release and two exports, tested on the installed wheel.
- **Pilot kit.** The owner can run the QCEW model on the real files; the kit was dry-run end to end on a stand-in.
- **Ossie.** The export is pinned to the core specification 0.2.0.dev0.

**M4 status: kit done, pilot pending.** The M4 gate needs the owner's pilot and the release round after it.

Final state: ruff, ruff format, mypy (strict) and **779 tests + 1 skipped** pass with PostgreSQL 16 through `docker compose` (773 + 7 skipped without it). The skip is the DuckDB CLI script test (no `duckdb` CLI here). Baseline at `85494ea`: 763 + 1 skipped.

## 2. Git log for the run

```text
$ git log --oneline 85494ea..HEAD
7e31869 WP4.3: tutorial, pilot kit, Ossie pin
b73b00a WP4.2: documentation site
9236cc5 WP4.1: packaging, clean-room install, M3 answers
```

This final report is committed on its own after `7e31869`. Nothing was pushed, amended or tagged; no commit carries an attribution line; the untracked `.claude/` folder at the repository root was left alone.

Network use, all within section 1 of the brief:
- package installs;
- one HEAD request to the PyPI project page (round 26);
- one GET of the Apache Ossie core specification (round 28);
- dbt ran with tracking and the version check off.

The owner's real QCEW data was never touched.

## 3. Rounds and acceptance

| Round | Work | Report | Acceptance |
| --- | --- | --- | --- |
| 26 | WP4.1 packaging, clean-room install, M3 answers Q1, Q2, Q4, Q5, Q6 | `rounds/2026-10-27-report-wp4.1.md` | all items ticked; PyPI answers 200 for `factmodel` (reported, owner decides) |
| 27 | WP4.2 documentation site | `rounds/2026-10-27-report-wp4.2.md` | all items ticked |
| 28 | WP4.3 tutorial, pilot kit, Ossie pin | `rounds/2026-10-27-report-wp4.3.md` | all items ticked; the dry run found and fixed an equivalence-script defect |

## 4. Clean-room install and tutorial test

**The clean-room install** (`tests/install/test_clean_room.py`). The test:
- builds the wheel;
- installs `factmodel[sql]` into a fresh virtual environment outside the repository;
- asserts that `factmodel`, its vocabulary and its profiles resolve inside that environment and that nothing on `sys.path` is under the source tree;
- runs the Chinook loop from a folder outside the tree.

```text
fact 0.1.0 (schemas 2.2.0)
gate: pass
generated/ is up to date
45 probes, 0 written, 0 facts skipped
customer-purchases: 31 pass, 0 fail, 0 error of 31
share 1.000, threshold 0.9: proven
release 0.1.0: 135 exported, 14 projected, 48 refused -> .../work/release
gate: pass
customer-purchases -> dbt: 1 file(s), 0 note(s)
```

**The tutorial** (`docs/tutorial/chinook.md`). The test runs on the same wheel environment, which round 28 made a shared session fixture. It asserts that `fact` resolves inside that environment, then runs every block of the page in order in an empty temporary folder. Every promised output appeared:

```text
FAIL  projection (4)
gate: fail
the gate failed, as expected
gate: pass
residue: 0
invoice	direct	-	-	true
invoice_line	transitive	unique_target	invoice_line.to-invoice	true
19 probes run, 0 failed: probes/results/chinook-db@2026-10-27.jsonl
19 in range, 0 out of range, 0 failed, 0 rejected; 38 files written
purchases: 3 pass, 0 fail, 0 error of 3
share 1.000, threshold 0.9: proven
purchases: accepted
release 0.1.0: 54 exported, 6 projected, 37 refused -> chinook-release
PASS  release
gate: pass
purchases -> ossie: 1 file(s), 5 note(s)
purchases -> dbt: 1 file(s), 2 note(s)
```

## 5. Spec and vocabulary edits across the run

- **`spec/VOCABULARY.md`** (round 26):
  - the concept form `values_table`;
  - the per-layer join table `semantic/<layer>/generated/joins.tsv` and its `derived-not-authored` check;
  - release notes live in the model repository.
  - No vocabulary block gained or lost a value in M4.
- **`spec/SPEC.md`**:
  - toolset rows `fact --version` (26), `fact probe render` and `fact quote` (27);
  - roadmap: M3 caveat points at `docs/pilot/qcew-real-data.md`; M4 "kit done, pilot pending: rounds 26 to 28" (28);
  - open question on export priority: Ossie pinned to 0.2.0.dev0 (28);
  - sources: the Ossie core specification link (28).
- **`spec/VERSIONING.md`** (26): current schema version 2.2.0; `fact migrate` lists the registered steps.
- **`spec/IMPLEMENTATION_PLAN.md`**:
  - section 9 has a paragraph per round and "Status: kit done, pilot pending";
  - WP3.5 notes the round-28 pin.
- Full old and new text is in each round report, section 4.

## 6. Decisions

None written or changed. Two classifications under D-018 were judged; both are in the round-28 report:
- the Ossie export follows the target's document: implementation, no framework key changed;
- the equivalence-script fix makes code do what the spec says: a defect fix.

D-010 gained a dated evidence line only (round 26: PyPI 200).

## 7. Core-change ledger (`spec/CORE-CHANGES-M4.md`)

| # | Round | Change | Kind | Record |
| --- | --- | --- | --- | --- |
| 1 | 26 | Layer join tables `semantic/<layer>/generated/joins.tsv` | derived output, additive | ledger line (D-018) |
| 2 | 26 | Concept form `values_table` | contract, additive | ledger line (D-018) |
| 3 | 26 | Schemas 2.2.0 | version | D-018 (additive) |
| 4 | 26 | dbt derived metrics for formula measures | implementation | - |
| 5 | 26 | `release/RELEASE_NOTES.md` committed in the model repository | release format, additive | ledger line (D-018) |
| 6 | 26 | `fact migrate` registry slot | implementation | - |
| 7 | 26 | sdist excludes `.claude/`; `fact --version` shows the schema version | implementation | - |
| 8 | 27 | Documentation site; SPEC toolset catches up with the CLI | documentation | - |
| 9 | 28 | Ossie export pinned to the core specification 0.2.0.dev0 | implementation | - |
| 10 | 28 | Tutorial and pilot kit | documentation | - |

Defect fixes (CHANGELOG only, D-018): the EXCEPT operands of the equivalence script (28).

## 8. Confirmed / inferred / unknown

**Confirmed**

- **The wheel stands alone.** The wheel runs the Chinook loop and the whole tutorial with nothing from the source tree.
- **The site.** `mkdocs build --strict` passes; the tutorial and the pilot kit are in the nav.
- **Ossie 0.2.0.dev0.** The document marks itself a draft and has no JSON Schema. The export writes only keys it names, and every reference resolves to a declared field.
- **The pilot kit.** The kit ran end to end on a stand-in: the seed split into `annual_2024`, `annual_2025` and `qtrly_2025`, with `HOME` in a scratch folder.
  - The drift report works against a seed-shaped baseline.
  - 47 probes ran: 42 in range and 5 out of range, as the kit predicts.
  - The owner-run equivalence path gives 36 pass and 2 known gaps, proven.
  - The return folder is complete.
- **PyPI.** `factmodel` has a page (HTTP 200, round 26).

**Inferred**

- **What step 1 copies.** It also copies `evidence/` and `registers/`: the copied physical layer fails 127 reference checks without them.
- **The pilot model's sources.** `qcew-duckdb` is `owner_read`; `qcew-sqlite` stays registered as the source the seed's probe evidence names; the layer starts as `draft`.
- **Expected real counts.**
  - R1: 4,649 duplicate area codes;
  - V1: 1,316,380 `-` rows (47,061 + 46,370 + 612,719 + 610,230);
  - G2: 14,639,988 quarterly rows (4 x 3,659,997).
  - All three come from `profile.md` and the committed code list, not from a run on real data.

**Unknown**

- **The real data.** How the real catalog differs from the seed DDL, the real rollup counts (M5, H5), and whether `measure-sql` meets 0.9 on the owner's 30 questions. That is what the pilot answers.
- **Ossie's next version.** Whether Ossie changes again before its 0.2.0 release.
- **The PyPI name.** Who holds `factmodel` on PyPI.

## 9. Divergences

- **Pilot step 1 copies more than the brief names.** It also copies `evidence/` and `registers/` (the physical layer cites them).
- **`views.sql` also loads the code lists.** It creates the five code-list tables from the committed CSVs when the owner's file has none.
- **The kit adds a Python runner.** `run-duckdb.py` is a fallback for owners without the `duckdb` command line.
- **The kit's return folder adds the drift report.**
- **Round 28 changed code beyond the brief's list.** It fixed a defect in `fact equivalence script` (references that start with `WITH`), found by the pilot dry run. Without the fix, the owner's step 5 would have failed on every QCEW-style reference.

## 10. Questions for the owner

1. **PyPI name.** Keep `factmodel` (a page now exists), or choose another distribution name before publishing? A change needs a decision record superseding D-010.
   Correction (round 29): no page exists. `https://pypi.org/project/factmodel/` returns 200 for any name, because it serves an anti-bot "Client Challenge" page (it does so for `typer` too), so its status says nothing about the name. `https://pypi.org/simple/factmodel/` and `https://pypi.org/pypi/factmodel/json` both return 404: the name is free. The owner keeps the name (D-010 evidence).
2. **Ossie pin.** Keep the draft 0.2.0.dev0, or pin to the released 0.1.1, whose text was not read (one more read)?
3. **Site generator.** Stay on MkDocs Material, or move to its successor, Zensical, before Material's end of life (May 2027)?
4. **Seed evidence after the pilot.** Remove the seed's probe evidence and the `qcew-sqlite` source from the pilot model once real evidence is in, or keep them as history?
5. **2024 quarterly data.** Does `qcew.duckdb` hold a 2024 quarterly table? If so, adding it to the `qtrly` view closes the two expected prior-year findings.

## 11. Owner steps for the pilot, in order

Before the pilot (brief section 5, step 1):

1. Review the three commits and this report, then push: `git push origin main`.
2. Confirm CI is green on GitHub (tests, package build, strict site build).
3. Enable GitHub Pages with source "GitHub Actions", so `pages.yml` deploys the site.

The pilot (`docs/pilot/qcew-real-data.md`, every block in order, in one shell):

4. **Step 0, paths and install.**
   - Run `export QCEW_DB=/full/path/to/qcew.duckdb`.
   - Run the step-0 blocks. They set `FACTMODEL_REPO`, `PILOT` (`~/AI/semantic/qcew-semantic-model`) and `M` (`$PILOT/model`), and check that `$M` does not exist yet.
   - Then they build the wheel into `$PILOT/dist`, create `$PILOT/.venv`, install `factmodel[sql,duckdb]` and put it on `PATH`.
   - Check that `fact --version` prints `fact 0.1.0 (schemas 2.2.0)`.
5. **Step 1, the model.** Run the step-1 block:
   - `fact init "$M" --id qcew --profile statistics`;
   - copy the physical entities, the `employment-wages` layer, the `measure-sql` consumer, `evidence/` and `registers/` from `examples/qcew`;
   - drop the synthetic corpus and set the layer to `draft`;
   - `git init` and the first commit.
6. **Step 2, sources.**
   - Copy the document sources, `qcew-sqlite` and the code lists.
   - Register `qcew-duckdb` (`sql`, `duckdb`, `owner_read`, `dsn_env: FACT_DSN_QCEW`) and move the entities to it.
   - Write `$PILOT/views.sql`: `annual` = `annual_2024` UNION ALL BY NAME `annual_2025`; `qtrly` = `qtrly_2025`; the code-list tables if missing.
   - Apply it to `qcew.duckdb`, then run `fact project` and `fact check`. Expect `gate: pass`. Commit.
7. **Step 3, snapshot and drift.**
   - Build the seed-shaped baseline (`seed.py duckdb $PILOT/seed-shape.duckdb`) and snapshot it dated 2026-10-23.
   - Set `FACT_DSN_QCEW=duckdb:///$QCEW_DB` and `DAY=$(date +%F)`.
   - Snapshot your file, run `fact sync`, and read `generated/drift-qcew-duckdb.md` with the guide in the kit.
   - Fix field types that really differ. Run `fact project` and `fact check`, then commit.
8. **Step 4, probes.**
   - Run `fact probe generate` and `fact probe render --dialect duckdb --source qcew-duckdb`, and read the script.
   - If there is no `duckdb` command line, write `$PILOT/run-duckdb.py` and set `RUN_SQL`.
   - Run the script with `DUCKDB_DB="$QCEW_DB" PIN="duckdb:qcew@$DAY" DATA_QUALITY=representative RAN_ON="$DAY"` into `probes/results/qcew-duckdb@$DAY.jsonl`.
   - Then `fact probe intake`, `fact project`, `fact check` and `fact status`. Commit.
   - Compare the counts with the kit's table: R1 4,649; V1 1,316,380 (per quarter 47,061 / 46,370 / 612,719 / 610,230); G2 14,639,988; the real rollup counts; and two expected prior-year findings.
9. **Step 5, the real corpus.**
   - Write 30 questions with reference SQL in `$PILOT/corpus/`, outside the model repository.
   - Write `consumer.yaml` with `location: ../../../corpus` and `pin: qcew-semantic-model corpus@$DAY`.
   - Run `fact equivalence script --dialect duckdb`, run the script with `DUCKDB_DB` into `$PILOT/equivalence-$DAY.jsonl`, then `fact equivalence run --results ... --source qcew-duckdb --date "$DAY"`.
   - If it says `proven`: `fact equivalence accept`, set the layer to `reviewed`, `fact check`, commit.
   - If not: one finding per failing question, `finding:` on the question, commit, fix and rerun step 5.
10. **Step 6, send back.** Run the step-6 block and send `$PILOT/return/`:
    - `git-log.txt`;
    - `status.txt`;
    - `equivalence-employment-wages.md`;
    - `drift-qcew-duckdb.md`;
    - `probe-results/`.
    - Keep the corpus with you; its pin is in `consumer.yaml`.

After the pilot (brief section 5, step 3): round 29 records the pilot results, sets version 1.0.0, writes the release notes and runs `uv build`; the owner publishes.

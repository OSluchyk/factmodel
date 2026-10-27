# Pilot: the QCEW model on real data

This is the owner's kit for the M4 pilot. It moves the QCEW example from its synthetic seed to the real 2024 and 2025 files in your `qcew.duckdb`, and brings back what the acceptance round needs. You run every command; nothing here reaches the data on its own. Every query returns counts only.

The commands were dry-run in round 28 on a stand-in: the synthetic seed split into the same per-year tables (`annual_2024`, `annual_2025`, `qtrly_2025`). The real numbers will differ; section 4 says which ones to expect.

Run the blocks in order, in one shell session. Each step ends with a commit, so `git log` tells the story.

## 0. Before you start

You need `uv`, `git`, `perl` and the framework checkout. Set four paths. `QCEW_DB` is the one only you know: the full path of your `qcew.duckdb`.

```bash
export FACTMODEL_REPO="${FACTMODEL_REPO:-$HOME/AI/semantic/factmodel}"
export PILOT="${PILOT:-$HOME/AI/semantic/qcew-semantic-model}"
export M="$PILOT/model"
export QCEW_DB="${QCEW_DB:?set QCEW_DB to the full path of your qcew.duckdb}"
mkdir -p "$PILOT"
if [ -e "$M" ]; then echo "STOP: $M exists; move it away before step 1"; else echo "ok: $M is free"; fi
```

Install the framework from a wheel built from the checkout, into its own environment next to the model, with the DuckDB driver:

```bash
uv build "$FACTMODEL_REPO" --wheel --out-dir "$PILOT/dist"
uv venv "$PILOT/.venv" --python 3.12 --quiet
uv pip install --python "$PILOT/.venv/bin/python" --quiet "$(ls "$PILOT"/dist/factmodel-*.whl)[sql,duckdb]"
export PATH="$PILOT/.venv/bin:$PATH"
fact --version
```

Expect `fact 0.1.0 (schemas 2.2.0)`.

## 1. Create the model and copy the example into it

```bash
fact init "$M" --id qcew --profile statistics
E="$FACTMODEL_REPO/examples/qcew"
cp -R "$E/physical/entities/." "$M/physical/entities/"
cp -R "$E/semantic/employment-wages" "$M/semantic/"
cp -R "$E/consumers" "$M/"
cp -R "$E/evidence/." "$M/evidence/"
cp -R "$E/registers/." "$M/registers/"
rm -rf "$M/semantic/employment-wages/corpus" "$M/semantic/employment-wages/generated"
perl -pi -e 's/^status: reviewed$/status: draft/' "$M/semantic/employment-wages/layer.yaml"
git -C "$M" init --quiet
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 1: model from examples/qcew"
```

What is copied, and why:

- `physical/entities/`: the seven entities (`annual`, `qtrly` and the five code lists), with their fields, keys, relationships and meanings. This is the physical layer.
- `semantic/employment-wages/`: the layer (concepts, the level matrix, measures, rollups) and its consumer file.
- `consumers/measure-sql/`: the reference consumer, the code that turns a request into SQL.
- `evidence/` and `registers/`: the physical layer cites them. The evidence holds the document quotes (BLS layouts, title files, your `profile.md`) and the probe results measured on the seed. The registers hold hazards H-0001 and H-0002 and findings F-0001 to F-0009.

What is not copied: the synthetic corpus (the real corpus is yours, step 5), the seed, the snapshots, the probes (step 4 generates them again) and the accepted equivalence run. The layer goes back to `draft`, because its proof was on synthetic data.

Why the model still has to re-snapshot: every copied fact was checked against the seed's catalog, not against your file. The entities still describe the seed shape until a snapshot of your file says otherwise, and the probe evidence still measures synthetic rows (it stays `inferred`, because this model has no `treat_synthetic_as_representative`).

## 2. Sources

Register your DuckDB file, the documents, and the real code lists:

```bash
cp "$E"/sources/{bls-layout-annual,bls-layout-qtrly,bls-titles,owner-profile,qcew-sqlite}.yaml "$M/sources/"
cp -R "$E/sources/codelists" "$M/sources/"
fact source add --root "$M" --id qcew-duckdb --title "QCEW in the owner's DuckDB file" --kind warehouse --access-mode owner_read --engine duckdb --adapter sql --dsn-env FACT_DSN_QCEW
perl -pi -e 's/^source: qcew-sqlite$/source: qcew-duckdb/' "$M"/physical/entities/*.yaml
```

- `qcew-duckdb` is your file: adapter `sql`, engine `duckdb`, connection string in `FACT_DSN_QCEW` (never in a file), `owner_read` because only you read it.
- The entities now live in `qcew-duckdb`. `qcew-sqlite` stays registered only as the source the seed's probe evidence names.
- The documents are the BLS layouts (annual and quarterly), the BLS title files and your `profile.md`. The code lists are the real BLS files, committed unchanged (D-016).

The physical layer reads two tables, `annual` and `qtrly`, and five code lists. Your file has per-year tables. Two views make the physical layer apply unchanged, and the code lists are loaded from the CSV files when your file does not already have them. This adds two views and at most five small tables to `qcew.duckdb`; nothing that is there changes. If you have more yearly tables (for example `qtrly_2024`), add a `UNION ALL BY NAME SELECT * FROM qtrly_2024` line to the view.

```bash
cat > "$PILOT/views.sql" <<SQL
CREATE OR REPLACE VIEW annual AS
  SELECT * FROM annual_2024
  UNION ALL BY NAME SELECT * FROM annual_2025;
CREATE OR REPLACE VIEW qtrly AS
  SELECT * FROM qtrly_2025;
CREATE TABLE IF NOT EXISTS agglevel_titles AS SELECT * FROM read_csv('$M/sources/codelists/agglevel_titles.csv', all_varchar = true);
CREATE TABLE IF NOT EXISTS area_titles AS SELECT * FROM read_csv('$M/sources/codelists/area_titles.csv', all_varchar = true);
CREATE TABLE IF NOT EXISTS industry_titles AS SELECT * FROM read_csv('$M/sources/codelists/industry_titles.csv', all_varchar = true);
CREATE TABLE IF NOT EXISTS ownership_titles AS SELECT * FROM read_csv('$M/sources/codelists/ownership_titles.csv', all_varchar = true);
CREATE TABLE IF NOT EXISTS size_titles AS SELECT * FROM read_csv('$M/sources/codelists/size_titles.csv', all_varchar = true);
SQL
python -c "import duckdb, sys; duckdb.connect(sys.argv[1]).execute(open(sys.argv[2]).read())" "$QCEW_DB" "$PILOT/views.sql"
fact project --root "$M"
fact check --root "$M"
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 2: sources"
```

Expect `gate: pass`.

## 3. Snapshot, sync and the drift report

`fact sync` compares the two latest snapshots of a source. So the first snapshot is a baseline of the seed shape (a throwaway DuckDB file the seed script creates next to the model), and the second is your file. The drift report then lists exactly what your catalog changes against the shape the model was written for.

```bash
python "$E/seed/seed.py" duckdb "$PILOT/seed-shape.duckdb"
FACT_DSN_QCEW="duckdb:///$PILOT/seed-shape.duckdb" fact snapshot --root "$M" --source qcew-duckdb --date 2026-10-23
export FACT_DSN_QCEW="duckdb:///$QCEW_DB"
export DAY="$(date +%F)"
fact snapshot --root "$M" --source qcew-duckdb --date "$DAY"
fact sync --root "$M" --source qcew-duckdb
cat "$M/generated/drift-qcew-duckdb.md"
fact project --root "$M"
fact check --root "$M"
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 3: snapshot of the real catalog, drift report"
```

How to read the drift report (`generated/drift-qcew-duckdb.md`), from the dry run:

- `annual_2024`, `annual_2025`, `qtrly_2025` are new objects with draft entities under `drafts/`. They are the storage behind the views; leave the drafts where they are, the model reads `annual` and `qtrly`.
- Key fields of `annual` and `qtrly` change `nullable false -> true`: a view does not carry the tables' NOT NULL. Not a change in the data.
- A `type_class_change` (for example `year` text to integer) is a real difference between the seed DDL and your load. Each one is a fact to review: update the field's `type` in `physical/entities/`, or open a finding if the meaning changes.
- Anything else, such as a column the seed does not have, is a new fact to model or to leave out on purpose.

## 4. Probes

```bash
fact probe generate --root "$M"
fact probe render --root "$M" --dialect duckdb --source qcew-duckdb
less "$M/probes/scripts/qcew-duckdb.duckdb.sh"
```

Read the script: every query is a count. It runs with the `duckdb` command line (`brew install duckdb`). Without it, a five-line Python runner does the same:

```bash
cat > "$PILOT/run-duckdb.py" <<'PY'
"""Run the SQL read from stdin on DUCKDB_DB, read-only; print the one value it returns."""
import os
import sys

import duckdb

with duckdb.connect(os.environ["DUCKDB_DB"], read_only=True) as conn:
    print(conn.execute(sys.stdin.read()).fetchone()[0])
PY
command -v duckdb >/dev/null || export RUN_SQL="python $PILOT/run-duckdb.py"
```

Run the probes and take the results in:

```bash
mkdir -p "$M/probes/results"
DUCKDB_DB="$QCEW_DB" PIN="duckdb:qcew@$DAY" DATA_QUALITY=representative RAN_ON="$DAY" bash "$M/probes/scripts/qcew-duckdb.duckdb.sh" > "$M/probes/results/qcew-duckdb@$DAY.jsonl"
fact probe intake --root "$M" "$M/probes/results/qcew-duckdb@$DAY.jsonl"
fact project --root "$M"
fact check --root "$M"
fact status --root "$M"
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 4: probes on real data"
```

`PIN` must be the pin of the snapshot you took today (`duckdb:qcew@<date>`; the stem of the file name is the location). `DATA_QUALITY=representative` says these are the real files. The model has no `treat_synthetic_as_representative`, so it matters: every result here is `representative`, and an in-range result confirms its fact.

What to expect in `probes/results/qcew-duckdb@<date>.jsonl`:

| Probe | Expected on your data | Why |
| --- | --- | --- |
| `key-duplicates-area-titles` (R1) | `duplicate_keys` 4,649 | The committed area code list is the real file (F-0001). Out of range by design; it cites F-0001. |
| `value-set-qtrly-disclosure-code` (V1) | `outside_values` 1, `outside_rows` 1,316,380 | The `-` rows: 47,061 + 46,370 + 612,719 + 610,230 in 2025 Q1 to Q4 (`profile.md` Q07, F-0002). |
| `row-count-qtrly` (G2) | `row_count` 14,639,988 | Four quarters of exactly 3,659,997 rows each: the padding (`profile.md` G2, Q08, F-0006). |
| `rollup-employment-month3-area-titles-in-state` (M5, H5) | real counts | `exact` where nothing is suppressed (M5); `parents_with_suppressed_child` and `suppressed_parents_disclosed_children` measure H5 (F-0007). The seed gave 148 exact, 12 with a suppressed child. |
| `rollup-employment-month3-industry-titles-parent` (M5, H5) | real counts | The seed gave 108 exact, 4 suppressed parents with disclosed children. |
| `rollup-annual-employment-area-titles-in-state` (H-0001) | real counts | `within_rounding` measures how far annual averages are from sums. The seed gave 47 exact, 27 within rounding, 0 beyond. |
| `join-match-qtrly-prior-year` | out of range | Your file has no 2024 quarterly table, so no 2025 quarter finds its prior year. Intake opens a finding; close it as explained, or add `qtrly_2024` to the view. |
| `join-match-annual-to-quarters` | out of range | The 2024 annual rows have no quarterly rows, for the same reason. |

The per-quarter split of V1 and G2 is one count query each, if you want to check it against `profile.md` Q07 and Q08:

```bash
python -c "import duckdb, sys; c = duckdb.connect(sys.argv[1], read_only=True); print(c.execute(\"SELECT qtr, COUNT(*) AS rows, COUNT(*) FILTER (WHERE disclosure_code = '-') AS dash_rows FROM qtrly GROUP BY qtr ORDER BY qtr\").fetchall())" "$QCEW_DB"
```

A result out of range opens a finding (`registers/findings/`). Read each one: either the model is wrong (fix the fact) or the data is (keep the finding open, it is now evidence).

Now remove the seed's probe evidence. Those records measured the synthetic seed, not your platform; the real intake above replaces them. The script deletes every record from source `qcew-sqlite` with `data_quality: synthetic`, and every citation of one. Catalog evidence and document evidence (BLS layouts, title files, `profile.md`) stay.

```bash
cat > "$PILOT/drop-seed-evidence.py" <<'PY'
"""Remove probe records measured on the seed (source qcew-sqlite, data_quality synthetic) and
every citation of them from the model at argv[1]; keep catalog and document evidence. A file
is rewritten only when something was removed from it."""
import sys
from pathlib import Path

from ruamel.yaml import YAML

root = Path(sys.argv[1])


def writer(nulls):
    """The settings fact probe intake writes with; nulls stay 'null' where the file wrote them so."""
    out = YAML(typ="rt")
    out.preserve_quotes = True
    out.width = 4096
    if nulls:
        out.representer.add_representer(
            type(None), lambda r, _: r.represent_scalar("tag:yaml.org,2002:null", "null")
        )
    return out


yaml = writer(False)


def seed(record):
    return record.get("source") == "qcew-sqlite" and record.get("data_quality") == "synthetic"


def cites(value, ids):
    return isinstance(value, str) and value in ids


def prune(node, ids):
    """Drop citations of ids; a list of nothing but such citations goes with its key."""
    changed = False
    if isinstance(node, dict):
        for key in list(node):
            value = node[key]
            if isinstance(value, list) and value and all(cites(v, ids) for v in value):
                del node[key]
                changed = True
            else:
                changed |= prune(value, ids)
    elif isinstance(node, list):
        for i in reversed(range(len(node))):
            if cites(node[i], ids):
                del node[i]
                changed = True
            else:
                changed |= prune(node[i], ids)
    return changed


files = sorted(p for p in root.rglob("*.yaml") if ".git" not in p.parts and "drafts" not in p.parts)
docs = {p: yaml.load(p.read_text(encoding="utf-8")) for p in files}
ids, deleted, edited = set(), 0, 0
for path, doc in docs.items():
    records = doc.get("records") if isinstance(doc, dict) else None
    if records and any(seed(r) for r in records):
        ids |= {r["id"] for r in records if seed(r)}
        doc["records"] = [r for r in records if not seed(r)]
        doc["_dirty"] = True
for path, doc in docs.items():
    if not isinstance(doc, dict):
        continue
    dirty = doc.pop("_dirty", False)
    if dirty and not doc["records"] and doc.get("kind") == "evidence":
        path.unlink()
        deleted += 1
        continue
    if prune(doc, ids) or dirty:
        nulls = ": null\n" in path.read_text(encoding="utf-8")
        with path.open("w", encoding="utf-8") as handle:
            writer(nulls).dump(doc, handle)
        edited += 1
print(f"{len(ids)} seed probe records removed; {deleted} files deleted, {edited} edited")
PY
python "$PILOT/drop-seed-evidence.py" "$M"
fact project --root "$M"
fact check --root "$M"
fact status --root "$M"
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 4: seed probe evidence removed"
```

Expect `49 seed probe records removed; 49 files deleted` and `gate: pass`. A fact the seed alone had confirmed now rests on your intake: in range, it is `confirmed`; out of range, its finding is open.

## 5. The real corpus

Write 30 questions, each with the SQL you trust as the answer. Keep them outside the model repository, in `$PILOT/corpus/`, one YAML file per question, in the same form as the example corpus (`examples/qcew/semantic/employment-wages/corpus/` has 38 to read). For example:

```yaml
id: de-private-total-2025q1
request:
  measure: employment_month3
  area: '10000'
  industry: '10'
  ownership: '5'
  year: '2025'
  qtr: '1'
reference: WITH sel AS (SELECT * FROM qtrly WHERE area_fips = '10000' AND industry_code = '10' AND own_code = '5' AND year = '2025' AND qtr = '1' AND agglvl_code = '51') SELECT SUM(CASE WHEN disclosure_code IS NULL THEN month3_emplvl END) AS value, SUM(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) AS suppressed_cells FROM sel
mode: same_rows
```

The `request` keys are what the consumer understands (`consumers/measure-sql/compile.py` lists them). The `reference` names tables by entity id (`qtrly`, `annual`, `area_titles`, ...). A question the consumer cannot answer yet gets `known_gap: <why>`; the threshold counts the others.

Point the consumer at the corpus by pin. The pin is your record of which version of the questions was run: use the date you froze them, or a commit if `$PILOT/corpus` is a git repository.

```bash
cat > "$M/semantic/employment-wages/consumer.yaml" <<YAML
kind: consumer
id: measure-sql
meaning: >-
  Turns a measure request (measure, area, industry, ownership, period, level) into SQL using
  only the employment-wages layer, and reports suppressed cells next to the measure.
layers: [employment-wages]
corpus:
  location: ../../../corpus
  pin: qcew-semantic-model corpus@$DAY
threshold: 0.9
interface: consumers/measure-sql/compile.py:compile
YAML
fact check --root "$M"
fact equivalence script --root "$M" --layer employment-wages --dialect duckdb
less "$M/equivalence/scripts/employment-wages.duckdb.sh"
DUCKDB_DB="$QCEW_DB" bash "$M/equivalence/scripts/employment-wages.duckdb.sh" > "$PILOT/equivalence-$DAY.jsonl"
fact equivalence run --root "$M" --layer employment-wages --source qcew-duckdb --results "$PILOT/equivalence-$DAY.jsonl" --date "$DAY"
cat "$M/generated/equivalence-employment-wages.md"
```

`location` is relative to the layer folder, so `../../../corpus` is `$PILOT/corpus`. The script runs both sides of every question and prints counts only: rows on each side and rows only one side has. On the dry run (the 38 example questions on the stand-in) it gave `36 pass, 0 fail, 2 error of 38`, `share 1.000, threshold 0.9: proven`; the two errors are the known gaps.

If the run says `proven`, accept it and mark the layer reviewed:

```bash
fact equivalence accept --root "$M" --layer employment-wages
perl -pi -e 's/^status: draft$/status: reviewed/' "$M/semantic/employment-wages/layer.yaml"
fact check --root "$M"
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 5: real corpus, equivalence accepted"
```

If it says `not proven`, do not accept. Each failing question is a finding: write `registers/findings/F-00NN.yaml` (copy the form of F-0007: what was asked, what differed, which fact or measure is suspect) and add `finding: F-00NN` to the question. Then fix the layer or the consumer and run step 5 again. Commit the findings either way:

```bash
git -C "$M" add -A
git -C "$M" commit --quiet -m "Pilot step 5: real corpus, findings" || true
```

## 6. What to send back

```bash
mkdir -p "$PILOT/return"
git -C "$M" log --stat > "$PILOT/return/git-log.txt"
fact status --root "$M" > "$PILOT/return/status.txt"
cp "$M/generated/equivalence-employment-wages.md" "$M/generated/drift-qcew-duckdb.md" "$PILOT/return/"
cp -R "$M/probes/results" "$PILOT/return/probe-results"
ls "$PILOT/return"
```

Send the `return` folder: the git log, `fact status`, the equivalence report, the drift report and the probe results. All of it is counts, outcomes and model files; no rows of data. The corpus stays with you; send its pin, which is in `consumer.yaml`.

# Adopter guide: BigQuery

How to model a BigQuery dataset with factmodel without giving the agent any credentials. Two paths read the same catalog; start with `export`, add `sql` when you want the agent (or CI) to run probes itself.

The framework repository holds no cloud credentials and runs no query against a cloud platform (D-011). Everything below runs on your machine, in your project, with your own login. What comes back to the model repository is files: snapshots, probe results and `fact check` output.

## 0. Before you start

- A model repository: `fact init <folder> --profile <profile>`.
- The Google Cloud SDK (`gcloud`, `bq`) logged in to the project that holds the dataset, with permission to read its `INFORMATION_SCHEMA`.
- The dataset's full name, `<project>.<dataset>`. It becomes the source's `location` and the target in every pin (`bigquery:<project>.<dataset>@<date>`).

Register the source once:

```bash
fact source add --id sales-bq --title "Sales dataset" --kind warehouse \
  --access-mode export_file --engine bigquery --adapter export \
  --location my-project.sales
```

## 1. The `export` path (no connection from factmodel)

1. Print the export queries:

   ```bash
   fact export-sql --source sales-bq > export.sql
   ```

   The file holds one query per `INFORMATION_SCHEMA` view: the five standard views (`TABLES`, `COLUMNS`, `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `REFERENTIAL_CONSTRAINTS`) and the three BigQuery extras (`COLUMN_FIELD_PATHS`, `TABLE_OPTIONS`, `CONSTRAINT_COLUMN_USAGE`). They read metadata only, never a data row.

2. Run each query with `bq` and save the result under the view's name, in one folder:

   ```bash
   mkdir -p sources/exports/sales-bq
   bq query --use_legacy_sql=false --format=json --max_rows=100000 \
     'SELECT table_schema, table_name, table_type FROM `my-project.sales`.INFORMATION_SCHEMA.TABLES' \
     > sources/exports/sales-bq/TABLES.json
   ```

   Repeat for every view in `export.sql`. `--format=csv` works too (keep the header row); the file name is what matters (`COLUMNS.csv`, `COLUMNS.json`). `TABLES` and `COLUMNS` are required; a missing optional view only means less is known.

3. Turn the export into a snapshot:

   ```bash
   fact snapshot --source sales-bq --from-export sources/exports/sales-bq
   ```

   This writes `sources/snapshots/sales-bq@<date>.yaml` and sets the source's `current_pin`. BigQuery does not enforce declared keys, so every constraint is `enforced: false` and every drafted relationship starts `inferred`.

4. Draft entities and check:

   ```bash
   fact draft --source sales-bq
   fact check
   ```

Decide whether to commit `sources/exports/`: it holds metadata only (names, types, descriptions), but descriptions are free text written by people. Read them first. The snapshot is what the model needs; the export folder can stay local.

## 2. The `sql` path (factmodel connects with your login)

The `sql` adapter reflects the catalog through SQLAlchemy and can run probes (`fact probe run`). It needs a SQLAlchemy dialect for BigQuery, which factmodel does not ship:

```bash
uv pip install "factmodel[sql]" sqlalchemy-bigquery
gcloud auth application-default login
```

Add a second source that reads the same dataset live:

```bash
fact source add --id sales-bq-live --title "Sales dataset (live)" --kind warehouse \
  --access-mode agent_read --engine bigquery --adapter sql \
  --location my-project.sales --dsn-env FACT_DSN_SALES_BQ
export FACT_DSN_SALES_BQ="bigquery://my-project/sales"
fact snapshot --source sales-bq-live
```

The connection string lives only in the environment variable the source names (`dsn_env`); it is never written to a file, a log or a pin, and the `privacy` stage fails on a literal DSN in the repository. The application-default credentials stay in your user profile.

Compare the two snapshots: `fact sync --source sales-bq-live` writes a drift report against the previous snapshot of the same source; for a one-off comparison of the two paths, diff the two snapshot files. The neutral parts (names, nullability, type class, constraints) should agree; `sqlalchemy-bigquery` may not report nested fields (`STRUCT`, `ARRAY`) the way `COLUMN_FIELD_PATHS` does, and that difference is worth a finding.

Probes:

```bash
fact probe generate
fact probe run --source sales-bq-live --data-quality representative
fact probe intake probes/results/sales-bq-live@<date>.jsonl
```

Probes return counts only. Scanning large tables costs money: render the probes first (`fact probe render --dialect bigquery`), read them, and run them on a sample dataset if cost matters.

## 3. What you send back

To the model repository (or, to report how the adapters worked on BigQuery, to the FactModel maintainers in an issue):

- the snapshot files from both paths (`sources/snapshots/*.yaml`);
- the probe result files (`probes/results/*.jsonl`), if you ran probes;
- the output of `fact check`;
- a short note of what differed between the two paths and anything that failed.

Never send credentials, connection strings, service account keys, query results with data rows, or screenshots of the console.

## 4. Status

This guide is written from the adapter code and its tests on exported fixtures. A run by an adopter on a real BigQuery project has not been done yet.

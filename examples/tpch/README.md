# TPC-H example

A FactModel model of the eight TPC-H tables on DuckDB, the example of Part 2 of the article series. It shows one thing: a catalog can be complete and still declare no key. DuckDB's `tpch` extension builds the tables with 61 NOT NULL constraints and not one primary or foreign key (its `dbgen` pushes `NotNullConstraint` and nothing else), so the first snapshot shows no key at all. `fact propose` measures the rows and proposes keys and joins; then the reference kit's constraints are applied, the catalog is snapshotted again, and the drift and the probes show what was declared and confirmed.

Source: TPC Benchmark H, Transaction Processing Performance Council, specification v3.0.1 (https://www.tpc.org/tpch/, read 2026-11-02). The constraint script follows `dss.ri` of the dbgen kit, public mirror https://raw.githubusercontent.com/electrum/tpch-dbgen/master/dss.ri (read 2026-11-02). The data is generated; no row of it is committed.

## What is here

| Path | What |
| --- | --- |
| `factmodel.yaml` | Profile `statistics`, no `anchor_entity` (D-015); `treat_synthetic_as_representative: true` (the data is generated, D-014). |
| `sources/tpch-duckdb.yaml` | The one source (adapter `sql`, engine `duckdb`); the connection string lives in `FACT_DSN_TPCH_DUCKDB`. |
| `scripts/generate.sh` | Builds `tpch.duckdb` with the extension (`CALL dbgen`), or from the kit's `.tbl` files with `--from-tbl` and `scripts/schema.sql`, the extension's own table definitions. |
| `scripts/apply-constraints.sql` | The kit's 8 primary and 8 foreign keys, each `dss.ri` statement quoted above its DuckDB translation. |
| `scripts/reproduce.sh` | Rebuilds every artifact below in one run; `scripts/summary.py` prints the counts of this page. |
| `sources/snapshots/tpch-duckdb@2026-11-02.yaml` | Snapshot A: the catalog as the extension built it, no constraint. |
| `drafts/tpch-duckdb/keys.yaml`, `joins.yaml` | What `fact propose keys` and `fact propose joins` measured on A: candidates with their counts, `status: inferred`. |
| `sources/snapshots/tpch-duckdb@2026-11-02_2.yaml` | Snapshot B: the second read of the same day, after `apply-constraints.sql`; its pin is `duckdb:tpch@2026-11-02_2`. |
| `generated/drift-tpch-duckdb.md` | What `fact sync` saw between A and B: eight `constraint_change` items, all `changed_fact`. |
| `drafts/tpch-duckdb/entities/`, `physical/entities/` | The drafts from B (declared keys and `declared_fk` relationships, `confirmed` because DuckDB enforces them) and the same files accepted as they are. |
| `probes/`, `probes/results/`, `evidence/probes/` | The probes generated from B, their run on the data, and the evidence intake wrote: every foreign key confirmed by a `join_match` with no orphan. |
| `generated/` | Labels, scope and residue from `fact project`. |

## Counts

Measured at scale factor 1 (`scripts/summary.py`, 2026-11-02).

| What | Count |
| --- | --- |
| Constraints in snapshot A | 0 (the 61 NOT NULL constraints are column facts, not constraints of the snapshot) |
| Constraints in snapshot B | 8 primary keys, 8 foreign keys |
| Key candidates proposed on A | 34 over 8 tables, 102 queries |
| Tables whose kit primary key is among the candidates | 8 of 8; for `lineitem` the pair `(l_orderkey, l_linenumber)` is the only candidate |
| Join candidates proposed on A at threshold 0.999 | 31, 385 queries |
| Kit foreign keys among the candidates | 8 of 8, all `many_to_one` |
| Specification foreign keys the kit leaves out (`lineitem` to `part`, `lineitem` to `supplier`) | 2 of 2 |
| Other inclusions above the threshold | 21; see below |
| Probes run on B | 32, none out of range (8 `row_count`, 8 `key_duplicates`, 8 `join_match`, 8 `fan_out`) |
| Runtime at scale factor 1, 4 cores | snapshot 0.6 s; propose keys 6.8 s; propose joins 9.4 s; apply the constraints 19.7 s; 32 probes 1.3 s |

## What DuckDB did with the kit's constraints

DuckDB 2.0 has no `ALTER TABLE ... ADD FOREIGN KEY`, so `apply-constraints.sql` adds two primary keys with `ALTER TABLE` and rebuilds the six tables that carry a foreign key in dependency order, with their primary and foreign keys in `CREATE TABLE`; at scale factor 1 that takes about 20 seconds on 4 cores. DuckDB also discards the constraint names `dss.ri` gives (`NATION_FK1` and the rest) and reports its own, such as `nation_n_regionkey_r_regionkey_fkey`.

**Why there are inclusions that are not foreign keys.** TPC-H keys are dense ranges: 0 to 4 for regions, 0 to 24 for nations, 1 to N for everything else. Any column with a small range of integers is therefore included in every larger key column of the same type class: line numbers 1 to 7 exist among nation keys, supplier keys, customer keys, part keys and the first order keys; `o_shippriority`, which is always 0, is a region key and a nation key; the 10,000 supplier keys are a subset of the 150,000 customer keys and the 200,000 part keys; at scale factor 1 the 800,000 `ps_availqty` draws cover every value from 1 to 9999, so they are a subset of three key columns too. The measurement cannot tell these from foreign keys, and does not try: it reports the inclusion and the coverage of the target, and a person decides. The regression test lists every one of them with its reason (`tests/examples/test_tpch.py`).

## Reproduce

From the framework root, with the `duckdb` extra and a route to DuckDB's extension repository:

```bash
uv run examples/tpch/scripts/reproduce.sh 1
```

The run builds the database (gitignored), takes snapshot A, proposes keys and joins, drafts and accepts the entities, passes the gate, applies the kit's constraints, takes snapshot B (the same day's second read, `_2`), syncs, drafts and accepts again, generates and runs the probes, takes their results in and passes the gate again. It ends with the counts above. `uv run pytest -q tests/examples/test_tpch.py` does the same at scale factor 0.01 (`FACT_TPCH_SF=1` for the example's scale; `FACT_TPCH_DB` points at a database built earlier) and checks the proposals against the kit, including the 21 coincidences, each with its reason.

# Quickstart

From an empty folder to a model of the eight TPC-H tables with a green gate, in nine steps and about two minutes. You need the `fact` command with the DuckDB extra (`pip install "factmodel[sql,duckdb]"`) and a route to DuckDB's extension repository (`INSTALL tpch`). The SQLite walk, two tables with declared keys, is in [quickstart-sqlite.md](quickstart-sqlite.md).

The point of this walk: DuckDB's `tpch` extension builds the eight tables with 61 NOT NULL constraints and not one primary or foreign key, so a snapshot of the catalog shows no key at all. `fact propose` measures the rows and proposes them; a person decides. The model uses the `statistics` profile, which has no subject (D-015), so drafted tables pass the gate as they are. Dates are fixed so the outputs match.

**1. Create the model.**

```bash
fact init tpch --profile statistics
```

Output:

```text
created tpch with 35 files (profile statistics)
```

**2. Build the database** at scale factor 1: 6,001,215 line items, the same build the [example](https://github.com/OSluchyk/factmodel/tree/main/examples/tpch) and the article use, about 1 GB on disk.

```bash
python3 -c "import duckdb; duckdb.connect('tpch.duckdb').execute('INSTALL tpch; LOAD tpch; CALL dbgen(sf = 1)')"
```

**3. Register the source.** The connection string stays in the environment variable and never enters a file.

```bash
export FACT_DSN_TPCH="duckdb:///$PWD/tpch.duckdb"
fact source add --root tpch --id tpch-db --title "TPC-H on DuckDB" --kind warehouse --access-mode agent_read --engine duckdb --adapter sql --dsn-env FACT_DSN_TPCH
```

Output:

```text
wrote sources/tpch-db.yaml
```

**4. Snapshot the catalog.** Eight tables, 61 columns, no constraint of any kind.

```bash
fact snapshot --root tpch --source tpch-db --date 2026-11-02
```

Output:

```text
wrote sources/snapshots/tpch-db@2026-11-02.yaml (8 objects)
```

**5. Propose keys from the rows.** Every table has no declared primary key, so every one is measured: single columns and column pairs that are unique and never null.

```bash
fact propose keys --root tpch --source tpch-db --environment local --data-quality synthetic --date 2026-11-02
```

Output:

```text
8 tables, 34 key candidates, 102 queries
wrote drafts/tpch-db/keys.yaml
```

Thirty-four candidates over eight tables, 102 queries, seven seconds on a laptop. The kit's primary key is among them for every table, and for `lineitem` it is the only candidate: `(l_orderkey, l_linenumber)`, 6,001,215 rows, 6,001,215 distinct, no null. `customer` has five: the key and three other unique columns (`c_name`, `c_address`, `c_phone`), plus the pair `(c_acctbal, c_comment)`.

**6. Propose joins from the rows.** Every type-compatible column pair across tables whose target is unique is measured for inclusion.

```bash
fact propose joins --root tpch --source tpch-db --environment local --data-quality synthetic --date 2026-11-02
```

Output:

```text
8 tables, 31 join candidates, 385 queries
wrote drafts/tpch-db/joins.yaml
```

Thirty-one candidates, 385 queries, nine seconds. Ten are foreign keys: the eight of the reference kit and the two the specification lists but the kit leaves out (`lineitem` to `part`, `lineitem` to `supplier`). The other 21 are coincidences of dense key ranges, and each record says so in its coverage: `l_linenumber` (1 to 7) is included in `n_nationkey` (0 to 24) with coverage 0.28, and `o_shippriority`, always 0, is a region key with coverage 0.2. Column names were not used: `l_linenumber = n_nationkey` and `n_regionkey = r_regionkey` are measured the same way, and only the note says that the second pair shares a suffix.

**7. Draft the entities** and accept them as they are. The drafts have no relationship, because the catalog declares none; the candidates in `drafts/tpch-db/` wait for a person.

```bash
fact draft --root tpch --source tpch-db
cp tpch/drafts/tpch-db/entities/*.yaml tpch/physical/entities/
```

Output:

```text
8 drafts, 8 written
```

**8. Compute the derived values.**

```bash
fact project --root tpch
```

**9. Run the gate.**

```bash
fact check --root tpch
```

Output:

```text
gate: pass
```

What happened:

1. `fact init` created a model repository: `factmodel.yaml`, the folder layout, agent files and CI.
2. The `tpch` extension built the eight tables. Its `dbgen` adds a NOT NULL constraint to every column and nothing else.
3. `fact source add` registered the database with the name of the environment variable, never its value.
4. `fact snapshot` read the catalog through the `sql` adapter: eight objects, no constraint.
5. `fact propose keys` measured every table and wrote the unique, never-null columns and pairs to `drafts/tpch-db/keys.yaml`, each with a measurement record (`status: inferred`). The kit's primary key is among the candidates for all eight tables; so are other columns that happen to be unique.
6. `fact propose joins` measured every type-compatible column pair across tables, towards unique targets only, and wrote the inclusions at or above 0.999 to `drafts/tpch-db/joins.yaml`: ten foreign keys and 21 coincidences, told apart by coverage, not by name.
7. `fact draft` turned the snapshot into entity drafts; copying them into `physical/` is the review step a person does, here skipped.
8. `fact project` computed labels, scope and residue; `fact check` ran every gate stage.

Next: the [TPC-H example](https://github.com/OSluchyk/factmodel/tree/main/examples/tpch) applies the kit's 8 primary and 8 foreign keys, snapshots again, and shows the drift and the probes that confirm them; the [tutorial](tutorial/chinook.md) goes on to probes, a proven layer, a release and two exports.

# Article support: Part 2 on the TPC-H example

The commands and outputs Part 2 of the article shows, copied from `examples/tpch` and
[the quickstart](quickstart.md) so that the article and the repository cannot drift. One
block per article section; each block ends with the file it was taken from. Commands are the
lines of `examples/tpch/scripts/reproduce.sh` with its variables filled in
(`examples/tpch`, `tpch-duckdb`, `2026-11-02`). Outputs are from a run of those commands on
2026-11-03 against the scale factor 1 database that `scripts/generate.sh` built on 2026-11-02,
on 4 cores; every artifact the run wrote is byte-identical to the committed one. The seconds
in an output line are that machine's. `tests/docs/test_article_support.py` checks every block
against its file: commands against the script, copied text verbatim, counts against the
committed artifacts.

This page is not in the site navigation and nothing links to it.

## 1. The snapshot with zero keys

```bash
fact snapshot --root examples/tpch --source tpch-duckdb --date 2026-11-02
```

```text
wrote sources/snapshots/tpch-duckdb@2026-11-02.yaml (8 objects)
```

The `region` object of the snapshot. No object of the eight has a `constraints` key; the 61
NOT NULL constraints of the catalog are `nullable: false` on the fields.

```yaml
- name: region
  object_type: table
  fields:
  - name: r_regionkey
    type: INTEGER
    type_class: integer
    nullable: false
  - name: r_name
    type: VARCHAR
    type_class: text
    nullable: false
  - name: r_comment
    type: VARCHAR
    type_class: text
    nullable: false
```

From: `examples/tpch/scripts/reproduce.sh` (command), `examples/tpch/sources/snapshots/tpch-duckdb@2026-11-02.yaml` (the object), the run (output line).

## 2. Propose keys

```bash
fact propose keys --root examples/tpch --source tpch-duckdb --environment local --data-quality synthetic --date 2026-11-02
```

```text
8 tables, 34 key candidates, 102 queries, 6.8 s: wrote drafts/tpch-duckdb/keys.yaml
```

What `scripts/summary.py` prints for the candidates, read from `drafts/tpch-duckdb/keys.yaml`:

```text
keys on A: 34 candidates over 8 tables, 102 queries;
  the kit's primary key is among them for 8 of 8 tables
  customer: (c_custkey), (c_name), (c_address), (c_phone), (c_acctbal, c_comment)
  lineitem: (l_orderkey, l_linenumber)
  nation: (n_nationkey), (n_name), (n_comment)
  orders: (o_orderkey), (o_custkey, o_totalprice), (o_custkey, o_comment), (o_totalprice, o_comment)
  part: (p_partkey), (p_name, p_mfgr), (p_name, p_brand), (p_name, p_type), (p_name, p_size), (p_name, p_container), (p_name, p_retailprice), (p_name, p_comment)
  partsupp: (ps_partkey, ps_suppkey), (ps_partkey, ps_comment), (ps_suppkey, ps_comment), (ps_availqty, ps_comment), (ps_supplycost, ps_comment)
  region: (r_regionkey), (r_name), (r_comment)
  supplier: (s_suppkey), (s_name), (s_address), (s_phone), (s_comment)
```

From: `examples/tpch/scripts/reproduce.sh` (command), `examples/tpch/drafts/tpch-duckdb/keys.yaml` (the counts), `examples/tpch/scripts/summary.py` (the listing), the run (output lines).

## 3. Propose joins

```bash
fact propose joins --root examples/tpch --source tpch-duckdb --environment local --data-quality synthetic --date 2026-11-02
```

```text
8 tables, 31 join candidates, 385 queries, 9.0 s: wrote drafts/tpch-duckdb/joins.yaml
```

What `scripts/summary.py` prints for the candidates, read from `drafts/tpch-duckdb/joins.yaml`:

```text
joins on A: 31 candidates at threshold 0.999, 385 queries;
  8 of the kit's 8 foreign keys recovered
  2 of the specification's 2 foreign keys the kit leaves out
  21 other inclusions above the threshold, for a reader to judge:
    customer.c_custkey = part.p_partkey  (one_to_one, coverage 0.75)
    lineitem.l_linenumber = customer.c_custkey  (many_to_one, coverage 4.7e-05)
    lineitem.l_linenumber = nation.n_nationkey  (many_to_one, coverage 0.28)
    lineitem.l_linenumber = orders.o_orderkey  (many_to_one, coverage 5e-06)
    lineitem.l_linenumber = part.p_partkey  (many_to_one, coverage 3.5e-05)
    lineitem.l_linenumber = supplier.s_suppkey  (many_to_one, coverage 0.0007)
    lineitem.l_suppkey = customer.c_custkey  (many_to_one, coverage 0.066667)
    lineitem.l_suppkey = part.p_partkey  (many_to_one, coverage 0.05)
    orders.o_custkey = part.p_partkey  (many_to_one, coverage 0.49998)
    orders.o_shippriority = nation.n_nationkey  (many_to_one, coverage 0.04)
    orders.o_shippriority = region.r_regionkey  (many_to_one, coverage 0.2)
    part.p_size = customer.c_custkey  (many_to_one, coverage 0.000333)
    part.p_size = supplier.s_suppkey  (many_to_one, coverage 0.005)
    partsupp.ps_availqty = customer.c_custkey  (many_to_one, coverage 0.06666)
    partsupp.ps_availqty = part.p_partkey  (many_to_one, coverage 0.049995)
    partsupp.ps_availqty = supplier.s_suppkey  (many_to_one, coverage 0.9999)
    partsupp.ps_suppkey = customer.c_custkey  (many_to_one, coverage 0.066667)
    partsupp.ps_suppkey = part.p_partkey  (many_to_one, coverage 0.05)
    region.r_regionkey = nation.n_nationkey  (one_to_one, coverage 0.2)
    supplier.s_suppkey = customer.c_custkey  (one_to_one, coverage 0.066667)
    supplier.s_suppkey = part.p_partkey  (one_to_one, coverage 0.05)
```

From: `examples/tpch/scripts/reproduce.sh` (command), `examples/tpch/drafts/tpch-duckdb/joins.yaml` (the counts), `examples/tpch/scripts/summary.py` (the listing), the run (output lines).

## 4. The constraint rebuild

The sentence of the example's README:

```text
DuckDB 2.0 has no `ALTER TABLE ... ADD FOREIGN KEY`, so `apply-constraints.sql` adds two primary keys with `ALTER TABLE` and rebuilds the six tables that carry a foreign key in dependency order, with their primary and foreign keys in `CREATE TABLE`; at scale factor 1 that takes about 20 seconds on 4 cores. DuckDB also discards the constraint names `dss.ri` gives (`NATION_FK1` and the rest) and reports its own, such as `nation_n_regionkey_r_regionkey_fkey`.
```

What `reproduce.sh` prints after `apply-constraints.sql`, from `duckdb_constraints()`:

```text
[('FOREIGN KEY', 8), ('NOT NULL', 61), ('PRIMARY KEY', 8)]
```

From: `examples/tpch/README.md` (the sentence), `examples/tpch/scripts/apply-constraints.sql` (the script), the run (output line).

## 5. Snapshot B and the sync diff

```bash
fact snapshot --root examples/tpch --source tpch-duckdb --date 2026-11-02
fact sync --root examples/tpch --source tpch-duckdb
```

```text
wrote sources/snapshots/tpch-duckdb@2026-11-02_2.yaml (8 objects)
changed_fact 8; 1 files written
  generated/drift-tpch-duckdb.md
```

The `region` object of snapshot B, the same day's second read:

```yaml
- name: region
  object_type: table
  fields:
  - name: r_regionkey
    type: INTEGER
    type_class: integer
    nullable: false
  - name: r_name
    type: VARCHAR
    type_class: text
    nullable: false
  - name: r_comment
    type: VARCHAR
    type_class: text
    nullable: false
  constraints:
  - constraint_type: primary_key
    name: region_r_regionkey_pkey
    fields:
    - r_regionkey
    enforced: true
```

The drift table `fact sync` wrote:

```text
| Object | Field | Kind | Class | Entity | Detail |
| --- | --- | --- | --- | --- | --- |
| customer | - | constraint_change | changed_fact | customer | added foreign_key(c_nationkey) -> nation(n_nationkey); added primary_key(c_custkey) |
| lineitem | - | constraint_change | changed_fact | lineitem | added foreign_key(l_orderkey) -> orders(o_orderkey); added foreign_key(l_partkey, l_suppkey) -> partsupp(ps_partkey,ps_suppkey); added primary_key(l_orderkey, l_linenumber) |
| nation | - | constraint_change | changed_fact | nation | added foreign_key(n_regionkey) -> region(r_regionkey); added primary_key(n_nationkey) |
| orders | - | constraint_change | changed_fact | orders | added foreign_key(o_custkey) -> customer(c_custkey); added primary_key(o_orderkey) |
| part | - | constraint_change | changed_fact | part | added primary_key(p_partkey) |
| partsupp | - | constraint_change | changed_fact | partsupp | added foreign_key(ps_partkey) -> part(p_partkey); added foreign_key(ps_suppkey) -> supplier(s_suppkey); added primary_key(ps_partkey, ps_suppkey) |
| region | - | constraint_change | changed_fact | region | added primary_key(r_regionkey) |
| supplier | - | constraint_change | changed_fact | supplier | added foreign_key(s_nationkey) -> nation(n_nationkey); added primary_key(s_suppkey) |
```

From: `examples/tpch/scripts/reproduce.sh` (commands), `examples/tpch/sources/snapshots/tpch-duckdb@2026-11-02_2.yaml` (the object), `examples/tpch/generated/drift-tpch-duckdb.md` (the table), the run (output lines).

## 6. The probe run

```bash
fact probe generate --root examples/tpch --source tpch-duckdb
fact probe run --root examples/tpch --source tpch-duckdb --environment local --data-quality synthetic --date 2026-11-02
fact probe intake --root examples/tpch examples/tpch/probes/results/tpch-duckdb@2026-11-02.jsonl
```

```text
32 probes, 32 written, 0 facts skipped
32 probes run, 0 failed: probes/results/tpch-duckdb@2026-11-02.jsonl
32 in range, 0 out of range, 0 failed, 0 rejected; 64 files written
```

The eight `join_match` results. `orphans_left` is what the probe bounds (`max: 0`): source rows
without a target row. `orphans_right` is reported, not bounded: target rows no source row points
at (50,004 customers without an order, 459 part-supplier pairs never ordered).

```text
{"probe": "join-match-customer-to-nation", "measurement": {"source_rows": 150000, "orphans_left": 0, "orphans_right": 0}}
{"probe": "join-match-lineitem-to-orders", "measurement": {"source_rows": 6001215, "orphans_left": 0, "orphans_right": 0}}
{"probe": "join-match-lineitem-to-partsupp", "measurement": {"source_rows": 6001215, "orphans_left": 0, "orphans_right": 459}}
{"probe": "join-match-nation-to-region", "measurement": {"source_rows": 25, "orphans_left": 0, "orphans_right": 0}}
{"probe": "join-match-orders-to-customer", "measurement": {"source_rows": 1500000, "orphans_left": 0, "orphans_right": 50004}}
{"probe": "join-match-partsupp-to-part", "measurement": {"source_rows": 800000, "orphans_left": 0, "orphans_right": 0}}
{"probe": "join-match-partsupp-to-supplier", "measurement": {"source_rows": 800000, "orphans_left": 0, "orphans_right": 0}}
{"probe": "join-match-supplier-to-nation", "measurement": {"source_rows": 10000, "orphans_left": 0, "orphans_right": 0}}
```

From: `examples/tpch/scripts/reproduce.sh` (commands), `examples/tpch/probes/results/tpch-duckdb@2026-11-02.jsonl` (the results), `examples/tpch/probes/join-match-orders-to-customer.yaml` (the bound), the run (output lines).

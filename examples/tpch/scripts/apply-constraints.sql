-- The 8 primary keys and 8 foreign keys of the TPC-H reference kit, applied to tpch.duckdb.
--
-- Source: dss.ri of the dbgen kit, public mirror electrum/tpch-dbgen (master),
--   https://raw.githubusercontent.com/electrum/tpch-dbgen/master/dss.ri (read 2026-11-02,
--   sha256 86ab46bad881a98b7591dede639190fe416ab9f5d13c8de19ffc65b4b1975cbc), whose header reads
--   "-- Sccsid:     @(#)dss.ri	2.1.8.1" / "-- TPCD Benchmark Version 8.0".
-- The TPC-H specification (v3.0.1, clause 1.4.2) makes these constraints optional; DuckDB's tpch
-- extension creates none of them, and the kit's dss.ddl creates none either: they live in dss.ri.
--
-- Translation. dss.ri is DB2 syntax: ALTER TABLE TPCD.<T> ADD PRIMARY KEY (...), and ALTER TABLE
-- TPCD.<T> ADD FOREIGN KEY <name> (...) references TPCD.<P> with the parent's primary key implied.
-- DuckDB 2.0 accepts ALTER TABLE ... ADD PRIMARY KEY but not ADD FOREIGN KEY ("No support for
-- adding FOREIGN_KEY constraints with ALTER TABLE"), so each table that carries a foreign key is
-- rebuilt with its constraints in CREATE TABLE, in dependency order, keeping the extension's
-- column names and types (scripts/schema.sql). Every dss.ri statement is quoted above its
-- translation. The kit's constraint names are written as CONSTRAINT names, but DuckDB reports
-- foreign keys under its own names (for example nation_n_regionkey_r_regionkey_fkey).
--
-- Run: duckdb tpch.duckdb < apply-constraints.sql, or through Python as reproduce.sh does.

-- For table REGION
-- dss.ri: ALTER TABLE TPCD.REGION ADD PRIMARY KEY (R_REGIONKEY);
ALTER TABLE region ADD PRIMARY KEY (r_regionkey);

-- For table PART
-- dss.ri: ALTER TABLE TPCD.PART ADD PRIMARY KEY (P_PARTKEY);
ALTER TABLE part ADD PRIMARY KEY (p_partkey);

-- For table NATION
-- dss.ri: ALTER TABLE TPCD.NATION ADD PRIMARY KEY (N_NATIONKEY);
-- dss.ri: ALTER TABLE TPCD.NATION ADD FOREIGN KEY NATION_FK1 (N_REGIONKEY) references TPCD.REGION;
ALTER TABLE nation RENAME TO nation_old;
CREATE TABLE nation (
  n_nationkey INTEGER NOT NULL,
  n_name VARCHAR NOT NULL,
  n_regionkey INTEGER NOT NULL,
  n_comment VARCHAR NOT NULL,
  PRIMARY KEY (n_nationkey),
  CONSTRAINT nation_fk1 FOREIGN KEY (n_regionkey) REFERENCES region (r_regionkey)
);
INSERT INTO nation SELECT * FROM nation_old;
DROP TABLE nation_old;

-- For table SUPPLIER
-- dss.ri: ALTER TABLE TPCD.SUPPLIER ADD PRIMARY KEY (S_SUPPKEY);
-- dss.ri: ALTER TABLE TPCD.SUPPLIER ADD FOREIGN KEY SUPPLIER_FK1 (S_NATIONKEY) references TPCD.NATION;
ALTER TABLE supplier RENAME TO supplier_old;
CREATE TABLE supplier (
  s_suppkey BIGINT NOT NULL,
  s_name VARCHAR NOT NULL,
  s_address VARCHAR NOT NULL,
  s_nationkey INTEGER NOT NULL,
  s_phone VARCHAR NOT NULL,
  s_acctbal DECIMAL(15, 2) NOT NULL,
  s_comment VARCHAR NOT NULL,
  PRIMARY KEY (s_suppkey),
  CONSTRAINT supplier_fk1 FOREIGN KEY (s_nationkey) REFERENCES nation (n_nationkey)
);
INSERT INTO supplier SELECT * FROM supplier_old;
DROP TABLE supplier_old;

-- For table CUSTOMER
-- dss.ri: ALTER TABLE TPCD.CUSTOMER ADD PRIMARY KEY (C_CUSTKEY);
-- dss.ri: ALTER TABLE TPCD.CUSTOMER ADD FOREIGN KEY CUSTOMER_FK1 (C_NATIONKEY) references TPCD.NATION;
ALTER TABLE customer RENAME TO customer_old;
CREATE TABLE customer (
  c_custkey BIGINT NOT NULL,
  c_name VARCHAR NOT NULL,
  c_address VARCHAR NOT NULL,
  c_nationkey INTEGER NOT NULL,
  c_phone VARCHAR NOT NULL,
  c_acctbal DECIMAL(15, 2) NOT NULL,
  c_mktsegment VARCHAR NOT NULL,
  c_comment VARCHAR NOT NULL,
  PRIMARY KEY (c_custkey),
  CONSTRAINT customer_fk1 FOREIGN KEY (c_nationkey) REFERENCES nation (n_nationkey)
);
INSERT INTO customer SELECT * FROM customer_old;
DROP TABLE customer_old;

-- For table PARTSUPP
-- dss.ri: ALTER TABLE TPCD.PARTSUPP ADD PRIMARY KEY (PS_PARTKEY,PS_SUPPKEY);
-- dss.ri: ALTER TABLE TPCD.PARTSUPP ADD FOREIGN KEY PARTSUPP_FK1 (PS_SUPPKEY) references TPCD.SUPPLIER;
-- dss.ri: ALTER TABLE TPCD.PARTSUPP ADD FOREIGN KEY PARTSUPP_FK2 (PS_PARTKEY) references TPCD.PART;
ALTER TABLE partsupp RENAME TO partsupp_old;
CREATE TABLE partsupp (
  ps_partkey BIGINT NOT NULL,
  ps_suppkey BIGINT NOT NULL,
  ps_availqty BIGINT NOT NULL,
  ps_supplycost DECIMAL(15, 2) NOT NULL,
  ps_comment VARCHAR NOT NULL,
  PRIMARY KEY (ps_partkey, ps_suppkey),
  CONSTRAINT partsupp_fk1 FOREIGN KEY (ps_suppkey) REFERENCES supplier (s_suppkey),
  CONSTRAINT partsupp_fk2 FOREIGN KEY (ps_partkey) REFERENCES part (p_partkey)
);
INSERT INTO partsupp SELECT * FROM partsupp_old;
DROP TABLE partsupp_old;

-- For table ORDERS
-- dss.ri: ALTER TABLE TPCD.ORDERS ADD PRIMARY KEY (O_ORDERKEY);
-- dss.ri: ALTER TABLE TPCD.ORDERS ADD FOREIGN KEY ORDERS_FK1 (O_CUSTKEY) references TPCD.CUSTOMER;
ALTER TABLE orders RENAME TO orders_old;
CREATE TABLE orders (
  o_orderkey BIGINT NOT NULL,
  o_custkey BIGINT NOT NULL,
  o_orderstatus VARCHAR NOT NULL,
  o_totalprice DECIMAL(15, 2) NOT NULL,
  o_orderdate DATE NOT NULL,
  o_orderpriority VARCHAR NOT NULL,
  o_clerk VARCHAR NOT NULL,
  o_shippriority INTEGER NOT NULL,
  o_comment VARCHAR NOT NULL,
  PRIMARY KEY (o_orderkey),
  CONSTRAINT orders_fk1 FOREIGN KEY (o_custkey) REFERENCES customer (c_custkey)
);
INSERT INTO orders SELECT * FROM orders_old;
DROP TABLE orders_old;

-- For table LINEITEM
-- dss.ri: ALTER TABLE TPCD.LINEITEM ADD PRIMARY KEY (L_ORDERKEY,L_LINENUMBER);
-- dss.ri: ALTER TABLE TPCD.LINEITEM ADD FOREIGN KEY LINEITEM_FK1 (L_ORDERKEY)  references TPCD.ORDERS;
-- dss.ri: ALTER TABLE TPCD.LINEITEM ADD FOREIGN KEY LINEITEM_FK2 (L_PARTKEY,L_SUPPKEY) references TPCD.PARTSUPP;
ALTER TABLE lineitem RENAME TO lineitem_old;
CREATE TABLE lineitem (
  l_orderkey BIGINT NOT NULL,
  l_partkey BIGINT NOT NULL,
  l_suppkey BIGINT NOT NULL,
  l_linenumber BIGINT NOT NULL,
  l_quantity DECIMAL(15, 2) NOT NULL,
  l_extendedprice DECIMAL(15, 2) NOT NULL,
  l_discount DECIMAL(15, 2) NOT NULL,
  l_tax DECIMAL(15, 2) NOT NULL,
  l_returnflag VARCHAR NOT NULL,
  l_linestatus VARCHAR NOT NULL,
  l_shipdate DATE NOT NULL,
  l_commitdate DATE NOT NULL,
  l_receiptdate DATE NOT NULL,
  l_shipinstruct VARCHAR NOT NULL,
  l_shipmode VARCHAR NOT NULL,
  l_comment VARCHAR NOT NULL,
  PRIMARY KEY (l_orderkey, l_linenumber),
  CONSTRAINT lineitem_fk1 FOREIGN KEY (l_orderkey) REFERENCES orders (o_orderkey),
  CONSTRAINT lineitem_fk2 FOREIGN KEY (l_partkey, l_suppkey) REFERENCES partsupp (ps_partkey, ps_suppkey)
);
INSERT INTO lineitem SELECT * FROM lineitem_old;
DROP TABLE lineitem_old;

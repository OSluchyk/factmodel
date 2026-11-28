-- Load the fetched BLS slices and the committed code lists into the QCEW tables.
--
-- Run by scripts/load.sh from examples/qcew, after sources/ddl/duckdb.sql created the tables.
-- With the DuckDB shell, from examples/qcew:
--   duckdb qcew.duckdb < sources/ddl/duckdb.sql
--   duckdb qcew.duckdb < scripts/load.sql
--
-- Nothing is filtered or cleaned: every row of every slice is loaded, and the title files are
-- loaded as they are (D-016), the second header line of area_titles.csv included. Fields are
-- read as text and cast by the table's column types, so a blank field becomes NULL, as in the
-- seeded tables. BY NAME matches the CSV header against the column names: a slice whose
-- layout differs from sources/ddl/duckdb.sql stops the load.
--
-- raw is the folder scripts/fetch.sh wrote; scripts/load.sh sets it for tests.
SET VARIABLE raw = coalesce(getvariable('raw'), 'data/raw');

INSERT INTO annual BY NAME
SELECT * FROM read_csv(
  getvariable('raw') || '/*/a/*.csv',
  header = true, delim = ',', quote = '"', all_varchar = true, nullstr = ''
);

INSERT INTO qtrly BY NAME
SELECT * FROM read_csv(
  getvariable('raw') || '/*/[1-4]/*.csv',
  header = true, delim = ',', quote = '"', all_varchar = true, nullstr = ''
);

INSERT INTO agglevel_titles
SELECT * FROM read_csv(
  'sources/codelists/agglevel_titles.csv', auto_detect = false,
  header = true, delim = ',', quote = '"', escape = '"',
  columns = {'agglvl_code': 'VARCHAR', 'agglvl_title': 'VARCHAR'}
);

INSERT INTO area_titles
SELECT * FROM read_csv(
  'sources/codelists/area_titles.csv', auto_detect = false,
  header = true, delim = ',', quote = '"', escape = '"',
  columns = {'area_fips': 'VARCHAR', 'area_title': 'VARCHAR'}
);

INSERT INTO industry_titles
SELECT * FROM read_csv(
  'sources/codelists/industry_titles.csv', auto_detect = false,
  header = true, delim = ',', quote = '"', escape = '"',
  columns = {'industry_code': 'VARCHAR', 'industry_title': 'VARCHAR'}
);

INSERT INTO ownership_titles
SELECT * FROM read_csv(
  'sources/codelists/ownership_titles.csv', auto_detect = false,
  header = true, delim = ',', quote = '"', escape = '"',
  columns = {'own_code': 'VARCHAR', 'own_title': 'VARCHAR'}
);

INSERT INTO size_titles
SELECT * FROM read_csv(
  'sources/codelists/size_titles.csv', auto_detect = false,
  header = true, delim = ',', quote = '"', escape = '"',
  columns = {'size_code': 'VARCHAR', 'size_title': 'VARCHAR'}
);

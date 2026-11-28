-- The documented QCEW key on the quarterly rows, then the same key with one field left out.
-- duplicate_rows is the number of rows that share their key with another row.
WITH keys AS (
  SELECT 1 AS n, 'area_fips, own_code, industry_code, size_code, year, qtr' AS key_fields,
    count(*) AS row_count,
    count(DISTINCT (area_fips, own_code, industry_code, size_code, year, qtr)) AS distinct_keys
  FROM qtrly
  UNION ALL
  SELECT 2, 'without size_code', count(*),
    count(DISTINCT (area_fips, own_code, industry_code, year, qtr)) FROM qtrly
  UNION ALL
  SELECT 3, 'without qtr', count(*),
    count(DISTINCT (area_fips, own_code, industry_code, size_code, year)) FROM qtrly
  UNION ALL
  SELECT 4, 'without year', count(*),
    count(DISTINCT (area_fips, own_code, industry_code, size_code, qtr)) FROM qtrly
  UNION ALL
  SELECT 5, 'without industry_code', count(*),
    count(DISTINCT (area_fips, own_code, size_code, year, qtr)) FROM qtrly
  UNION ALL
  SELECT 6, 'without own_code', count(*),
    count(DISTINCT (area_fips, industry_code, size_code, year, qtr)) FROM qtrly
  UNION ALL
  SELECT 7, 'without area_fips', count(*),
    count(DISTINCT (own_code, industry_code, size_code, year, qtr)) FROM qtrly
)
SELECT key_fields, row_count, distinct_keys, row_count - distinct_keys AS rows_over
FROM keys ORDER BY n

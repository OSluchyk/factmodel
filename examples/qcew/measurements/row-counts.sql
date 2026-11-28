-- Rows and areas per table, year and period, as loaded from the slices.
SELECT 'annual' AS source_table, year, qtr, count(*) AS row_count,
  count(DISTINCT area_fips) AS areas
FROM annual GROUP BY year, qtr
UNION ALL
SELECT 'qtrly', year, qtr, count(*), count(DISTINCT area_fips)
FROM qtrly GROUP BY year, qtr
ORDER BY source_table, year, qtr

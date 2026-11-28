-- The query of grain-mixed-level for Maryland: private employment, March 2025, once at one
-- aggregation level, once with no level filter.
SELECT 'agglvl_code = 51' AS level_filter, count(*) AS row_count,
  sum(month3_emplvl) AS employment
FROM qtrly
WHERE area_fips = '24000' AND own_code = '5' AND year = '2025' AND qtr = '1'
  AND agglvl_code = '51'
UNION ALL
SELECT 'none', count(*), sum(month3_emplvl)
FROM qtrly
WHERE area_fips = '24000' AND own_code = '5' AND year = '2025' AND qtr = '1'
ORDER BY row_count

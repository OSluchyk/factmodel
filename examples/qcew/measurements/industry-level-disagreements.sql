-- Quarterly rows of 2025 Q1 whose industry level differs between the two readings.
WITH rows_two_ways AS (
  SELECT area_fips, own_code, industry_code, agglvl_code, year, qtr, month3_emplvl,
    CASE
      WHEN industry_code = '10' THEN CASE WHEN own_code = '0' THEN '0' ELSE '1' END
      WHEN industry_code IN ('101', '102') THEN '2'
      WHEN length(industry_code) = 4 AND industry_code LIKE '10%' THEN '3'
      WHEN industry_code LIKE '%-%' OR length(industry_code) = 2 THEN '4'
      ELSE CAST(length(industry_code) + 2 AS VARCHAR)
    END AS level_from_code
  FROM qtrly
)
SELECT r.area_fips, r.own_code, r.industry_code, r.agglvl_code, t.agglvl_title,
  r.level_from_code, substr(r.agglvl_code, 2, 1) AS level_from_agglvl, r.month3_emplvl
FROM rows_two_ways AS r
JOIN agglevel_titles AS t ON r.agglvl_code = t.agglvl_code
WHERE r.level_from_code <> substr(r.agglvl_code, 2, 1) AND r.year = '2025' AND r.qtr = '1'
ORDER BY r.area_fips, r.own_code

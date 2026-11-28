-- Quarterly rows of 2025 Q1 whose kind of area differs between the two readings.
SELECT q.area_fips, a.area_title, q.own_code, q.industry_code, q.agglvl_code, t.agglvl_title,
  q.month3_emplvl
FROM qtrly AS q
JOIN agglevel_titles AS t ON q.agglvl_code = t.agglvl_code
JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) AS a ON q.area_fips = a.area_fips
WHERE q.year = '2025' AND q.qtr = '1'
  AND substr(q.agglvl_code, 1, 1) <> CASE
    WHEN q.area_fips LIKE 'US%' THEN '1'
    WHEN q.area_fips LIKE 'CS%' THEN '3'
    WHEN q.area_fips LIKE 'C%' THEN '4'
    WHEN substr(q.area_fips, 3, 3) = '000' THEN '5'
    ELSE '7'
  END
ORDER BY q.area_fips, q.own_code

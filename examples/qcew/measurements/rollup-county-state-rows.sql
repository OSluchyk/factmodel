-- The rows behind rollup-county-state: the state row and its county rows.
SELECT q.area_fips, t.area_title, q.agglvl_code,
  coalesce(q.disclosure_code, '') AS disclosure_code, q.month3_emplvl
FROM qtrly AS q
JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) AS t ON q.area_fips = t.area_fips
WHERE substr(q.area_fips, 1, 2) = '10' AND q.own_code = '5' AND q.industry_code = '62'
  AND q.year = '2025' AND q.qtr = '1'
ORDER BY q.area_fips

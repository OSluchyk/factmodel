-- The rows behind rollup-naics-parent: the sector row and its 3-digit subsector rows.
SELECT q.industry_code, t.industry_title, q.agglvl_code,
  coalesce(q.disclosure_code, '') AS disclosure_code, q.month3_emplvl
FROM qtrly AS q
JOIN industry_titles AS t ON q.industry_code = t.industry_code
WHERE q.area_fips = '10000' AND q.own_code = '5' AND substr(q.industry_code, 1, 2) = '52'
  AND length(q.industry_code) <= 3 AND q.year = '2025' AND q.qtr = '1'
ORDER BY q.industry_code

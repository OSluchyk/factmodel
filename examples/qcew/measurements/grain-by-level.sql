-- The same selection as grain-mixed-level, one line per aggregation level: every level
-- restates the same workers, less the cells BLS withheld at that level.
SELECT q.agglvl_code, t.agglvl_title, count(*) AS row_count,
  sum(CASE WHEN q.disclosure_code = 'N' THEN 1 ELSE 0 END) AS suppressed_rows,
  sum(q.month3_emplvl) AS employment
FROM qtrly AS q
JOIN agglevel_titles AS t ON q.agglvl_code = t.agglvl_code
WHERE q.area_fips = '10000' AND q.own_code = '5' AND q.year = '2025' AND q.qtr = '1'
GROUP BY q.agglvl_code, t.agglvl_title
ORDER BY q.agglvl_code

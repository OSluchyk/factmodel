-- Annual rows by year: with a row of the same key one year earlier or without, by the
-- disclosure code of the over-the-year fields. No over-the-year field is NULL in any row.
SELECT a.year,
  CASE WHEN p.year IS NULL THEN 'no prior-year row' ELSE 'prior-year row' END AS prior,
  coalesce(a.oty_disclosure_code, 'blank') AS oty_disclosure_code,
  count(*) AS row_count,
  sum(CASE WHEN a.oty_annual_avg_emplvl_chg IS NULL THEN 1 ELSE 0 END) AS oty_change_null
FROM annual AS a
LEFT JOIN annual AS p
  ON a.area_fips = p.area_fips AND a.own_code = p.own_code
  AND a.industry_code = p.industry_code AND a.size_code = p.size_code
  AND CAST(a.year AS INTEGER) - 1 = CAST(p.year AS INTEGER)
GROUP BY a.year, prior, coalesce(a.oty_disclosure_code, 'blank')
ORDER BY a.year, prior, oty_disclosure_code

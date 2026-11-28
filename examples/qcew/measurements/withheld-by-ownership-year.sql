-- Withheld (N) share in percent of the quarterly rows of Delaware and Maryland, per ownership
-- and year. Padding rows are left out of both counts.
SELECT CASE substr(area_fips, 1, 2) WHEN '10' THEN 'DE' ELSE 'MD' END AS st, own_code,
  sum(CASE WHEN year = '2024' THEN 1 ELSE 0 END) AS rows_2024,
  sum(CASE WHEN year = '2024' AND disclosure_code = 'N' THEN 1 ELSE 0 END) AS n_2024,
  round(100.0 * sum(CASE WHEN year = '2024' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2024' THEN 1 ELSE 0 END), 0), 1) AS pct_2024,
  sum(CASE WHEN year = '2025' THEN 1 ELSE 0 END) AS rows_2025,
  sum(CASE WHEN year = '2025' AND disclosure_code = 'N' THEN 1 ELSE 0 END) AS n_2025,
  round(100.0 * sum(CASE WHEN year = '2025' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2025' THEN 1 ELSE 0 END), 0), 1) AS pct_2025
FROM qtrly
WHERE substr(area_fips, 1, 2) IN ('10', '24') AND disclosure_code IS DISTINCT FROM '-'
GROUP BY st, own_code
ORDER BY st, own_code

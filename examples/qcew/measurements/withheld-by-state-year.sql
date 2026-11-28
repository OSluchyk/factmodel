-- Withheld (N) annual cells of Delaware and Maryland, state and county rows, per aggregation
-- level and year: cells, withheld cells and the withheld share in percent.
WITH cells AS (
  SELECT CASE substr(area_fips, 1, 2) WHEN '10' THEN 'DE' ELSE 'MD' END AS st, year,
    agglvl_code, CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END AS withheld
  FROM annual
  WHERE substr(area_fips, 1, 2) IN ('10', '24') AND agglvl_code BETWEEN '50' AND '78'
)
SELECT agglvl_code,
  sum(CASE WHEN st = 'DE' AND year = '2024' THEN 1 ELSE 0 END) AS de_2024,
  sum(CASE WHEN st = 'DE' AND year = '2024' THEN withheld ELSE 0 END) AS de_2024_n,
  round(100.0 * sum(CASE WHEN st = 'DE' AND year = '2024' THEN withheld ELSE 0 END)
    / sum(CASE WHEN st = 'DE' AND year = '2024' THEN 1 ELSE 0 END), 1) AS de_2024_pct,
  sum(CASE WHEN st = 'DE' AND year = '2025' THEN 1 ELSE 0 END) AS de_2025,
  sum(CASE WHEN st = 'DE' AND year = '2025' THEN withheld ELSE 0 END) AS de_2025_n,
  round(100.0 * sum(CASE WHEN st = 'DE' AND year = '2025' THEN withheld ELSE 0 END)
    / sum(CASE WHEN st = 'DE' AND year = '2025' THEN 1 ELSE 0 END), 1) AS de_2025_pct,
  sum(CASE WHEN st = 'MD' AND year = '2024' THEN 1 ELSE 0 END) AS md_2024,
  sum(CASE WHEN st = 'MD' AND year = '2024' THEN withheld ELSE 0 END) AS md_2024_n,
  round(100.0 * sum(CASE WHEN st = 'MD' AND year = '2024' THEN withheld ELSE 0 END)
    / sum(CASE WHEN st = 'MD' AND year = '2024' THEN 1 ELSE 0 END), 1) AS md_2024_pct,
  sum(CASE WHEN st = 'MD' AND year = '2025' THEN 1 ELSE 0 END) AS md_2025,
  sum(CASE WHEN st = 'MD' AND year = '2025' THEN withheld ELSE 0 END) AS md_2025_n,
  round(100.0 * sum(CASE WHEN st = 'MD' AND year = '2025' THEN withheld ELSE 0 END)
    / sum(CASE WHEN st = 'MD' AND year = '2025' THEN 1 ELSE 0 END), 1) AS md_2025_pct
FROM cells
GROUP BY agglvl_code
ORDER BY agglvl_code

-- Withheld (N) share in percent of the quarterly rows of Delaware and Maryland, state and
-- county rows, per aggregation level and quarter. Padding rows are left out of both counts.
SELECT CASE substr(area_fips, 1, 2) WHEN '10' THEN 'DE' ELSE 'MD' END AS st, agglvl_code,
  round(100.0 * sum(CASE WHEN year = '2024' AND qtr = '1' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2024' AND qtr = '1' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2024q1",
  round(100.0 * sum(CASE WHEN year = '2024' AND qtr = '2' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2024' AND qtr = '2' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2024q2",
  round(100.0 * sum(CASE WHEN year = '2024' AND qtr = '3' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2024' AND qtr = '3' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2024q3",
  round(100.0 * sum(CASE WHEN year = '2024' AND qtr = '4' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2024' AND qtr = '4' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2024q4",
  round(100.0 * sum(CASE WHEN year = '2025' AND qtr = '1' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2025' AND qtr = '1' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2025q1",
  round(100.0 * sum(CASE WHEN year = '2025' AND qtr = '2' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2025' AND qtr = '2' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2025q2",
  round(100.0 * sum(CASE WHEN year = '2025' AND qtr = '3' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2025' AND qtr = '3' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2025q3",
  round(100.0 * sum(CASE WHEN year = '2025' AND qtr = '4' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    / nullif(sum(CASE WHEN year = '2025' AND qtr = '4' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END), 0), 1) AS "2025q4"
FROM qtrly
WHERE substr(area_fips, 1, 2) IN ('10', '24') AND agglvl_code BETWEEN '50' AND '78'
GROUP BY st, agglvl_code
ORDER BY st, agglvl_code

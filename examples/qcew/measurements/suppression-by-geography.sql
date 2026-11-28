-- The same counts per table and geography, the first digit of agglvl_code.
SELECT 'qtrly' AS source_table, substr(agglvl_code, 1, 1) AS geography_digit,
  count(*) AS row_count,
  sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) AS n_rows,
  sum(CASE WHEN disclosure_code = '-' THEN 1 ELSE 0 END) AS dash_rows,
  round(100.0 * sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) / count(*), 1) AS n_pct,
  round(100.0 * sum(CASE WHEN disclosure_code = '-' THEN 1 ELSE 0 END) / count(*), 1)
    AS dash_pct
FROM qtrly GROUP BY substr(agglvl_code, 1, 1)
UNION ALL
SELECT 'annual', substr(agglvl_code, 1, 1), count(*),
  sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END),
  sum(CASE WHEN disclosure_code = '-' THEN 1 ELSE 0 END),
  round(100.0 * sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) / count(*), 1),
  round(100.0 * sum(CASE WHEN disclosure_code = '-' THEN 1 ELSE 0 END) / count(*), 1)
FROM annual GROUP BY substr(agglvl_code, 1, 1)
ORDER BY source_table DESC, geography_digit

-- Padding (-) rows and records (rows that are not padding) per quarter, in all and at the MSA
-- levels (agglvl_code 40 to 48).
SELECT year, qtr, count(*) AS row_count,
  sum(CASE WHEN disclosure_code = '-' THEN 1 ELSE 0 END) AS dash_rows,
  sum(CASE WHEN disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS records,
  sum(CASE WHEN agglvl_code BETWEEN '40' AND '48' THEN 1 ELSE 0 END) AS msa_rows,
  sum(CASE WHEN agglvl_code BETWEEN '40' AND '48' AND disclosure_code = '-' THEN 1 ELSE 0 END)
    AS msa_dash_rows,
  sum(CASE WHEN agglvl_code BETWEEN '40' AND '48' AND disclosure_code = 'N' THEN 1 ELSE 0 END)
    AS msa_n_rows
FROM qtrly
GROUP BY year, qtr
ORDER BY year, qtr

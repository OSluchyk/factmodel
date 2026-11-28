-- Rows per MSA aggregation level (agglvl_code 40 to 48) and quarter, and how many of them
-- are records: rows that are not padding (disclosure_code is not '-'). The quarterly file
-- pads a key to the four quarters of its year, so a level keeps its rows to the end of the
-- year of its last record. The last two columns are the rows of the annual file, which has
-- no padding.
WITH counted AS (
  SELECT agglvl_code, 1 AS n, 'rows' AS what,
    sum(CASE WHEN year = '2024' AND qtr = '1' THEN 1 ELSE 0 END) AS "2024q1",
    sum(CASE WHEN year = '2024' AND qtr = '2' THEN 1 ELSE 0 END) AS "2024q2",
    sum(CASE WHEN year = '2024' AND qtr = '3' THEN 1 ELSE 0 END) AS "2024q3",
    sum(CASE WHEN year = '2024' AND qtr = '4' THEN 1 ELSE 0 END) AS "2024q4",
    sum(CASE WHEN year = '2025' AND qtr = '1' THEN 1 ELSE 0 END) AS "2025q1",
    sum(CASE WHEN year = '2025' AND qtr = '2' THEN 1 ELSE 0 END) AS "2025q2",
    sum(CASE WHEN year = '2025' AND qtr = '3' THEN 1 ELSE 0 END) AS "2025q3",
    sum(CASE WHEN year = '2025' AND qtr = '4' THEN 1 ELSE 0 END) AS "2025q4"
  FROM qtrly WHERE agglvl_code BETWEEN '40' AND '48' GROUP BY agglvl_code
  UNION ALL
  SELECT agglvl_code, 2, 'records',
    sum(CASE WHEN year = '2024' AND qtr = '1' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2024q1",
    sum(CASE WHEN year = '2024' AND qtr = '2' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2024q2",
    sum(CASE WHEN year = '2024' AND qtr = '3' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2024q3",
    sum(CASE WHEN year = '2024' AND qtr = '4' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2024q4",
    sum(CASE WHEN year = '2025' AND qtr = '1' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2025q1",
    sum(CASE WHEN year = '2025' AND qtr = '2' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2025q2",
    sum(CASE WHEN year = '2025' AND qtr = '3' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2025q3",
    sum(CASE WHEN year = '2025' AND qtr = '4' AND disclosure_code IS DISTINCT FROM '-' THEN 1 ELSE 0 END) AS "2025q4"
  FROM qtrly WHERE agglvl_code BETWEEN '40' AND '48' GROUP BY agglvl_code
), yearly AS (
  SELECT agglvl_code, sum(CASE WHEN year = '2024' THEN 1 ELSE 0 END) AS annual_2024,
    sum(CASE WHEN year = '2025' THEN 1 ELSE 0 END) AS annual_2025
  FROM annual WHERE agglvl_code BETWEEN '40' AND '48' GROUP BY agglvl_code
)
SELECT c.agglvl_code, c.what, c."2024q1", c."2024q2", c."2024q3", c."2024q4", c."2025q1", c."2025q2", c."2025q3", c."2025q4",
  coalesce(y.annual_2024, 0) AS annual_2024, coalesce(y.annual_2025, 0) AS annual_2025
FROM counted AS c LEFT JOIN yearly AS y ON y.agglvl_code = c.agglvl_code
ORDER BY c.agglvl_code, c.n

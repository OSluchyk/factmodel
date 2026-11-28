-- What reading the industry level from the length of industry_code alone would give
-- (2 characters a sector, 3 a 3-digit industry, and so on), against agglvl_code, per shape
-- of code. Rows at the special levels 94 to 96 are left out.
WITH shaped AS (
  SELECT
    CASE
      WHEN industry_code = '10' THEN '1 total (10)'
      WHEN industry_code IN ('101', '102') THEN '2 domain (101, 102)'
      WHEN length(industry_code) = 4 AND industry_code LIKE '10%' THEN '3 supersector (10xx)'
      WHEN industry_code LIKE '%-%' THEN '4 sector written as a range (nn-nn)'
      ELSE '5 NAICS, ' || length(industry_code) || ' digits'
    END AS shape,
    CAST(length(industry_code) + 2 AS VARCHAR) AS level_from_length,
    substr(agglvl_code, 2, 1) AS level_from_agglvl
  FROM qtrly
  WHERE agglvl_code < '90'
)
SELECT shape, level_from_length, level_from_agglvl,
  CASE WHEN level_from_length = level_from_agglvl THEN 'agree' ELSE 'disagree' END AS verdict,
  count(*) AS row_count
FROM shaped
GROUP BY shape, level_from_length, level_from_agglvl
ORDER BY shape, level_from_agglvl

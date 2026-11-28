-- The industry level of every quarterly row, read two ways: from the shape of industry_code
-- (with own_code for the total) and from the second digit of agglvl_code.
WITH rows_two_ways AS (
  SELECT
    CASE
      WHEN industry_code = '10' THEN CASE WHEN own_code = '0' THEN '0' ELSE '1' END
      WHEN industry_code IN ('101', '102') THEN '2'
      WHEN length(industry_code) = 4 AND industry_code LIKE '10%' THEN '3'
      WHEN industry_code LIKE '%-%' OR length(industry_code) = 2 THEN '4'
      ELSE CAST(length(industry_code) + 2 AS VARCHAR)
    END AS level_from_code,
    substr(agglvl_code, 2, 1) AS level_from_agglvl,
    substr(agglvl_code, 1, 1) AS geography_digit
  FROM qtrly
)
SELECT level_from_code, level_from_agglvl,
  CASE WHEN level_from_code = level_from_agglvl THEN 'agree' ELSE 'disagree' END AS verdict,
  count(*) AS row_count,
  string_agg(DISTINCT geography_digit, ' ' ORDER BY geography_digit) AS geography_digits
FROM rows_two_ways
GROUP BY level_from_code, level_from_agglvl
ORDER BY level_from_code, level_from_agglvl

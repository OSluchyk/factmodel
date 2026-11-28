-- Rows on which two readings of the same thing agree and disagree, in all: the industry level
-- from a rule that knows the shapes of industry_code, the industry level from the length of
-- the code alone, and the kind of area from the shape of area_fips, each against agglvl_code.
WITH readings AS (
  SELECT
    CASE
      WHEN industry_code = '10' THEN CASE WHEN own_code = '0' THEN '0' ELSE '1' END
      WHEN industry_code IN ('101', '102') THEN '2'
      WHEN length(industry_code) = 4 AND industry_code LIKE '10%' THEN '3'
      WHEN industry_code LIKE '%-%' OR length(industry_code) = 2 THEN '4'
      ELSE CAST(length(industry_code) + 2 AS VARCHAR)
    END AS level_from_shape,
    CAST(length(industry_code) + 2 AS VARCHAR) AS level_from_length,
    CASE
      WHEN area_fips LIKE 'US%' THEN '1'
      WHEN area_fips LIKE 'CS%' THEN '3'
      WHEN area_fips LIKE 'C%' THEN '4'
      WHEN substr(area_fips, 3, 3) = '000' THEN '5'
      ELSE '7'
    END AS kind_from_shape,
    substr(agglvl_code, 2, 1) AS level_from_agglvl,
    substr(agglvl_code, 1, 1) AS kind_from_agglvl
  FROM qtrly
)
SELECT 1 AS n, 'industry level: shape of industry_code' AS reading, count(*) AS row_count,
  sum(CASE WHEN level_from_shape = level_from_agglvl THEN 1 ELSE 0 END) AS agree,
  sum(CASE WHEN level_from_shape <> level_from_agglvl THEN 1 ELSE 0 END) AS disagree
FROM readings
UNION ALL
SELECT 2, 'industry level: length of industry_code', count(*),
  sum(CASE WHEN level_from_length = level_from_agglvl THEN 1 ELSE 0 END),
  sum(CASE WHEN level_from_length <> level_from_agglvl THEN 1 ELSE 0 END)
FROM readings
UNION ALL
SELECT 3, 'kind of area: shape of area_fips', count(*),
  sum(CASE WHEN kind_from_shape = kind_from_agglvl THEN 1 ELSE 0 END),
  sum(CASE WHEN kind_from_shape <> kind_from_agglvl THEN 1 ELSE 0 END)
FROM readings
ORDER BY n

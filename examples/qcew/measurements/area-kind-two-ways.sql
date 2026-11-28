-- The kind of area of every quarterly row, read two ways: from the shape of area_fips and
-- from the first digit of agglvl_code (1 nation, 3 CSA, 4 MSA, 5 state, 7 county, 8 MicroSA,
-- 9 special totals).
WITH rows_two_ways AS (
  SELECT
    CASE
      WHEN area_fips LIKE 'US%' THEN '1 nation (US...)'
      WHEN area_fips LIKE 'CS%' THEN '3 CSA (CS...)'
      WHEN area_fips LIKE 'C%' THEN '4 MSA (C....)'
      WHEN substr(area_fips, 3, 3) = '000' THEN '5 state (nn000)'
      ELSE '7 county (nnnnn)'
    END AS kind_from_code,
    substr(agglvl_code, 1, 1) AS kind_from_agglvl
  FROM qtrly
)
SELECT kind_from_code, kind_from_agglvl,
  CASE WHEN substr(kind_from_code, 1, 1) = kind_from_agglvl THEN 'agree' ELSE 'disagree' END
    AS verdict,
  count(*) AS row_count
FROM rows_two_ways
GROUP BY kind_from_code, kind_from_agglvl
ORDER BY kind_from_code, kind_from_agglvl

-- Average weekly wage, private, total, Maryland, 2025 Q1: the state's published value, the
-- formula over the summed county rows, and the plain average of the county rows' published
-- values. No county row of Maryland is withheld at this level.
WITH counties AS (
  SELECT * FROM qtrly
  WHERE substr(area_fips, 1, 2) = '24' AND agglvl_code = '71' AND own_code = '5'
    AND industry_code = '10' AND year = '2025' AND qtr = '1'
)
SELECT 1 AS n, 'published state row (agglvl_code 51)' AS what, avg_wkly_wage AS avg_weekly_wage
FROM qtrly
WHERE area_fips = '24000' AND agglvl_code = '51' AND own_code = '5' AND industry_code = '10'
  AND year = '2025' AND qtr = '1'
UNION ALL
SELECT 2, 'formula over the summed county rows',
  CAST(round(sum(total_qtrly_wages)
    / (sum(month1_emplvl + month2_emplvl + month3_emplvl) / 3.0) / 13) AS BIGINT)
FROM counties
UNION ALL
SELECT 3, 'average of avg_wkly_wage over the ' || count(*) || ' county rows ('
    || sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) || ' withheld)',
  CAST(round(avg(avg_wkly_wage)) AS BIGINT)
FROM counties
ORDER BY n

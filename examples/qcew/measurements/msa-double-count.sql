-- Total covered employment, March 2025: Delaware, Maryland, the MSA that crosses both (C3798,
-- Philadelphia-Camden-Wilmington, PA-NJ-DE-MD), and the two counties of the MSA that lie in
-- the two states. Adding the two state rows and the MSA row counts those two counties twice.
-- The rest of the MSA row is not counted twice: it is nine counties of Pennsylvania and New
-- Jersey, which belong to neither state.
WITH areas AS (
  SELECT q.area_fips, t.area_title, q.agglvl_code, q.month3_emplvl
  FROM qtrly AS q
  JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) AS t
    ON q.area_fips = t.area_fips
  WHERE q.own_code = '0' AND q.industry_code = '10' AND q.year = '2025' AND q.qtr = '1'
    AND q.area_fips IN ('10000', '24000', 'C3798', '10003', '24015')
)
SELECT 1 AS n, area_fips || ' ' || area_title AS what, agglvl_code, month3_emplvl AS employment
FROM areas
UNION ALL
SELECT 2, 'sum of the two states', '50', sum(month3_emplvl)
FROM areas WHERE area_fips IN ('10000', '24000')
UNION ALL
SELECT 3, 'the two state rows and the MSA row added', '50, 40', sum(month3_emplvl)
FROM areas WHERE area_fips IN ('10000', '24000', 'C3798')
UNION ALL
SELECT 4, 'counted twice in that sum: New Castle and Cecil', '70',
  sum(month3_emplvl)
FROM areas WHERE area_fips IN ('10003', '24015')
UNION ALL
SELECT 5, 'in the MSA row, outside the two states: nine counties of PA and NJ', '40 - 70',
  sum(CASE WHEN area_fips = 'C3798' THEN month3_emplvl
           WHEN area_fips IN ('10003', '24015') THEN -month3_emplvl ELSE 0 END)
FROM areas
ORDER BY n, what

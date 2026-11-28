-- The NAICS child to parent pairs of parent-child-gaps that sit at the MSA levels (agglvl_code
-- 41 to 48), per quarter: disclosed parents with at least one child row that is not padding,
-- and how many differ from the sum of their disclosed children in third-month employment. A
-- quarter without such a pair has no line.
WITH parents AS (
  SELECT p.area_fips, p.own_code, p.industry_code, p.year, p.qtr,
    max(p.month3_emplvl) AS p_emp,
    sum(CASE WHEN c.disclosure_code IS NULL THEN c.month3_emplvl ELSE 0 END) AS s_emp
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.industry_code, 1, length(c.industry_code) - 1) = p.industry_code
    AND length(c.industry_code) > 2 AND c.area_fips = p.area_fips AND c.own_code = p.own_code
    AND c.size_code = p.size_code AND c.year = p.year AND c.qtr = p.qtr
  WHERE p.agglvl_code BETWEEN '41' AND '48' AND p.disclosure_code IS NULL
    AND (c.disclosure_code IS NULL OR c.disclosure_code = 'N')
  GROUP BY p.area_fips, p.own_code, p.industry_code, p.year, p.qtr
)
SELECT year, qtr, count(*) AS parents,
  sum(CASE WHEN p_emp <> s_emp THEN 1 ELSE 0 END) AS mismatch
FROM parents
GROUP BY year, qtr
ORDER BY year, qtr

-- A published parent against the sum of its children, quarterly rows, for two hierarchies
-- (county to state by the area code, NAICS child to parent by the code one character
-- shorter) and three measures. A pair counts when the parent row is disclosed and has at
-- least one child row; padding rows are left out. The sum takes disclosed children only for
-- employment and wages, and every child for establishments, which stay filled on withheld
-- rows. gap is the parent less the sum, as a percentage of the parent, over the mismatches.
-- This is parent-child-gaps with one line per year.
WITH pairs AS (
  SELECT 'county to state' AS hierarchy, p.area_fips, p.own_code, p.industry_code, p.year,
    p.qtr, p.month3_emplvl AS p_emp, p.total_qtrly_wages AS p_wages, p.qtrly_estabs AS p_est,
    c.disclosure_code AS c_code, c.month3_emplvl AS c_emp, c.total_qtrly_wages AS c_wages,
    c.qtrly_estabs AS c_est
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.area_fips, 1, 2) || '000' = p.area_fips AND substr(c.area_fips, 3, 3) <> '000'
    AND substr(c.area_fips, 1, 1) <= '9' AND c.own_code = p.own_code
    AND c.industry_code = p.industry_code AND c.size_code = p.size_code
    AND c.year = p.year AND c.qtr = p.qtr
  WHERE p.disclosure_code IS NULL AND (c.disclosure_code IS NULL OR c.disclosure_code = 'N')
  UNION ALL
  SELECT 'NAICS child to parent', p.area_fips, p.own_code, p.industry_code, p.year, p.qtr,
    p.month3_emplvl, p.total_qtrly_wages, p.qtrly_estabs,
    c.disclosure_code, c.month3_emplvl, c.total_qtrly_wages, c.qtrly_estabs
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.industry_code, 1, length(c.industry_code) - 1) = p.industry_code
    AND length(c.industry_code) > 2 AND c.area_fips = p.area_fips AND c.own_code = p.own_code
    AND c.size_code = p.size_code AND c.year = p.year AND c.qtr = p.qtr
  WHERE p.disclosure_code IS NULL AND (c.disclosure_code IS NULL OR c.disclosure_code = 'N')
), parents AS (
  SELECT hierarchy, area_fips, own_code, industry_code, year, qtr,
    max(p_emp) AS p_emp, max(p_wages) AS p_wages, max(p_est) AS p_est,
    sum(CASE WHEN c_code IS NULL THEN c_emp ELSE 0 END) AS s_emp,
    sum(CASE WHEN c_code IS NULL THEN c_wages ELSE 0 END) AS s_wages,
    sum(c_est) AS s_est,
    sum(CASE WHEN c_code = 'N' THEN 1 ELSE 0 END) AS withheld_children
  FROM pairs
  GROUP BY hierarchy, area_fips, own_code, industry_code, year, qtr
), measured AS (
  SELECT hierarchy, year, 1 AS n, 'employment, third month' AS measure, p_emp AS parent,
    s_emp AS children, withheld_children FROM parents
  UNION ALL
  SELECT hierarchy, year, 2, 'total wages', p_wages, s_wages, withheld_children FROM parents
  UNION ALL
  SELECT hierarchy, year, 3, 'establishments', p_est, s_est, withheld_children FROM parents
)
SELECT hierarchy, measure, year, count(*) AS parents,
  sum(CASE WHEN parent = children THEN 1 ELSE 0 END) AS exact,
  sum(CASE WHEN parent <> children AND withheld_children > 0 THEN 1 ELSE 0 END)
    AS mismatch_withheld_child,
  sum(CASE WHEN parent <> children AND withheld_children = 0 THEN 1 ELSE 0 END)
    AS mismatch_no_withheld_child,
  round(median(CASE WHEN parent <> children AND parent > 0
    THEN 100.0 * (parent - children) / parent END), 1) AS gap_pct_median,
  round(quantile_cont(CASE WHEN parent <> children AND parent > 0
    THEN 100.0 * (parent - children) / parent END, 0.9), 1) AS gap_pct_p90,
  round(max(CASE WHEN parent <> children AND parent > 0
    THEN 100.0 * (parent - children) / parent END), 1) AS gap_pct_max
FROM measured
GROUP BY hierarchy, n, measure, year
ORDER BY hierarchy, n, year

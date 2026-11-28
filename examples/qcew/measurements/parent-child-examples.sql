-- Six rows behind parent-child-gaps: county to state, private, NAICS sectors, third month of
-- 2025 Q1. For each state the three largest sectors whose county rows do not add up to the
-- state row.
WITH parents AS (
  SELECT p.area_fips, p.industry_code, max(p.month3_emplvl) AS published_parent,
    sum(CASE WHEN c.disclosure_code IS NULL THEN c.month3_emplvl ELSE 0 END)
      AS sum_disclosed_children,
    count(*) AS children,
    sum(CASE WHEN c.disclosure_code = 'N' THEN 1 ELSE 0 END) AS withheld_children
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.area_fips, 1, 2) || '000' = p.area_fips AND substr(c.area_fips, 3, 3) <> '000'
    AND c.own_code = p.own_code AND c.industry_code = p.industry_code
    AND c.size_code = p.size_code AND c.year = p.year AND c.qtr = p.qtr
  WHERE p.area_fips IN ('10000', '24000') AND p.own_code = '5' AND p.agglvl_code = '54'
    AND p.year = '2025' AND p.qtr = '1' AND p.disclosure_code IS NULL
    AND (c.disclosure_code IS NULL OR c.disclosure_code = 'N')
  GROUP BY p.area_fips, p.industry_code
), ranked AS (
  SELECT *, row_number() OVER (PARTITION BY area_fips ORDER BY published_parent DESC) AS n
  FROM parents WHERE published_parent <> sum_disclosed_children
)
SELECT r.area_fips, t.industry_title, r.published_parent, r.sum_disclosed_children,
  r.published_parent - r.sum_disclosed_children AS gap,
  round(100.0 * (r.published_parent - r.sum_disclosed_children) / r.published_parent, 1)
    AS gap_pct,
  r.children, r.withheld_children
FROM ranked AS r
JOIN industry_titles AS t ON r.industry_code = t.industry_code
WHERE r.n <= 3
ORDER BY r.area_fips, r.published_parent DESC

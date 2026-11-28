-- What the two rollup probes on third-month employment count as a parent with nothing
-- withheld (parents_compared), split by what the parent row is: a record, or a padding row
-- (disclosure_code '-'), whose value 0 equals the sum 0 of its padding children. The probes
-- know withheld rows (N) only. The last column counts the padding parents at the MSA levels
-- 41 to 48 in 2025 Q3 and Q4, the rows BLS stopped publishing (F-0012).
WITH pairs AS (
  SELECT 'county to state' AS hierarchy, p.area_fips, p.own_code, p.industry_code,
    p.size_code, p.year, p.qtr, p.agglvl_code, p.disclosure_code AS p_code,
    c.disclosure_code AS c_code
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.area_fips, 1, 2) || '000' = p.area_fips AND substr(c.area_fips, 3, 3) <> '000'
    AND substr(c.area_fips, 1, 1) <= '9' AND c.own_code = p.own_code
    AND c.industry_code = p.industry_code AND c.size_code = p.size_code
    AND c.year = p.year AND c.qtr = p.qtr
  UNION ALL
  SELECT 'NAICS child to parent', p.area_fips, p.own_code, p.industry_code, p.size_code,
    p.year, p.qtr, p.agglvl_code, p.disclosure_code, c.disclosure_code
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.industry_code, 1, length(c.industry_code) - 1) = p.industry_code
    AND length(c.industry_code) > 2 AND c.area_fips = p.area_fips AND c.own_code = p.own_code
    AND c.size_code = p.size_code AND c.year = p.year AND c.qtr = p.qtr
), parents AS (
  SELECT hierarchy, area_fips, own_code, industry_code, size_code, year, qtr,
    max(agglvl_code) AS agglvl_code, max(coalesce(p_code, '')) AS p_code,
    sum(CASE WHEN c_code = 'N' THEN 1 ELSE 0 END) AS withheld_children
  FROM pairs
  GROUP BY hierarchy, area_fips, own_code, industry_code, size_code, year, qtr
)
SELECT hierarchy, count(*) AS parents_compared,
  sum(CASE WHEN p_code = '' THEN 1 ELSE 0 END) AS records,
  sum(CASE WHEN p_code = '-' THEN 1 ELSE 0 END) AS padding_rows,
  sum(CASE WHEN p_code = '-' AND agglvl_code BETWEEN '41' AND '48' AND year = '2025'
    AND qtr IN ('3', '4') THEN 1 ELSE 0 END) AS msa_padding_2025_q3_q4
FROM parents
WHERE p_code <> 'N' AND withheld_children = 0
GROUP BY hierarchy
ORDER BY hierarchy

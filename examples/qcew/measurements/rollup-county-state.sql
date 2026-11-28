-- One county-to-state rollup: private health care and social assistance (NAICS 62) in
-- Delaware, March 2025. The parent is the state row; the children are the county rows.
WITH parent AS (
  SELECT month3_emplvl AS published, disclosure_code FROM qtrly
  WHERE area_fips = '10000' AND own_code = '5' AND industry_code = '62'
    AND year = '2025' AND qtr = '1' AND agglvl_code = '54'
), children AS (
  SELECT area_fips, disclosure_code, month3_emplvl FROM qtrly
  WHERE substr(area_fips, 1, 2) = '10' AND substr(area_fips, 3, 3) <> '000'
    AND own_code = '5' AND industry_code = '62'
    AND year = '2025' AND qtr = '1' AND agglvl_code = '74'
)
SELECT (SELECT published FROM parent) AS published_parent,
  sum(CASE WHEN disclosure_code IS NULL THEN month3_emplvl END) AS sum_disclosed_children,
  (SELECT published FROM parent)
    - sum(CASE WHEN disclosure_code IS NULL THEN month3_emplvl END) AS gap,
  count(*) AS children,
  sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) AS suppressed_children
FROM children

-- One NAICS child-to-parent rollup: private finance and insurance (NAICS 52) in Delaware,
-- March 2025. The parent is the sector row; the children are its 3-digit subsectors.
WITH parent AS (
  SELECT month3_emplvl AS published FROM qtrly
  WHERE area_fips = '10000' AND own_code = '5' AND industry_code = '52'
    AND year = '2025' AND qtr = '1' AND agglvl_code = '54'
), children AS (
  SELECT industry_code, disclosure_code, month3_emplvl FROM qtrly
  WHERE area_fips = '10000' AND own_code = '5'
    AND substr(industry_code, 1, 2) = '52' AND length(industry_code) = 3
    AND year = '2025' AND qtr = '1' AND agglvl_code = '55'
)
SELECT (SELECT published FROM parent) AS published_parent,
  sum(CASE WHEN disclosure_code IS NULL THEN month3_emplvl END) AS sum_disclosed_children,
  (SELECT published FROM parent)
    - sum(CASE WHEN disclosure_code IS NULL THEN month3_emplvl END) AS gap,
  count(*) AS children,
  sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) AS suppressed_children
FROM children

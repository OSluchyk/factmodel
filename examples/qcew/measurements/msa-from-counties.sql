-- An MSA rebuilt from its counties: private employment, third month of each 2025 quarter,
-- for Baltimore-Columbia-Towson, MD (C1258). Its seven counties are all in Maryland (BLS
-- County-MSA-CSA crosswalk, 2024 to current). From 2025 Q3 the MSA's private row is padding.
WITH msa AS (
  SELECT qtr, coalesce(disclosure_code, '') AS disclosure_code, month3_emplvl
  FROM qtrly
  WHERE area_fips = 'C1258' AND own_code = '5' AND industry_code = '10'
    AND agglvl_code = '41' AND year = '2025'
), counties AS (
  SELECT qtr, sum(month3_emplvl) AS employment, count(*) AS county_rows,
    sum(CASE WHEN disclosure_code = 'N' THEN 1 ELSE 0 END) AS suppressed_rows
  FROM qtrly
  WHERE area_fips IN ('24003', '24005', '24013', '24025', '24027', '24035', '24510')
    AND own_code = '5' AND industry_code = '10' AND agglvl_code = '71' AND year = '2025'
  GROUP BY qtr
)
SELECT m.qtr, m.disclosure_code AS msa_disclosure_code, m.month3_emplvl AS msa_row,
  c.employment AS sum_of_counties, c.county_rows, c.suppressed_rows
FROM msa AS m JOIN counties AS c ON m.qtr = c.qtr
ORDER BY m.qtr

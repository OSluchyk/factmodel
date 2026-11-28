-- Annual average employment, county rows summed to their state row: the state's published
-- value minus the sum of its counties, for every key where neither the state row nor any
-- county row is withheld. The same pairs as the probe
-- rollup-annual-employment-area-titles-in-state compares.
WITH pairs AS (
  SELECT max(p.annual_avg_emplvl) AS parent_value, sum(c.annual_avg_emplvl) AS child_sum,
    count(*) AS children,
    max(CASE WHEN p.disclosure_code = 'N' THEN 1 ELSE 0 END) AS parent_suppressed,
    sum(CASE WHEN c.disclosure_code = 'N' THEN 1 ELSE 0 END) AS suppressed_children
  FROM annual AS p
  JOIN annual AS c
    ON substr(c.area_fips, 1, 2) || '000' = p.area_fips AND substr(c.area_fips, 3, 3) <> '000'
    AND substr(c.area_fips, 1, 1) <= '9' AND c.own_code = p.own_code
    AND c.industry_code = p.industry_code AND c.size_code = p.size_code
    AND c.year = p.year AND c.qtr = p.qtr
  GROUP BY p.area_fips, p.own_code, p.industry_code, p.size_code, p.year, p.qtr
)
SELECT parent_value - child_sum AS state_minus_counties, count(*) AS keys
FROM pairs
WHERE parent_suppressed = 0 AND suppressed_children = 0
GROUP BY parent_value - child_sum
ORDER BY state_minus_counties

-- Rows without a row of the same key one year earlier, by table and year: all of them, and
-- those that claim an over-the-year value (oty_disclosure_code blank). 2024 is the first year
-- in the slices, so its rows have no prior year here; 2025 is the year the relationship can
-- be tested on. The line "all" adds the two years.
WITH by_year AS (
  SELECT 'annual' AS source_table, a.year, count(*) AS row_count,
    sum(CASE WHEN p.year IS NULL THEN 1 ELSE 0 END) AS without_prior_row,
    sum(CASE WHEN p.year IS NULL AND a.oty_disclosure_code IS NULL THEN 1 ELSE 0 END)
      AS without_prior_row_and_oty_value,
    sum(CASE WHEN a.oty_disclosure_code IS NULL THEN 1 ELSE 0 END) AS with_oty_value
  FROM annual AS a
  LEFT JOIN annual AS p
    ON a.area_fips = p.area_fips AND a.own_code = p.own_code
    AND a.industry_code = p.industry_code AND a.size_code = p.size_code
    AND CAST(a.year AS INTEGER) - 1 = CAST(p.year AS INTEGER)
  GROUP BY a.year
  UNION ALL
  SELECT 'qtrly', a.year, count(*),
    sum(CASE WHEN p.year IS NULL THEN 1 ELSE 0 END),
    sum(CASE WHEN p.year IS NULL AND a.oty_disclosure_code IS NULL THEN 1 ELSE 0 END),
    sum(CASE WHEN a.oty_disclosure_code IS NULL THEN 1 ELSE 0 END)
  FROM qtrly AS a
  LEFT JOIN qtrly AS p
    ON a.area_fips = p.area_fips AND a.own_code = p.own_code
    AND a.industry_code = p.industry_code AND a.size_code = p.size_code
    AND CAST(a.year AS INTEGER) - 1 = CAST(p.year AS INTEGER) AND a.qtr = p.qtr
  GROUP BY a.year
)
SELECT * FROM by_year
UNION ALL
SELECT source_table, 'all', sum(row_count), sum(without_prior_row),
  sum(without_prior_row_and_oty_value), sum(with_oty_value)
FROM by_year GROUP BY source_table
ORDER BY source_table, year

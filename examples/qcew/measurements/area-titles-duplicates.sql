-- The area code list as BLS serves it: rows, distinct codes, codes that occur twice, and the
-- second header line, which loads as a row.
SELECT count(*) AS row_count,
  count(DISTINCT area_fips) AS distinct_codes,
  (SELECT count(*) FROM (SELECT area_fips FROM area_titles GROUP BY area_fips
     HAVING count(*) = 2)) AS codes_twice,
  (SELECT count(*) FROM (SELECT area_fips FROM area_titles GROUP BY area_fips
     HAVING count(*) > 2)) AS codes_more_than_twice,
  (SELECT count(*) FROM (SELECT area_fips FROM area_titles GROUP BY area_fips
     HAVING count(DISTINCT area_title) > 1)) AS codes_with_two_titles,
  sum(CASE WHEN area_fips = 'area_fips' THEN 1 ELSE 0 END) AS header_rows
FROM area_titles

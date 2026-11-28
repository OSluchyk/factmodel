-- The counties of C3798 (Philadelphia-Camden-Wilmington, PA-NJ-DE-MD) by state, from the BLS
-- County-MSA-CSA crosswalk, sheet for data from 2024 on, and whether the slices hold them.
SELECT substr(c.county_code, 1, 2) AS state_fips,
  trim(split_part(c.county_title, ',', 2)) AS state, count(*) AS counties,
  string_agg(c.county_code || ' ' || trim(split_part(c.county_title, ',', 1)), '; '
    ORDER BY c.county_code) AS county_list,
  sum(CASE WHEN EXISTS (SELECT 1 FROM annual AS a WHERE a.area_fips = c.county_code)
    THEN 1 ELSE 0 END) AS in_the_slices
FROM crosswalk AS c
WHERE c.msa_code = 'C3798'
GROUP BY substr(c.county_code, 1, 2), trim(split_part(c.county_title, ',', 2))
ORDER BY state_fips

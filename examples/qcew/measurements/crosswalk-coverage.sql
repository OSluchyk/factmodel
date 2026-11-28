-- The crosswalk against the slices: counties of Delaware and Maryland by the kind of area
-- they belong to, and whether every MSA and MicroSA code the crosswalk gives them has a slice.
SELECT substr(c.county_code, 1, 2) AS state_fips,
  CASE WHEN c.msa_title LIKE '%MicroSA' THEN 'MicroSA' WHEN c.msa_code <> '' THEN 'MSA'
    ELSE 'none' END AS in_area_of_kind,
  count(*) AS counties, count(DISTINCT nullif(c.msa_code, '')) AS areas,
  count(DISTINCT CASE WHEN EXISTS (SELECT 1 FROM annual AS a WHERE a.area_fips = c.msa_code)
    THEN c.msa_code END) AS areas_with_a_slice
FROM crosswalk AS c
WHERE substr(c.county_code, 1, 2) IN ('10', '24')
GROUP BY substr(c.county_code, 1, 2), in_area_of_kind
ORDER BY state_fips, in_area_of_kind

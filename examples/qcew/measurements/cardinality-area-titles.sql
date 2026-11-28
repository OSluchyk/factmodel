-- Quarterly rows before a join to the area code list, after a plain join, and after a join
-- to distinct codes.
SELECT 1 AS step, 'qtrly' AS rows_of, count(*) AS row_count FROM qtrly
UNION ALL
SELECT 2, 'qtrly JOIN area_titles', count(*)
FROM qtrly AS q JOIN area_titles AS t ON q.area_fips = t.area_fips
UNION ALL
SELECT 3, 'qtrly JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles)', count(*)
FROM qtrly AS q
JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) AS t ON q.area_fips = t.area_fips
ORDER BY step

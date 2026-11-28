-- The industry level of every quarterly row, read three ways and checked against what the
-- title of its aggregation level says: from the length of industry_code, from a rule that
-- knows the shapes of the code, and from the second digit of agglvl_code. Per kind of code:
-- rows, rows each reading gets wrong, and rows where length and second digit disagree.
WITH readings AS (
  SELECT
    CASE
      WHEN q.industry_code = '10' AND q.agglvl_code >= '90' THEN '2 total (10) at levels 94 to 96'
      WHEN q.industry_code = '10' THEN '1 total (10)'
      WHEN q.industry_code IN ('101', '102') THEN '3 domain (101, 102)'
      WHEN length(q.industry_code) = 4 AND q.industry_code LIKE '10%' THEN '4 supersector (10xx)'
      WHEN q.industry_code LIKE '%-%' THEN '5 sector written as a range (nn-nn)'
      ELSE '6 NAICS, ' || length(q.industry_code) || ' digits'
    END AS kind_of_code,
    CASE
      WHEN t.agglvl_title LIKE '%Domain%' THEN 'domain'
      WHEN t.agglvl_title LIKE '%Supersector%' THEN 'supersector'
      WHEN t.agglvl_title LIKE '%NAICS Sector%' THEN 'sector'
      WHEN t.agglvl_title LIKE '%NAICS _-digit%' THEN 'naics' || substr(t.agglvl_title, strpos(t.agglvl_title, 'NAICS ') + 6, 1)
      ELSE 'total'
    END AS level_by_title,
    CASE length(q.industry_code) WHEN 2 THEN 'sector' ELSE 'naics' || length(q.industry_code) END
      AS level_by_length,
    CASE
      WHEN q.industry_code = '10' THEN 'total'
      WHEN q.industry_code IN ('101', '102') THEN 'domain'
      WHEN length(q.industry_code) = 4 AND q.industry_code LIKE '10%' THEN 'supersector'
      WHEN q.industry_code LIKE '%-%' OR length(q.industry_code) = 2 THEN 'sector'
      ELSE 'naics' || length(q.industry_code)
    END AS level_by_shape,
    CASE substr(q.agglvl_code, 2, 1)
      WHEN '0' THEN 'total' WHEN '1' THEN 'total' WHEN '2' THEN 'domain'
      WHEN '3' THEN 'supersector' WHEN '4' THEN 'sector'
      ELSE 'naics' || CAST(CAST(substr(q.agglvl_code, 2, 1) AS INTEGER) - 2 AS VARCHAR)
    END AS level_by_digit
  FROM qtrly AS q
  JOIN agglevel_titles AS t ON q.agglvl_code = t.agglvl_code
)
SELECT kind_of_code, count(*) AS row_count,
  sum(CASE WHEN level_by_length <> level_by_title THEN 1 ELSE 0 END) AS wrong_by_length,
  sum(CASE WHEN level_by_shape <> level_by_title THEN 1 ELSE 0 END) AS wrong_by_shape,
  sum(CASE WHEN level_by_digit <> level_by_title THEN 1 ELSE 0 END) AS wrong_by_digit,
  sum(CASE WHEN level_by_length <> level_by_digit THEN 1 ELSE 0 END) AS length_and_digit_differ,
  sum(CASE WHEN level_by_shape <> level_by_digit THEN 1 ELSE 0 END) AS shape_and_digit_differ
FROM readings
GROUP BY kind_of_code
ORDER BY kind_of_code

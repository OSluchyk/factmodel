-- The distinct values of industry_code in the data rows, by the shape of the code.
WITH codes AS (
  SELECT DISTINCT industry_code FROM qtrly
  UNION
  SELECT DISTINCT industry_code FROM annual
), shaped AS (
  SELECT industry_code,
    CASE
      WHEN industry_code = '10' THEN '1 total (10)'
      WHEN industry_code IN ('101', '102') THEN '2 domain (101, 102)'
      WHEN length(industry_code) = 4 AND industry_code LIKE '10%' THEN '3 supersector (10xx)'
      WHEN industry_code LIKE '%-%' THEN '4 sector written as a range (nn-nn)'
      ELSE '5 NAICS, ' || length(industry_code) || ' digits'
    END AS shape
  FROM codes
)
SELECT shape, count(*) AS codes, min(industry_code) AS first_code, max(industry_code) AS last_code,
  sum(CASE WHEN length(industry_code) > 2 AND NOT EXISTS (
        SELECT 1 FROM industry_titles AS p
        WHERE p.industry_code = substr(shaped.industry_code, 1, length(shaped.industry_code) - 1)
      ) THEN 1 ELSE 0 END) AS without_prefix_parent
FROM shaped
GROUP BY shape
ORDER BY shape

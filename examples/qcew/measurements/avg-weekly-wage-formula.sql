-- avg_wkly_wage against the documented formula, recomputed from the published, rounded
-- fields: total_qtrly_wages / mean of the three monthly levels / 13. Disclosed rows with
-- employment in every month.
WITH recomputed AS (
  SELECT avg_wkly_wage,
    round(total_qtrly_wages / ((month1_emplvl + month2_emplvl + month3_emplvl) / 3.0) / 13)
      AS from_fields
  FROM qtrly
  WHERE disclosure_code IS NULL AND month1_emplvl > 0 AND month2_emplvl > 0
    AND month3_emplvl > 0
)
SELECT count(*) AS row_count,
  sum(CASE WHEN avg_wkly_wage = from_fields THEN 1 ELSE 0 END) AS equal,
  sum(CASE WHEN abs(avg_wkly_wage - from_fields) = 1 THEN 1 ELSE 0 END) AS off_by_one,
  sum(CASE WHEN abs(avg_wkly_wage - from_fields) > 1 THEN 1 ELSE 0 END) AS off_by_more
FROM recomputed

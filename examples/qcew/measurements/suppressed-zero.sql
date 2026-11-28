-- What a withheld (N) or padding (-) quarterly row holds: zeros, not NULL, and for N rows an
-- establishment count.
SELECT coalesce(disclosure_code, 'blank') AS disclosure_code, count(*) AS row_count,
  sum(CASE WHEN month1_emplvl IS NULL OR month2_emplvl IS NULL OR month3_emplvl IS NULL
        OR total_qtrly_wages IS NULL THEN 1 ELSE 0 END) AS rows_with_null,
  sum(CASE WHEN month1_emplvl = 0 AND month2_emplvl = 0 AND month3_emplvl = 0
        AND total_qtrly_wages = 0 THEN 1 ELSE 0 END) AS employment_and_wages_zero,
  sum(CASE WHEN qtrly_estabs > 0 THEN 1 ELSE 0 END) AS establishments_filled
FROM qtrly
GROUP BY coalesce(disclosure_code, 'blank')
ORDER BY disclosure_code

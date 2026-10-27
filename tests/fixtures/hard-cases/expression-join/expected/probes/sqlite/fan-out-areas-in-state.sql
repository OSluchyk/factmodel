SELECT COALESCE(MAX("f"."n"), 0) AS "max_fan_out" FROM (SELECT COUNT(*) AS "n" FROM "stats"."areas" AS "t" WHERE NOT "t"."area_fips" IS NULL GROUP BY "t"."area_fips") AS "f"

-- Quarterly rows per aggregation level: disclosed, withheld (N) and padding (-) rows, and
-- their shares in percent.
SELECT q.agglvl_code, t.agglvl_title, count(*) AS row_count,
  sum(CASE WHEN q.disclosure_code = 'N' THEN 1 ELSE 0 END) AS n_rows,
  sum(CASE WHEN q.disclosure_code = '-' THEN 1 ELSE 0 END) AS dash_rows,
  round(100.0 * sum(CASE WHEN q.disclosure_code = 'N' THEN 1 ELSE 0 END) / count(*), 1)
    AS n_pct,
  round(100.0 * sum(CASE WHEN q.disclosure_code = '-' THEN 1 ELSE 0 END) / count(*), 1)
    AS dash_pct
FROM qtrly AS q
JOIN agglevel_titles AS t ON q.agglvl_code = t.agglvl_code
GROUP BY q.agglvl_code, t.agglvl_title
ORDER BY q.agglvl_code

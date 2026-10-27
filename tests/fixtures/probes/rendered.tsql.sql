-- key_duplicates
SELECT COUNT(*) AS [duplicate_keys] FROM (SELECT [t].[CustomerId] AS [CustomerId] FROM [sales].[Customer] AS [t] WHERE NOT [t].[CustomerId] IS NULL GROUP BY [t].[CustomerId] HAVING COUNT(*) > 1) AS [d];
-- join_match
SELECT (SELECT COUNT(*) FROM [sales].[Order] AS [s] WHERE NOT [s].[CustomerId] IS NULL) AS [source_rows], (SELECT COUNT(*) FROM [sales].[Order] AS [s] WHERE NOT [s].[CustomerId] IS NULL AND NOT EXISTS(SELECT 1 FROM [sales].[Customer] AS [t] WHERE [s].[CustomerId] = [t].[CustomerId])) AS [orphans_left], (SELECT COUNT(*) FROM [sales].[Customer] AS [t] WHERE NOT EXISTS(SELECT 1 FROM [sales].[Order] AS [s] WHERE [s].[CustomerId] = [t].[CustomerId])) AS [orphans_right];
-- fan_out
SELECT COALESCE(MAX([f].[n]), 0) AS [max_fan_out] FROM (SELECT COUNT(*) AS [n] FROM [sales].[Customer] AS [t] WHERE NOT [t].[CustomerId] IS NULL GROUP BY [t].[CustomerId]) AS [f];
-- null_rate
SELECT COUNT(*) AS [row_count], COUNT([t].[CustomerId]) AS [non_null] FROM [sales].[Order] AS [t];
-- row_count
SELECT COUNT(*) AS [row_count] FROM [sales].[Order] AS [t];
-- current_row_ties
SELECT COUNT(*) AS [tied_keys] FROM (SELECT [t].[CustomerId] AS [CustomerId] FROM [sales].[CustomerVersion] AS [t] WHERE [t].[IsCurrent] = 1 GROUP BY [t].[CustomerId] HAVING COUNT(*) > 1) AS [d];
-- value_set
SELECT COUNT(DISTINCT [t].[EmailHash]) AS [distinct_values] FROM [sales].[Customer] AS [t];
-- rollup
SELECT COALESCE(SUM(CASE WHEN [r].[parent_suppressed] = 0 AND [r].[suppressed_children] = 0 THEN 1 ELSE 0 END), 0) AS [parents_compared], COALESCE(SUM(CASE WHEN ([r].[parent_suppressed] = 0 AND [r].[suppressed_children] = 0) AND [r].[child_sum] = [r].[parent_value] THEN 1 ELSE 0 END), 0) AS [exact], COALESCE(SUM(CASE WHEN ([r].[parent_suppressed] = 0 AND [r].[suppressed_children] = 0) AND ABS([r].[child_sum] - [r].[parent_value]) > 0 AND ABS([r].[child_sum] - [r].[parent_value]) <= [r].[children] THEN 1 ELSE 0 END), 0) AS [within_rounding], COALESCE(SUM(CASE WHEN ([r].[parent_suppressed] = 0 AND [r].[suppressed_children] = 0) AND ABS([r].[child_sum] - [r].[parent_value]) > [r].[children] THEN 1 ELSE 0 END), 0) AS [beyond], COALESCE(SUM(CASE WHEN [r].[suppressed_children] > 0 THEN 1 ELSE 0 END), 0) AS [parents_with_suppressed_child], COALESCE(SUM(CASE WHEN [r].[parent_suppressed] = 1 AND [r].[suppressed_children] < [r].[children] THEN 1 ELSE 0 END), 0) AS [suppressed_parents_disclosed_children] FROM (SELECT MAX([p].[Amount]) AS [parent_value], MAX(CASE WHEN [p].[Flag] = 'N' THEN 1 ELSE 0 END) AS [parent_suppressed], COUNT(*) AS [children], SUM([c].[Amount]) AS [child_sum], SUM(CASE WHEN [c].[Flag] = 'N' THEN 1 ELSE 0 END) AS [suppressed_children] FROM [sales].[Revenue] AS [p] JOIN [sales].[Revenue] AS [c] ON [c].[ParentRegion] = [p].[Region] AND [c].[Year] = [p].[Year] GROUP BY [p].[Region], [p].[Year]) AS [r];

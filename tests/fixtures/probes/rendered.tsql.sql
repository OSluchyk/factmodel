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

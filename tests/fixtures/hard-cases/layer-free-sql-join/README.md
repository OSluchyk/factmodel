# layer-free-sql-join

A layer whose `joins` holds free SQL instead of a relationship key. The schema refuses it (D-019: joins are relationship keys only, never SQL).

Plan case: - (D-019). Gate: fails `schema` (and `references`: the key does not resolve).

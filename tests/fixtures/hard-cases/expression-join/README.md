# expression-join

A join that is not field equality (D-017): a county to its state by code prefix, written as a self-reference on one code list. The left operand of each comparison is the source row (the county), the right operand the target row (the state). `expected/probes/` holds the `join_match` and `fan_out` SQL the generator must write for SQLite and PostgreSQL; a test also runs them on a few rows.

Plan case: - (D-017). Gate: pass.

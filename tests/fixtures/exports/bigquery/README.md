# BigQuery export (JSON)

Synthetic export of a made-up shop schema, written by hand for tests. Metadata only, no rows.

Values are strings as the `bq` tool writes them. `orders` is partitioned on `ordered_on`, clustered on `customer_id`, has a STRUCT (`context`) and an ARRAY (`tags`). No `REFERENTIAL_CONSTRAINTS`: foreign key targets come from `CONSTRAINT_COLUMN_USAGE`.

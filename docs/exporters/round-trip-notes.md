# Exporters: round-trip notes

`fact export --target <ossie|dbt> --layer <id> --out <dir>` writes a layer for another tool and `EXPORT_NOTES.md`, the list of what the target cannot hold. Nothing is dropped silently. This page lists those limits for each target, and what each export was checked against.

## dbt (MetricFlow semantic models and metrics)

Pinned to dbt-core 1.12.6 with dbt-duckdb 1.11.1 (dev dependencies). The tests run `dbt parse` on a throwaway project holding the export, stub models and a time spine. Tracking and the version check are off.

| Layer part | In dbt | Notes |
| --- | --- | --- |
| Entity | A semantic model on `ref('<entity id>')` with a primary entity on the key (fields joined with `||` for a composite key) | The project must provide the models and a MetricFlow time spine. |
| Join (relationship key) | A foreign entity on the source field | Single-field equality joins only; an expression join is a note. |
| Concept with a predicate | A categorical dimension per field it reads, and a metric `filter` (`{{ Dimension('<entity>__<field>') }}`) when the concept is a default filter of the entity | Applied to every metric whose measure does not include suppressed cells. |
| Required concept with no fixed value (QCEW `level`) | Nothing | Note: the query must set it. |
| Distinct rule (QCEW `distinct_areas`) | Nothing | Note: no MetricFlow form. |
| Value vocabulary | Nothing | Note: kept only in the meaning. |
| Measure (`sum`, `count`, `count_distinct`, `avg`, `min`, `max`) | A measure and a simple metric | `config.meta` carries `factmodel_suppressed` and the measure's hazards. |
| Measure with aggregation `none` (QCEW `avg_weekly_wage`, `annual_employment`) | Nothing | Note: a formula over aggregates, or a value read at its grain, needs a hand-written derived metric. |
| Time field that is not a date (QCEW `qtr`, `year`) | A time dimension on the field | Note: MetricFlow needs an expression that yields a date. |
| Evidence status, layer status, physical name | `config.meta` of the semantic model | |

## Apache Ossie (formerly Open Semantic Interchange)

Pinned to the Apache Ossie core specification, https://github.com/apache/ossie/blob/main/core-spec/spec.md, version `0.2.0.dev0`, read once on 2026-10-27 (round 28). The document marks itself a draft that may change before 0.2.0 is released, and publishes no JSON Schema, so the tests are structural: every key the export writes is one the document names, every name a key refers to resolves as the document says (`primary_key`, `from_columns`, `to_columns` and metric expressions name dataset fields, metrics are model-scoped with `dataset.field` references), and every expression parses in its dialect.

The document is flat: one model at the root, with `version`, `name`, `description`, `ai_context`, `datasets`, `relationships`, `metrics` and `custom_extensions`. Round 25 wrote the `semantic_model` list shown on the project page; version 0.2.0.dev0 removes that list.

| Layer part | In Ossie | Notes |
| --- | --- | --- |
| Entity | A dataset: physical name as `source`, primary key (field names), grain as `description`, every field | |
| Field | A field: `expression.dialects` with the source column, meaning as `description`, `datatype` when the engine type maps to the document's enumeration | A nested path becomes one name with `__` in place of the dot. A type sqlglot cannot read, or one outside the enumeration, has no `datatype`. |
| Field a concept reads, or a measure's time field | `dimension.is_time` false or true | A date or timestamp field defaults to `is_time` true under the document's rule. |
| Join (relationship key), equality, to a one side, both entities in the layer | A relationship: `from` is the many side, `to` the one side, `from_columns` and `to_columns` are field names, the meaning is `ai_context` | A `one_to_many` key is written from its target. |
| Join that is an expression, `many_to_many` or `unknown`, or to an entity outside the layer (QCEW `qtrly.to-area`, `annual.to-area`) | Text in `ai_context.instructions` | Note per join. Ossie's `to_columns` must be a key of the `to` dataset. |
| Measure | A model-scoped metric: aggregation and expression, rendered per dialect of the layer's sources; meaning as `description` | Dialect names follow sqlglot; the document leaves names free-form and defines only `OSSIE_SQL_2026`, which is not written. |
| Measure with suppressed-cell handling (every QCEW measure) | `custom_extensions` of the metric | Ossie metrics have no filter. |
| Measure with aggregation `none` and no aggregate (QCEW `annual_employment`) | A metric whose expression is the field | Note: read at its grain. |
| Required concepts, hazards, evidence status | Text in `ai_context.instructions`, and JSON in `custom_extensions` (vendor `factmodel`) on the model, each dataset and each metric | The document names no key for them. |
| Concept with no required flag, value vocabulary, values table | Nothing beyond the field's `dimension` | |

`custom_extensions` follows the document's schema: a list of `vendor_name` and `data`, where `data` is a JSON string. Vendor name `factmodel`. Keys: on the model `layer_status`, `consumer`, `required_concepts`, `hazards`; on a dataset `evidence_status`, `current_row_rule`, `default_filters`; on a metric `aggregation`, `grain`, and `suppressed` and `hazards` when set.

When Ossie releases 0.2.0 or publishes a JSON Schema, the pin moves in a round with one read of the released document.

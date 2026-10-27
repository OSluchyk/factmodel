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

Two versions of the core specification are pinned, each read once on 2026-10-27. Neither publishes a JSON Schema, so the tests are structural: every key the export writes is one the document names, every name a key refers to resolves, and every expression parses in its dialect.

| | 0.1.1 (default) | 0.2.0.dev0 (`--spec-version 0.2.0.dev0`) |
| --- | --- | --- |
| Document | https://github.com/apache/ossie/blob/osi-0.1.1-rc1/core-spec/spec.md, the released version (tag `osi-0.1.1-rc1`), read in round 29 | https://github.com/apache/ossie/blob/main/core-spec/spec.md, a draft that may change before 0.2.0, read in round 28 |
| Model | A `semantic_model` list holding one model; no `version` key | One model at the root, with `version: 0.2.0.dev0` |
| Keys and relationship columns | Name source columns | Name dataset fields |
| Field type | No key; not written | `datatype`, when the engine type maps to the document's enumeration |
| Dialects | A closed enumeration: `SNOWFLAKE` and `DATABRICKS` for those engines; every other engine is written once as neutral `ANSI_SQL` | Free-form: sqlglot names, one per source dialect; `OSSIE_SQL_2026`, the only dialect the document defines, is not written |
| `custom_extensions` | Vendor names are a closed enumeration: vendor `COMMON`, the framework's keys under `factmodel` in the JSON | Vendor `factmodel` |

Fields are written as the entity's columns, so a field name equals its column name and both versions resolve. Expressions in `ANSI_SQL` are sqlglot's neutral SQL, which is not checked against any one engine.

| Layer part | In Ossie | Notes |
| --- | --- | --- |
| Entity | A dataset: physical name as `source`, primary key, grain as `description`, every field | |
| Field | A field: `expression.dialects` with the source column, meaning as `description`; `datatype` in 0.2.0.dev0 only | A nested path becomes one name with `__` in place of the dot. |
| Field a concept reads, or a measure's time field | `dimension.is_time` false or true | |
| Join (relationship key), equality, to a one side, both entities in the layer | A relationship: `from` is the many side, `to` the one side; the meaning is `ai_context` | A `one_to_many` key is written from its target. |
| Join that is an expression, `many_to_many` or `unknown`, or to an entity outside the layer (QCEW `qtrly.to-area`, `annual.to-area`) | Text in `ai_context.instructions` | Note per join. Ossie's `to_columns` must be a key of the `to` dataset. |
| Measure | A model-level metric: aggregation and expression with `dataset.field` references; meaning as `description` | |
| Measure with suppressed-cell handling (every QCEW measure) | `custom_extensions` of the metric | Ossie metrics have no filter. |
| Measure with aggregation `none` and no aggregate (QCEW `annual_employment`) | A metric whose expression is the field | Note: read at its grain. |
| Required concepts, hazards, evidence status | Text in `ai_context.instructions`, and JSON in `custom_extensions` on the model, each dataset and each metric | Neither document names a key for them. |
| Concept with no required flag, value vocabulary, values table | Nothing beyond the field's `dimension` | |

The framework's keys in `custom_extensions`: on the model `layer_status`, `consumer`, `required_concepts`, `hazards`; on a dataset `evidence_status`, `current_row_rule`, `default_filters`; on a metric `aggregation`, `grain`, and `suppressed` and `hazards` when set.

When Ossie releases 0.2.0 or publishes a JSON Schema, a new pin needs one read of that document.

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

Pinned to https://ossie.apache.org/, read once on 2026-10-27. The page names no version and no published JSON Schema. It links the core specification at https://github.com/apache/ossie/blob/main/core-spec/spec.md, which was not read (one network read only). The exporter writes only the keys the page's example shows: `semantic_model[]` with `name`, `description`, `ai_context.instructions`, `datasets[]` (`name`, `source`, `primary_key`, `fields[]` with `name` and `dimension.is_time`) and `metrics[]` (`name`, `expression.dialects[]` with `dialect` and `expression`). The tests are structural only.

| Layer part | In Ossie | Notes |
| --- | --- | --- |
| Entity | A dataset: physical name as `source`, primary key, every field | |
| Field a concept reads, or a measure's time field | `dimension.is_time` false or true | |
| Measure | A metric: aggregation and expression, rendered per dialect of the layer's sources | Dialect identifiers follow sqlglot; the page names none. |
| Required concepts, joins, hazards, evidence status | Text in `ai_context.instructions` | No key for them on the pinned page. |

When the Ossie specification is read and pinned to a version, the instructions text should move into the keys it defines. That needs a network read and an owner decision.

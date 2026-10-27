# Core changes in M3

The current core-change ledger (D-018): every change to the contract since the M2 freeze (`61f9112`, schemas 1.0.0), with the record that covers it. What counts as core is defined in `spec/CORE-CHANGES-M2.md`.

**Rule (D-018).** A decision record is required when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result. Adding an optional key, a vocabulary value or a probe kind needs a `CHANGELOG.md` entry and a line here. A defect fix needs a `CHANGELOG.md` entry only.

| # | Round | Change | Kind | Record | Platform |
| --- | --- | --- | --- | --- | --- |
| 1 | 20 | Layer contract v1: `entities` (current-row rule, default filters), concepts in three forms (`field`/`values`, `predicate`, `distinct`) with `required`, measures with `expression`, `grain`, `time`, `formula_source`, `hazards`, `suppressed`, `companion`; `filters`, measure `field` and `time_field` removed; consumer `interface` | contract, breaking | D-019 | QCEW, Chinook |
| 2 | 20 | Schemas 2.0.0 | version | D-019 | QCEW, Chinook |
| 3 | 20 | Vocabulary blocks `measure_aggregation`, `time_granularity`, `suppressed_handling` | vocabulary | D-019 | QCEW, Chinook |
| 4 | 20 | Gate stage `layers` | gate | D-019 | QCEW, Chinook |
| 5 | 20 | `fact check` warns (never fails) on a `schema_version` difference when every file validates | implementation | - | none |
| 6 | 20 | Framework version 0.1.0 (M2 closed; 1.0.0 is M4) | release | - | none |
| 7 | 21 | Equivalence corpus item format (`id`, `request`, `reference`, `mode`, `note`, `tags`) and vocabulary block `equivalence_mode` | contract, additive | ledger line (D-018) | none |
| 8 | 21 | `fact equivalence run`, `accept`, `script`; `equivalence/last-run.json`, `equivalence/accepted.json`, `generated/equivalence-<layer>.md` | implementation (plan WP3.2) | - | none |

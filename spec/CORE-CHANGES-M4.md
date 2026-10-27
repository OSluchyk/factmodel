# Core changes in M4

The current core-change ledger (D-018), continuing `spec/CORE-CHANGES-M3.md` from `85494ea` (schemas 2.1.0, framework 0.1.0). What counts as core is defined in `spec/CORE-CHANGES-M2.md`.

**Rule (D-018).** A decision record is required when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result. Adding an optional key, a vocabulary value or a probe kind needs a `CHANGELOG.md` entry and a line here. A defect fix needs a `CHANGELOG.md` entry only.

| # | Round | Change | Kind | Record | Platform |
| --- | --- | --- | --- | --- | --- |
| 1 | 26 | Derived file `semantic/<layer>/generated/joins.tsv`, written by `fact project`, checked by `derived-not-authored` (M3 answer Q1) | derived output, additive | ledger line (D-018) | QCEW, Chinook |
| 2 | 26 | Concept form `values_table` (`columns`, `rows` or `entity`); the `layers` stage checks it (M3 answer Q2) | contract, additive | ledger line (D-018) | QCEW |
| 3 | 26 | Schemas 2.2.0 | version | D-018 (additive) | QCEW |
| 4 | 26 | dbt export: derived metrics for formula measures over exported metrics (M3 answer Q4) | implementation | - | QCEW |
| 5 | 26 | `RELEASE_NOTES.md` committed in the model repository (`release/RELEASE_NOTES.md`); `fact release` appends and copies (M3 answer Q5) | release format, additive | ledger line (D-018) | none |
| 6 | 26 | `fact migrate` registry with one documented slot (1.0.0 to 2.0.0, no automatic step) (M3 answer Q6) | implementation | - | none |
| 7 | 26 | Packaging: sdist excludes the root `.claude/`; `fact --version` prints the schema version | implementation | - | none |

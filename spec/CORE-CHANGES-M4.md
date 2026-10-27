# Core changes in M4

The current core-change ledger (D-018), continuing `spec/CORE-CHANGES-M3.md` from the end of round 25 (schemas 2.1.0, framework 0.1.0). What counts as core is defined in `spec/CORE-CHANGES-M2.md`.

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
| 8 | 27 | Documentation site: `mkdocs.yml`, `docs/_site/hooks.py`, quickstart, FAQ, `pages.yml`; SPEC toolset gains `fact probe render` and `fact quote` (the spec lagged the CLI) | documentation | - | none |
| 9 | 28 | Ossie export pinned to the core specification 0.2.0.dev0: flat document, `version`, field expressions and `datatype`, `relationships`, model-scoped metrics with `description`, `custom_extensions` (vendor `factmodel`) | implementation (the target's format, no framework key) | - | QCEW, Chinook |
| 10 | 28 | Tutorial `docs/tutorial/chinook.md` (tested on the installed wheel) and the owner's pilot kit (kept with the owner's working notes) | documentation | - | QCEW, Chinook |
| 11 | 29 | Ossie export defaults to the released core specification 0.1.1; `fact export --spec-version` keeps 0.2.0.dev0 | implementation (the target's format, no framework key); CLI option, additive | - | QCEW, Chinook |

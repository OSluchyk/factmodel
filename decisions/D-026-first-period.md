# D-026 A self-reference by period names its period field

Date: 2026-11-28 · Status: accepted
Platform that forced it: QCEW (published rows)

## Context

`annual.prior-year` and `qtrly.prior-year` join a row to the row of the same key one year earlier. The rows of the first year in a source have no earlier row there, whatever the source holds. To keep the probes in range the joins carried a literal, `year > 2024`, which is wrong the day an earlier year is loaded.

Two ways to remove the literal were considered. Declaring the loaded range on the source and referring to it from the join needs a reference syntax inside join expressions, which every reader of a join would have to resolve. Reading the first period from the data needs one field name on the relationship and touches the probe generator only.

## Decision

- A relationship may carry `first_period: <field>`. It applies to a self-reference.
- For such a relationship the probe generator leaves out, on the source side, the rows whose field equals the smallest value of that field in the table. The join expression itself is unchanged and holds no literal.
- The first period is read when the probe runs, so loading an earlier period needs no edit to the model.
- A join expression stays a condition, not a query (D-017): the subquery is written by the generator, never by a person.

## Consequences

- Schemas 2.4.0: one optional key on a relationship. Models written for 2.3.0 are valid as they are.
- QCEW: both prior-year relationships name `year`; the literal is gone; the probe counts are the same as with the literal.
- A period field compared as text must sort in period order; a four-digit year does.

## Evidence

- `tests/probes/test_bounds.py::test_first_period_is_read_from_the_data`: with 2023 loaded into the seeded table, the 2024 rows become source rows and every one finds its prior row, with no edit to the relationship.

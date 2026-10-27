# D-006 Data quality instead of a boolean

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

The first draft of the vocabulary defined probe evidence with `representative: true | false | unknown`. In YAML, unquoted `true` and `false` are booleans and `unknown` is a string, so one key holds two types. The vocabulary block had to quote the values, and every reader would have to handle both forms.

## Decision

The `representative` block is renamed `data_quality`, with the values `representative | synthetic | unknown`. Evidence from a probe carries `data_quality` (and `environment`) instead of `representative`.

## Consequences

- One type (a slug string) for the key, in YAML, JSON Schema and Python.
- `synthetic` names the common case (generated test data) directly instead of `false`.
- `spec/VOCABULARY.md`, `spec/SPEC.md` and the vocabulary tests are updated.

## Evidence

- Maintainer decision, 2026-10-23.

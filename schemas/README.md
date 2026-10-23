# Schemas

One JSON Schema (Draft 2020-12) per file kind in `vocabulary:file_kind`, plus `snapshot.schema.json` for engine-neutral metadata snapshots. Schema version: `0.1.0` (in each `$id`).

**These files are generated. Do not edit them by hand.**

## How they are made

- Templates: `src/factmodel/schemas/templates/<kind>.yaml`, plus `_common.yaml` for shared definitions.
- Renderer: `src/factmodel/schemas/build.py`.
- Every enumeration comes from `spec/VOCABULARY.md` through `factmodel.vocabulary`, never typed into a template:
  - `{$vocab: <block>}` renders as `{enum: [...]}` with the block's values.
  - `{$const: "<block>:<value>"}` renders as `{const: <value>}` and fails if the value is not in the block.
  - `$forbid: <block>` rejects every value of the block as a key (used for derived values).
- Shared definitions are copied into each schema's `$defs`, so every file is self-contained.

To change a list of values, edit `spec/VOCABULARY.md`. To change a shape, edit a template. Then render:

```bash
uv run python -m factmodel.schemas.build
```

`tests/test_schemas.py` fails when a committed file differs from a fresh render (`--check` does the same from the command line).

## Rules every schema follows

- `additionalProperties: false` everywhere except `extensions:`, a free map the core never reads.
- Derived keys (`vocabulary:derived_value`) are rejected in entities and relationships.
- The key `evidence` always holds evidence IDs; the key `records` always holds inline evidence records.
- Dates are `YYYY-MM-DD` strings. The strict loader (`factmodel.io.yaml_strict`) reads YAML dates as strings and fails on duplicate keys.

What a schema cannot check (references between files, unique IDs across the model, a rule's label being in the profile's labels, a nested field's `name` being the last segment of its `path`) is checked by the loader and the gate.

## Fixtures

`tests/fixtures/schemas/<kind>/valid/` holds examples that must pass. `tests/fixtures/schemas/<kind>/invalid/` holds files that must fail for exactly one reason: the file name names the reason, and a `# expect: <json path>` line names where the error must be reported.

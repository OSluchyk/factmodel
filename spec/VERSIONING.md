# Versioning

FactModel has two version numbers that move separately.

| Number | Where | What it versions |
| --- | --- | --- |
| Schema version | `$id` of every file in `schemas/` (`urn:factmodel:schema:<kind>:<version>`); `SCHEMA_VERSION` in `factmodel.schemas.build` | The contract: the file kinds, their keys and the vocabulary blocks the schemas read |
| Framework version | `version` in `pyproject.toml`; `fact --version` | The package: commands, gate stages, probes, adapters, documentation |

All schemas share one version. A framework release may leave the schema version as it is (a bug fix, a new command, a new adapter), and a schema change always comes with a framework release.

## Schema version rules

Semantic versioning, applied to the contract:

- **Major**: removing or renaming a key, a file kind or a vocabulary value; making an optional key required; narrowing what a key accepts. A model valid before may be invalid after.
- **Minor**: adding an optional key, a file kind or a vocabulary value; relaxing a rule. Every model valid before stays valid.
- **Patch**: fixing a description or an example. Validation does not change.

After the freeze (M2), D-018 says what a change needs:

- A **decision record** naming the platform that forced it, when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result.
- A **`CHANGELOG.md` entry and a line in `spec/CORE-CHANGES.md`**, when it adds an optional key, a vocabulary value or a probe kind.
- A **`CHANGELOG.md` entry** only, for a defect fix: code made to obey the existing schema.

Current schema version: **2.2.0**. 2.0.0 (D-019) was the semantic layer contract v1, which removes and renames layer keys; 2.1.0 (D-020) added the optional measure key `rollups` and the probe kind `rollup`; 2.2.0 adds the concept form `values_table`. Frozen 1.0.0 was the M2 gate. The next removal or rename of a key is **3.0.0**.

## `framework_version` in a model

`factmodel.yaml` carries `framework_version`, the framework release that created the model or last migrated it, and since 1.0.0 the optional `schema_version`, the schema version its files were last checked against. `fact init` writes both from the installed framework.

- The loader does not reject a model whose `framework_version` differs from the installed one; it validates the files against the installed schemas, and that verdict is what counts.
- `fact check` passes with a warning when a model's `schema_version` differs from the installed schemas and every file validates; nothing rewrites `schema_version` (only a future `fact migrate --apply` will).
- `fact migrate --root <dir>` reports the model's `framework_version` and `schema_version`, the installed framework and schema versions, the difference between the two schema versions (or that the model records none), and whether every model file validates against the installed schemas (`compatible`) or not (`not compatible`, with the files that fail). A model at 0.1.0 whose files validate is compatible. It changes nothing yet; it lists the registered steps between the two versions (`factmodel.migrate.MIGRATIONS`, one documented slot for 1.0.0 to 2.0.0 with no automatic step), and the first real migration goes there.
- Update `framework_version` and `schema_version` by hand, or with a future `fact migrate --apply`, only when the model has been checked with the newer framework.

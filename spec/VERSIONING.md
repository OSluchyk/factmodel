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

After the freeze (M2), every minor or major change needs a decision record that names the platform that forced it (`decisions/README.md`).

Current schema version: **0.1.0**. The freeze to 1.0.0 is the M2 gate. It waits for the owner's decision on the three changes without a record in `spec/CORE-CHANGES-M2.md`.

## `framework_version` in a model

`factmodel.yaml` carries `framework_version`, the framework release that created the model or last migrated it. `fact init` writes the installed version.

- The loader does not reject a model whose `framework_version` differs from the installed one; it validates the files against the installed schemas, and that verdict is what counts.
- `fact migrate --root <dir>` reports the model's `framework_version`, the installed framework and schema versions, and whether every model file validates against the installed schemas (`compatible`) or not (`not compatible`, with the files that fail). It changes nothing yet: migrations come with the first major schema change.
- Update `framework_version` by hand, or with a future `fact migrate --apply`, only when the model has been checked with the newer framework.

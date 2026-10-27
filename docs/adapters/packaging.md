# Packaging a third-party adapter

An adapter turns one kind of source into a snapshot (`schemas/snapshot.schema.json`), the only contract between adapters and the core (D-011). factmodel finds adapters through the Python entry-point group `factmodel.adapters`. The three built-in adapters (`export`, `sql`, `git`) register there exactly as a third-party package does, so adding one never needs a change to factmodel.

A working example lives in `tests/fixtures/plugin/` (package `factmodel-csvdir`): it reads a folder of CSV files as tables, header only. The tests install it into the development environment and check that `fact adapters` lists it and `fact snapshot` runs through it.

## 1. The protocol

An adapter is a class (or an instance) with:

| Member | Meaning |
|---|---|
| `name: str` | The adapter name, equal to the entry-point name. Sources name it in `adapter`. |
| `engines() -> list[str]` | Engines it reads, or `["*"]` for any engine. |
| `default_dialect(engine) -> str` | The sqlglot dialect probes render in for that engine. Use `factmodel.adapters.base.dialect_for(engine)` to take the vocabulary's default. |
| `snapshot(source, model_root) -> Snapshot` | Read the source and return a `factmodel.model.types.Snapshot`. |

See `factmodel.adapters.base.Adapter`.

Rules for `snapshot`:

- Read metadata, never data rows. A snapshot holds names, types, nullability, constraints and descriptions.
- Fill `type_class` on every field with `factmodel.adapters.types.type_class(type_text)` (D-013), unless your engine needs a mapping of its own.
- Set `enforced` on constraints from `factmodel.adapters.base.enforces_foreign_keys(engine)`, which reads the vocabulary. Do not decide it in code.
- Give the snapshot a pin. Warehouses use `warehouse_pin(engine, target, taken_on)`, which is `<engine>:<target>@<YYYY-MM-DD>`.
- Take secrets only from the environment variable the source names in `dsn_env`. Never write them to the snapshot, a log or an error message.
- Raise `factmodel.adapters.base.AdapterError` with a plain message when the source cannot be read as configured.

## 2. Register the entry point

In the package's `pyproject.toml`:

```toml
[project]
name = "factmodel-csvdir"
dependencies = ["factmodel"]

[project.entry-points."factmodel.adapters"]
csvdir = "factmodel_csvdir:CsvDirAdapter"
```

The entry-point name is the adapter name. The value is `module:attribute`; the attribute may be a class (factmodel instantiates it with no arguments) or a ready instance.

## 3. Install and check

```bash
uv pip install factmodel-csvdir      # or: uv pip install -e path/to/package
fact adapters
```

`fact adapters` lists every installed adapter with its engines and default dialects:

```text
csvdir  engines: csvdir  default dialects: csvdir=duckdb
export  engines: *  default dialects: ...
```

Then use it on a source:

```bash
fact source add --id codes --title "Code lists" --kind document --access-mode agent_read \
  --engine csvdir --adapter csvdir --location codes
fact snapshot --source codes
```

## 4. When the engine is new to the vocabulary

An engine factmodel has never seen works without any change, as long as the adapter returns a default dialect sqlglot knows. To make the engine a first-class name (its default dialect, whether it enforces foreign keys, how probes are run), propose a change to `spec/VOCABULARY.md`: the blocks `engine_dialect`, `engine_enforces_foreign_keys` and `dialect_runner`. Enforcement is measured, not assumed: include a test that inserts a row violating a declared foreign key (see `tests/adapters/test_duckdb.py`).

## 5. Test the package

At least:

- the entry point is found (`factmodel.adapters.registry.get("<name>")`);
- `snapshot` returns a `Snapshot` that validates and carries a pin;
- for a SQL engine, the neutral parts of a snapshot of a small schema agree with SQLite's (`tests/adapters/helpers.py: neutral`), and the generated probes return the same counts.

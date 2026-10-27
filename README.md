# FactModel

FactModel builds a model of a data platform in which every fact carries its evidence: a source, a pin and a status, with every derived value computed by code and checked by a gate. On top of that physical layer, semantic layers serve one use case each, and a layer counts as correct only when its consumer answers a corpus of questions the way the platform does. AI agents read sources, draft facts and write probes; people with access to the platform run them.

## What 0.1.0 contains

- **An engine-neutral core.** A loader, projection and scope, and a gate with twelve stages, all reading model files and metadata snapshots only.
- **Adapters.** `export` (you run the export SQL, the model reads the files), `sql` (SQLAlchemy; tested on SQLite, PostgreSQL and DuckDB) and `git` (DDL at a commit). Third parties can add their own through an entry-point registry.
- **Probes.** Data checks generated from the model and rendered per SQL dialect, returning counts only. Intake turns results into evidence and opens findings for results out of range.
- **Sync and drift.** New snapshots are compared with earlier ones and with the model. Each change is classified; new facts become drafts and lost ones become findings; triggers keep follow-ups from being forgotten.
- **Semantic layers and the equivalence harness.** A layer contract the gate checks, and a harness that proves a layer by running its consumer against reference SQL.
- **Release projection.** A pinned, checked, readable copy of a model for consumers, with append-only release notes.
- **Exporters.** dbt semantic models and metrics, and Apache Ossie 0.1.1. Each export lists what its target cannot hold.
- **Two example models.**
  - [Chinook](examples/chinook) (retail, on SQLite and PostgreSQL);
  - [QCEW](examples/qcew) (BLS employment and wages: no subject, code hierarchies, suppressed cells).

## Install

```bash
pip install "factmodel[sql,duckdb]"
```

or, in a uv project, `uv add "factmodel[sql,duckdb]"`. Python 3.12 or later. Add `[postgres]` for PostgreSQL.

## Quickstart

From an empty folder to a green gate (you need the `sqlite3` command line):

```bash
fact init shop --profile statistics
sqlite3 shop.db "CREATE TABLE region (code TEXT PRIMARY KEY, name TEXT); CREATE TABLE sales (region_code TEXT REFERENCES region (code), year INTEGER, amount INTEGER, PRIMARY KEY (region_code, year));"
export FACT_DSN_SHOP="sqlite:///$PWD/shop.db"
fact source add --root shop --id shop-db --title "Shop database" --kind warehouse --access-mode agent_read --engine sqlite --adapter sql --dsn-env FACT_DSN_SHOP
fact snapshot --root shop --source shop-db --date 2026-10-27
fact draft --root shop --source shop-db
cp shop/drafts/shop-db/entities/*.yaml shop/physical/entities/
fact project --root shop
fact check --root shop
```

The last line prints `gate: pass`. The [quickstart](docs/quickstart.md) explains each step. The [tutorial](docs/tutorial/chinook.md) goes on to probes, a proven layer, a release and two exports.

## Documentation

- [Specification](spec/SPEC.md) and [vocabulary](spec/VOCABULARY.md)
- [Algorithms](spec/ALGORITHMS.md), [versioning](spec/VERSIONING.md) and the [core-change ledger](spec/CORE-CHANGES.md)
- [Roadmap](spec/ROADMAP.md)
- [Decision records](decisions/README.md)
- [Examples](examples/)
- Documentation site: <https://osluchyk.github.io/factmodel/>. It is built from this repository and includes the CLI reference, the schema reference and one page per agent skill.

## Development

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy src
docker compose up -d --wait
FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
```

Without `FACT_PG_DSN`, the PostgreSQL tests are skipped. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

# FactModel

FactModel builds a model of a data platform in which every fact carries its evidence: a source, a pin and a status, with every derived value computed by code and checked by a gate. On top of that physical layer, semantic layers serve one use case each, and a layer counts as correct only when its consumer answers a corpus of questions the way the platform does. AI agents read sources, draft facts and write probes; people with access to the platform run them.

## Start here

```bash
pip install "factmodel[sql,duckdb]"
fact init tpch --profile statistics
fact check --root tpch
```

The last line prints `gate: pass` on an empty model. The [quickstart](docs/quickstart.md) fills it: nine steps from the eight TPC-H tables, which DuckDB builds without a single key, to proposed keys and joins and a green gate. Python 3.12 or later; add `[postgres]` for PostgreSQL.

- **Snapshots** read a source's metadata into one engine-neutral file, through the `export`, `sql` or `git` adapter ([spec](spec/SPEC.md), [adapter packaging](docs/adapters/packaging.md), [BigQuery adopters](docs/adopters/bigquery.md)).
- **Drafts and proposals** turn a snapshot into entity drafts, and measure a live source for key and join candidates when the catalog declares none ([algorithms, section 4](spec/ALGORITHMS.md)).
- **The gate** checks every file against its schema and twelve rules, from evidence to privacy ([vocabulary](spec/VOCABULARY.md)).
- **Probes** generate data checks from the model, render them per dialect and turn counts into evidence ([tutorial](docs/tutorial/chinook.md)).
- **Sync and drift** compare snapshots with each other and with the model, and classify every change ([TPC-H example](examples/tpch)).
- **Semantic layers** are proven by a consumer against a corpus, then released and exported to dbt and Apache Ossie ([exporters](docs/exporters/round-trip-notes.md), [decisions](decisions/README.md)).
- **Three example models**: [Chinook](examples/chinook) (retail, SQLite and PostgreSQL), [QCEW](examples/qcew) (BLS employment and wages: no subject, code hierarchies, suppressed cells) and [TPC-H](examples/tpch) (DuckDB: keys proposed from the rows, then declared and confirmed).

## What 0.1.0 contains

- **An engine-neutral core.** A loader, projection and scope, and a gate with twelve stages, all reading model files and metadata snapshots only.
- **Adapters.** `export` (you run the export SQL, the model reads the files), `sql` (SQLAlchemy; tested on SQLite, PostgreSQL and DuckDB) and `git` (DDL at a commit). Third parties can add their own through an entry-point registry.
- **Probes.** Data checks generated from the model and rendered per SQL dialect, returning counts only. Intake turns results into evidence and opens findings for results out of range.
- **Sync and drift.** New snapshots are compared with earlier ones and with the model. Each change is classified; new facts become drafts and lost ones become findings; triggers keep follow-ups from being forgotten.
- **Semantic layers and the equivalence harness.** A layer contract the gate checks, and a harness that proves a layer by running its consumer against reference SQL.
- **Release projection.** A pinned, checked, readable copy of a model for consumers, with append-only release notes.
- **Exporters.** dbt semantic models and metrics, and Apache Ossie 0.1.1. Each export lists what its target cannot hold.
- **Two example models**, [Chinook](examples/chinook) and [QCEW](examples/qcew); the TPC-H example and `fact propose` came after 0.1.0 (`CHANGELOG.md`).

## Documentation

- [Quickstart](docs/quickstart.md) (TPC-H) and [quickstart on SQLite](docs/quickstart-sqlite.md); [tutorial](docs/tutorial/chinook.md); [FAQ](docs/faq.md)
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

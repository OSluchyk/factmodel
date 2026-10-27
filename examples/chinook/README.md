# Chinook example

A full FactModel model of the Chinook schema (a digital media store), the reference example of M1 (D-011). It runs on two local reference engines, SQLite and PostgreSQL, with synthetic rows; no cloud engine and no credentials.

## What is here

| Path | What |
| --- | --- |
| `factmodel.yaml` | Profile `retail`; `anchor_entity: customer` (D-012). |
| `sources/` | `chinook-sqlite` and `chinook-pg` (adapter `sql`), `chinook-ddl` (adapter `git`, the DDL in this repository). |
| `sources/ddl/` | The schema in SQLite and PostgreSQL DDL, written by hand (`SOURCES.md` says why). |
| `sources/snapshots/` | The SQLite catalog and the DDL snapshots. The PostgreSQL one is taken in CI and compared, not committed. |
| `seed/seed.py` | Deterministic synthetic rows (`customer-0042`, `c0042@example.invalid`). |
| `drafts/` | What `fact draft` proposed from the SQLite catalog, before review. |
| `physical/entities/` | The reviewed model: classes, grains, meanings, the anchor reference on Invoice, the scope admission on InvoiceLine. |
| `probes/`, `evidence/probes/` | Generated probes, their results on SQLite, and the evidence intake wrote. |
| `semantic/customer-purchases/` | The layer (D-019) and its consumer `filter-sql`: revenue, tracks bought and active customers by genre, billing country and period. |
| `consumers/filter-sql/`, `semantic/customer-purchases/corpus/`, `equivalence/` | The reference consumer, its corpus of 31 items and the accepted run (D-021). |
| `release/allowlist.yaml` | What leaves the repository in a release (`fact release --out release/out --version <v>`; the output is gitignored). |
| `generated/` | Labels, scope and residue from `fact project`, and the equivalence report. |

## Expected shape

| Entity | Class | Scope |
| --- | --- | --- |
| Customer | data | anchor (`direct`) |
| Invoice | data | `direct` (CustomerId) |
| InvoiceLine | data | `transitive` through Invoice (`unique_target`) |
| Employee | administrative | `none` |
| Artist, Album, Track, Genre, MediaType, Playlist, PlaylistTrack | reference | `none` |

## Reproduce

From the framework root:

```bash
uv run python examples/chinook/seed/seed.py sqlite /tmp/chinook.db
export FACT_DSN_CHINOOK_SQLITE=sqlite:////tmp/chinook.db
uv run fact snapshot --root examples/chinook --source chinook-sqlite --date 2026-10-23
uv run fact probe run --root examples/chinook --source chinook-sqlite --environment local --data-quality synthetic --date 2026-10-23
uv run fact check --root examples/chinook
```

PostgreSQL (`docker compose up -d --wait` at the framework root, then `export FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres`): `uv run pytest -q tests/examples` seeds a fresh schema and checks that its snapshot and every probe count match SQLite.

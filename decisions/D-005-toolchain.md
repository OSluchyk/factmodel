# D-005 Toolchain

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

Agents and people must run the same checks with the same tools. The roadmap's technical baseline (`spec/ROADMAP.md`, section 2) names the tools; this record fixes which are runtime dependencies and which are optional.

## Decision

- **Python 3.12+**, managed with **uv**; PEP 621 metadata in `pyproject.toml`, hatchling as build backend.
- **Runtime dependencies:** Typer (CLI), ruamel.yaml (strict YAML that keeps comments and order), jsonschema (Draft 2020-12), pydantic v2 (typed models, parity-tested against the JSON Schemas), sqlglot (probes rendered per dialect, DDL parsing).
- **Dev group:** pytest, hypothesis, ruff (lint and format, line length 100, rules `E,F,I,B,UP,SIM,RUF`), mypy (strict on `src/factmodel`), pre-commit.
- **Extras:** engine clients are optional, added with their adapters: SQLAlchemy (`sql`), psycopg (`postgres`), DuckDB (`duckdb`).
- **CI:** GitHub Actions, one job on Python 3.12: `uv sync --locked`, ruff check, ruff format check, mypy, pytest.

## Consequences

- `uv.lock` is committed so CI and local runs resolve the same versions.
- Dev tools are a dependency group, not an extra.
- Ruff does not format Markdown; Python shown in the spec is illustrative.

## Evidence

- Maintainer decision, 2026-10-23.
- `spec/ROADMAP.md`, section 2 (technical baseline).

# D-005 Toolchain

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

Agents and people must run the same checks with the same tools. The plan's technical baseline (section 3) names the tools; this record fixes which are runtime dependencies now.

## Decision

- **Python 3.12+**, managed with **uv**; PEP 621 metadata in `pyproject.toml`, hatchling as build backend.
- **Runtime dependencies now:** Typer (CLI), ruamel.yaml (strict YAML that keeps comments and order), jsonschema (Draft 2020-12), pydantic v2 (typed models, parity-tested against the JSON Schemas).
- **Dev group:** pytest, hypothesis, ruff (lint and format, line length 100, rules `E,F,I,B,UP,SIM,RUF`), mypy (strict on `src/plumbline`), pre-commit.
- **Later:** sqlglot becomes a runtime dependency in M1. BigQuery and PostgreSQL clients are optional extras added with their adapters, not now.
- **CI:** GitHub Actions, one job on Python 3.12: `uv sync --locked`, ruff check, ruff format check, mypy, pytest.

## Consequences

- `uv.lock` is committed so CI and local runs resolve the same versions.
- No extras exist yet; the plan's WP0.1 line about `[bigquery]`, `[postgres]`, `[dev]` extras is superseded (dev tools are a dependency group, not an extra).
- Ruff does not format Markdown; Python shown in the spec is illustrative.

## Evidence

- Owner decision in the owner brief of 2026-10-23 on WP0.1 and WP0.2 (private working notes), section 3.
- `spec/IMPLEMENTATION_PLAN.md`, section 3.

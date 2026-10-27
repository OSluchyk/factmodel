# D-010 Name: FactModel

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

The earlier working name, Plumbline, was dropped because `plumbline` is taken on PyPI. It was also a metaphor (a builder's tool for checking a wall is true) that needed a paragraph to explain.

## Decision

- The product is **FactModel**.
- The Python distribution and import name is `factmodel`.
- The command is `fact`.
- The model-config file in a model repository is `factmodel.yaml`.

## Consequences

- The package lives in `src/factmodel/`.
- Environment flags for live adapter tests use the `FACT_` prefix (`FACT_LIVE_BQ`, `FACT_LIVE_PG`).
- `factmodel` must be registered on PyPI, or this record is superseded.

## Evidence

- Maintainer decision, 2026-10-23.
- 2026-10-23: `https://pypi.org/project/factmodel/` returned 404.
- 2026-10-23: GitHub checked by the maintainer.
- 2026-10-27: the PyPI simple index (`https://pypi.org/simple/factmodel/`) and the JSON API (`https://pypi.org/pypi/factmodel/json`) both return 404, so the name is free. The project page `https://pypi.org/project/factmodel/` answers 200 for any name (an anti-bot page, also for `typer`), so its status says nothing about a name.

# D-010 Name: FactModel

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

D-003 found `plumbline` taken on PyPI and chose the distribution name `plumbline-model` with the command `plb`. The name was a metaphor (a builder's tool for checking a wall is true) that needed a paragraph to explain. Nothing has been pushed or published yet, so a rename costs one round.

## Decision

- The product is **FactModel**.
- The Python distribution and import name is `factmodel`.
- The command is `fact`.
- The model-config file in a model repository is `factmodel.yaml`.
- `plumbline-model` and `plb` are retired.

This supersedes the name part of D-003. D-003's PyPI and GitHub findings stay valid history.

## Consequences

- The package moves from `src/plumbline/` to `src/factmodel/`. Paths in earlier decision records (D-003, D-004, D-005) read as `src/factmodel/` from this commit on; those records are not edited.
- Earlier decision records keep the old names as history.
- Environment flags for live adapter tests use the `FACT_` prefix (`FACT_LIVE_BQ`, `FACT_LIVE_PG`).
- `factmodel` must be registered on PyPI before WP4.1, or this record is superseded.
- GitHub and trademark checks are still open; the owner checks before the first public push.
- The folder is renamed by the owner after this commit (`~/AI/semantic/factmodel`).

## Evidence

- Maintainer decision, 2026-10-23.
- 2026-10-23: `https://pypi.org/project/factmodel/` returned 404.
- 2026-10-23: GitHub checked by the maintainer.
- 2026-10-27: the PyPI simple index (`https://pypi.org/simple/factmodel/`) and the JSON API (`https://pypi.org/pypi/factmodel/json`) both return 404, so the name is free. The project page `https://pypi.org/project/factmodel/` answers 200 for any name (an anti-bot page, also for `typer`), so its status says nothing about a name.

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
- Earlier round reports, the round 1 brief and past `CHANGELOG.md` entries keep the old names as history.
- Environment flags for live adapter tests use the `FACT_` prefix (`FACT_LIVE_BQ`, `FACT_LIVE_PG`).
- `factmodel` must be registered on PyPI before WP4.1, or this record is superseded.
- GitHub and trademark checks are still open; the owner checks before the first public push.
- The folder is renamed by the owner after this commit (`~/AI/semantic/factmodel`).

## Evidence

- Owner decision in the owner brief of 2026-10-23 on the rename to FactModel (private working notes), section 1.
- `https://pypi.org/project/factmodel/` returned 404 on 2026-10-23 (owner check, recorded in the brief; not re-checked in this round).
- GitHub: not checked.
- 2026-10-27 (round 26, one HEAD request by the agent): `https://pypi.org/project/factmodel/` returned 200, so a project page of that name now exists. Who owns it was not read. The owner decides before publishing (round 26 report of 2026-10-27, private working notes).
- 2026-10-27 (reviewer check, correcting the line above): `https://pypi.org/project/factmodel/` returns 200 for any name, because it serves an anti-bot "Client Challenge" page (it does so for `typer` too), so its status says nothing about the name. `https://pypi.org/simple/factmodel/` and `https://pypi.org/pypi/factmodel/json` both return 404: the name is free. The owner keeps the name and publishes 0.1.0 to hold it.

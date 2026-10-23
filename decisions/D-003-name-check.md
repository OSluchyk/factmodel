# D-003 Name check: distribution name `plumbline-model`

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

The spec leaves the package-name check open before M1. The brief asks for evidence from PyPI and from a GitHub search for `plumbline` repositories that are data or schema tools. A trademark search is not part of this record.

## Decision

- The name `plumbline` is taken on PyPI by an unrelated project.
- The distribution name is `plumbline-model`. The import name stays `plumbline`, and the command stays `plb`.
- The project name in prose stays "Plumbline".

## Consequences

- `pip install plumbline-model` / `uv add plumbline-model`; `import plumbline`.
- `pyproject.toml` uses `name = "plumbline-model"`.
- `plumbline-model` must be registered on PyPI before WP4.1, or this record is superseded.
- Several GitHub projects use the name for AI-agent and data-checking tools (below). None is a semantic-model or schema framework of this kind, but two are close in spirit. The owner should weigh this before the first public push; a rename would be a new record.
- Trademark search is still open (spec, Open questions).

## Evidence

All read on 2026-10-23 through the public PyPI JSON API and the GitHub repository search API.

**PyPI**

- `https://pypi.org/project/plumbline/` - exists. Version 0.0.6, summary "Python for comparing EPT and DEM data", home `https://github.com/hobu/plumbline`, last upload 2021-09-29. Geospatial, unrelated.
- `https://pypi.org/project/plumbline-model/` - 404, free.
- `https://pypi.org/project/plumbline-sl/` - 404, free.

**GitHub** (`https://github.com/search?q=plumbline&type=repositories`, about 200 results)

Data or schema tools:

- `https://github.com/beej41031-max/plumbline` - "Evidence-based survey tool for Postgres and Supabase", 0 stars. Closest in purpose.
- `https://github.com/mark124/plumbline` - checks AI-written data code against a DataHub catalog, 0 stars.
- `https://github.com/jpmcdonald/plumbline` - data validation for AI agents, 0 stars.
- `https://github.com/TMHSDigital/plumbline` - checks calibration of decision-model probabilities, 0 stars.

Searches for `plumbline semantic`, `plumbline warehouse` and `plumbline dbt` returned no repositories.

AI-agent tools with the same name (not data tools, but the same audience):

- `https://github.com/ActaClad/plumbline` - analyzer for LLM and agentic systems, 30 stars.
- `https://github.com/nickyfactz/plumbline` - workflow plugin for Codex and Claude Code, 28 stars.
- `https://github.com/EmilioCarrion/plumbline` - verification infrastructure for AI-assisted work, 5 stars.

# Changelog

Newest first. Every entry says why, not only what.

## 0.0.1 - 2026-10-23 - WP0.1 Repository bootstrap, WP0.2 Core vocabulary

**Why.** The repository held only the specification and the plan. Later work packages need a project that installs, lints, type-checks and tests, and a fixed vocabulary that every schema will share, before any schema is written.

- Bootstrap the Python project: `src/plumbline/` layout (D-004), `uv`, Typer, ruamel.yaml, jsonschema and pydantic v2 (D-005), CI and pre-commit hooks, `plb --version`.
- License the framework under Apache 2.0 (D-001).
- Publish under the distribution name `plumbline-model`, keeping the import name `plumbline`, because `plumbline` is taken on PyPI (D-003).
- Add `spec/VOCABULARY.md` with machine-readable enumeration blocks, and `plumbline.vocabulary` to load them, so later schemas have one source for every list.
- Make relationship identity an author-set key, never a list position (D-002).
- Align the spec and plan wording with the vocabulary; see the round report for each edit.

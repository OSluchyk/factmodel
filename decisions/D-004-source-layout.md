# D-004 Source layout: `src/plumbline/`

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

A Python package can sit at the repository root (`plumbline/`) or under `src/` (`src/plumbline/`). With a root layout, running tests from the repository root imports the package from the working directory, not the installed copy, so missing package data or a broken install can pass unnoticed.

## Decision

The package lives in `src/plumbline/`. Tests import only the installed package (`uv sync` installs it in editable mode).

## Consequences

- Tests cannot import the package from the working directory by accident; they see what users see.
- Files the package needs at run time must be shipped explicitly. `spec/VOCABULARY.md` is copied into the wheel as `plumbline/VOCABULARY.md` (`pyproject.toml`, `force-include`), and `plumbline.vocabulary` falls back to the source tree in an editable install.
- `spec/SPEC.md` already shows `src/plumbline/` in its repository layout.

## Evidence

- Maintainer decision, 2026-10-23.
- Python Packaging User Guide, "src layout vs flat layout" (`https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/`), general knowledge, not re-read in this round.

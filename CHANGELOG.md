# Changelog

Newest first. Every entry says why, not only what.

## Unreleased - 2026-10-23 - Round 4: WP1.1 Model loader

**Why.** The gate, the projection and every command read the same model. One loader that finds every problem at once, and says where and how to fix it, keeps those parts simple and gives agents an error they can act on.

- Add `factmodel.model.loader`: discovers model files, validates them against their schemas, checks references between files (entities, evidence, sources, fields, joins, registers, profile labels) and returns a typed `Model` with every issue.
- Each issue has file, line, column, gate stage and a fix hint.
- Add typed pydantic models for every kind; a parity test checks they agree with the JSON Schemas on every schema fixture.

## Unreleased - 2026-10-23 - Round 3: WP0.4 Algorithms, WP0.5 spec-v0.1

**Why.** The core's three algorithms must be exact before code exists, so that the code is checked against the spec and not the other way round. The test vectors are that check, written by hand from the text.

- Add `spec/ALGORITHMS.md`: projection with rule 0, subject scope closure (D-007) with admission rejections and reachability, release partition.
- Add 21 test vectors in `tests/vectors/` and a test that every vector input is valid and every expected output covers its input.
- Release key lists are `keep` and `drop` per kind, so an undeclared key fails closed.
- New vocabulary blocks `admission_rejection` and `release_failure`.
- **spec-v0.1**: `spec/SPEC.md` and `spec/VOCABULARY.md` are version 0.1, with links to the vocabulary, algorithms and schemas. The owner creates the git tag.

## Unreleased - 2026-10-23 - Round 2: WP0.3 JSON Schemas

**Why.** Every later piece (loader, gate, adapters) needs a normative shape for each file kind, and the shapes must not drift from the vocabulary. Three round-1 choices would have made the schemas awkward: a boolean-or-string field, an authored scope checked against a computed one, and a status block named for entities only.

- Record D-006 (`data_quality` instead of `representative`), D-007 (subject scope is derived; `anchor_reference` and `scope_admission` are authored) and D-009 (`review_status` for entities and layers), and apply them to the vocabulary, spec and plan.
- Add `schemas/` for every file kind plus the metadata snapshot, rendered by `factmodel.schemas.build` from templates and the vocabulary, so enumerations have one source.
- Add valid and invalid fixtures for every kind; each invalid fixture fails for one named reason at one path.
- Add `factmodel.io.yaml_strict`: duplicate keys fail, dates stay strings, nodes keep their positions.
- Inline evidence records move under `records:`; `evidence:` always holds IDs.

## 0.0.1 - 2026-10-23 - Round 2a: rename to FactModel, agent commits per round

**Why.** The name should say what the thing is - a model made of proven facts - instead of a metaphor that needs a paragraph; nothing was public yet, so the rename was cheap now and expensive later. Committing by hand after each round added owner work without adding review.

- Rename Plumbline to FactModel: distribution and import `factmodel`, command `fact`, model config `factmodel.yaml`, package in `src/factmodel/` (D-010). Earlier decision records, round reports and changelog entries keep the old names as history.
- The agent commits once per round and never pushes, amends or adds attribution lines; `AGENTS.md` rule 4 and the round workflow docs changed to match (D-008).

## 0.0.1 - 2026-10-23 - WP0.1 Repository bootstrap, WP0.2 Core vocabulary

**Why.** The repository held only the specification and the plan. Later work packages need a project that installs, lints, type-checks and tests, and a fixed vocabulary that every schema will share, before any schema is written.

- Bootstrap the Python project: `src/plumbline/` layout (D-004), `uv`, Typer, ruamel.yaml, jsonschema and pydantic v2 (D-005), CI and pre-commit hooks, `plb --version`.
- License the framework under Apache 2.0 (D-001).
- Publish under the distribution name `plumbline-model`, keeping the import name `plumbline`, because `plumbline` is taken on PyPI (D-003).
- Add `spec/VOCABULARY.md` with machine-readable enumeration blocks, and `plumbline.vocabulary` to load them, so later schemas have one source for every list.
- Make relationship identity an author-set key, never a list position (D-002).
- Align the spec and plan wording with the vocabulary; see the round report for each edit.

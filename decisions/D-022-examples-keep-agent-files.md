# D-022 Example models keep their agent files in the public tree

Date: 2026-11-02 · Status: accepted
Platform that forced it: none (the TPC-H example, the third one)

## Context

`fact init` writes `AGENTS.md`, `agent/brief.md`, `agent/report.md` and `.claude/skills/` (a copy of `agent/skills/`) into every model repository. The three example models carry these files, so the public tree holds four copies of each skill. The question was whether the examples should drop them to avoid the duplication.

## Decision

The examples keep them. An example is a model repository exactly as `fact init` makes it, and the reader of the article or the tutorial compares their own repository with it file for file; a repository that lacks the agent files is not what `fact init` produces. The copies are kept identical to `agent/skills/` by a test (`tests/examples/test_agent_files.py`), so the duplication cannot drift. The owner's local agent folder at the framework root (`/.claude/`) is a different thing: it is not part of the framework and stays out of releases (`pyproject.toml`, sdist exclude).

## Consequences

- A change to a skill is made once in `agent/skills/` and copied to every example; the test fails until the copies match.
- `fact init` keeps writing `.claude/skills/`; a model repository that uses another agent tool reads `AGENTS.md` and `agent/skills/` through the package.

## Evidence

- Maintainer decision, 2026-11-02.
- `examples/*/.claude/skills/` compared with `agent/skills/`: identical on 2026-11-02.

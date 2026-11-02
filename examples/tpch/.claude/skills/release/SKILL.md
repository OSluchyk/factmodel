---
name: release
description: Build and check a release of a model - the readable copy consumers use - with the allowlist, VERSION and append-only release notes. Use when the owner asks for a release or a consumer needs a pinned copy.
---

# release

## When to use

The owner asks for a release, or a layer became `reviewed` and its consumers need a pinned copy.

## Inputs

- The model repository and the release version the owner names (for example `0.2.0`).
- `release/allowlist.yaml`: which files leave the repository and which keys projected files keep.

## Steps

1. `fact check --root <dir>` must pass; a release is never built from a failing model.
2. For every `reviewed` layer, the last equivalence run must not drop against the accepted one (`fact equivalence run --root <dir> --layer <id>`; the owner accepts with `fact equivalence accept`). A drop refuses the release.
3. Build: `fact release --root <dir> --out <dir>/release/out --version <version>`. Every file gets exactly one disposition (export, project, refuse); an unmatched file, a projected file of a kind without a key list, an undeclared key, or an unclosed internal block refuses the release. Lines between `internal:begin` and `internal:end` never leave the repository.
4. Check: `fact check --release <out> --previous <previous release folder>`. Earlier sections of `RELEASE_NOTES.md` must stay byte for byte; a version's section is written once.
5. Hand the folder to the owner; publishing it is a step only the owner takes.

## Rules

- Never edit a file in the release folder by hand; change the model and rebuild.
- Never widen the allowlist to make a release pass; an undeclared key is a decision for the owner.
- Personal data and connection strings never enter a model, so they cannot enter a release; the release gate runs `privacy` again.

## Report

The version, the counts per disposition, the release gate output, and any refusal with its reason.

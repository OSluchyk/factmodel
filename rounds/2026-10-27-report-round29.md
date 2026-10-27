# Report - Round 29: D-010 evidence correction, Ossie 0.1.1 pin, kit step

Date: 2026-10-27 · Brief: the owner's round-29 message (rounds 26 to 28 accepted) · Branch `main`, from `a2dd946`

## 1. Outcome

D-010 now records that the PyPI name `factmodel` is free, and the Ossie export defaults to the released core specification 0.1.1, with the 0.2.0.dev0 draft behind `fact export --spec-version`. The pilot kit removes the seed's probe evidence after the real intake; the block was dry-run on the stand-in file.

Tests: **779 + 1 skipped before, 782 + 1 skipped after** (with PostgreSQL); without it, 773 + 7 skipped before and 776 + 7 skipped after.

## 2. Files

Created:

- This report.

Updated:

- `decisions/D-010-name-factmodel.md` (one dated evidence line appended; the earlier lines unchanged)
- `rounds/2026-10-27-report-wp4.1.md` (a correction section appended), `rounds/2026-10-27-report-m4-kit-final.md` (a correction note under question 1)
- `src/factmodel/export/ossie.py` (two pinned versions, default 0.1.1), `src/factmodel/cli.py` (`fact export --spec-version`)
- `tests/export/test_export.py` (the structure test for both versions; a test for the default and the option)
- `docs/exporters/round-trip-notes.md` (both versions)
- `docs/pilot/qcew-real-data.md` (step 4: the seed-evidence block)
- `spec/SPEC.md`, `spec/IMPLEMENTATION_PLAN.md`, `spec/CORE-CHANGES-M4.md`, `CHANGELOG.md`

## 3. Verification

```text
$ curl -sS -o $S/ossie011/spec.md -w "%{http_code} %{size_download}\n" https://raw.githubusercontent.com/apache/ossie/osi-0.1.1-rc1/core-spec/spec.md
200 14944
(read 2026-10-27T12:46Z; the only network read of the round; URL given by the owner)

Before (at a2dd946):
$ FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
779 passed, 1 skipped in 92.90s (0:01:32)
$ uv run pytest -q
773 passed, 7 skipped in 91.25s (0:01:31)

After:
$ uv run ruff check .
All checks passed!
$ uv run ruff format --check .
130 files already formatted
$ uv run mypy src
Success: no issues found in 65 source files
$ FACT_PG_DSN=postgresql://postgres@localhost:55432/postgres uv run pytest -q
782 passed, 1 skipped in 94.14s (0:01:34)
$ uv run pytest -q   (no PostgreSQL)
776 passed, 7 skipped in 92.81s (0:01:32)
$ uv run mkdocs build --strict --site-dir <tmp>
INFO    -  Documentation built in 1.23 seconds
$ uv run fact check --root examples/chinook
gate: pass
$ uv run fact check --root examples/qcew
gate: pass
```

Pilot kit dry run. Every block of the page ran in order, as in round 28:
- `HOME` pointed at a scratch folder and `QCEW_DB` at the stand-in (the seed in `annual_2024`, `annual_2025`, `qtrly_2025`); the owner's folders were not touched.
- A `date` shim returned 2026-11-02, so the real intake does not share a file name with the seed's 2026-10-27 evidence, as it would not for the owner on a later day.

```text
42 in range, 5 out of range, 0 failed, 0 rejected; 91 files written
gate: pass
49 seed probe records removed; 49 files deleted, 15 edited
gate: pass
open findings: 11
employment-wages: 36 pass, 0 fail, 2 error of 38
share 1.000, threshold 0.9: proven
employment-wages: accepted
gate: pass
```

What the removal commit holds (`git show ba499d8` in the dry-run model): 64 files, 1 insertion, 716 deletions.
- The 49 deleted files are all `evidence/probes/*@2026-10-27.yaml`.
- Every other changed line removes one seed citation, apart from one flow list: `[ev-doc-r1, ev-key-duplicates-area-titles-2026-10-27]` became `[ev-doc-r1]`.
- Afterwards no record with `data_quality: synthetic` is left. The 27 document records and the 7 entities' catalog records (source `qcew-sqlite`) stay.

## 4. Spec edits

- `spec/SPEC.md`, open questions:
  - Old: "Ossie pinned to the core specification 0.2.0.dev0 (a draft, read in round 28), structural tests because no JSON Schema is published."
  - New: "Ossie pinned to the released core specification 0.1.1 by default (read in round 29) and to the 0.2.0.dev0 draft behind `--spec-version` (read in round 28); structural tests, because no JSON Schema is published."
- `spec/SPEC.md`, sources:
  - Old: "core specification 0.2.0.dev0: https://github.com/apache/ossie/blob/main/core-spec/spec.md (read 2026-10-27)"
  - New: "core specification 0.1.1: https://github.com/apache/ossie/blob/osi-0.1.1-rc1/core-spec/spec.md and 0.2.0.dev0: https://github.com/apache/ossie/blob/main/core-spec/spec.md (both read 2026-10-27)"
- `spec/IMPLEMENTATION_PLAN.md`, WP3.5:
  - Appended: "Round 29 read the released 0.1.1 once and made it the default; 0.2.0.dev0 stays behind `--spec-version`."
- `spec/CORE-CHANGES-M4.md`: row 11, the Ossie default and the CLI option.

## 5. Confirmed / inferred / unknown

**Confirmed**

- **The 0.1.1 document.** It states "Version: 0.1.1", and its version history gives 0.1.1 (2025-12-11) as the initial release. Its title is "OSI - Core Metadata Specification", the name before Apache.
- **0.1.1's shape.** A `semantic_model` list, no `version` key, no field `datatype`.
  - The dialect enumeration is `ANSI_SQL`, `SNOWFLAKE`, `MDX`, `TABLEAU`, `DATABRICKS`, `MAQL`, and fields must use one of them.
  - The vendor enumeration is `COMMON`, `SNOWFLAKE`, `SALESFORCE`, `DBT`, `DATABRICKS`, `GOODDATA`, and extensions must use one of them.
  - Keys and relationship columns name columns.
- **The export, both versions.** It writes only keys the pinned document names, every reference resolves, and every expression parses in its dialect (tests, both examples).
- **The CLI.** `--spec-version` rejects an unknown version (exit 1) and any target other than `ossie` (exit 2).
- **D-010.** The earlier lines are unchanged; the correction follows them.

**Inferred**

- **Tag `osi-0.1.1-rc1` as the released 0.1.1.** The owner gave the URL. The tag name says release candidate 1, while the document says 0.1.1 and calls it the initial release.
- **Engines outside the 0.1.1 enumeration.** DuckDB, SQLite and PostgreSQL are not in it, so their expressions are written once as sqlglot's neutral SQL under `ANSI_SQL`.
- **The vendor for the framework's metadata.** `factmodel` is not in 0.1.1's vendor enumeration, so it travels under `COMMON`, inside a `factmodel` key in the JSON.
- **The D-018 class.** The default change is implementation: the target's format, no framework key. The CLI option is additive. No decision record.
- **Rewriting edited files.** The kit's removal script rewrites only the files it changes, with the YAML settings `fact probe intake` uses, and keeps a file's `null` style. The first dry run showed a re-wrap and a `null` change.

**Unknown**

- Whether Ossie will publish 0.1.1 under a tag without `-rc1`.

## 6. Divergences

- **The read's URL came from the owner.** The brief did not name it, and the saved 0.2.0.dev0 text names no tag; I asked, so that a guess would not spend the one read.
- **The final report's owner steps.** The M4 final report's step list (section 11, item 8) does not mention the new removal block; the kit page does. Only question 1 of that report was to change.

## 7. Questions for the next round

1. When Ossie tags 0.1.1 without `-rc1`, or publishes a JSON Schema, should the pin move (one read)?

## 8. Commit

Committed on `main` as `Round 29: D-010 evidence correction, Ossie 0.1.1 pin, kit step` with every file in section 2. The untracked `.claude/` folder is not committed.

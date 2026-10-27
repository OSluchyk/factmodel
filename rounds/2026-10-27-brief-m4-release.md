# Brief - Rounds 26 to 28: M4 packaging, docs, tutorial, pilot kit (continuous run)

Date: 2026-10-27 · Owner: Oleksandr Sluchyk · Status: approved
Repository: `~/AI/semantic/factmodel`, branch `main`, start at `85494ea` (M3 done on synthetic corpora, schemas 2.1.0, framework 0.1.0).
Read first: `AGENTS.md`, `spec/IMPLEMENTATION_PLAN.md` section 9, `spec/VERSIONING.md`, `decisions/D-018`, `rounds/2026-10-27-report-m3-final.md` sections 8 to 11, `docs/` as it stands.

## 0. Goal

M4 makes the framework installable, documented and teachable, and prepares the one thing the agent cannot do: the pilot on the owner's real QCEW data, which closes the SPEC's M3 gate (a real corpus) and the plan's M4 gate. The agent's three rounds end with a pilot kit; the owner runs the pilot; a short round afterwards records its results and sets version 1.0.0. The framework version stays 0.1.0 until then.

Owner-run, never the agent: pushing, publishing to PyPI, enabling GitHub Pages, every query against the real data.

## 1. Mode

Three rounds, as before: clean tree at each round start; green checks with PostgreSQL through `docker compose`; a round report; a `CHANGELOG.md` entry with the why; one commit per round; no push, no tag, no amend, no attribution lines. `UV_PROJECT_ENVIRONMENT=.venv`. Leave `.claude/` alone. Network: package installs, plus two single reads: `https://pypi.org/project/factmodel/` (name re-check, D-010) in round 26, and the Apache Ossie core specification document once in round 28 (question 3 of the M3 report; record URL, version or "not stated", read date). No other network use; `dbt` runs with its version check and tracking off.

After round 28 write `rounds/<date>-report-m4-kit-final.md` and stop.

## 2. Round 26 - WP4.1 Packaging, and the M3 "can wait" answers

- Name re-check: one HEAD or GET of the PyPI page; record the result in the round report and in D-010's evidence section as a dated line (do not edit the decision text).
- Build: `uv build` produces wheel and sdist; `twine check` (dev dependency) passes; the wheel ships the vocabulary, schema templates, `gate.yaml`, profiles, agent templates and skills; extras `[sql]`, `[postgres]`, `[duckdb]`; `fact --version` prints package and schema versions.
- Clean-room install test (a test, not a script): a fresh virtual environment outside the repository, install the built wheel only, then on a copy of `examples/chinook`: `fact check`, `fact project`, `fact probe generate`, `fact equivalence run` on SQLite, `fact release --out`, `fact check --release`, `fact export --target dbt`. Nothing may import from the source tree.
- M3 answers, each a ledger line under D-018 unless the rule says decision:
  - Q1 yes: the release carries a derived file `semantic/<layer>/generated/joins.tsv` (relationship key, source, target, resolved join condition), written by `fact project`, never authored; the `derived-not-authored` stage covers it.
  - Q2 yes: a concept may be table-valued (`values_table`: rows of named columns, from a code list or written in the layer); the QCEW layer gets the A4 level matrix as `level_matrix`; the consumer uses it instead of deriving `agglvl_code`. Additive.
  - Q4 yes: the dbt exporter emits `derived` metrics for formula measures when the formula is an expression over other exported metrics; what it still cannot express stays in `EXPORT_NOTES.md`.
  - Q5 yes: `RELEASE_NOTES.md` is committed in the model repository and `fact release` appends to it; the release copies it. Update both examples.
  - Q6 no migration is written; `fact migrate` gets a registry with one documented empty slot so the first real migration has a place.

Commit `WP4.1: packaging, clean-room install, M3 answers`.

## 3. Round 27 - WP4.2 Documentation site

- MkDocs Material (dev dependency). Sources: `spec/` (the spec, vocabulary, algorithms, versioning, plan as "roadmap"), `docs/` (adopters, adapters, dogfood, export notes), `decisions/` (one page, the index with each record), skills (one page per skill, rendered from `agent/skills/*/SKILL.md`), CLI reference generated from Typer (every command and option, with one example each), schema reference generated from the JSON Schemas (one page per file kind: keys, types, required, description), a quickstart (init to first green gate in ten commands), FAQ (the questions the round reports asked and the answers).
- `mkdocs build --strict` passes locally and in CI; a `pages.yml` workflow builds the site on push to `main` (the owner enables GitHub Pages).
- Content comes from the existing files, not a rewrite: generated pages and short index pages only; where a spec section is out of date with the code, fix the spec, not the site.

Commit `WP4.2: documentation site`.

## 4. Round 28 - WP4.3 Tutorial, pilot kit, Ossie pin

- Tutorial `docs/tutorial/chinook.md`: from an empty folder to a release and an export, every step a command; a test runs every command block in order on a temporary copy and compares the outputs it promises (gate verdicts, residue 0, equivalence verdict). The tutorial uses the installed package only.
- Pilot kit `docs/pilot/qcew-real-data.md`, written for the owner, English, plain:
  1. Create the standalone model `~/AI/semantic/qcew-semantic-model/model/` from the installed wheel: `fact init --profile statistics`, then copy the physical layer, the layer and the consumer from `examples/qcew` (one command block; say what is copied and why the model still has to re-snapshot).
  2. Sources: `qcew-duckdb` (adapter `sql`, engine `duckdb`, `dsn_env: FACT_DSN_QCEW`, pointing at the owner's `qcew.duckdb` with its per-year tables; the kit gives the two views `annual` and `qtrly` the owner creates as `UNION ALL` over the yearly tables so the physical layer applies unchanged) plus the BLS document sources and the real code lists.
  3. `fact snapshot`, `fact sync`, the drift report: what differs between the seed-shaped DDL and the real catalog.
  4. `fact probe generate` and `fact probe render --dialect duckdb`: the owner runs the script, returns counts; `fact probe intake`; `treat_synthetic_as_representative` absent, so every result is `representative`. Expected: R1 4,649 duplicates, V1 the `-` counts per quarter from `profile.md` Q07, G2 the padding, rollups with real M5 and H5 counts.
  5. The real corpus: 30 questions the owner writes with reference SQL, kept outside the repository, referenced by pin; `fact equivalence script` for an owner-run comparison; `fact equivalence accept` when the threshold holds; failures become findings.
  6. What to send back for the acceptance round: `git log`, `fact status`, the equivalence report, the probe results folder.
- Ossie: one read of the core specification document; pin version and date; move what the document names into real keys of the export; what it does not name stays in `ai_context`; update `EXPORT_NOTES.md`.
- `spec/SPEC.md` roadmap and the plan: M4 "kit done, pilot pending"; the M3 real-corpus caveat points at the pilot.

Commit `WP4.3: tutorial, pilot kit, Ossie pin`.

## 5. After the run (owner)

1. Push `main`; confirm CI green (lint, types, tests with the PostgreSQL service, both example gates, `mkdocs build --strict`); enable GitHub Pages for `pages.yml`.
2. Run the pilot from `docs/pilot/qcew-real-data.md`; return the items of step 6.
3. Then a short round 29 (next brief): record the pilot results as findings and evidence in `examples/qcew` where they are general, version 1.0.0, release notes for 1.0.0, `uv build`; the owner publishes.

## 6. Stop conditions

- Credentials, network beyond section 1, or a query against any remote platform or the owner's real data.
- A contract change that D-018's rule classes as a decision: stop, do not invent D-022.
- Any check cannot be made green without weakening a test or a rule.
- The working tree is not clean at a round start.

Not stop conditions: PyPI name taken since D-010 (report; the owner decides); the Ossie document unreachable (keep the pinned page, say so); `twine` or MkDocs needing a plugin that is a plain package install.

## 7. Final report

`rounds/<date>-report-m4-kit-final.md`: outcome, git log, acceptance per round, the clean-room install log, the tutorial test result, spec and vocabulary edits, ledger lines, confirmed / inferred / unknown, divergences, questions, and the exact owner steps for the pilot in the order to run them.

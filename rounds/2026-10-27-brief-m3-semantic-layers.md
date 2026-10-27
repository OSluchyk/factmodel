# Brief - Rounds 20 to 25: M3 semantic layers, equivalence, release, export (continuous run)

Date: 2026-10-27 · Owner: Oleksandr Sluchyk · Status: approved
Repository: `~/AI/semantic/factmodel`, branch `main`, start at `61f9112` (schemas 1.0.0, M2 done).
Read first: `AGENTS.md`, `spec/SPEC.md` (semantic layer, consumer, release, security), `spec/VOCABULARY.md` section 9 and the release and export blocks, `spec/IMPLEMENTATION_PLAN.md` section 8, `spec/VERSIONING.md`, `decisions/D-018`, `rounds/2026-10-27-report-m2-final.md` section 10, both examples' registers.

## 0. Goal

M3 proves the second half of the framework: a semantic layer built only on physical facts by ID, a consumer that uses it, and an equivalence corpus that says whether the consumer answers like the platform. QCEW is the hard case: a correct answer needs the disclosure filter, the level discriminator, the distinct-area join and measures from monthly levels. A consumer that sums suppressed rows as zeros is wrong, and the layer must make that impossible to miss. Chinook is the second consumer. The run ends with release projection and two exporters.

Decisions this brief pre-approves (record each in the round that needs it, with the platform that forced it):

- **D-019 Semantic layer contract v1** (round 20): the layer and consumer schemas get their final v1 shape (section 2). Where that removes, renames or changes the meaning of a 1.0.0 key, D-019 is the record and the schemas go to 1.1.0 if additive, 2.0.0 if not; D-018's rule decides which. Platform: QCEW and Chinook.
- **D-020 Rollup probe kind** (round 22): `rollup` compares a parent row's measure with the sum of its children, counting suppressed children; closes QCEW F-0007 and checks M5 and H-0001. Additive probe kind: ledger line, but the record exists because it changes what "confirmed" means for a hierarchy. Platform: QCEW.
- **D-021 Equivalence threshold** (round 23): a consumer proves a layer when at least 90 percent of corpus items pass in `same_rows` or `same_predicate`, no item regresses against the last accepted run (`equivalence/accepted.json`, committed), and every failing item has a finding or a `known_gap` entry with a reason. The owner may lower or raise the floor per consumer in `consumer.yaml` (`threshold`). Platform: none.

Owner-pending inputs, not blocking: the BLS County-MSA-CSA crosswalk and the NAICS hierarchy crosswalk may be added under D-016 if the owner places them in `~/AI/semantic/qcew-semantic-model/qcew-model/data/raw/`; if present at round 22, use them to resolve F-0009 and `to-supersector`, otherwise leave those `unresolved`.

## 1. Mode

Six rounds, as before: clean tree at each round start; green checks with PostgreSQL through `docker compose`; a round report; a `CHANGELOG.md` entry with the why; one commit per round; no push, no tag, no amend, no attribution lines. `UV_PROJECT_ENVIRONMENT=.venv`. Leave `.claude/` alone. Network: package installs, plus one read of the Apache Ossie specification page to pin its version in round 25 (record the URL, the version and the read date in the exporter's docstring and the report).

Round 20 also: framework version to `0.1.0` (M2 closed; 1.0.0 is M4), `fact check` warns, not fails, when a model's `schema_version` differs from the installed schemas while every file validates; nothing rewrites `schema_version` automatically (only a future `fact migrate --apply`).

After round 25 write `rounds/<date>-report-m3-final.md` and stop.

## 2. Round 20 - WP3.1 Semantic layer contract (D-019)

Layer file `semantic/<layer-id>/layer.yaml`:

- `id`, `purpose`, `consumer`, `status` (`review_status`), `evidence` and `records` as today.
- `entities`: the physical entity ids the layer reads; each with the `current_row_rule` copied by reference (the gate checks it equals the entity's) and `default_filters` (named, see concepts).
- `joins`: physical relationship keys only (`<entity>.<key>`), never SQL; the gate fails on an unknown key or a relationship with `status: unresolved`.
- `concepts`: named filters over physical fields with a value vocabulary or a predicate in the D-017 expression form; `required: true` marks a concept every query must apply (QCEW: `disclosed`, `level`); the consumer must prove it applies them (round 23).
- `measures`: `id`, `expression` over physical fields (sqlglot-parsed, neutral dialect), `aggregation`, `grain` (the entity and the key fields a result row is at), `time` (the entity field that carries time, with its granularity), `formula_source` (evidence id of the documented formula where one exists), `hazards` (hazard ids inherited).
- `hazards`: ids from the registers the layer inherits; the gate fails when a hazard names a field the layer uses and the layer does not list it.
- Consumer file `semantic/<layer-id>/consumer.yaml`: `id`, `meaning`, `layers`, `corpus` (path under the layer folder), `threshold` (D-021 default 0.9), `interface` (`compile` entry point, section 3).

Gate: a new stage `layers` (or extend `references`): every id resolves, joins are relationship keys, measures parse, required concepts exist, hazards are listed, `status: reviewed` requires an accepted equivalence run (round 23 wires that). Hard cases: layer with free SQL in `joins` (fails), layer missing an inherited hazard (fails), layer on an unresolved relationship (fails), valid minimal layer (passes). Spec text in SPEC.md and VOCABULARY.md section 9.

Commit `WP3.1: semantic layer contract v1 (D-019)`.

## 3. Round 21 - WP3.2 Equivalence harness

`src/factmodel/equivalence/`, `fact equivalence run --layer <id> [--corpus <path>]`.

- Corpus item (`corpus/*.yaml`): `id`, `request` (consumer input, free text plus structured fields the consumer defines), `reference` (hand-written SQL in the neutral dialect, or a result file), `mode` (`same_rows | same_count | same_predicate`), `note`. Items in the repository are synthetic; a real corpus outside the repository is referenced by pin and read from a path given at run time.
- Consumer interface: a Python entry point `compile(request: dict, layer: Layer) -> str` returning SQL in the neutral dialect; the harness renders both sides per dialect with sqlglot and executes offline on SQLite and DuckDB fixture data (the examples' seeds), or prints a probe-style script for an owner-run live comparison.
- `same_predicate`: normalised AST equality via sqlglot (qualified names, sorted conjuncts, literals kept).
- Report `generated/equivalence-<layer>.md` and `equivalence/last-run.json`; `equivalence/accepted.json` is written only by `fact equivalence accept` (owner-run, idempotent). A drop against accepted blocks `fact release` (round 24).
- Tests with a toy layer and three toy consumers: right, wrong, partially right; all three modes; regression detection; idempotency.

Commit `WP3.2: equivalence harness`.

## 4. Round 22 - Layers for both examples, rollup probe (D-020)

- QCEW `semantic/employment-wages/`: entities `qtrly`, `annual`, the title tables; concepts `disclosed` (required: `disclosure_code` blank; cite F-0002, F-0003, F-0006), `level` (required: the `(agglvl_code, industry_code)` discriminator, F-0008), `ownership`, `area_kind` (county, state, MSA by code shape), `period`; join to `area_titles` through the distinct-codes rule (F-0001: the layer states the join must be to distinct codes, as a `default_filters` entry, and a measure on it carries the hazard); measures `employment_month3`, `employment_avg` (mean of the three monthly levels), `total_wages`, `avg_weekly_wage` (from monthly levels and the documented formula, H-0002), `establishments`, `oty_employment_change`; each measure lists what it does with suppressed cells (`suppressed: exclude` plus a companion `suppressed_cells` count measure). Never a sum of annual averages (H-0001).
- Chinook `semantic/customer-purchases/`: concepts `genre`, `country`, `period`; measures `revenue`, `tracks_bought`, `customers_active`; joins by relationship keys through `invoice_line`, `invoice`, `track`, `album`, `genre`.
- D-020 `rollup` probe: for a hierarchy relationship with a measure, compare each parent with the sum of its children at one level; result counts: parents compared, exact, within rounding (one unit per child), beyond, parents with a suppressed child, parents suppressed with disclosed children. Run on the QCEW seed; the result confirms M5 where nothing is suppressed and records H5 as measured; update F-0007.
- Gate green on both examples with layers at `status: draft`.

Commit `WP3.3a: layers for QCEW and Chinook, rollup probe (D-020)`.

## 5. Round 23 - WP3.3 Reference consumers, corpora, threshold (D-021)

- QCEW `examples/qcew/consumers/measure-sql/`: a small generator, no model, no network: a structured request (`measure`, `area`, `industry`, `ownership`, `period`, optional `level`) becomes SQL using only the layer: it must apply every required concept, use the layer's joins and measure expressions, and report `suppressed_cells` next to the measure. Corpus of at least 30 items with hand-written reference SQL against the seed; include at least five where a naive query (summing `N` rows as zeros, joining the raw area list, mixing levels) gives a different answer, with the naive SQL kept in `note` so the difference is visible. Items 31 and up may be `known_gap` (rollups across the geography lattice, MSA detail).
- Chinook `examples/chinook/consumers/filter-sql/`: filter requests ("customers who bought tracks of genre X in period Y", "revenue by country in year Z") to SQL through the layer; corpus of at least 30 items.
- Run both; record D-021; `fact equivalence accept` for both (the owner's act is simulated once here; say so in the report); layers to `status: reviewed` only if the threshold holds, otherwise `draft` with findings for each failure.
- Dogfood the `model-lookup` need: note every physical fact the consumer had to look up, for round 24's skill.

Commit `WP3.3: reference consumers and corpora, threshold (D-021)`.

## 6. Round 24 - WP3.4 Release projection and skills

- `release/allowlist.yaml` format (per kind: `keep`, `drop`, fail-closed on undeclared keys, as the round-5 partition already does); `fact release --out <dir>`: complete partition export / project / refuse, internal-note markers stripped, derived keys never leak, `VERSION` file (release version, source commit, schema version), `RELEASE_NOTES.md` append-only (one section per version, never edited; the gate on the release folder checks that older sections are byte-identical to the previous release).
- A release refuses to build when the last equivalence run of any `reviewed` layer dropped against accepted.
- Skills: `agent/skills/model-lookup/` (reader side: how an agent finds an entity, a measure, a hazard in a release, with the commands), `agent/skills/release/`.
- Release both examples into `examples/<name>/release/out/` (gitignored) in a test; check the release reads cleanly with `fact check --release` (a reduced gate for releases: yaml, schema, references, privacy).

Commit `WP3.4: release projection, model-lookup and release skills`.

## 7. Round 25 - WP3.5 Exporters, WP3.6 skills

- `src/factmodel/export/ossie.py`: read the current Apache Ossie specification version (one network read) and pin it; map layer concepts, measures and joins; carry evidence status as metadata where the target allows; a warning list for what cannot be expressed. Validate against the published schema if one exists at that version, otherwise structural tests plus round-trip notes.
- `src/factmodel/export/dbt.py`: dbt semantic models and metrics YAML (MetricFlow); validate with `dbt-core` as a dev dependency only if it installs cleanly, otherwise structural tests; round-trip notes.
- `fact export --target <ossie|dbt> --layer <id> --out <dir>`; both examples exported in tests.
- Skills `drift-review`, `layer-build`, `escalation-draft`, `maintenance-pack`; `fact probe generate --set volatile` (the probes a maintenance pack re-runs: key duplicates, row counts, value sets, rollups).

Commit `WP3.5, WP3.6: exporters and maintenance skills`.

## 8. Stop conditions

- Credentials, network beyond package installs and the one Ossie read, or a query against any remote platform.
- A contract change that D-018's rule classes as a decision and that D-019 to D-021 do not cover: stop, do not invent D-022.
- Any check cannot be made green without weakening a test or a rule.
- The working tree is not clean at a round start.

Not stop conditions: `dbt-core` does not install (structural tests only); the Ossie page is unreachable (pin the last version named in `spec/SPEC.md` sources and say so); the crosswalk files are absent.

## 9. Final report

`rounds/<date>-report-m3-final.md`: outcome, git log, acceptance per round, equivalence results per consumer (counts per mode and outcome), spec and vocabulary edits, decisions, confirmed / inferred / unknown, divergences, questions, and a suggested M4 brief (packaging, docs site, tutorial, external pilot on the owner's standalone QCEW model with real data).

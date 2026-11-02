# FAQ

## Platforms and access

**Does the agent need credentials for a cloud warehouse?** No. The core reads model files and snapshots only. Cloud engines are reached through the `export` adapter (the owner runs the export SQL) or the `sql` adapter with the owner's own login (D-011, `docs/adopters/bigquery.md`).

**Can a probe on test data confirm a fact?** No. Only a result on representative data confirms. Example models whose platform is itself synthetic set `treat_synthetic_as_representative` (D-014).

**Does `fact sync` take a fresh snapshot?** No. It compares the latest committed snapshots; taking one is `fact snapshot`.

**Which engines are tested?** SQLite, PostgreSQL and DuckDB (`sql` adapter). Engines whose SQLAlchemy dialect cannot reflect are read through the standard `INFORMATION_SCHEMA` views.

## Modelling

**Must a profile name a subject?** No. A domain whose rows are aggregates (statistics) has no subject and no anchor (D-015).

**Can a join be something other than equal fields?** Yes: a boolean SQL expression over the two ends, for example a code prefix (D-017).

**May real data enter the repository?** Only public-domain code lists under 1 MB, unchanged, with a source line (D-016).

**May a single-target relationship carry a discriminator?** Yes, when the target's meaning depends on a field of the source (QCEW `agglvl_code`).

**May an unresolved relationship omit its join?** Yes; its target is still checked.

**Should drafts keep the engine's constraint names?** Yes, in `extensions.draft.constraint_name`.

**The catalog declares no key. Where do keys come from?** `fact propose keys` and `fact propose joins` measure the rows (counts only) and write candidates to `drafts/`, each with its measurement as `inferred` evidence. A candidate becomes a key or a relationship only when a person accepts it; an inclusion between two columns is often a coincidence of value ranges, so the record also carries the target's coverage (`spec/ALGORITHMS.md`, section 4).

## Change and versions

**When does a change need a decision record?** When it removes or renames a key, changes the meaning of a key or value, or changes an algorithm's result. Additive changes need a CHANGELOG entry and a ledger line; defect fixes a CHANGELOG entry (D-018).

**Why are the schemas at 2.x after a 1.0.0 freeze?** The semantic layer contract v1 replaced the 1.0.0 placeholders (D-019, 2.0.0); rollups (2.1.0) and value tables (2.2.0) were added later.

**How do I migrate a model?** `fact migrate` reports versions and compatibility. Its registry holds one documented slot (1.0.0 to 2.0.0, no automatic step); no model has needed a migration yet.

## Semantic layers

**When is a layer proven?** When its consumer passes at least the threshold share (0.9 by default) in `same_rows` or `same_predicate`, nothing regresses, and every failure has a known gap or a finding (D-021).

**How does a consumer get the join behind a relationship key?** From `semantic/<layer>/generated/joins.tsv`, which `fact project` derives and a release carries, or from `fact lookup`.

**How does a consumer find a QCEW aggregation level?** From the layer's `level_matrix`, a table-valued concept.

**Does a hierarchy add up?** A `rollup` probe measures it (D-020). A hierarchy is confirmed for aggregation only by a rollup in range.

## Releases and exports

**Where do release notes live?** In the model repository (`release/RELEASE_NOTES.md`), append-only. `fact release` adds a section per new version and copies the file into the release.

**What does dbt not hold?** Measures read at their grain, distinct rules, value tables and value vocabularies, listed in each export's `EXPORT_NOTES.md`. A formula over exported metrics becomes a derived metric (`docs/exporters/round-trip-notes.md`).

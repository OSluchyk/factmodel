# Dogfood: what the reference consumers had to look up (round 23)

Both reference consumers receive only their layer (`compile(request, layer)`). Everything else they needed was looked up by hand in the physical model or the documents. This is the reader's need the `model-lookup` skill (round 24) answers from a release.

## QCEW `measure-sql`

| Needed | Found in | Why the layer did not give it |
| --- | --- | --- |
| The aggregation-level matrix (A4): geography digit and industry/ownership digit of `agglvl_code` | `evidence/documents.yaml` `ev-doc-agglvl`, the `agglevel_titles` code list, `profile.md` A4 | The layer says `level` is required and why (F-0008), not how to compute a level from a request. |
| The join condition behind `qtrly.to-area` (`qtrly.area_fips = area_titles.area_fips`) | `physical/entities/qtrly.yaml` | A layer lists relationship keys, not their joins (D-019). |
| That MSA detail is level 41 and the MSA total level 40 | `profile.md` A4, the seed | Part of the same matrix. |
| That `area_titles` is joined through its distinct rule as a subquery, keeping the entity id as alias | The `distinct_areas` concept, plus SQL knowledge | The concept names the fields; how to apply it is the consumer's. |

## Chinook `filter-sql`

| Needed | Found in | Why the layer did not give it |
| --- | --- | --- |
| The join conditions behind `invoice_line.to-invoice`, `invoice_line.to-track`, `track.to-genre` | `physical/entities/*.yaml` | A layer lists relationship keys, not their joins. |
| The genre names and billing countries a request may use | The seed (data) | Concepts on free-text fields carry no value vocabulary. |
| How `InvoiceDate` compares with a date literal (text in SQLite, timestamp in DuckDB) | Snapshots (`type_class`) | Type is a physical fact. |

## For the skill

A reader of a release needs, for one layer: each relationship key with its join, each concept with its predicate or values, each measure with its expression and grain, the hazards with their text, and the documents behind required concepts. The `model-lookup` skill should show the commands that print these from a release, so a consumer's author never opens the model repository.

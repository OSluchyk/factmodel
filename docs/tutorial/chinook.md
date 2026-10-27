# Tutorial: model Chinook from an empty folder

This tutorial takes an empty folder to a released model and two exports. Every step is a command; a test runs them in order, on a fresh folder, with the installed package only, and checks every output this page promises.

You need the `fact` command (`pip install factmodel`, or `uv pip install` the wheel), the `sqlite3` command line and `perl` (used for small edits to YAML files; any editor does the same). Run the blocks in one shell session, in order, from the same folder.

The platform is a small part of the Chinook music store: customers, invoices, invoice lines, tracks and genres, with a few made-up rows. The model uses the `retail` profile, whose subject is the customer. The dates are fixed at 2026-10-27 so the outputs match; use your own date in a real model.

## 1. Create the model and the database

```bash
fact init chinook --profile retail
sqlite3 chinook.db <<'SQL'
CREATE TABLE Customer (CustomerId INTEGER PRIMARY KEY, Country TEXT);
CREATE TABLE Genre (GenreId INTEGER PRIMARY KEY, Name TEXT);
CREATE TABLE Track (TrackId INTEGER PRIMARY KEY, Name TEXT, GenreId INTEGER REFERENCES Genre (GenreId));
CREATE TABLE Invoice (InvoiceId INTEGER PRIMARY KEY, CustomerId INTEGER NOT NULL REFERENCES Customer (CustomerId), InvoiceDate TEXT, BillingCountry TEXT);
CREATE TABLE InvoiceLine (InvoiceLineId INTEGER PRIMARY KEY, InvoiceId INTEGER NOT NULL REFERENCES Invoice (InvoiceId), TrackId INTEGER NOT NULL REFERENCES Track (TrackId), UnitPrice NUMERIC, Quantity INTEGER);
INSERT INTO Customer VALUES (1, 'Brazil'), (2, 'Canada'), (3, 'Canada');
INSERT INTO Genre VALUES (1, 'Rock'), (2, 'Jazz');
INSERT INTO Track VALUES (1, 'Song A', 1), (2, 'Song B', 1), (3, 'Song C', 2);
INSERT INTO Invoice VALUES (1, 1, '2024-01-10', 'Brazil'), (2, 2, '2024-02-03', 'Canada'), (3, 3, '2024-05-20', 'Canada'), (4, 1, '2024-06-01', 'Brazil');
INSERT INTO InvoiceLine VALUES (1, 1, 1, 0.99, 1), (2, 1, 3, 0.99, 2), (3, 2, 2, 0.99, 1), (4, 3, 3, 1.99, 1), (5, 4, 1, 0.99, 3);
SQL
```

Output:

```text
created chinook with
(profile retail)
```

`fact init` wrote the model repository: `factmodel.yaml`, the folder layout, agent files and CI. The database is the platform you model; in real life it already exists.

## 2. Register the source and draft the entities

```bash
export FACT_DSN_CHINOOK="sqlite:///$PWD/chinook.db"
fact source add --root chinook --id chinook-db --title "Chinook database" --kind warehouse --access-mode agent_read --engine sqlite --adapter sql --dsn-env FACT_DSN_CHINOOK
fact snapshot --root chinook --source chinook-db --date 2026-10-27
fact draft --root chinook --source chinook-db
cp chinook/drafts/chinook-db/entities/*.yaml chinook/physical/entities/
```

Output:

```text
wrote sources/snapshots/chinook-db@2026-10-27.yaml (5 objects)
5 drafts, 5 written
```

The connection string stays in `FACT_DSN_CHINOOK` and never enters a file. `fact snapshot` read the catalog; `fact draft` turned each table into an entity draft, and each declared foreign key into a relationship with `inferred` evidence (SQLite does not enforce foreign keys).

## 3. The first gate: residue

```bash
fact project --root chinook
fact check --root chinook || echo "the gate failed, as expected"
```

Output:

```text
FAIL  projection (4)
gate: fail
the gate failed, as expected
```

`fact project` labels every relationship with the profile's rules. Four relationships match no rule: they are the **residue**. A draft calls every table `data`, and nothing yet says which rows belong to a customer, so the profile cannot tell customer data from catalog data. The gate fails until the residue is 0.

## 4. Review the entities

Three facts clear the residue: tracks and genres are shared catalog data (class `reference`); an invoice belongs to the customer in its `CustomerId` (the anchor reference); and an invoice line belongs to the customer of its invoice, because each line has exactly one invoice (scope admitted on `unique_target`).

```bash
perl -pi -e 's/^class: data$/class: reference/' chinook/physical/entities/genre.yaml chinook/physical/entities/track.yaml
cat >> chinook/physical/entities/invoice.yaml <<'YAML'
anchor_reference:
  field: CustomerId
  evidence: [ev-invoice-to-customer]
YAML
perl -pi -e 's/^(  join: invoice_line\.InvoiceId = invoice\.InvoiceId\n)/$1  scope_admission: {basis: unique_target, evidence: [ev-invoice-catalog]}\n/' chinook/physical/entities/invoice_line.yaml
fact project --root chinook
fact check --root chinook
echo "residue: $(tail -n +3 chinook/generated/residue.tsv | wc -l | tr -d ' ')"
cat chinook/generated/scope.tsv
```

Output:

```text
PASS  projection
gate: pass
residue: 0
invoice	direct
invoice_line	transitive	unique_target	invoice_line.to-invoice
```

`generated/scope.tsv` now says which entities hold customer data: `customer` and `invoice` directly, `invoice_line` through its invoice, `track` and `genre` not at all. In a real model each entity is reviewed with its owner and its meanings are written (the `entity-scaffold` skill); the placeholders the drafts left are allowed while an entity is `draft`.

## 5. Confirm the facts with probes

```bash
fact probe generate --root chinook
fact probe run --root chinook --source chinook-db --date 2026-10-27
fact probe intake --root chinook chinook/probes/results/chinook-db@2026-10-27.jsonl
fact project --root chinook
fact check --root chinook
```

Output:

```text
19 probes, 19 written, 0 facts skipped
19 probes run, 0 failed
19 in range, 0 out of range, 0 failed, 0 rejected
gate: pass
```

A probe is a readable SQL script that returns counts only: key duplicates, null rates, join matches, fan-out. Here the source allows the agent to read it (`agent_read`), so `fact probe run` runs them; on a platform where only people may run queries, `fact probe render` prints the scripts instead. `fact probe intake` turns each result into evidence and opens a finding for any result out of range.

## 6. Add a semantic layer, a consumer and a corpus

A layer is what a consumer needs to answer questions: the entities, the joins, the concepts a question names and the measures it asks for. The consumer here is a small function that turns a request into SQL; the corpus holds questions with reference SQL written by hand.

```bash
mkdir -p chinook/semantic/purchases/corpus chinook/consumers/genre-sql
cat > chinook/semantic/purchases/layer.yaml <<'YAML'
kind: layer
id: purchases
purpose: Revenue and active customers by genre and billing country.
consumer: genre-sql
status: draft
entities:
- {entity: invoice_line, current_row_rule: null}
- {entity: invoice, current_row_rule: null}
- {entity: track, current_row_rule: null}
- {entity: genre, current_row_rule: null}
joins:
- invoice_line.to-invoice
- invoice_line.to-track
- track.to-genre
concepts:
- id: genre
  meaning: The genre of a track bought.
  field: genre.Name
- id: country
  meaning: The billing country of the invoice.
  field: invoice.BillingCountry
measures:
- id: revenue
  meaning: Money billed, unit price times quantity.
  expression: invoice_line.UnitPrice * invoice_line.Quantity
  aggregation: sum
  grain: {entity: invoice_line, fields: [InvoiceLineId]}
  suppressed: not_applicable
- id: customers_active
  meaning: Customers with at least one invoice in the selection.
  expression: invoice.CustomerId
  aggregation: count_distinct
  grain: {entity: invoice, fields: [InvoiceId]}
  suppressed: not_applicable
YAML
cat > chinook/semantic/purchases/consumer.yaml <<'YAML'
kind: consumer
id: genre-sql
meaning: Turns a request (a measure, by genre or by country) into SQL using only the purchases layer.
layers: [purchases]
corpus:
  location: corpus
  synthetic: true
threshold: 0.9
interface: consumers/genre-sql/compile.py:compile
YAML
cat > chinook/consumers/genre-sql/compile.py <<'PY'
"""A request {measure, by} becomes SQL over the purchases layer."""

JOINS = (
    "JOIN invoice ON invoice_line.InvoiceId = invoice.InvoiceId "
    "JOIN track ON invoice_line.TrackId = track.TrackId "
    "JOIN genre ON track.GenreId = genre.GenreId"
)


def compile(request, layer):
    measure = next(m for m in layer.measures if m.id == request["measure"])
    key = next(c for c in layer.concepts if c.id == request["by"]).field
    if measure.aggregation == "count_distinct":
        value = f"COUNT(DISTINCT {measure.expression})"
    else:
        value = f"SUM({measure.expression})"
    return f"SELECT {key} AS key, {value} AS value FROM invoice_line {JOINS} GROUP BY {key}"
PY
cat > chinook/semantic/purchases/corpus/01-revenue-by-genre.yaml <<'YAML'
id: revenue-by-genre
request: {measure: revenue, by: genre}
reference: SELECT g.Name, SUM(l.UnitPrice * l.Quantity) FROM InvoiceLine l JOIN Track t ON t.TrackId = l.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.Name
mode: same_rows
YAML
cat > chinook/semantic/purchases/corpus/02-revenue-by-country.yaml <<'YAML'
id: revenue-by-country
request: {measure: revenue, by: country}
reference: SELECT i.BillingCountry, SUM(l.UnitPrice * l.Quantity) FROM InvoiceLine l JOIN Invoice i ON i.InvoiceId = l.InvoiceId GROUP BY i.BillingCountry
mode: same_rows
YAML
cat > chinook/semantic/purchases/corpus/03-customers-by-genre.yaml <<'YAML'
id: customers-by-genre
request: {measure: customers_active, by: genre}
reference: SELECT g.Name, COUNT(DISTINCT i.CustomerId) FROM InvoiceLine l JOIN Invoice i ON i.InvoiceId = l.InvoiceId JOIN Track t ON t.TrackId = l.TrackId JOIN Genre g ON g.GenreId = t.GenreId GROUP BY g.Name
mode: same_rows
YAML
fact project --root chinook
fact check --root chinook
```

Output:

```text
wrote semantic/purchases/generated/joins.tsv
gate: pass
```

The consumer names tables by entity id; the harness binds each to its physical name. A real corpus has at least 30 questions (D-021); three keep this page short.

## 7. Prove the layer

```bash
fact equivalence run --root chinook --layer purchases --date 2026-10-27
fact equivalence accept --root chinook --layer purchases
perl -pi -e 's/^status: draft$/status: reviewed/' chinook/semantic/purchases/layer.yaml
fact check --root chinook
```

Output:

```text
purchases: 3 pass, 0 fail, 0 error of 3
share 1.000, threshold 0.9: proven
purchases: accepted
gate: pass
```

`fact equivalence run` runs the consumer on every corpus question and compares its rows with the reference rows. The layer is proven when the share of passing questions meets the threshold, with no regression against the accepted run. Only then may the layer be `reviewed`: the gate refuses a reviewed layer that no accepted run proves.

## 8. Release

A release is the readable copy of the model that consumers get. The allowlist sorts every file of the repository: exported as is, projected (some keys dropped), or refused. A file it does not match refuses the release.

```bash
cat > chinook/release/allowlist.yaml <<'YAML'
kind: release-allowlist
files:
- {pattern: factmodel.yaml, disposition: export}
- {pattern: physical/entities/*.yaml, disposition: project, reason: drafting metadata stays}
- {pattern: sources/*.yaml, disposition: project, reason: how access is obtained stays}
- {pattern: evidence/**, disposition: export}
- {pattern: registers/**/*.yaml, disposition: export}
- {pattern: semantic/**, disposition: export}
- {pattern: equivalence/*.json, disposition: export}
- {pattern: generated/*.tsv, disposition: export}
- {pattern: generated/*.md, disposition: export}
- {pattern: probes/*.yaml, disposition: export}
- {pattern: '**', disposition: refuse, reason: 'drafts, snapshots, probe results, code and agent files stay'}
keys:
  entity:
    keep: [kind, id, physical_name, source, grain, class, status, meaning, keys, anchor_reference, evidence, fields, relationships, hazards, records]
    drop: [extensions]
  source:
    keep: [kind, id, title, source_kind, access_mode, rank, adapter, engine, dialect, location, current_pin, meaning]
    drop: [access, dsn_env, revision, include, extensions]
YAML
fact release --root chinook --out chinook-release --version 0.1.0 --date 2026-10-27
fact check --release chinook-release
fact lookup --root chinook-release --layer purchases
```

Output:

```text
release 0.1.0:
PASS  release
gate: pass
invoice_line.to-invoice: invoice_line.InvoiceId = invoice.InvoiceId (many_to_one, declared_fk)
```

The release holds `VERSION` and `RELEASE_NOTES.md`; the notes live in the model (`release/RELEASE_NOTES.md`) and only grow. `fact lookup` reads a release as well as a model, with every join resolved.

## 9. Export

```bash
fact export --root chinook --target ossie --layer purchases --out chinook-export/ossie
fact export --root chinook --target dbt --layer purchases --out chinook-export/dbt
```

Output:

```text
purchases -> ossie: 1 file(s)
purchases -> dbt: 1 file(s)
```

Each export writes `EXPORT_NOTES.md`, the list of what the target cannot hold; nothing is dropped silently. See [round-trip notes](../exporters/round-trip-notes.md).

## Where next

- Keep the model current: `fact snapshot` on a schedule, then `fact sync` drafts what changed and fires triggers.
- Hazards, findings and escalations: the registers, and `fact status` for what needs doing.
- The full examples in the repository: `examples/chinook` (31 corpus questions, two engines) and `examples/qcew` (a statistics domain with suppressed cells and rollups).

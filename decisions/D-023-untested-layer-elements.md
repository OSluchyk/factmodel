# D-023 Untested layer elements carry a recorded reason

Date: 2026-11-22 · Status: accepted
Platform that forced it: Chinook, QCEW

## Context

D-021 says when a consumer proves a layer: enough items pass, none regresses, and every item that does not pass is explained (rule 3). It says nothing about what the corpus exercises. A layer could be proven and `reviewed` while part of it was never tested. The equivalence harness now traces the reference SQL of every item and reports, for each entity, join, concept and measure of the layer, how many items use it and how many of those pass (`coverage` in the run summary). The first coverage run showed elements of both reviewed example layers that no item uses.

## Decision

This record extends rule 3 of D-021, which stays as it is: a failing item is explained, and so is an untested element.

1. An element of a layer is **tested** when at least one passing corpus item uses it. An element that only failing items use is not tested.
2. The rule applies to **enforced** elements: entities, joins the trace evaluates (a single-target relationship whose condition it can read), concepts in the `field` form, and measures. It does not apply to concepts in the `predicate` form, which the trace finds only as written, or to elements in a form the trace does not evaluate.
3. An enforced element that is not tested carries an entry in the layer's optional `untested` list: `{kind, id, reason}`, with `kind` from the vocabulary block `layer_element_kind`. The author writes the reason: what needs the element and what would test it. The reason may cite a probe or an evidence id. A reference from a rollup or another layer key is not a reason by itself.
4. A layer may be `status: reviewed` only when its accepted run holds coverage, every enforced element that the run does not test has an `untested` entry, and no entry names an enforced element that the run does test (a stale entry). An entry for a predicate concept or a not-evaluated element is allowed and is never stale.
5. For every layer, each `untested` entry names an element of the layer, once.

The gate's `layers` stage checks 4 and 5 (`no_coverage`, `missing_reason`, `stale_untested`, `unknown_untested`). The run's own `proven` key keeps the D-021 meaning: the threshold, the share and the regression rule do not change.

## Consequences

- Layers gain the optional key `untested`; the vocabulary gains `layer_element_kind`; schemas 2.3.0 (minor, D-018 additive).
- The `coverage` key of a run gains `no_passing_item` and `tested`; `fact equivalence accept` copies it into `accepted.json` with the rest of the run.
- A reviewed layer whose accepted run predates coverage fails the gate until the owner runs and accepts again. Its files still validate, so `fact migrate` reports a 2.2.0 model as compatible and names the layers to accept again.
- Example cleanup: Chinook drops `album` and `track.to-album`; QCEW drops `ownership_titles` and three joins nothing reads, and records reasons for `industry_titles`, `qtrly.to-industry` and `annual.to-area`.

## Evidence

- The first coverage run on the example layers, before the cleanup in this change: Chinook `album` and `track.to-album` used by 0 of 31 items; QCEW `industry_titles`, `ownership_titles` and five joins used by 0 of 38 items, while both layers were `reviewed` and proven.
- Maintainer decision, 2026-11-22.

# D-013 Neutral type class on snapshot fields

Date: 2026-10-23 · Status: accepted
Platform that forced it: none

## Context

Snapshot fields carry the engine's own type text (`INT64`, `integer`, `NUMBER(38,0)`). Comparing two engines, or two reads of one engine after a cosmetic change, on that text alone reports differences that do not matter and misses none that do.

## Decision

- Snapshot fields get an optional `type_class` from a new vocabulary block: `integer, decimal, float, boolean, text, date, time, timestamp, interval, binary, json, array, struct, geography, other`.
- `type` keeps the engine's own text, unchanged.
- Each adapter maps engine types to a class; an unknown type maps to `other`.
- Drift (WP1.6) treats a change of `type_class` as a type change, and a change of `type` text within the same class as "no effect, listed".

## Consequences

- Snapshots of the same schema on two engines can be compared on their neutral parts (names, nullability, constraints, type class).
- The type mapping lives with the adapters, not in the core.

## Evidence

- Maintainer decision, 2026-10-23.

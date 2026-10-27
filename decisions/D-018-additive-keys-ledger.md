# D-018 Additive keys need a ledger line, not a decision record

Date: 2026-10-27 · Status: accepted
Platform that forced it: none (the framework's own probes and adapters)

## Context

The M2 freeze review (`spec/CORE-CHANGES-M2.md`, round 18) found three contract changes without a decision record: snapshot `pin` keys (round 8), the optional probe `expected` with the probe keys `entity` and `note` (round 11), and the field key `values` (round 14). Each only adds an optional key. The rule "every core change needs a decision record" stopped the freeze over changes that cannot break a model, while it did not say what a defect fix needs.

## Decision

1. **Retroactive record.** The three changes stand: snapshot `pin` and per-object `pin`; probe `expected` optional, probe keys `entity` and `note`; field key `values`. None removes, renames or changes the meaning of an existing key. Platform that forced them: none.
2. **The rule from here on.**
   - A decision record is required when a contract change removes or renames a key, changes the meaning of an existing key or value, or changes an algorithm's result.
   - Adding an optional key, a vocabulary value or a probe kind needs a `CHANGELOG.md` entry and a line in the current core-change ledger, nothing more.
   - A fix that makes code obey the existing schema is a defect fix, not a core change; it needs a `CHANGELOG.md` entry only.
3. An owner brief is not a decision record. When a brief decides something this rule classes as a decision, the round records it in `decisions/`.

## Consequences

- `spec/CORE-CHANGES-M2.md` cites D-018 for the three rows and states the rule at the top.
- `spec/VERSIONING.md` and `AGENTS.md` rule 6 state the rule.
- The schemas freeze at 1.0.0 in the same round.

## Evidence

- Owner decision in the owner brief of 2026-10-27 on closing the M2 freeze (private working notes), sections 1 and 4 (Q3).
- `spec/CORE-CHANGES-M2.md`, section "Changes without a decision record".

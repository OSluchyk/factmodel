# soft-delete

An entity with a `deleted_at` flag and a current-row rule. The rule lets `item_returns` be admitted with basis `current_row_rule`. The probe for ties after the rule is deferred.

Plan case: `soft-delete`. Gate: pass.

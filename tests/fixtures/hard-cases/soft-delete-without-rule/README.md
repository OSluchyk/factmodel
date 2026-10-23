# soft-delete-without-rule

The same model without the current-row rule: the admission is rejected (`no_current_row_rule`), so `item_returns` stays unscoped and its link is residue.

Plan case: `soft-delete`. Gate: fails `projection`, `scope`.

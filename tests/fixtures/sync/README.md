# Sync fixtures

Two synthetic snapshots of one source, `shop`, that differ in every drift kind (spec/VOCABULARY.md, section 11). The model in `tests/sync/test_sync.py` describes `customers`, `orders` (with its `note` field) and `legacy_carts`; `tmp_import` and `refunds` are not modelled. `expected-drift-shop.md` is the report `fact sync` must write.

# reference-chain

Data to reference to data: `price_changes` -> `products` <- `order_items` -> `orders`. Scope never passes through the reference entity, so `price_changes` stays unscoped; the admission is rejected and its link is residue.

Plan case: `reference-chain`. Gate: fails `projection`, `scope`.

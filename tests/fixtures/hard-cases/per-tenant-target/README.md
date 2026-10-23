# per-tenant-target

Two links whose target is chosen per tenant (no discriminator; `tenants.yaml` shows which tenant ingests which). `for-order` agrees (rule 0 keeps the label); `sold-via` disagrees (`withheld`).

Plan case: `per-tenant-target`. Gate: pass.

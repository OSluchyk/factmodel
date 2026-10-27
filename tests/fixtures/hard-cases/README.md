# Hard cases

Small model repositories for what public datasets do not show (plan WP1.8b). Each folder holds the model files, `generated/` as committed, `expected/verdict.json` (the stages `fact check` must fail, and whether `fact project` writes or refuses) and `expected/generated/` (what `fact project` must write). `tests/hard_cases/test_hard_cases.py` runs both commands on every case.

| Case | Plan case | Gate |
| --- | --- | --- |
| [`soft-delete`](soft-delete/README.md) | soft-delete | pass |
| [`soft-delete-without-rule`](soft-delete-without-rule/README.md) | soft-delete | projection, scope |
| [`key-not-unique`](key-not-unique/README.md) | key-not-unique | pass |
| [`key-not-unique-unique-basis`](key-not-unique-unique-basis/README.md) | key-not-unique | projection, scope |
| [`polymorphic`](polymorphic/README.md) | polymorphic | pass |
| [`per-tenant-target`](per-tenant-target/README.md) | per-tenant-target | pass |
| [`nullable-fk`](nullable-fk/README.md) | nullable-fk | pass |
| [`reference-chain`](reference-chain/README.md) | reference-chain | projection, scope |
| [`nested-field`](nested-field/README.md) | nested-field | pass |
| [`stale-evidence`](stale-evidence/README.md) | stale-evidence | pass |
| [`retraction`](retraction/README.md) | retraction | pass |
| [`retraction-without-error`](retraction-without-error/README.md) | retraction | schema |
| [`retracted-still-cited`](retracted-still-cited/README.md) | retraction | evidence |
| [`deleted-finding`](deleted-finding/README.md) | - | registers |
| [`authored-scope`](authored-scope/README.md) | - | derived-not-authored |
| [`polymorphic-missing-target`](polymorphic-missing-target/README.md) | polymorphic | references |
| [`duplicate-key`](duplicate-key/README.md) | - | yaml |
| [`stale-generated`](stale-generated/README.md) | nullable-fk | generated-fresh |
| [`trigger-without-follow-up`](trigger-without-follow-up/README.md) | - | triggers |
| [`probe-error-with-row`](probe-error-with-row/README.md) | - | privacy |
| [`no-subject`](no-subject/README.md) | - (D-015) | pass |
| [`expression-join`](expression-join/README.md) | - (D-017) | pass |
| [`subject-profile-without-anchor`](subject-profile-without-anchor/README.md) | - (D-015) | references |

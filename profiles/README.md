# Profiles

A profile is the domain layer over the neutral core: the anchor entity, the labels it may assign and the ordered rules that assign them (`spec/VOCABULARY.md`, section 7; `spec/ALGORITHMS.md`, algorithm 1). Each profile lives in `profiles/<id>/profile.yaml` and must match `schemas/profile.schema.json`.

A profile names the role of its subjects (`subject: customer`); the model binds the entity that holds them with `anchor_entity` in `factmodel.yaml` (D-012), so one profile fits many platforms. `factmodel.yaml` names a profile by ID. The loader takes a model's own `kind: profile` file with that ID if there is one, else the profile shipped here.

| Profile | Subject | Use |
| --- | --- | --- |
| `retail` | `customer` | Retail and e-commerce; first used on the Chinook example. |

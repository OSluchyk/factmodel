# subject-profile-without-anchor

The retail profile names a subject (`customer`), but `factmodel.yaml` binds no anchor. Since D-015 the schema allows a config without `anchor_entity`, so the loader reports the mismatch (`missing_anchor`) and `fact project` refuses.

Plan case: - (D-015). Gate: fails `references`.

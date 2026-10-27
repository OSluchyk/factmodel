# Quickstart

From an empty folder to a first green gate in ten commands. You need the `fact` command (`pip install factmodel`, or `uv pip install` the wheel) and the `sqlite3` command line.

The model uses the `statistics` profile, which has no subject (D-015): labels come from entity class and mechanism alone, so two drafted tables pass the gate as they are.

```bash
fact init shop --profile statistics
sqlite3 shop.db "CREATE TABLE region (code TEXT PRIMARY KEY, name TEXT); CREATE TABLE sales (region_code TEXT REFERENCES region (code), year INTEGER, amount INTEGER, PRIMARY KEY (region_code, year));"
export FACT_DSN_SHOP="sqlite:///$PWD/shop.db"
fact source add --root shop --id shop-db --title "Shop database" --kind warehouse --access-mode agent_read --engine sqlite --adapter sql --dsn-env FACT_DSN_SHOP
fact snapshot --root shop --source shop-db --date 2026-10-27
fact draft --root shop --source shop-db
cp shop/drafts/shop-db/entities/*.yaml shop/physical/entities/
fact project --root shop
fact check --root shop
fact lookup --root shop --entity sales
```

Output:

```text
wrote sources/snapshots/shop-db@2026-10-27.yaml (2 objects)
2 drafts, 2 written
gate: pass
relationships:
  sales.to-region -> region: sales.region_code = region.code (many_to_one)
```

What happened:

1. `fact init` created a model repository: `factmodel.yaml`, the folder layout, agent files and CI.
2. `fact source add` registered the database. The connection string stays in `FACT_DSN_SHOP` and never enters a file.
3. `fact snapshot` read the catalog; `fact draft` turned it into entity drafts. The declared foreign key became a relationship with `inferred` evidence, because SQLite does not enforce foreign keys.
4. The drafts went into `physical/entities/` unchanged. In a real model you review each one first (the `entity-scaffold` skill).
5. `fact project` computed the derived values; `fact check` ran every gate stage.

Next: the [tutorial](tutorial/chinook.md) builds a model of part of the Chinook schema, from residue to probes, a proven layer, a release and two exports.

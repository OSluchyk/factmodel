"""A small model and database for probe tests: counts are known by construction."""

import sqlite3
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from factmodel.cli import app
from tests.model.helpers import dump

# 5 customers; 6 orders: one without a customer, one pointing to a missing customer (99);
# customers 4 and 5 have no orders. Customer 2 has two current versions (one tie).
DDL = """
CREATE TABLE "Customer" ("CustomerId" INTEGER NOT NULL PRIMARY KEY, "EmailHash" TEXT);
CREATE TABLE "Order" ("OrderId" INTEGER NOT NULL PRIMARY KEY, "CustomerId" INTEGER);
CREATE TABLE "CustomerVersion" ("VersionId" INTEGER NOT NULL PRIMARY KEY,
  "CustomerId" INTEGER NOT NULL, "IsCurrent" INTEGER NOT NULL);
"""
ROWS = [
    "INSERT INTO \"Customer\" VALUES (1, 'h1'), (2, 'h2'), (3, 'h2'), (4, NULL), (5, 'h5')",
    'INSERT INTO "Order" VALUES (10, 1), (11, 1), (12, 2), (13, 3), (14, NULL), (15, 99)',
    'INSERT INTO "CustomerVersion" VALUES (1, 1, 1), (2, 2, 1), (3, 2, 1), (4, 3, 0), (5, 3, 1)',
]
EXPECTED = {
    "row-count-customer": {"row_count": 5},
    "key-duplicates-customer": {"duplicate_keys": 0},
    "row-count-order": {"row_count": 6},
    "key-duplicates-order": {"duplicate_keys": 0},
    "null-rate-order-customer-id": {"row_count": 6, "non_null": 5},
    "join-match-order-to-customer": {"source_rows": 5, "orphans_left": 1, "orphans_right": 2},
    "fan-out-order-to-customer": {"max_fan_out": 1},
    "row-count-customer-version": {"row_count": 5},
    "key-duplicates-customer-version": {"duplicate_keys": 0},
    "current-row-ties-customer-version": {"tied_keys": 1},
}


def create_sqlite(path: Path) -> str:
    with sqlite3.connect(path) as conn:
        conn.executescript(DDL)
        for statement in ROWS:
            conn.execute(statement)
    return f"sqlite:///{path}"


def _entity(eid: str, physical: str, fields: list[tuple[str, bool]], **more: Any) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "kind": "entity",
        "id": eid,
        "physical_name": physical,
        "source": "shop",
        "grain": f"one row per {eid}",
        "class": "data",
        "status": "draft",
        "keys": {"primary": [fields[0][0]]},
        "evidence": ["ev-catalog"],
        "fields": [
            {"name": n, "type": "INTEGER", "nullable": nullable, "meaning": f"The {n}."}
            for n, nullable in fields
        ],
    }
    doc.update(more)
    return doc


def build_model(tmp_path: Path) -> Path:
    runner = CliRunner()
    root = tmp_path / "model"
    result = runner.invoke(app, ["init", str(root), "--profile", "retail", "--anchor", "customer"])
    assert result.exit_code == 0, result.output
    files: dict[str, Any] = {
        "sources/shop.yaml": {
            "kind": "source",
            "id": "shop",
            "title": "Shop",
            "source_kind": "warehouse",
            "access_mode": "agent_read",
            "adapter": "sql",
            "engine": "sqlite",
            "dsn_env": "FACT_TEST_SHOP_DSN",
        },
        "evidence/catalog.yaml": {
            "kind": "evidence",
            "records": [
                {
                    "id": "ev-catalog",
                    "source": "shop",
                    "pin": "sqlite:shop@2026-10-23",
                    "quote": "catalog read",
                    "status": "inferred",
                    "read_on": "2026-10-23",
                }
            ],
        },
        "physical/entities/customer.yaml": _entity(
            "customer", "Customer", [("CustomerId", False), ("EmailHash", True)]
        ),
        "physical/entities/order.yaml": _entity(
            "order",
            "Order",
            [("OrderId", False), ("CustomerId", True)],
            anchor_reference={"field": "CustomerId", "evidence": ["ev-catalog"]},
            relationships=[
                {
                    "key": "to-customer",
                    "to": "customer",
                    "join": "order.CustomerId = customer.CustomerId",
                    "meaning": "The customer who placed the order.",
                    "mechanism": "inferred_join",
                    "cardinality": "many_to_one",
                    "evidence": ["ev-catalog"],
                }
            ],
        ),
        "physical/entities/customer_version.yaml": _entity(
            "customer_version",
            "CustomerVersion",
            [("VersionId", False), ("CustomerId", False), ("IsCurrent", False)],
            keys={
                "primary": ["VersionId"],
                "unique": [["CustomerId"]],
                "current_row_rule": '"IsCurrent" = 1',
            },
        ),
    }
    for rel, doc in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(dump(doc), encoding="utf-8")
    return root

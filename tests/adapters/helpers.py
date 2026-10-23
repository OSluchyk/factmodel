"""Shared pieces for adapter tests: sources, the SQLite and PostgreSQL test schema."""

import os
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from factmodel.model.types import Snapshot, Source

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXPORTS = FIXTURES / "exports"
PG_DSN = os.environ.get("FACT_PG_DSN")
needs_pg = pytest.mark.skipif(not PG_DSN, reason="FACT_PG_DSN not set (CI only)")

# One schema in two dialects: a declared foreign key, a unique constraint and a view.
SQLITE_DDL = """
CREATE TABLE customers (
  customer_id INTEGER NOT NULL PRIMARY KEY,
  email_hash NVARCHAR(64),
  created_at DATETIME NOT NULL,
  CONSTRAINT customers_email_uq UNIQUE (email_hash)
);
CREATE TABLE orders (
  order_id INTEGER NOT NULL PRIMARY KEY,
  customer_id INTEGER,
  total NUMERIC(10, 2) NOT NULL,
  CONSTRAINT orders_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);
CREATE VIEW customer_totals AS
  SELECT customer_id, SUM(total) AS total FROM orders GROUP BY customer_id;
"""
PG_DDL = """
CREATE TABLE customers (
  customer_id INTEGER NOT NULL PRIMARY KEY,
  email_hash VARCHAR(64),
  created_at TIMESTAMP NOT NULL,
  CONSTRAINT customers_email_uq UNIQUE (email_hash)
);
CREATE TABLE orders (
  order_id INTEGER NOT NULL PRIMARY KEY,
  customer_id INTEGER,
  total NUMERIC(10, 2) NOT NULL,
  CONSTRAINT orders_customer_fk FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);
CREATE VIEW customer_totals AS
  SELECT customer_id, SUM(total) AS total FROM orders GROUP BY customer_id;
"""


def source(**fields: Any) -> Source:
    base: dict[str, Any] = {
        "kind": "source",
        "id": "shop",
        "title": "Shop",
        "source_kind": "warehouse",
        "access_mode": "agent_read",
    }
    return Source.model_validate({**base, **fields})


def sqlite_db(path: Path, ddl: str = SQLITE_DDL) -> str:
    """Create a SQLite database file from DDL; return its SQLAlchemy URL."""
    with sqlite3.connect(path) as conn:
        conn.executescript(ddl)
    return f"sqlite:///{path}"


def neutral(snap: Snapshot) -> list[Any]:
    """The parts of a snapshot that must agree across engines.

    View columns are compared without their type class: SQLite gives a computed view column
    no type at all (it reflects as ``other``), where PostgreSQL infers one.
    """
    return [
        (
            o.name,
            o.object_type,
            [
                (f.name, f.nullable, f.type_class if o.object_type != "view" else None)
                for f in o.fields
            ],
            sorted(
                (
                    c.constraint_type,
                    tuple(c.fields),
                    (c.references.object, tuple(c.references.fields)) if c.references else None,
                )
                for c in o.constraints or []
            ),
        )
        for o in snap.objects
    ]

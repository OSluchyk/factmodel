"""Deterministic synthetic rows for the Chinook schema (D-011).

A local engine seeded with these rows is a test fixture, not a platform. Every value is made
up: names and emails are generated strings that do not look like real people
(``customer-0042``, ``c0042@example.invalid``). The same seed always gives the same rows, so
SQLite and PostgreSQL return the same probe counts.

Usage:
    python examples/chinook/seed/seed.py sqlite <file.db>
    python examples/chinook/seed/seed.py postgres <dsn>    # for example after docker compose up
"""

import datetime
import random
import sqlite3
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

SEED = 20261023
DDL = Path(__file__).resolve().parents[1] / "sources" / "ddl"
ORDER = (
    "Artist",
    "Album",
    "Genre",
    "MediaType",
    "Track",
    "Playlist",
    "PlaylistTrack",
    "Employee",
    "Customer",
    "Invoice",
    "InvoiceLine",
)
COUNTRIES = ("Country A", "Country B", "Country C", "Country D")

Rows = dict[str, list[tuple[Any, ...]]]


def rows() -> Rows:
    """Every table's rows, in insert order."""
    rng = random.Random(SEED)
    out: Rows = {t: [] for t in ORDER}
    out["Artist"] = [(i, f"artist-{i:02d}") for i in range(1, 26)]
    out["Album"] = [(i, f"album-{i:02d}", rng.randint(1, 25)) for i in range(1, 61)]
    out["Genre"] = [(i, f"genre-{i}") for i in range(1, 9)]
    out["MediaType"] = [(i, f"media-type-{i}") for i in range(1, 5)]
    prices = {}
    for i in range(1, 301):
        price = Decimal("1.99") if i % 7 == 0 else Decimal("0.99")
        prices[i] = price
        out["Track"].append(
            (
                i,
                f"track-{i:03d}",
                None if i % 97 == 0 else rng.randint(1, 60),
                rng.randint(1, 4),
                None if i % 61 == 0 else rng.randint(1, 8),
                None if i % 3 else f"composer-{rng.randint(1, 40):02d}",
                rng.randint(60_000, 420_000),
                rng.randint(1_000_000, 9_000_000),
                price,
            )
        )
    out["Playlist"] = [(i, f"playlist-{i}") for i in range(1, 9)]
    pairs = sorted({(rng.randint(1, 8), rng.randint(1, 300)) for _ in range(450)})
    out["PlaylistTrack"] = pairs
    reports = {1: None, 2: 1, 3: 2, 4: 2, 5: 2, 6: 1}
    titles = {1: "manager", 2: "manager", 3: "rep", 4: "rep", 5: "rep", 6: "support"}
    for i in range(1, 7):
        hired = datetime.datetime(2020, 1, 1) + datetime.timedelta(days=30 * i)
        name = (i, f"employee-{i:02d}", f"e{i:02d}", titles[i], reports[i], None, hired)
        contact = (
            None,
            None,
            None,
            COUNTRIES[i % 4],
            None,
            None,
            None,
            f"e{i:02d}@example.invalid",
        )
        out["Employee"].append((*name, *contact))
    for i in range(1, 301):
        rep = None if i % 10 == 0 else rng.choice((3, 4, 5))
        name = (i, f"customer-{i:04d}", f"c{i:04d}", None, None, None, None, rng.choice(COUNTRIES))
        contact = (None, None, None, f"c{i:04d}@example.invalid", rep)
        out["Customer"].append((*name, *contact))
    invoice_id = 0
    line_id = 0
    for customer in range(1, 301):
        for _ in range(rng.randint(0, 4)):
            invoice_id += 1
            day = datetime.datetime(2024, 1, 1) + datetime.timedelta(days=rng.randint(0, 364))
            lines = []
            for _ in range(rng.randint(1, 5)):
                line_id += 1
                track = rng.randint(1, 300)
                lines.append((line_id, invoice_id, track, prices[track], 1))
            total = sum((line[3] for line in lines), Decimal("0"))
            country = rng.choice(COUNTRIES)
            out["Invoice"].append(
                (invoice_id, customer, day, None, None, None, country, None, total)
            )
            out["InvoiceLine"].extend(lines)
    return out


def _sqlite_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep=" ")
    return value


def load_sqlite(path: Path) -> str:
    """Create the schema and the rows in a SQLite file; return its SQLAlchemy URL."""
    with sqlite3.connect(path) as conn:
        conn.executescript((DDL / "sqlite.sql").read_text(encoding="utf-8"))
        for table, items in rows().items():
            if items:
                marks = ", ".join("?" for _ in items[0])
                conn.executemany(
                    f'INSERT INTO "{table}" VALUES ({marks})',
                    [tuple(_sqlite_value(v) for v in row) for row in items],
                )
    return f"sqlite:///{path}"


def load_postgres(url: str) -> None:
    """Create the schema and the rows in the database (and search path) ``url`` names."""
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            for statement in (DDL / "postgres.sql").read_text(encoding="utf-8").split(";"):
                body = "\n".join(
                    line for line in statement.splitlines() if not line.strip().startswith("--")
                )
                if body.strip():
                    conn.execute(text(body))
            for table, items in rows().items():
                if not items:
                    continue
                names = ", ".join(f":c{i}" for i in range(len(items[0])))
                conn.execute(
                    text(f'INSERT INTO "{table}" VALUES ({names})'),
                    [{f"c{i}": v for i, v in enumerate(row)} for row in items],
                )
    finally:
        engine.dispose()


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("sqlite", "postgres"):
        print(__doc__)
        return 2
    if argv[0] == "sqlite":
        print(load_sqlite(Path(argv[1])))
    else:
        load_postgres(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

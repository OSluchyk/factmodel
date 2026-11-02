"""``fact propose keys`` and ``fact propose joins`` on a small SQLite fixture: minimal keys,
a composite key, inclusions that are keys and one that is not, the threshold, and nothing
written outside ``drafts/``."""

import sqlite3
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from factmodel import propose
from factmodel.cli import app
from factmodel.io.yaml_strict import load
from factmodel.model.types import EvidenceRecord
from tests.model.helpers import dump

runner = CliRunner()

# No declared key anywhere: every key below is found from the rows.
DDL = """
CREATE TABLE region (r_regionkey INTEGER NOT NULL, r_name TEXT NOT NULL);
CREATE TABLE nation (
  n_nationkey INTEGER NOT NULL, n_name TEXT NOT NULL, n_regionkey INTEGER NOT NULL
);
CREATE TABLE item (
  i_nationkey INTEGER NOT NULL, i_seq INTEGER NOT NULL, i_rank INTEGER NOT NULL,
  i_note TEXT, i_weight REAL NOT NULL
);
CREATE TABLE shipment (
  s_nationkey INTEGER NOT NULL, s_seq INTEGER NOT NULL, s_box INTEGER NOT NULL
);
CREATE TABLE orphan (o_nationkey INTEGER NOT NULL);
"""


def _rows(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO region VALUES (?, ?)", [(0, "AFRICA"), (1, "AMERICA"), (2, "ASIA")]
    )
    conn.executemany(
        "INSERT INTO nation VALUES (?, ?, ?)",
        [
            (0, "ALGERIA", 0),
            (1, "ARGENTINA", 1),
            (2, "BRAZIL", 1),
            (3, "CANADA", 1),
            (4, "CHINA", 2),
        ],
    )
    items = []
    for nation in range(5):
        for seq in range(1, 5):
            items.append((nation, seq, (nation + seq) % 3, None if seq == 1 else f"n{nation}", 1.5))
    conn.executemany("INSERT INTO item VALUES (?, ?, ?, ?, ?)", items)
    conn.executemany(
        "INSERT INTO shipment VALUES (?, ?, ?)", [(n, s, n * 10 + s) for n, s, *_ in items]
    )
    # 9 of 10 values exist in nation: below the default threshold, above 0.9
    conn.executemany(
        "INSERT INTO orphan VALUES (?)", [(n,) for n in [0, 1, 2, 3, 4, 0, 1, 2, 3, 99]]
    )


def _model(tmp_path: Path, monkeypatch: Any) -> Path:
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "statistics"]).exit_code == 0
    db = tmp_path / "shop.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(DDL)
        _rows(conn)
    monkeypatch.setenv("FACT_DSN_SHOP", f"sqlite:///{db}")
    doc = {
        "kind": "source",
        "id": "shop",
        "title": "Shop",
        "source_kind": "warehouse",
        "access_mode": "agent_read",
        "adapter": "sql",
        "engine": "sqlite",
        "location": "shop",
        "dsn_env": "FACT_DSN_SHOP",
    }
    (root / "sources" / "shop.yaml").write_text(dump(doc), encoding="utf-8")
    done = runner.invoke(
        app, ["snapshot", "--root", str(root), "--source", "shop", "--date", "2026-11-02"]
    )
    assert done.exit_code == 0, done.output
    return root


def _propose(root: Path, command: str, *extra: str) -> Any:
    args = ["propose", command, "--root", str(root), "--source", "shop", "--date", "2026-11-02"]
    return runner.invoke(app, [*args, *extra])


def _candidates(doc: dict[str, Any]) -> dict[str, list[list[str]]]:
    return {o["object"]: [c["fields"] for c in o["candidates"]] for o in doc["objects"]}


def test_keys_finds_minimal_keys_and_pairs(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    done = _propose(root, "keys", "--environment", "local", "--data-quality", "synthetic")
    assert done.exit_code == 0, done.output
    assert "5 tables, " in done.output and "key candidates" in done.output
    path = root / "drafts" / "shop" / "keys.yaml"
    doc = load(path).data
    found = _candidates(doc)
    assert found["region"] == [["r_regionkey"], ["r_name"]]
    assert found["nation"] == [["n_nationkey"], ["n_name"]]
    # the composite key; i_note is nullable and i_weight a float, so neither is tried
    assert found["item"] == [["i_nationkey", "i_seq"]]
    assert found["shipment"] == [["s_box"], ["s_nationkey", "s_seq"]]
    assert "orphan" not in found  # repeats, no key
    record = next(r for r in doc["records"] if r["id"] == "ev-propose-key-item-i-nationkey-i-seq")
    assert record["measurement"] == {
        "row_count": 20,
        "non_null": 20,
        "null_count": 0,
        "distinct": 20,
    }
    assert record["status"] == "inferred" and record["data_quality"] == "synthetic"
    for r in doc["records"]:
        EvidenceRecord.model_validate(r)  # every record is a valid evidence record
    assert doc["skipped"] == []
    assert not list((root / "physical" / "entities").glob("*.yaml"))
    text = path.read_text(encoding="utf-8")
    again = _propose(root, "keys", "--environment", "local", "--data-quality", "synthetic")
    assert again.exit_code == 0 and "unchanged" in again.output
    assert path.read_text(encoding="utf-8") == text  # a second run changes nothing


def test_keys_single_columns_only(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    done = _propose(root, "keys", "--max-columns", "1")
    assert done.exit_code == 0, done.output
    found = _candidates(load(root / "drafts" / "shop" / "keys.yaml").data)
    assert "item" not in found and found["shipment"] == [["s_box"]]


def test_joins_recover_inclusions_and_list_the_rest(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    for command in ("keys", "joins"):
        done = _propose(root, command, "--environment", "local", "--data-quality", "synthetic")
        assert done.exit_code == 0, done.output
    doc = load(root / "drafts" / "shop" / "joins.yaml").data
    joins = {c["join"]: c for c in doc["candidates"]}
    expected = {
        # the three real links, and the composite one read backwards (both pairs are unique)
        "nation.n_regionkey = region.r_regionkey": "many_to_one",
        "item.i_nationkey = nation.n_nationkey": "many_to_one",
        "shipment.s_nationkey = item.i_nationkey AND shipment.s_seq = item.i_seq": "one_to_one",
        "item.i_nationkey = shipment.s_nationkey AND item.i_seq = shipment.s_seq": "one_to_one",
        # not links, listed because the values happen to be included; each with its reason
        "shipment.s_nationkey = nation.n_nationkey": "many_to_one",  # true, but through item
        "item.i_rank = region.r_regionkey": "many_to_one",  # ranks 0..2 look like region keys
        "item.i_rank = nation.n_nationkey": "many_to_one",  # ranks 0..2 inside nations 0..4
        "item.i_seq = nation.n_nationkey": "many_to_one",  # sequence 1..4 inside nations 0..4
        "shipment.s_seq = nation.n_nationkey": "many_to_one",  # the same sequence numbers
        "item.i_seq = shipment.s_box": "many_to_one",  # boxes of nation 0 are numbered 1..4
        "region.r_regionkey = nation.n_nationkey": "one_to_one",  # region keys 0..2 inside 0..4
        "item.i_rank = shipment.s_nationkey AND item.i_seq = shipment.s_seq": "many_to_one",
        # (rank, seq) pairs all exist among (nation, seq) pairs: ranks and nations share 0..2
    }
    assert set(joins) == set(expected), sorted(joins)
    assert {k: v["cardinality"] for k, v in joins.items()} == expected
    assert all(
        c["mechanism"] == "inferred_join" and c["status"] == "inferred" for c in joins.values()
    )
    rank = joins["item.i_rank = region.r_regionkey"]
    assert rank["inclusion"] == 1.0 and "names differ" in rank["note"]
    real = joins["nation.n_regionkey = region.r_regionkey"]
    assert "share the suffix regionkey" in real["note"]
    record = next(r for r in doc["records"] if r["id"] == real["evidence"][0])
    assert record["measurement"] == {
        "source_distinct": 3,
        "included": 3,
        "inclusion": 1.0,
        "target_distinct": 3,
        "coverage": 1.0,
    }
    for r in doc["records"]:
        EvidenceRecord.model_validate(r)
    assert "orphan.o_nationkey = nation.n_nationkey" not in joins  # 5 of 6 values: under 0.999


def test_joins_threshold_admits_the_orphan_link(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    done = _propose(root, "joins", "--threshold", "0.8")
    assert done.exit_code == 0, done.output
    doc = load(root / "drafts" / "shop" / "joins.yaml").data
    joins = {c["join"]: c for c in doc["candidates"]}
    assert joins["orphan.o_nationkey = nation.n_nationkey"]["inclusion"] == 0.833333


def test_name_note_never_decides() -> None:
    assert propose.name_note("l_orderkey", "o_orderkey").startswith(
        "names share the suffix orderkey"
    )
    assert propose.name_note("id", "id").startswith("same column name")
    assert propose.name_note("i_rank", "r_regionkey").startswith("names differ")
    assert propose.name_note("key", "orderkey").startswith("key is part of orderkey")


def test_queries_are_counts_only() -> None:
    for query in (
        propose.column_stats("t", ["a", "b"]),
        propose.pair_stats("t", ["a", "b"]),
        propose.inclusion("s", ["a"], "t", ["b"]),
        propose.inclusion("s", ["a", "b"], "t", ["c", "d"]),
    ):
        sql = query.sql(dialect="duckdb", identify=True)
        assert sql.upper().startswith("SELECT")
        assert "COUNT(" in sql.upper()
        assert "*" not in sql.replace("COUNT(*)", "")


def test_propose_needs_a_live_source(tmp_path: Path) -> None:
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "statistics"]).exit_code == 0
    done = runner.invoke(app, ["propose", "keys", "--root", str(root), "--source", "nothing"])
    assert done.exit_code == 1 and "not registered" in done.output

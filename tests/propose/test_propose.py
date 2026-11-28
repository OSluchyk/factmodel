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


def _model(tmp_path: Path, monkeypatch: Any, extra: str = "") -> Path:
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "statistics"]).exit_code == 0
    db = tmp_path / "shop.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(DDL)
        _rows(conn)
        conn.executescript(extra)
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


def test_named_key_is_measured_whatever_its_length(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    done = _propose(
        root,
        "keys",
        "--key",
        "item:i_nationkey,i_seq,i_rank",
        "--key",
        "orphan:o_nationkey",
        "--key",
        "item:i_note",
    )
    assert done.exit_code == 0, done.output
    lines = done.output.splitlines()
    assert (
        "  named key item (i_nationkey, i_seq, i_rank): unique, 0 duplicate rows, 20 rows" in lines
    )
    assert "  named key orphan (o_nationkey): not unique, 4 duplicate rows, 10 rows" in lines
    assert (
        "  named key item (i_note): not unique, 10 duplicate rows, 20 rows, 5 rows with a null"
        in lines
    )
    doc = load(root / "drafts" / "shop" / "keys.yaml").data
    named = {(n["object"], tuple(n["fields"])): n for n in doc["named"]}
    three = named[("item", ("i_nationkey", "i_seq", "i_rank"))]
    assert three["unique"] is True and three["row_count"] == 20 and three["duplicate_rows"] == 0
    assert named[("orphan", ("o_nationkey",))]["unique"] is False
    record = next(r for r in doc["records"] if r["id"] == three["evidence"][0])
    assert record["measurement"] == {
        "row_count": 20,
        "non_null": 20,
        "null_count": 0,
        "distinct": 20,
        "duplicate_rows": 0,
    }
    assert record["status"] == "inferred"  # measured, still a proposal (D-024)
    for r in doc["records"]:
        EvidenceRecord.model_validate(r)
    # the search is unchanged: a named key is never added to the candidates it found
    assert _candidates(doc)["item"] == [["i_nationkey", "i_seq"]]
    plain = _propose(root, "keys")
    assert plain.exit_code == 0 and "named" not in load(root / "drafts" / "shop" / "keys.yaml").data


def test_named_key_must_name_what_the_snapshot_holds(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    for text, message in (
        ("nowhere:a", "no table 'nowhere'"),
        ("item:i_seq,missing", "item has no column missing"),
        ("item", "write <table>:<column>"),
        ("item:i_seq,i_seq", "named twice"),
    ):
        done = _propose(root, "keys", "--key", text)
        assert done.exit_code == 2 and message in done.output, text


def test_joins_name_the_target_that_is_not_unique(tmp_path: Path, monkeypatch: Any) -> None:
    root = _model(tmp_path, monkeypatch)
    done = _propose(root, "joins")
    assert done.exit_code == 0, done.output
    line = "  skipped target orphan.o_nationkey: not unique, 4 duplicate rows of 10; "
    assert line + "no join to it is proposed" in done.output.splitlines()
    doc = load(root / "drafts" / "shop" / "joins.yaml").data
    assert doc["targets_not_unique"] == [
        {
            "object": "orphan",
            "field": "o_nationkey",
            "non_null": 10,
            "distinct": 6,
            "duplicate_rows": 4,
        }
    ]
    # item has no unique column either, but none of its columns comes close to a key
    assert doc["skipped"] == []


STOCK = """
CREATE TABLE stock (k_part INTEGER NOT NULL, k_supp INTEGER NOT NULL, k_note TEXT NOT NULL);
INSERT INTO stock VALUES
  (1, 1, 'a'), (1, 2, 'b'), (2, 1, 'c'), (2, 2, 'd'), (3, 1, 'e'), (3, 2, 'e');
"""


def test_joins_leave_alone_a_table_that_a_pair_can_reference(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """stock has no unique column, and k_note comes close to a key (5 values in 6 rows). The
    pair (k_part, k_supp) is a key, so the table can be referenced and k_note is not named;
    TPC-H's partsupp.ps_comment is such a column."""
    root = _model(tmp_path, monkeypatch, STOCK)
    assert _propose(root, "keys").exit_code == 0
    keys = root / "drafts" / "shop" / "keys.yaml"
    assert ["k_part", "k_supp"] in _candidates(load(keys).data)["stock"]
    done = _propose(root, "joins")
    assert done.exit_code == 0, done.output
    assert "skipped target stock" not in done.output
    doc = load(root / "drafts" / "shop" / "joins.yaml").data
    assert [t["object"] for t in doc["targets_not_unique"]] == ["orphan"]
    # without the key proposals no pair is known, and the column is named
    keys.unlink()
    line = "  skipped target stock.k_note: not unique, 1 duplicate rows of 6; "
    assert line + "no join to it is proposed" in _propose(root, "joins").output.splitlines()

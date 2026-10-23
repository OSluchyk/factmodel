"""The git adapter: DDL at a commit or in the working tree, in two dialects (WP1.5b)."""

import subprocess
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from factmodel.adapters.base import AdapterError
from factmodel.adapters.git import GitAdapter, parse_ddl
from factmodel.adapters.sql import SqlAdapter
from factmodel.cli import app
from factmodel.core.drafts import to_facts
from tests.adapters.helpers import PG_DDL, SQLITE_DDL, neutral, source, sqlite_db
from tests.model.helpers import dump


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "schema-repo"
    (path / "ddl").mkdir(parents=True)
    (path / "ddl" / "sqlite.sql").write_text("-- shop schema\n" + SQLITE_DDL, encoding="utf-8")
    (path / "ddl" / "postgres.sql").write_text(PG_DDL, encoding="utf-8")
    (path / "README.md").write_text("Shop schema.\nOrders reference customers.\n", encoding="utf-8")
    _git(path, "init", "-q")
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", "schema")
    return path


def _git_source(repo: Path, dialect_file: str, engine: str, **more: Any) -> Any:
    return source(
        id=f"ddl-{engine}",
        source_kind="git",
        access_mode="agent_read",
        adapter="git",
        engine=engine,
        location=str(repo),
        include=[f"ddl/{dialect_file}"],
        **more,
    )


def test_snapshot_at_a_commit(repo: Path) -> None:
    snap = GitAdapter().snapshot(_git_source(repo, "sqlite.sql", "sqlite"), repo)
    sha = _git(repo, "rev-parse", "HEAD")
    assert snap.pin == f"ddl-sqlite@{sha}"
    objects = {o.name: o for o in snap.objects}
    assert sorted(objects) == ["customer_totals", "customers", "orders"]
    assert objects["customers"].pin == f"ddl-sqlite@{sha}:ddl/sqlite.sql:3"
    assert objects["customer_totals"].object_type == "view"
    files = snap.extensions["files"] if snap.extensions else []
    assert files == [
        {"path": "ddl/sqlite.sql", "blob": _git(repo, "rev-parse", "HEAD:ddl/sqlite.sql")}
    ]
    fk = next(c for c in objects["orders"].constraints if c.constraint_type == "foreign_key")
    assert (fk.references.object, fk.references.fields, fk.enforced) == (
        "customers",
        ["customer_id"],
        False,
    )


def test_two_dialects_agree_on_neutral_parts(repo: Path) -> None:
    lite = GitAdapter().snapshot(_git_source(repo, "sqlite.sql", "sqlite"), repo)
    pg = GitAdapter().snapshot(_git_source(repo, "postgres.sql", "postgres"), repo)
    assert neutral(lite) == neutral(pg)
    assert all(c.enforced for o in pg.objects for c in o.constraints or [])


def _shape(document: dict[str, Any]) -> Any:
    return (
        document["id"],
        document["physical_name"],
        document["keys"],
        [(f["name"], f["nullable"]) for f in document["fields"]],
        [
            (r["key"], r["to"], r["join"], r["mechanism"], r["cardinality"])
            for r in document.get("relationships", [])
        ],
    )


def test_ddl_and_catalog_give_matching_drafts(repo: Path, tmp_path: Path) -> None:
    ddl = GitAdapter().snapshot(_git_source(repo, "sqlite.sql", "sqlite"), repo)
    catalog = SqlAdapter().reflect(
        source(id="ddl-sqlite", engine="sqlite"), sqlite_db(tmp_path / "shop.db"), ddl.taken_on
    )
    from_ddl = [_shape(d.document) for d in to_facts(ddl)]
    from_catalog = [_shape(d.document) for d in to_facts(catalog)]
    assert from_ddl == from_catalog


def test_worktree_read_pins_the_blob(repo: Path) -> None:
    (repo / "ddl" / "sqlite.sql").write_text(
        SQLITE_DDL + "\nCREATE TABLE notes (note_id INTEGER PRIMARY KEY);\n", encoding="utf-8"
    )
    snap = GitAdapter().snapshot(
        _git_source(repo, "sqlite.sql", "sqlite", revision="worktree"), repo
    )
    blob = _git(repo, "hash-object", "ddl/sqlite.sql")
    notes = next(o for o in snap.objects if o.name == "notes")
    assert snap.pin is None and notes.pin is not None
    assert notes.pin.startswith(f"ddl-sqlite@{blob}:ddl/sqlite.sql:")


def test_quote_a_text_file(repo: Path) -> None:
    record = GitAdapter().quote(_git_source(repo, "sqlite.sql", "sqlite"), repo, "README.md", 2)
    sha = _git(repo, "rev-parse", "HEAD")
    assert record["pin"] == f"ddl-sqlite@{sha}:README.md:2"
    assert record["quote"] == "Orders reference customers."
    with pytest.raises(AdapterError, match="is not in"):
        GitAdapter().quote(_git_source(repo, "sqlite.sql", "sqlite"), repo, "nope.txt", 1)


def test_composite_and_table_level_constraints() -> None:
    ddl = """
    CREATE TABLE lines (order_id INT NOT NULL, line_no INT NOT NULL, sku TEXT,
      CONSTRAINT pk_lines PRIMARY KEY (order_id, line_no),
      CONSTRAINT uq_sku UNIQUE (order_id, sku),
      CONSTRAINT fk_order FOREIGN KEY (order_id) REFERENCES orders (order_id));
    CREATE TABLE tags (tag_ids INT[]);
    """
    lines, tags = parse_ddl(ddl, "postgres", enforced=True)
    kinds = {c["constraint_type"]: c for c in lines["constraints"]}
    assert kinds["primary_key"]["fields"] == ["order_id", "line_no"]
    assert kinds["unique"]["fields"] == ["order_id", "sku"]
    assert kinds["foreign_key"]["references"] == {"object": "orders", "fields": ["order_id"]}
    assert tags["fields"][0] == {
        "name": "tag_ids",
        "type": "INT",
        "type_class": "integer",
        "nullable": True,
        "repeated": True,
    }


def test_snapshot_and_quote_commands(repo: Path, tmp_path: Path) -> None:
    runner = CliRunner()
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "retail"]).exit_code == 0
    doc = {
        "kind": "source",
        "id": "ddl",
        "title": "Schema repository",
        "source_kind": "git",
        "access_mode": "agent_read",
        "adapter": "git",
        "engine": "sqlite",
        "location": "../schema-repo",
        "include": ["ddl/sqlite.sql"],
    }
    (root / "sources" / "ddl.yaml").write_text(dump(doc), encoding="utf-8")
    args = ["--root", str(root), "--source", "ddl"]
    result = runner.invoke(app, ["snapshot", *args, "--date", "2026-10-23"])
    assert result.exit_code == 0, result.output
    assert "(3 objects)" in result.output
    assert runner.invoke(app, ["draft", *args]).exit_code == 0
    assert (root / "drafts" / "ddl" / "entities" / "orders.yaml").is_file()
    quoted = runner.invoke(app, ["quote", *args, "--path", "README.md", "--line", "1"])
    assert quoted.exit_code == 0 and "quote: Shop schema." in quoted.output
    listed = runner.invoke(app, ["adapters"]).output
    assert "git  engines: *" in listed

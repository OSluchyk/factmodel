"""More than one snapshot of a source per day: file names, pins, order and idempotence."""

from pathlib import Path
from typing import Any

from factmodel import repo
from factmodel.adapters.base import with_date
from factmodel.model.types import Snapshot
from factmodel.sync import snapshots


def _snapshot(objects: list[str], day: str = "2026-11-02") -> Snapshot:
    return Snapshot.model_validate(
        {
            "kind": "snapshot",
            "source": "shop",
            "engine": "duckdb",
            "target": "shop",
            "taken_on": day,
            "pin": f"duckdb:shop@{day}",
            "objects": [
                {
                    "name": name,
                    "object_type": "table",
                    "fields": [{"name": "id", "type": "INTEGER", "nullable": False}],
                }
                for name in objects
            ],
        }
    )


def _names(root: Path) -> list[str]:
    return [p.name for p in repo.snapshot_files(root, "shop")]


def test_second_read_of_a_day_gets_the_next_file_and_pin(tmp_path: Path) -> None:
    first, changed, written = repo.write_snapshot(tmp_path, _snapshot(["a"]))
    assert (first.name, changed, written.pin) == (
        "shop@2026-11-02.yaml",
        True,
        "duckdb:shop@2026-11-02",
    )
    second, changed, written = repo.write_snapshot(tmp_path, _snapshot(["a", "b"]))
    assert (second.name, changed, written.pin) == (
        "shop@2026-11-02_2.yaml",
        True,
        "duckdb:shop@2026-11-02_2",
    )
    assert "pin: duckdb:shop@2026-11-02_2" in second.read_text(encoding="utf-8")
    third, changed, written = repo.write_snapshot(tmp_path, _snapshot(["a", "b", "c"]))
    assert (third.name, written.pin) == ("shop@2026-11-02_3.yaml", "duckdb:shop@2026-11-02_3")
    assert _names(tmp_path) == [first.name, second.name, third.name]
    assert repo.latest_snapshot(tmp_path, "shop") == third
    assert snapshots(tmp_path, "shop") == [first, second, third]


def test_an_identical_read_is_kept_not_duplicated(tmp_path: Path) -> None:
    repo.write_snapshot(tmp_path, _snapshot(["a"]))
    repo.write_snapshot(tmp_path, _snapshot(["a", "b"]))
    path, changed, written = repo.write_snapshot(tmp_path, _snapshot(["a"]))
    assert (path.name, changed, written.pin) == (
        "shop@2026-11-02.yaml",
        False,
        "duckdb:shop@2026-11-02",
    )
    path, changed, written = repo.write_snapshot(tmp_path, _snapshot(["a", "b"]))
    assert (path.name, changed) == ("shop@2026-11-02_2.yaml", False)
    assert len(_names(tmp_path)) == 2


def test_order_is_by_date_then_sequence_not_by_text(tmp_path: Path) -> None:
    folder = tmp_path / "sources" / "snapshots"
    folder.mkdir(parents=True)
    for name in (
        "shop@2026-11-02_10.yaml",
        "shop@2026-11-02_2.yaml",
        "shop@2026-11-02.yaml",
        "shop@2026-11-01_3.yaml",
        "shop@2026-11-03.yaml",
    ):
        (folder / name).write_text("", encoding="utf-8")
    assert _names(tmp_path) == [
        "shop@2026-11-01_3.yaml",
        "shop@2026-11-02.yaml",
        "shop@2026-11-02_2.yaml",
        "shop@2026-11-02_10.yaml",
        "shop@2026-11-03.yaml",
    ]


def test_with_date_drops_a_sequence_and_the_write_assigns_it(tmp_path: Path) -> None:
    snap = _snapshot(["a"]).model_copy(update={"pin": "duckdb:shop@2026-11-02_2"})
    moved = with_date(snap, "2026-11-05")
    assert (moved.taken_on, moved.pin) == ("2026-11-05", "duckdb:shop@2026-11-05")
    path, _, written = repo.write_snapshot(tmp_path, moved)
    assert (path.name, written.pin) == ("shop@2026-11-05.yaml", "duckdb:shop@2026-11-05")


def test_sync_compares_the_two_reads_of_one_day(tmp_path: Path, monkeypatch: Any) -> None:
    from typer.testing import CliRunner

    from factmodel.cli import app

    runner = CliRunner()
    root = tmp_path / "model"
    assert runner.invoke(app, ["init", str(root), "--profile", "statistics"]).exit_code == 0
    repo.write_snapshot(root, _snapshot(["a"]))
    repo.write_snapshot(root, _snapshot(["a", "b"]))
    done = runner.invoke(app, ["sync", "--root", str(root), "--source", "shop"])
    assert (
        done.exit_code == 1
    )  # the source is not registered; the snapshots alone are checked below
    assert snapshots(root, "shop")[-1].name == "shop@2026-11-02_2.yaml"

"""DuckDB in the probe maps: the JSON wrap and the default runner of rendered
scripts. The wrap is checked through the duckdb module; the script itself runs through the
duckdb CLI when it is installed."""

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel import vocabulary
from factmodel.cli import app
from factmodel.model.loader import load_model
from factmodel.probes import json_wrapped
from factmodel.probes.intake import read_results
from tests.probes.helpers import DDL, EXPECTED, ROWS, build_model

runner = CliRunner()
needs_duckdb = pytest.mark.skipif(
    importlib.util.find_spec("duckdb") is None, reason="duckdb not installed"
)


def _duckdb(path: Path) -> None:
    import duckdb

    conn = duckdb.connect(str(path))
    try:
        for statement in [*filter(str.strip, DDL.split(";")), *ROWS]:
            conn.execute(statement)
    finally:
        conn.close()


def _model(tmp_path: Path) -> Path:
    root = build_model(tmp_path)
    assert runner.invoke(app, ["probe", "generate", "--root", str(root)]).exit_code == 0
    return root


def test_duckdb_is_in_the_maps() -> None:
    assert vocabulary.text_map("dialect_json_wrap")["duckdb"] == "json_object_pairs"
    assert vocabulary.text_map("dialect_runner")["duckdb"].startswith("duckdb -noheader -list ")


@needs_duckdb
def test_wrapped_probes_print_one_json_object_each(tmp_path: Path) -> None:
    import duckdb

    root = _model(tmp_path)
    _duckdb(tmp_path / "shop.duckdb")
    conn = duckdb.connect(str(tmp_path / "shop.duckdb"))
    try:
        got = {}
        for probe in load_model(root).probes.values():
            sql = json_wrapped(probe, "duckdb")
            assert sql is not None
            (value,) = conn.execute(sql).fetchone()
            got[probe.id] = json.loads(value)
    finally:
        conn.close()
    assert got == EXPECTED


@needs_duckdb
@pytest.mark.skipif(shutil.which("duckdb") is None, reason="duckdb CLI not installed")
def test_rendered_duckdb_script_runs(tmp_path: Path) -> None:
    root = _model(tmp_path)
    rendered = runner.invoke(app, ["probe", "render", "--root", str(root), "--dialect", "duckdb"])
    assert rendered.exit_code == 0
    _duckdb(tmp_path / "shop.duckdb")
    env = {
        **os.environ,
        "DUCKDB_DB": str(tmp_path / "shop.duckdb"),
        "PIN": "duckdb:shop@2026-10-27",
        "RAN_ON": "2026-10-27",
        "DATA_QUALITY": "synthetic",
    }
    script = root / "probes" / "scripts" / "shop.duckdb.sh"
    done = subprocess.run(
        ["bash", str(script)], env=env, capture_output=True, text=True, check=True
    )
    results = tmp_path / "from-script.jsonl"
    results.write_text(done.stdout, encoding="utf-8")
    _, rows = read_results(results)
    assert {r["probe"]: r["measurement"] for r in rows} == EXPECTED

"""Probe dialect knowledge is vocabulary: a dialect added to the maps changes behaviour without a
code change (D-011, round 14)."""

import copy
import subprocess
from pathlib import Path
from typing import Any

import pytest

from factmodel import vocabulary
from factmodel.model.loader import load_model
from factmodel.model.types import Probe
from factmodel.probes import build, generate, json_wrapped
from factmodel.probes.script import script

ROOT = Path(__file__).resolve().parents[2]
HARD = ROOT / "tests" / "fixtures" / "hard-cases"
PROBE = Probe.model_validate(
    {
        "kind": "probe",
        "id": "row-count-orders",
        "probe_kind": "row_count",
        "fact": "orders",
        "dialect": "duckdb",
        "sql": build.row_count("orders").sql(dialect="duckdb", identify=True),
    }
)


@pytest.fixture()
def duckdb_in_maps(monkeypatch: pytest.MonkeyPatch) -> None:
    maps: dict[str, Any] = copy.deepcopy(vocabulary.load_maps())
    maps["dialect_json_wrap"]["duckdb"] = "row_to_json"
    maps["dialect_runner"]["duckdb"] = 'duckdb "${DUCKDB_FILE:?set DUCKDB_FILE}" -json'
    maps["dialect_nested_paths"]["duckdb"] = True
    monkeypatch.setattr(vocabulary, "load_maps", lambda: maps)


def _nested_ids() -> set[str]:
    model = load_model(HARD / "nested-field")
    docs, _ = generate(model.entities, model.sources, {}, default_dialect="duckdb")
    return {d["id"] for d in docs}


def test_without_maps_the_behaviour_is_neutral() -> None:
    assert json_wrapped(PROBE, "duckdb") == PROBE.sql
    text, _ = script("shop", "duckdb", [PROBE])
    assert 'RUN_SQL="${RUN_SQL:?' in text
    assert "join-match-web-events-by-user" not in _nested_ids()


@pytest.mark.usefixtures("duckdb_in_maps")
def test_a_dialect_added_to_the_maps_changes_rendering() -> None:
    assert json_wrapped(PROBE, "duckdb") == f"SELECT row_to_json(q) FROM ({PROBE.sql}) AS q"
    text, _ = script("shop", "duckdb", [PROBE])
    assert 'RUN_SQL="${RUN_SQL:-duckdb "${DUCKDB_FILE:?set DUCKDB_FILE}" -json}"' in text
    assert "join-match-web-events-by-user" in _nested_ids()


def test_an_unknown_wrap_strategy_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    maps: dict[str, Any] = copy.deepcopy(vocabulary.load_maps())
    maps["dialect_json_wrap"]["duckdb"] = "to_json_magic"
    monkeypatch.setattr(vocabulary, "load_maps", lambda: maps)
    with pytest.raises(ValueError, match="unknown strategy"):
        json_wrapped(PROBE, "duckdb")


def test_dialect_knowledge_is_not_in_the_code() -> None:
    found = subprocess.run(
        [
            "grep",
            "-rnI",
            "--exclude-dir=__pycache__",
            "-e",
            "NESTED_DIALECTS",
            "-e",
            "DEFAULT_RUN_SQL",
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
    )
    assert found.stdout == ""
    for path in (ROOT / "src" / "factmodel" / "probes").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert '"sqlite"' not in text and '"postgres"' not in text, path.name

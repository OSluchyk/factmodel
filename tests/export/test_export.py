"""Exporters (WP3.5): both examples to dbt (validated with dbt parse when dbt-core is installed)
and to Apache Ossie (structural tests against the pinned core specification, 0.2.0.dev0)."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import sqlglot
from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.export import dbt, ossie
from factmodel.io.yaml_strict import loads
from factmodel.model.loader import load_model

ROOT = Path(__file__).resolve().parents[2]
LAYERS = {"qcew": "employment-wages", "chinook": "customer-purchases"}
runner = CliRunner()
TIME_SPINE = """models:
  - name: metricflow_time_spine
    time_spine:
      standard_granularity_column: date_day
    columns:
      - name: date_day
        granularity: day
"""


def _model(example: str):  # type: ignore[no-untyped-def]
    return load_model(ROOT / "examples" / example)


@pytest.mark.parametrize("example", sorted(LAYERS))
def test_dbt_export_shape(example: str) -> None:
    model, layer = _model(example), LAYERS[example]
    result = dbt.export(model, layer)
    doc = loads(result.files[f"{layer}.yml"], "x").data
    names = {m["name"] for m in doc["semantic_models"]}
    assert names == {e.entity.replace("-", "_") for e in model.layers[layer].entities}
    for sm in doc["semantic_models"]:
        assert sm["config"]["meta"]["factmodel_evidence_status"] in ("confirmed", "inferred")
    metrics = {m["name"]: m for m in doc["metrics"]}
    if example == "qcew":
        assert (
            "{{ Dimension('qtrly__disclosure_code') }} IS NULL"
            in metrics["employment_month3"]["filter"]
        )
        assert "filter" not in metrics["establishments"]  # suppressed cells included
        assert "annual_employment" not in metrics  # read at its grain: no metric
        derived = metrics["avg_weekly_wage"]  # a formula over exported metrics (M3 answer Q4)
        assert derived["type"] == "derived"
        assert derived["type_params"]["expr"] == "total_wages / employment_avg / 13"
        assert not any("avg_weekly_wage" in w for w in result.warnings)
        assert any("annual_employment: aggregation none" in w for w in result.warnings)
        assert any("level_matrix: a values table" in w for w in result.warnings)
        assert any("distinct_areas" in w for w in result.warnings)
    else:
        assert set(metrics) == {"revenue", "tracks_bought", "customers_active"}
        assert result.warnings == []


@pytest.mark.skipif(shutil.which("dbt") is None, reason="dbt-core not installed")
@pytest.mark.parametrize("example", sorted(LAYERS))
def test_dbt_parse_accepts_the_export(example: str, tmp_path: Path) -> None:
    model, layer = _model(example), LAYERS[example]
    project = tmp_path / "project"
    (project / "models").mkdir(parents=True)
    (project / "dbt_project.yml").write_text(
        "name: fm\nversion: '1.0'\nconfig-version: 2\nprofile: fm\nmodel-paths: [models]\n"
    )
    (project / "profiles.yml").write_text(
        "fm:\n  target: dev\n  outputs:\n    dev:\n      type: duckdb\n"
        f"      path: {tmp_path / 'x.duckdb'}\n"
    )
    for item in model.layers[layer].entities:
        (project / "models" / f"{item.entity}.sql").write_text("select 1 as x\n")
    (project / "models" / "metricflow_time_spine.sql").write_text(
        "select cast('2024-01-01' as date) as date_day\n"
    )
    (project / "models" / "time_spine.yml").write_text(TIME_SPINE)
    for name, text in dbt.export(model, layer).files.items():
        (project / "models" / name).write_text(text)
    env = {**os.environ, "DBT_SEND_ANONYMOUS_USAGE_STATS": "false", "DO_NOT_TRACK": "1"}
    args = ["dbt", "parse", "--no-version-check", "--project-dir", str(project)]
    done = subprocess.run(
        [*args, "--profiles-dir", str(project)], capture_output=True, text=True, env=env
    )
    assert done.returncode == 0, done.stdout[-2000:]
    manifest = json.loads((project / "target" / "semantic_manifest.json").read_text())
    exported = loads(dbt.export(model, layer).files[f"{layer}.yml"], "x").data
    assert len(manifest["metrics"]) == len(exported["metrics"])
    assert len(manifest["semantic_models"]) == len(exported["semantic_models"])


# the keys the pinned Ossie core specification (0.2.0.dev0, read 2026-10-27) names
NAMED = {
    "model": {
        "version",
        "name",
        "description",
        "ai_context",
        "datasets",
        "relationships",
        "metrics",
        "custom_extensions",
    },
    "dataset": {"name", "source", "primary_key", "unique_keys", "description", "fields"}
    | {"ai_context", "metrics", "custom_extensions"},
    "field": {"name", "expression", "dimension", "label", "description", "datatype"}
    | {"ai_context", "custom_extensions"},
    "relationship": {"name", "from", "to", "from_columns", "to_columns", "ai_context"}
    | {"custom_extensions"},
    "metric": {"name", "expression", "description", "datatype", "ai_context"}
    | {"custom_extensions"},
}
DATATYPES = {"String", "Integer", "Decimal", "Float", "Boolean", "Date", "Time", "DateTime"}
DATATYPES |= {"DateTimeTz", "Opaque"}


def _vendor(node: dict[str, object]) -> dict[str, object]:
    (extension,) = node["custom_extensions"]  # type: ignore[misc]
    assert extension["vendor_name"] == ossie.VENDOR
    data: dict[str, object] = json.loads(extension["data"])
    return data


@pytest.mark.parametrize("example", sorted(LAYERS))
def test_ossie_export_uses_only_the_pinned_structure(example: str) -> None:
    model, layer = _model(example), LAYERS[example]
    result = ossie.export(model, layer)
    doc = loads(result.files[f"{layer}.ossie.yaml"], "x").data
    assert "semantic_model" not in doc and set(doc) <= NAMED["model"]
    assert doc["version"] == ossie.PINNED_VERSION == "0.2.0.dev0"
    assert {"version", "name", "datasets"} <= set(doc) and doc["datasets"]
    assert set(doc["ai_context"]) == {"instructions"}
    found = model.layers[layer]
    assert [d["name"] for d in doc["datasets"]] == [e.entity for e in found.entities]
    fields: dict[str, set[str]] = {}
    for dataset in doc["datasets"]:
        assert set(dataset) <= NAMED["dataset"] and {"name", "source"} <= set(dataset)
        fields[dataset["name"]] = {f["name"] for f in dataset["fields"]}
        assert set(dataset["primary_key"]) <= fields[dataset["name"]]  # fields, not columns
        assert _vendor(dataset)["evidence_status"] in ("confirmed", "inferred")
        for field in dataset["fields"]:
            assert set(field) <= NAMED["field"] and {"name", "expression"} <= set(field)
            assert set(field.get("dimension", {})) <= {"is_time"}
            assert field.get("datatype", "String") in DATATYPES
            for entry in field["expression"]["dialects"]:
                sqlglot.parse_one(entry["expression"], read=entry["dialect"])
    held = set()
    for rel in doc.get("relationships", []):
        assert set(rel) <= NAMED["relationship"]
        assert len(rel["from_columns"]) == len(rel["to_columns"]) > 0
        assert set(rel["from_columns"]) <= fields[rel["from"]]
        assert set(rel["to_columns"]) <= fields[rel["to"]]
        held.add(rel["name"].replace("__", "."))
    assert held, "every example layer has an equality join"
    assert [m["name"] for m in doc["metrics"]] == [m.id for m in found.measures or []]
    for metric in doc["metrics"]:
        assert set(metric) <= NAMED["metric"] and set(metric["expression"]) == {"dialects"}
        for entry in metric["expression"]["dialects"]:
            tree = sqlglot.parse_one(entry["expression"], read=entry["dialect"])
            for column in tree.find_all(sqlglot.exp.Column):  # model-scoped: dataset.field
                assert column.name in fields[column.table], (metric["name"], column.sql())
        assert "aggregation" in _vendor(metric)
    extension = _vendor(doc)
    assert extension["layer_status"] == found.status
    instructions = doc["ai_context"]["instructions"]
    for concept in found.concepts or []:
        if concept.required:
            assert f"- {concept.id}:" in instructions
            assert concept.id in extension["required_concepts"]  # type: ignore[operator]
    for ref in found.joins or []:
        assert (ref in held) != (ref in instructions)  # a key or text, never both or neither
    for hazard in found.hazards or []:
        assert f"Hazard {hazard}" in instructions
    assert "Evidence status:" in instructions
    assert any(ossie.SPEC_URL in w and "0.2.0.dev0" in w for w in result.warnings)


def test_cli_export_writes_files_and_notes(tmp_path: Path) -> None:
    for target, name in (("ossie", "employment-wages.ossie.yaml"), ("dbt", "employment-wages.yml")):
        out = tmp_path / target
        args = ["export", "--root", str(ROOT / "examples" / "qcew"), "--target", target]
        done = runner.invoke(app, [*args, "--layer", "employment-wages", "--out", str(out)])
        assert done.exit_code == 0, done.output
        assert (out / name).is_file()
        assert "What the target cannot hold" in (out / "EXPORT_NOTES.md").read_text()
    bad = runner.invoke(app, ["export", "--target", "cube", "--layer", "x", "--out", str(tmp_path)])
    assert bad.exit_code == 2


def test_volatile_set_writes_only_volatile_probes(tmp_path: Path) -> None:
    root = tmp_path / "qcew"
    shutil.copytree(ROOT / "examples" / "qcew", root, ignore=shutil.ignore_patterns("out"))
    shutil.rmtree(root / "probes")
    done = runner.invoke(app, ["probe", "generate", "--root", str(root), "--set", "volatile"])
    assert done.exit_code == 0, done.output
    kinds = {
        loads((p).read_text(), p.name).data["probe_kind"] for p in (root / "probes").glob("*.yaml")
    }
    assert kinds == {"key_duplicates", "row_count", "value_set", "rollup"}

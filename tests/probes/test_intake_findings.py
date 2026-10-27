"""Intake on a field probe out of range: the finding names the entity in ``about`` and keeps the
field in ``extensions.fact`` (defect fix, D-018), so the gate passes on what intake wrote."""

import os
from pathlib import Path

from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import load
from factmodel.probes.intake import intake
from tests.model.helpers import dump
from tests.probes.helpers import build_model, create_sqlite

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "probes" / "intake-findings"
runner = CliRunner()


def _field_probes_out_of_range(tmp_path: Path) -> Path:
    root = build_model(tmp_path)
    path = root / "physical" / "entities" / "customer.yaml"
    doc = load(path).data
    next(f for f in doc["fields"] if f["name"] == "EmailHash")["values"] = ["h1"]
    path.write_text(dump(doc), encoding="utf-8")
    assert runner.invoke(app, ["probe", "generate", "--root", str(root)]).exit_code == 0
    # the generated null_rate measures only; expect no nulls so its result is out of range
    probe = root / "probes" / "null-rate-order-customer-id.yaml"
    probe.write_text(
        probe.read_text(encoding="utf-8") + "expected:\n  null_rate:\n    max: 0\n",
        encoding="utf-8",
    )
    os.environ["FACT_TEST_SHOP_DSN"] = create_sqlite(tmp_path / "shop.db")
    try:
        args = ["--source", "shop", "--date", "2026-10-23", "--data-quality", "synthetic"]
        assert runner.invoke(app, ["probe", "run", "--root", str(root), *args]).exit_code == 0
    finally:
        del os.environ["FACT_TEST_SHOP_DSN"]
    intake(root, root / "probes" / "results" / "shop@2026-10-23.jsonl")
    return root


def _finding(root: Path, probe: str) -> Path:
    found = [
        p
        for p in sorted((root / "registers" / "findings").glob("F-*.yaml"))
        if load(p).data["extensions"]["probe"] == probe
    ]
    assert len(found) == 1, probe
    return found[0]


def test_field_findings_name_the_entity(tmp_path: Path) -> None:
    root = _field_probes_out_of_range(tmp_path)
    for probe in ("value-set-customer-email-hash", "null-rate-order-customer-id"):
        written = _finding(root, probe).read_text(encoding="utf-8")
        assert written == (GOLDEN / f"{probe}.yaml").read_text(encoding="utf-8").replace(
            "F-NNNN", load(_finding(root, probe)).data["id"]
        )
    relationship = load(_finding(root, "join-match-order-to-customer")).data
    assert relationship["about"] == ["order.to-customer"]
    assert "fact" not in relationship["extensions"]


def test_the_gate_reads_what_intake_wrote(tmp_path: Path) -> None:
    root = _field_probes_out_of_range(tmp_path)
    assert runner.invoke(app, ["project", "--root", str(root)]).exit_code == 0
    report = run_gate(root)
    assert report.passed, "\n".join(report.lines())


def test_intake_twice_changes_nothing(tmp_path: Path) -> None:
    root = _field_probes_out_of_range(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = intake(root, root / "probes" / "results" / "shop@2026-10-23.jsonl")
    assert result.written == []
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before

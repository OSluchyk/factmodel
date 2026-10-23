"""D-014: only representative data confirms a fact; example models may opt out. Golden tests for
both settings of treat_synthetic_as_representative."""

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.core.status import effective_status
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from factmodel.probes.intake import intake
from tests.model.helpers import dump
from tests.probes.helpers import build_model, create_sqlite

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "probes" / "intake-golden"
PROBE = "fan-out-order-to-customer"
runner = CliRunner()


def _intake(tmp_path: Path, data_quality: str, treat: bool | None) -> Path:
    root = build_model(tmp_path)
    if treat is not None:
        config = load(root / "factmodel.yaml").data
        config["treat_synthetic_as_representative"] = treat
        (root / "factmodel.yaml").write_text(dump(config), encoding="utf-8")
    assert runner.invoke(app, ["probe", "generate", "--root", str(root)]).exit_code == 0
    os.environ["FACT_TEST_SHOP_DSN"] = create_sqlite(tmp_path / "shop.db")
    try:
        args = ["--source", "shop", "--date", "2026-10-23", "--data-quality", data_quality]
        assert runner.invoke(app, ["probe", "run", "--root", str(root), *args]).exit_code == 0
    finally:
        del os.environ["FACT_TEST_SHOP_DSN"]
    intake(root, root / "probes" / "results" / "shop@2026-10-23.jsonl")
    return root


@pytest.mark.parametrize(
    ("data_quality", "treat", "golden", "fact_status"),
    [
        ("synthetic", None, "synthetic", "inferred"),
        ("unknown", None, "unknown", "inferred"),
        ("synthetic", True, "treated", "confirmed"),
        ("representative", None, "representative", "confirmed"),
    ],
)
def test_intake_golden(
    tmp_path: Path, data_quality: str, treat: bool | None, golden: str, fact_status: str
) -> None:
    root = _intake(tmp_path, data_quality, treat)
    written = (root / "evidence" / "probes" / f"{PROBE}@2026-10-23.yaml").read_text(
        encoding="utf-8"
    )
    assert written == (GOLDEN / f"{golden}.yaml").read_text(encoding="utf-8")
    model = load_model(root)
    rel = model.entities["order"].relationships[0]
    assert f"ev-{PROBE}-2026-10-23" in (rel.evidence or [])
    assert effective_status(rel.evidence, model.evidence) == fact_status


def test_out_of_range_on_synthetic_data_still_opens_a_finding(tmp_path: Path) -> None:
    root = _intake(tmp_path, "synthetic", None)
    findings = sorted((root / "registers" / "findings").glob("*.yaml"))
    assert [load(p).data["extensions"]["probe"] for p in findings] == [
        "current-row-ties-customer-version",
        "join-match-order-to-customer",
    ]

"""Run fact check and fact project on every hard case (plan WP1.8b)."""

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.gate.runner import stage_specs

CASES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "hard-cases"
CASES = sorted(p.name for p in CASES_DIR.iterdir() if p.is_dir())
FAILED_LINE = re.compile(r"^FAIL  (?P<stage>\S+)")
runner = CliRunner()


def _verdict(case: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((CASES_DIR / case / "expected" / "verdict.json").read_text())
    return data


@pytest.mark.parametrize("case", CASES)
def test_fact_check_gives_the_expected_verdict(case: str) -> None:
    expected = _verdict(case)["failed"]
    result = runner.invoke(app, ["check", "--root", str(CASES_DIR / case)])
    failed = [m["stage"] for line in result.output.splitlines() if (m := FAILED_LINE.match(line))]
    assert failed == expected, result.output
    assert result.exit_code == (1 if expected else 0)


@pytest.mark.parametrize("case", CASES)
def test_fact_project_writes_the_expected_files(case: str, tmp_path: Path) -> None:
    root = tmp_path / case
    shutil.copytree(CASES_DIR / case, root, ignore=shutil.ignore_patterns("expected", "generated"))
    result = runner.invoke(app, ["project", "--root", str(root)])
    if _verdict(case)["project"] == "refused":
        assert result.exit_code == 1
        assert not (root / "generated").exists()
        return
    assert result.exit_code == 0, result.output
    expected_dir = CASES_DIR / case / "expected" / "generated"
    expected = {p.name: p.read_text(encoding="utf-8") for p in expected_dir.iterdir()}
    written = {p.name: p.read_text(encoding="utf-8") for p in (root / "generated").iterdir()}
    assert written == expected


@pytest.mark.parametrize(
    "case", [c for c in CASES if "status_contains" in _verdict(c)], ids=lambda c: c
)
def test_fact_status(case: str) -> None:
    result = runner.invoke(app, ["status", "--root", str(CASES_DIR / case)])
    assert result.exit_code == 0
    for text in _verdict(case)["status_contains"]:
        assert text in result.output


def test_every_gate_stage_has_a_failing_hard_case() -> None:
    failed = {stage for case in CASES for stage in _verdict(case)["failed"]}
    assert failed == {s.name for s in stage_specs() if s.enabled}


def test_every_plan_case_is_present() -> None:
    plan = {
        "soft-delete",
        "key-not-unique",
        "polymorphic",
        "per-tenant-target",
        "nullable-fk",
        "reference-chain",
        "nested-field",
        "stale-evidence",
        "retraction",
    }
    assert plan <= set(CASES)

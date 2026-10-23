from pathlib import Path

from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.core.derived import GENERATED_HEADER
from tests.core import helpers as h
from tests.model.helpers import write_model

VOCABULARY = Path(__file__).resolve().parents[2] / "spec" / "VOCABULARY.md"


def test_header_is_the_one_the_vocabulary_names() -> None:
    assert f"`{GENERATED_HEADER}`" in VOCABULARY.read_text(encoding="utf-8")


def test_project_writes_generated_files_and_is_idempotent(tmp_path: Path) -> None:
    root = write_model(tmp_path, h.vector("projection", "rule-customer-scoped")["input"]["files"])
    runner = CliRunner()
    first = runner.invoke(app, ["project", "--root", str(root)])
    assert first.exit_code == 0, first.output
    assert sorted(p.name for p in (root / "generated").iterdir()) == [
        "labels.tsv",
        "residue.tsv",
        "scope-rejections.tsv",
        "scope.tsv",
    ]
    labels = (root / "generated" / "labels.tsv").read_text(encoding="utf-8").splitlines()
    assert labels == [
        GENERATED_HEADER,
        "relationship\tlabel\ttargets",
        "order_items.part-of\tcustomer_scoped\t-",
        "order_items.sells\tcustomer_scoped\t-",
        "orders.placed-by\tcustomer_scoped\t-",
    ]
    scope = (root / "generated" / "scope.tsv").read_text(encoding="utf-8").splitlines()
    assert "order_items\ttransitive\tunique_target\torder_items.part-of\ttrue" in scope
    before = {p.name: p.read_text(encoding="utf-8") for p in (root / "generated").iterdir()}
    second = runner.invoke(app, ["project", "--root", str(root)])
    assert second.exit_code == 0
    assert "up to date" in second.output
    after = {p.name: p.read_text(encoding="utf-8") for p in (root / "generated").iterdir()}
    assert after == before


def test_project_refuses_a_broken_model(tmp_path: Path) -> None:
    files = h.vector("projection", "rule-customer-scoped")["input"]["files"]
    next(f for f in files if f.get("id") == "orders")["evidence"] = ["ev-missing"]
    root = write_model(tmp_path, files)
    result = CliRunner().invoke(app, ["project", "--root", str(root)])
    assert result.exit_code == 1
    assert "ev-missing" in result.output
    assert not (root / "generated").exists()

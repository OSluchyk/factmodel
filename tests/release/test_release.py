"""Release projection (WP3.4): both examples release cleanly; every refusal; internal notes;
append-only release notes; the reduced release gate."""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from factmodel.cli import app
from factmodel.io.yaml_strict import load
from factmodel.release.build import ReleaseError, build, strip_internal
from factmodel.release.check import check
from factmodel.vocabulary import load as vocabulary

ROOT = Path(__file__).resolve().parents[2]
DAY = "2026-10-27"
runner = CliRunner()


@pytest.mark.parametrize("example", ["chinook", "qcew"])
def test_examples_release_into_release_out_and_read_cleanly(example: str) -> None:
    root = ROOT / "examples" / example
    out = root / "release" / "out"  # gitignored
    shutil.rmtree(out, ignore_errors=True)
    result = build(root, out, "0.1.0", DAY)
    assert result.count("export") > 0 and result.count("project") > 0
    report = check(out)
    assert report.passed, "\n".join(report.lines())
    derived = set(vocabulary()["derived_value"])
    for path in out.rglob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        data = load(path).data
        if isinstance(data, dict) and data.get("kind") == "entity":
            assert "extensions" not in data
            assert not derived & set(data), path
        if isinstance(data, dict) and data.get("kind") == "source":
            assert "access" not in data and "dsn_env" not in data
        assert "@example.invalid" not in text
    assert not (out / "seed").exists() and not (out / "drafts").exists()
    version = (out / "VERSION").read_text(encoding="utf-8")
    assert "release: 0.1.0" in version and "schema_version: " in version
    # the model's own gate ignores the built release
    assert runner.invoke(app, ["check", "--root", str(root)]).exit_code == 0


def _copy(tmp_path: Path, example: str = "chinook") -> Path:
    root = tmp_path / example
    shutil.copytree(ROOT / "examples" / example, root, ignore=shutil.ignore_patterns("out"))
    return root


def test_an_unmatched_file_refuses_the_release(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    allowlist = root / "release" / "allowlist.yaml"
    text = allowlist.read_text(encoding="utf-8")
    allowlist.write_text(text.replace("- {pattern: '**', disposition: refuse", "# -"), "utf-8")
    with pytest.raises(ReleaseError, match="unmatched"):
        build(root, tmp_path / "out", "0.1.0", DAY)


def test_an_undeclared_key_refuses_the_release(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    allowlist = root / "release" / "allowlist.yaml"
    text = allowlist.read_text(encoding="utf-8")
    allowlist.write_text(
        text.replace("    drop: [access, dsn_env, revision, include, extensions]\n", ""), "utf-8"
    )
    with pytest.raises(ReleaseError, match="undeclared_key"):
        build(root, tmp_path / "out", "0.1.0", DAY)


def test_a_failing_gate_refuses_the_release(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "generated" / "labels.tsv").write_text("stale\n", encoding="utf-8")
    with pytest.raises(ReleaseError, match="generated-fresh"):
        build(root, tmp_path / "out", "0.1.0", DAY)


def test_an_equivalence_drop_refuses_the_release(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    path = root / "equivalence" / "last-run.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    item = sorted(data["layers"]["customer-purchases"]["items"])[0]
    data["layers"]["customer-purchases"]["items"][item]["outcome"] = "fail"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ReleaseError, match=f"dropped against its accepted run: {item}"):
        build(root, tmp_path / "out", "0.1.0", DAY)


def test_internal_notes_are_stripped_and_must_close(tmp_path: Path) -> None:
    text = "keep\n<!-- internal:begin -->\nsecret plan\n<!-- internal:end -->\nkeep too\n"
    assert strip_internal(text, "x.md") == "keep\nkeep too\n"
    with pytest.raises(ReleaseError, match="never closed"):
        strip_internal("a\n# internal:begin\nb\n", "x.md")
    root = _copy(tmp_path)
    readme = root / "README.md"
    readme.write_text(text + readme.read_text(encoding="utf-8"), encoding="utf-8")
    build(root, tmp_path / "out", "0.1.0", DAY)
    released = (tmp_path / "out" / "README.md").read_text(encoding="utf-8")
    assert "secret plan" not in released and released.startswith("keep\nkeep too\n")


def test_release_notes_are_append_only(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    out, before = tmp_path / "out", tmp_path / "v1"
    build(root, out, "0.1.0", DAY)
    shutil.copytree(out, before)
    build(root, out, "0.1.0", DAY)  # the same version again: its section is not rewritten
    assert (out / "RELEASE_NOTES.md").read_text() == (before / "RELEASE_NOTES.md").read_text()
    build(root, out, "0.2.0", "2026-11-01")
    notes = (out / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert notes.index("## 0.1.0 - 2026-10-27") < notes.index("## 0.2.0 - 2026-11-01")
    assert check(out, previous=before).passed
    committed = root / "release" / "RELEASE_NOTES.md"  # the log lives in the model repository
    assert committed.read_text(encoding="utf-8") == notes
    build(root, tmp_path / "fresh", "0.3.0", "2026-11-02")  # a fresh folder keeps the history
    fresh = (tmp_path / "fresh" / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert fresh.startswith(notes.rstrip("\n")) and "## 0.3.0 - 2026-11-02" in fresh
    edited = notes.replace("## 0.1.0 - 2026-10-27", "## 0.1.0 - 2026-10-28")
    (out / "RELEASE_NOTES.md").write_text(edited, encoding="utf-8")
    failed = check(out, previous=before)
    assert failed.failed == ["release"]
    cli = runner.invoke(app, ["check", "--release", str(out), "--previous", str(before)])
    assert cli.exit_code == 1 and "an earlier section of RELEASE_NOTES.md changed" in cli.output


def test_a_folder_that_is_not_a_release_is_never_wiped(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    other = tmp_path / "precious"
    other.mkdir()
    (other / "notes.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(ReleaseError, match="not empty"):
        build(root, other, "0.1.0", DAY)
    assert (other / "notes.txt").read_text() == "mine"


def test_cli_release_and_lookup(tmp_path: Path) -> None:
    root = _copy(tmp_path, "qcew")
    out = tmp_path / "out"
    args = ["release", "--root", str(root), "--out", str(out), "--version", "0.1.0", "--date", DAY]
    done = runner.invoke(app, args)
    assert done.exit_code == 0, done.output
    looked = runner.invoke(app, ["lookup", "--root", str(out), "--layer", "employment-wages"])
    assert looked.exit_code == 0, looked.output
    assert "qtrly.to-area: qtrly.area_fips = area_titles.area_fips" in looked.output
    assert "disclosed [required]: predicate qtrly.disclosure_code IS NULL" in looked.output
    hazard = runner.invoke(app, ["lookup", "--root", str(out), "--hazard", "H-0002"])
    assert "avg_wkly_wage has a documented formula" in hazard.output

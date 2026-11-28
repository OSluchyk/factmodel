"""docs/article-support-part3.md, the commands and outputs Part 3 of the article shows, cannot
drift from the repository: every ``fact`` command is a line of
``examples/qcew/scripts/reproduce.sh``, every SQL block is a query file, every output block is
verbatim in a file its section names, every YAML block is verbatim in a model file its section
names, and every measurement command runs on the seeded tables. CI has no BLS rows, so the
numbers themselves are checked against the committed outputs, not recomputed."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

from tests.docs.blocks import FENCE

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs" / "article-support-part3.md"
EXAMPLE = ROOT / "examples" / "qcew"
MEASUREMENTS = EXAMPLE / "measurements"
SCRIPT_VALUES = {
    "$M": "examples/qcew",
    "$S": "qcew-duckdb-real",
    "$DAY": "2026-11-28",
    "$L": "employment-wages",
    "$KEY": "area_fips,own_code,industry_code,size_code,year,qtr",
}
SETUP = {
    "git clone https://github.com/OSluchyk/factmodel",
    "cd factmodel",
    "uv sync",
    "source .venv/bin/activate",
    "bash examples/qcew/scripts/fetch.sh",
    "uv run examples/qcew/scripts/load.sh",
    'export FACT_DSN_QCEW_REAL="duckdb:///$PWD/examples/qcew/qcew.duckdb"',
}
MEASURE = "uv run python examples/qcew/scripts/measure.py "
needs_duckdb = pytest.mark.skipif(
    importlib.util.find_spec("duckdb") is None, reason="extra [duckdb] not installed"
)


def _module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sections() -> list[tuple[str, list[tuple[str, str]], list[str]]]:
    """(heading, [(language, body)], files named on the From line) per numbered section."""
    out = []
    text = PAGE.read_text(encoding="utf-8")
    for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        heading = part.splitlines()[0]
        blocks = [(m.group(1), m.group(2)) for m in FENCE.finditer(part)]
        froms = re.findall(r"^From: (.*)$", part, flags=re.MULTILINE)
        assert len(froms) == 1, f"section {heading!r} needs one From line"
        files = [f for f in re.findall(r"`([^`]+)`", froms[0]) if "/" in f]
        out.append((heading, blocks, files))
    return out


def _script() -> str:
    """reproduce.sh with its variables filled in and the shell quotes dropped."""
    text = (EXAMPLE / "scripts" / "reproduce.sh").read_text(encoding="utf-8")
    for var, value in SCRIPT_VALUES.items():
        text = text.replace(var, value)
    return text.replace('"', "")


def _commands() -> list[str]:
    return [
        line
        for _, blocks, _ in _sections()
        for language, body in blocks
        if language == "bash"
        for line in body.splitlines()
    ]


def test_page_has_the_nine_sections() -> None:
    headings = [h for h, _, _ in _sections()]
    assert [h.split(".")[0] for h in headings] == [str(n) for n in range(1, 10)]
    assert "\u2014" not in PAGE.read_text(encoding="utf-8")


def test_every_command_is_a_script_line_a_setup_line_or_a_measurement() -> None:
    script = _script()
    names = {p.stem for p in MEASUREMENTS.glob("*.sql")}
    for line in _commands():
        if line in SETUP:
            continue
        if line.startswith(MEASURE):
            assert line.removeprefix(MEASURE) in names, line
            continue
        assert f"run {line}\n" in script, line


def test_every_block_is_verbatim_in_a_file_of_its_section() -> None:
    for heading, blocks, files in _sections():
        texts = {f: (ROOT / f).read_text(encoding="utf-8") for f in files}
        assert texts, heading
        for language, body in blocks:
            if language == "bash":
                continue
            if language == "sql":
                assert body in [t for f, t in texts.items() if f.endswith(".sql")], heading
            elif language == "yaml":
                assert any(body in t for f, t in texts.items() if f.endswith(".yaml")), body[:60]
            else:
                # a whole output file, or lines one after the other of a kept run
                whole = body in [t for f, t in texts.items() if f.endswith(".txt")]
                lines = body.splitlines()
                kept = "\n".join(t for f, t in texts.items() if f.endswith((".log", ".md")))
                assert whole or all(line in kept for line in lines), (heading, lines[0])


def test_every_output_follows_its_own_command() -> None:
    """A measurement output block is the output file of the command right before it."""
    for _, blocks, _ in _sections():
        last = None
        for language, body in blocks:
            if language == "bash" and body.strip().startswith(MEASURE):
                last = body.strip().removeprefix(MEASURE)
            elif language == "sql" and last:
                assert body == (MEASUREMENTS / f"{last}.sql").read_text(encoding="utf-8"), last
            elif language == "text" and last:
                assert body == (MEASUREMENTS / f"{last}.txt").read_text(encoding="utf-8"), last
                last = None
            elif language == "bash":
                last = None


@needs_duckdb
@pytest.mark.filterwarnings("ignore")
def test_measurement_commands_run_on_the_seeded_tables(tmp_path: Path) -> None:

    seed = _module("qcew_seed_page", EXAMPLE / "seed" / "seed.py")
    tool = _module("qcew_measure_page", EXAMPLE / "scripts" / "measure.py")
    seed.load_duckdb(tmp_path / "seeded.duckdb")
    names = [c.removeprefix(MEASURE) for c in _commands() if c.startswith(MEASURE)]
    assert len(names) == len(set(names)) >= 19
    conn = tool.connect(str(tmp_path / "seeded.duckdb"))
    try:
        for name in names:
            got = tool.run(conn, name).splitlines()
            shown = (MEASUREMENTS / f"{name}.txt").read_text(encoding="utf-8").splitlines()
            columns = [c.strip() for c in shown[0].split("|")]
            assert [c.strip() for c in got[0].split("|")] == columns, name
    finally:
        conn.close()

"""The QCEW example on the published BLS rows (source qcew-duckdb-real).

CI never downloads from BLS. These tests check the committed artifacts of the read of
2026-11-28 against each other, and run the fetch, load and measurement scripts on seeded rows
written out in the form of BLS slices. With ``FACT_DSN_QCEW_REAL`` set to a database that
``scripts/load.sh`` built from the same slices, the last test reruns the probes and the
measurement queries and compares them with the committed results.
"""

import csv
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from factmodel.adapters.sql import SqlAdapter, measure
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from factmodel.model.types import Snapshot
from factmodel.probes import render
from tests.adapters.helpers import neutral

ROOT = Path(__file__).resolve().parents[2]
QCEW = ROOT / "examples" / "qcew"
SOURCE = "qcew-duckdb-real"
DAY = "2026-11-28"
RESULTS = QCEW / "probes" / "results" / f"{SOURCE}@{DAY}.jsonl"
MEASUREMENTS = QCEW / "measurements"
needs_duckdb = pytest.mark.skipif(
    importlib.util.find_spec("duckdb_engine") is None, reason="extra [duckdb] not installed"
)
needs_shell = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("curl") is None, reason="needs bash and curl"
)


def _module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _seed() -> ModuleType:
    return _module("qcew_seed_real", QCEW / "seed" / "seed.py")


def _measure() -> ModuleType:
    return _module("qcew_measure", QCEW / "scripts" / "measure.py")


def _columns(table: str) -> list[str]:
    ddl = (QCEW / "sources" / "ddl" / "duckdb.sql").read_text(encoding="utf-8")
    found = re.search(rf"CREATE TABLE {table} \((.*?)\);", ddl, re.DOTALL)
    assert found
    return [line.split()[0] for line in found.group(1).strip().splitlines()]


def write_slices(folder: Path) -> int:
    """The seeded annual and qtrly rows as BLS area slices: <year>/<period>/<area>.csv, text
    quoted, numbers bare, a blank for NULL, CRLF line ends. Returns the number of files."""
    files: dict[tuple[str, str, str, str], list[tuple[Any, ...]]] = {}
    for table, rows in _seed().rows().items():
        for row in rows:
            period = "a" if table == "annual" else row[6]
            files.setdefault((row[5], period, row[0], table), []).append(row)
    for (year, period, area, table), rows in files.items():
        path = folder / year / period / f"{area}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, quoting=csv.QUOTE_NONNUMERIC, lineterminator="\r\n")
            writer.writerow(_columns(table))
            writer.writerows(["" if v is None else v for v in row] for row in rows)
    return len(files)


def load_slices(raw: Path, db: Path) -> None:
    """What scripts/load.sh does: the DDL, then scripts/load.sql, from examples/qcew."""
    import duckdb

    here = Path.cwd()
    conn = duckdb.connect(str(db))
    try:
        os.chdir(QCEW)
        conn.execute((QCEW / "sources" / "ddl" / "duckdb.sql").read_text(encoding="utf-8"))
        conn.execute("SET VARIABLE raw = ?", [str(raw)])
        conn.execute((QCEW / "scripts" / "load.sql").read_text(encoding="utf-8"))
    finally:
        os.chdir(here)
        conn.close()


def _results() -> tuple[dict[str, str], dict[str, Any]]:
    rows = [json.loads(line) for line in RESULTS.read_text(encoding="utf-8").splitlines()]
    return rows[0], {r["probe"]: r["measurement"] for r in rows[1:]}


def test_sources_page_and_checksums_list_the_same_read() -> None:
    page = (QCEW / "sources" / "SOURCES.md").read_text(encoding="utf-8")
    row = r"^\| (https://data\.bls\.gov/\S+) \|.*\| `([0-9a-f]{64})` \|$"
    listed = dict(re.findall(row, page, re.M))
    sums = {}
    for line in (QCEW / "scripts" / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, path = line.split("  ")
        year, period, name = path.removeprefix("data/raw/").split("/")
        sums[f"https://data.bls.gov/cew/data/api/{year}/{period}/area/{name}"] = digest
    assert listed == sums and len(sums) == 440
    areas = [
        line.split("\t")[0]
        for line in (QCEW / "scripts" / "areas.tsv").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    absent = set(re.findall(r"^\| `(\w+)` \|.*\| 10 \|$", page, re.M))
    per_area = {a: sum(1 for url in sums if url.endswith(f"/{a}.csv")) for a in areas}
    assert {a for a, n in per_area.items() if n == 0} == absent
    assert {n for a, n in per_area.items() if a not in absent} == {10}  # 2 years, a and 1 to 4


def test_data_and_database_stay_out_of_git_and_the_sdist() -> None:
    ignore = (QCEW / ".gitignore").read_text(encoding="utf-8").split()
    assert {"data/", "qcew.duckdb", "qcew.duckdb.wal"} <= set(ignore)
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"/examples/qcew/data"' in project and '"**/*.duckdb"' in project


def test_published_results_confirm_and_seeded_results_do_not() -> None:
    model = load_model(QCEW)
    assert model.config is not None and not model.config.treat_synthetic_as_representative
    header, results = _results()
    assert header["source"] == SOURCE and header["data_quality"] == "representative"
    assert sorted(results) == sorted(model.probes)
    out_of_range = {
        "key-duplicates-area-titles",  # F-0001
        "value-set-qtrly-disclosure-code",  # F-0002
    }
    for probe in model.probes:
        real = model.evidence[f"ev-{probe}-{DAY}"] if len(probe) < 50 else None
        if real is None:
            continue
        # the record is a measurement on representative data either way; a result out of
        # range is not cited by the fact it tests and has an open finding instead
        assert real.data_quality == "representative" and real.status == "confirmed"
        if probe in out_of_range:
            assert any(
                f.status == "open" and real.id in (f.evidence or [])
                for f in model.findings.values()
            ), probe
    seeded = [e for e in model.evidence.values() if e.data_quality == "synthetic"]
    assert seeded and all(e.status == "inferred" for e in seeded)  # D-014
    for ref, (_, rel) in model.relationships.items():
        if rel.status is not None:
            continue
        cited = [model.evidence[e] for e in rel.evidence or []]
        assert any(e.probe and e.source == SOURCE and e.status == "confirmed" for e in cited), ref


def test_documented_key_is_unique_and_proposals_stop_at_pairs() -> None:
    _, results = _results()
    assert results["key-duplicates-annual"] == {"duplicate_keys": 0}
    assert results["key-duplicates-qtrly"] == {"duplicate_keys": 0}
    keys = load(QCEW / "drafts" / SOURCE / "keys.yaml").data
    proposed = {o["object"] for o in keys["objects"]}
    assert keys["max_columns"] == 2 and keys["data_quality"] == "representative"
    assert proposed == {"agglevel_titles", "industry_titles", "ownership_titles", "size_titles"}
    joins = load(QCEW / "drafts" / SOURCE / "joins.yaml").data
    found = {c["join"] for c in joins["candidates"]}
    assert len(found) == 15
    assert "qtrly.industry_code = industry_titles.industry_code" in found
    assert "qtrly.area_fips = area_titles.area_fips" not in found  # the target repeats (F-0001)


@needs_duckdb
@pytest.mark.filterwarnings("ignore")
def test_load_sql_reads_slices_into_the_seeded_tables(tmp_path: Path) -> None:
    import duckdb

    assert write_slices(tmp_path / "raw") == 80
    load_slices(tmp_path / "raw", tmp_path / "loaded.duckdb")
    _seed().load_duckdb(tmp_path / "seeded.duckdb")
    loaded = duckdb.connect(str(tmp_path / "loaded.duckdb"), read_only=True)
    seeded = duckdb.connect(str(tmp_path / "seeded.duckdb"), read_only=True)
    try:
        for table in ("annual", "qtrly", "area_titles", "industry_titles", "size_titles"):
            query = f"SELECT * FROM {table} ORDER BY ALL"
            assert loaded.execute(query).fetchall() == seeded.execute(query).fetchall(), table
    finally:
        loaded.close()
        seeded.close()
    model = load_model(QCEW)
    url = f"duckdb:///{tmp_path / 'loaded.duckdb'}"
    snap = SqlAdapter().reflect(model.sources[SOURCE], url, DAY)
    path = QCEW / "sources" / "snapshots" / f"{SOURCE}@{DAY}.yaml"
    assert neutral(snap) == neutral(Snapshot.model_validate(load(path).data))


@needs_shell
def test_fetch_script_keeps_slices_and_records_what_is_absent(tmp_path: Path) -> None:
    served = tmp_path / "served"
    slice_a = served / "2024" / "a" / "area" / "US000.csv"
    slice_q = served / "2024" / "1" / "area" / "10000.csv"
    for path in (slice_a, slice_q):
        path.parent.mkdir(parents=True)
        path.write_bytes(b'"area_fips","own_code"\r\n"' + path.stem.encode() + b'","0"\r\n')
    handler = partial(SimpleHTTPRequestHandler, directory=str(served))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    env = {
        **os.environ,
        "FACT_QCEW_BASE": f"http://127.0.0.1:{server.server_address[1]}",
        "FACT_QCEW_RAW": str(tmp_path / "raw"),
        "FACT_QCEW_YEARS": "2024",
        "FACT_QCEW_PAUSE": "0",
        "NO_PROXY": "127.0.0.1",
        "no_proxy": "127.0.0.1",
    }
    script = str(QCEW / "scripts" / "fetch.sh")
    try:
        first = subprocess.run(["bash", script], env=env, capture_output=True, text=True)
        again = subprocess.run(
            ["bash", script, "--resume"], env=env, capture_output=True, text=True
        )
    finally:
        server.shutdown()
    assert first.returncode == 0, first.stderr
    assert "fetch: 255 requests, 2 slices (74 bytes), 253 not published" in first.stdout
    assert "fetch: 0 requests, 0 slices (0 bytes), 0 not published, 255 kept" in again.stdout
    with (tmp_path / "raw" / "MANIFEST.tsv").open(encoding="utf-8", newline="") as handle:
        lines = list(csv.DictReader(handle, delimiter="\t"))
    assert len(lines) == 255  # 51 areas, the annual file and four quarters
    kept = {line["file"]: line for line in lines if line["status"] == "200"}
    assert sorted(kept) == ["2024/1/10000.csv", "2024/a/US000.csv"]
    for path in (slice_a, slice_q):
        copy = tmp_path / "raw" / path.parents[2].name / path.parents[1].name / path.name
        assert copy.read_bytes() == path.read_bytes()
        line = kept[f"{path.parents[2].name}/{path.parents[1].name}/{path.name}"]
        assert line["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert {line["status"] for line in lines} == {"200", "404"}
    # the files differ from the committed read, and the script says so
    assert "changed since the committed read: 2024/a/US000.csv" in first.stdout
    assert "in checksums.sha256, not fetched: data/raw/2025/a/US000.csv" in first.stdout
    assert "0 same, 2 changed, 0 new, 438 missing" in first.stdout


@needs_duckdb
@pytest.mark.filterwarnings("ignore")
def test_measurement_queries_run_on_the_seeded_tables(tmp_path: Path) -> None:

    tool = _measure()
    _seed().load_duckdb(tmp_path / "seeded.duckdb")
    conn = tool.connect(str(tmp_path / "seeded.duckdb"))
    has_crosswalk = (
        QCEW / "sources" / "codelists" / "qcew-county-msa-csa-crosswalk.xlsx"
    ).is_file()
    try:
        names = tool.names()
        assert len(names) == 41
        for name in names:
            if tool.needs_crosswalk(name) and not has_crosswalk:
                continue
            committed = (MEASUREMENTS / f"{name}.txt").read_text(encoding="utf-8")
            header = lambda text: [c.strip() for c in text.splitlines()[0].split("|")]  # noqa: E731
            assert header(tool.run(conn, name)) == header(committed), name
    finally:
        conn.close()


def test_table_format_is_stable() -> None:
    tool = _measure()
    text = tool.table(["what", "row_count", "share"], [("a", 10, 0.5), ("long name", 2, None)])
    assert text == (
        "what      | row_count | share\n"
        "----------+-----------+------\n"
        "a         |        10 |   0.5\n"
        "long name |         2 |  NULL\n"
    )


def _numbers(text: str) -> set[str]:
    """Counts written with thousands separators, as plain digits."""
    return {n.replace(",", "") for n in re.findall(r"(?<![\w.])\d{1,3}(?:,\d{3})+(?![\w,])", text)}


def committed_numbers() -> str:
    """Every committed artifact of the read, as one text with the separators dropped."""
    parts = [RESULTS, QCEW / "sources" / "SOURCES.md"]
    parts += sorted(MEASUREMENTS.glob("*.txt"))
    parts += sorted((QCEW / "drafts" / SOURCE).glob("*.yaml"))
    parts += [QCEW / "evidence" / "measurements.yaml"]
    parts += sorted((QCEW / "sources" / "codelists").glob("SOURCES.md"))
    parts += [QCEW / "probes" / "results" / "qcew-sqlite@2026-10-27.jsonl"]
    return "\n".join(p.read_text(encoding="utf-8") for p in parts).replace(",", "")


@pytest.mark.parametrize(
    "path",
    [
        "examples/qcew/README.md",
        "examples/qcew/registers/findings",
        "examples/qcew/registers/hazards",
        "docs/article-support-part3.md",
        "docs/tutorial/qcew.md",
    ],
)
def test_every_count_in_a_document_is_in_a_committed_file(path: str) -> None:
    target = ROOT / path
    files = sorted(target.glob("*.yaml")) if target.is_dir() else [target]
    pool = committed_numbers()
    # quoted from the owner's profiling of the full BLS files, not measured on this slice
    profiled = {"3659997", "47061", "46370", "612719", "610230"}
    for file in files:
        missing = {n for n in _numbers(file.read_text(encoding="utf-8")) if n not in pool}
        assert missing <= profiled, f"{file.name}: {sorted(missing - profiled)}"


@pytest.mark.skipif(
    not os.environ.get("FACT_DSN_QCEW_REAL", "").startswith("duckdb:///"),
    reason="set FACT_DSN_QCEW_REAL to a database built by examples/qcew/scripts/load.sh",
)
@pytest.mark.filterwarnings("ignore")
def test_published_rows_reproduce_the_committed_results() -> None:

    url = os.environ["FACT_DSN_QCEW_REAL"]
    model = load_model(QCEW)
    queries = [(pid, render(p, "duckdb") or "") for pid, p in model.probes.items()]
    _, results = _results()
    assert {r["probe"]: r["measurement"] for r in measure(url, queries)} == results
    tool = _measure()
    conn = tool.connect(url.removeprefix("duckdb:///"))
    try:
        for name in tool.names():
            if not (MEASUREMENTS / f"{name}.txt").is_file():
                continue  # a crosswalk query, and the spreadsheet is not there
            committed = (MEASUREMENTS / f"{name}.txt").read_text(encoding="utf-8")
            assert tool.run(conn, name) == committed, name
    finally:
        conn.close()


def test_crosswalk_reader_reads_a_workbook_with_the_standard_library(tmp_path: Path) -> None:
    import zipfile

    main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    strings = ["County Code", "County Title", "MSA Code", "MSA Title", "CSA Code", "CSA Title"]
    strings += ["New Castle County, Delaware", "C3798", "Philadelphia-Camden-Wilmington MSA"]

    def cell(ref: str, value: str, shared: bool) -> str:
        return f'<c r="{ref}"{' t="s"' if shared else ""}><v>{value}</v></c>'

    header = "".join(cell(f"{'ABCDEF'[i]}2", str(i), True) for i in range(6))
    row = cell("A3", "10003", False) + cell("B3", "6", True) + cell("C3", "7", True)
    row += cell("D3", "8", True)
    low = cell("A4", "1001", False) + cell("B4", "6", True)
    sheet = f'<worksheet xmlns="{main}"><sheetData><row r="1"><c r="A1" t="s"><v>8</v></c></row>'
    sheet += f'<row r="2">{header}</row><row r="3">{row}</row><row r="4">{low}</row>'
    sheet += "</sheetData></worksheet>"
    shared = "".join(f"<si><t>{s}</t></si>" for s in strings)
    path = tmp_path / "crosswalk.xlsx"
    with zipfile.ZipFile(path, "w") as book:
        book.writestr(
            "xl/workbook.xml",
            f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets>'
            '<sheet name="Feb. 2013 Crosswalk" sheetId="1" r:id="rId1"/>'
            '<sheet name="July 2023 Crosswalk" sheetId="2" r:id="rId2"/></sheets></workbook>',
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>',
        )
        book.writestr("xl/sharedStrings.xml", f'<sst xmlns="{main}">{shared}</sst>')
        book.writestr(
            "xl/worksheets/sheet1.xml", f'<worksheet xmlns="{main}"><sheetData/></worksheet>'
        )
        book.writestr("xl/worksheets/sheet2.xml", sheet)
    reader = _module("qcew_crosswalk", QCEW / "scripts" / "crosswalk.py")
    name, rows = reader.sheet_name_and_rows(path)
    assert name == "July 2023 Crosswalk"
    assert rows == [
        (
            "10003",
            "New Castle County, Delaware",
            "C3798",
            "Philadelphia-Camden-Wilmington MSA",
            "",
            "",
        ),
        ("01001", "New Castle County, Delaware", "", "", "", ""),
    ]

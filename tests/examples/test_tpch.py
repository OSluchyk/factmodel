"""The TPC-H example: eight tables without a key, keys and joins proposed from the rows, then
the reference kit's constraints applied and confirmed by probes.

The data tests need DuckDB's tpch extension; where ``INSTALL tpch`` fails (no route to
extensions.duckdb.org) they skip. ``FACT_TPCH_SF`` sets the scale factor, default 1, the
example's scale; ``FACT_TPCH_DB`` points at a database that ``scripts/generate.sh`` built earlier
instead of building one. The inclusions that are not foreign keys are listed with a reason
each, so their count is a regression guard, not a surprise: at scale factor 1 the measured set
must equal the list (measured 2026-11-02: 21 of 21); at another scale factor it must be a
subset, because small scales leave gaps in the value ranges.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from factmodel import propose
from factmodel.adapters.sql import SqlAdapter, measure
from factmodel.gate.runner import run_gate
from factmodel.io.yaml_strict import load
from factmodel.model.loader import load_model
from factmodel.model.types import Snapshot
from factmodel.probes import render
from tests.adapters.helpers import neutral

ROOT = Path(__file__).resolve().parents[2]
TPCH = ROOT / "examples" / "tpch"
SCRIPTS = TPCH / "scripts"
SOURCE = "tpch-duckdb"
DAY = "2026-11-02"
DAY_A, DAY_B = DAY, f"{DAY}_2"  # the day's first and second snapshot
SF = float(os.environ.get("FACT_TPCH_SF", "1"))

# The kit's constraints (scripts/apply-constraints.sql).
KIT_PRIMARY = {
    "region": ("r_regionkey",),
    "nation": ("n_nationkey",),
    "supplier": ("s_suppkey",),
    "customer": ("c_custkey",),
    "part": ("p_partkey",),
    "partsupp": ("ps_partkey", "ps_suppkey"),
    "orders": ("o_orderkey",),
    "lineitem": ("l_orderkey", "l_linenumber"),
}
KIT_FOREIGN = {
    ("nation", ("n_regionkey",), "region", ("r_regionkey",)),
    ("supplier", ("s_nationkey",), "nation", ("n_nationkey",)),
    ("customer", ("c_nationkey",), "nation", ("n_nationkey",)),
    ("partsupp", ("ps_suppkey",), "supplier", ("s_suppkey",)),
    ("partsupp", ("ps_partkey",), "part", ("p_partkey",)),
    ("orders", ("o_custkey",), "customer", ("c_custkey",)),
    ("lineitem", ("l_orderkey",), "orders", ("o_orderkey",)),
    ("lineitem", ("l_partkey", "l_suppkey"), "partsupp", ("ps_partkey", "ps_suppkey")),
}
# Foreign keys the specification lists (clause 1.4.2.3) that dss.ri leaves out.
SPEC_ONLY = {
    ("lineitem", ("l_partkey",), "part", ("p_partkey",)),
    ("lineitem", ("l_suppkey",), "supplier", ("s_suppkey",)),
}
# Inclusions above the threshold that are not foreign keys, with the reason each one holds.
# Keys in TPC-H are dense ranges (1..N, or 0..N for region and nation), so any small range of
# integers is "included" in every larger key column of the same type class.
COINCIDENCES: dict[tuple[str, tuple[str, ...], str, tuple[str, ...]], str] = {
    ("region", ("r_regionkey",), "nation", ("n_nationkey",)): "region keys 0..4 inside 0..24",
    ("supplier", ("s_suppkey",), "customer", ("c_custkey",)): "1..S inside 1..C, S < C",
    ("supplier", ("s_suppkey",), "part", ("p_partkey",)): "1..S inside 1..P, S < P",
    ("customer", ("c_custkey",), "part", ("p_partkey",)): "1..C inside 1..P, C < P",
    ("part", ("p_size",), "supplier", ("s_suppkey",)): "sizes 1..50 inside 1..S",
    ("part", ("p_size",), "customer", ("c_custkey",)): "sizes 1..50 inside 1..C",
    ("partsupp", ("ps_suppkey",), "customer", ("c_custkey",)): "supplier keys inside 1..C",
    ("partsupp", ("ps_suppkey",), "part", ("p_partkey",)): "supplier keys inside 1..P",
    ("orders", ("o_custkey",), "part", ("p_partkey",)): "customer keys inside 1..P",
    ("orders", ("o_shippriority",), "region", ("r_regionkey",)): "the constant 0 is a region key",
    ("orders", ("o_shippriority",), "nation", ("n_nationkey",)): "the constant 0 is a nation key",
    ("lineitem", ("l_suppkey",), "customer", ("c_custkey",)): "supplier keys inside 1..C",
    ("lineitem", ("l_suppkey",), "part", ("p_partkey",)): "supplier keys inside 1..P",
    ("lineitem", ("l_linenumber",), "nation", ("n_nationkey",)): "line numbers 1..7 inside 0..24",
    ("lineitem", ("l_linenumber",), "supplier", ("s_suppkey",)): "line numbers 1..7 inside 1..S",
    ("lineitem", ("l_linenumber",), "customer", ("c_custkey",)): "line numbers 1..7 inside 1..C",
    ("lineitem", ("l_linenumber",), "part", ("p_partkey",)): "line numbers 1..7 inside 1..P",
    ("lineitem", ("l_linenumber",), "orders", ("o_orderkey",)): "order keys 1..7 exist",
    # at scale factor 1 the 800,000 availqty draws cover every value 1..9999
    ("partsupp", ("ps_availqty",), "supplier", ("s_suppkey",)): "quantities 1..9999 inside 1..S",
    ("partsupp", ("ps_availqty",), "customer", ("c_custkey",)): "quantities 1..9999 inside 1..C",
    ("partsupp", ("ps_availqty",), "part", ("p_partkey",)): "quantities 1..9999 inside 1..P",
}
# At scale factor 1 every coincidence above is measured; at 0.01, for example, the 8,000
# availqty draws leave gaps in 1..9999 and the three availqty rows drop out.
MEASURED_SCALE = 1.0


def _source() -> Any:
    return load_model(TPCH).sources[SOURCE]


@pytest.fixture(scope="module")
def tpch_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    out = tmp_path_factory.mktemp("tpch") / "tpch.duckdb"
    prebuilt = os.environ.get("FACT_TPCH_DB")  # a database generate.sh built earlier
    if prebuilt:
        shutil.copyfile(prebuilt, out)
        return f"duckdb:///{out}"
    done = subprocess.run(
        ["bash", str(SCRIPTS / "generate.sh"), str(SF), str(out)],
        env={
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        if "cannot load the tpch extension" in done.stdout + done.stderr:
            pytest.skip("the DuckDB tpch extension cannot be installed here")
        raise AssertionError(done.stdout + done.stderr)
    return f"duckdb:///{out}"


def _session(url: str) -> propose.Session:
    return propose.Session(run=lambda queries: measure(url, queries), dialect="duckdb")


def _committed(day: str) -> Snapshot | None:
    path = TPCH / "sources" / "snapshots" / f"{SOURCE}@{day}.yaml"
    return Snapshot.model_validate(load(path).data) if path.is_file() else None


def test_gate_is_green() -> None:
    report = run_gate(TPCH)
    assert report.passed, "\n".join(report.lines())


def test_build_declares_no_key(tpch_url: str) -> None:
    snap = SqlAdapter().reflect(_source(), tpch_url, DAY_A)
    assert [o.name for o in snap.objects] == sorted(KIT_PRIMARY)
    assert all(not o.constraints for o in snap.objects)
    committed = _committed(DAY_A)
    if committed is not None:
        assert neutral(snap) == neutral(committed)


def test_propose_keys_finds_the_kit_keys(tpch_url: str) -> None:
    snap = SqlAdapter().reflect(_source(), tpch_url, DAY_A)
    candidates, skipped = propose.propose_keys(snap, _session(tpch_url))
    assert skipped == []
    found = {(c.object, c.fields) for c in candidates}
    missing = {(t, k) for t, k in KIT_PRIMARY.items() if (t, k) not in found}
    assert not missing, missing


def test_propose_joins_recovers_the_kit_foreign_keys(tpch_url: str) -> None:
    snap = SqlAdapter().reflect(_source(), tpch_url, DAY_A)
    session = _session(tpch_url)
    keys, _ = propose.propose_keys(snap, session)
    by_object: dict[str, list[list[str]]] = {}
    for c in keys:
        by_object.setdefault(c.object, []).append(list(c.fields))
    candidates, skipped = propose.propose_joins(snap, session, keys=by_object)
    assert skipped == []
    found = {(c.source, c.source_fields, c.target, c.target_fields): c for c in candidates}
    assert set(found) >= KIT_FOREIGN, KIT_FOREIGN - set(found)
    assert set(found) >= SPEC_ONLY, SPEC_ONLY - set(found)
    assert all(found[k].cardinality == "many_to_one" for k in KIT_FOREIGN)
    extras = set(found) - KIT_FOREIGN - SPEC_ONLY
    unexpected = extras - set(COINCIDENCES)
    assert not unexpected, f"inclusions without a reason in COINCIDENCES: {sorted(unexpected)}"
    if SF == MEASURED_SCALE:
        gone = set(COINCIDENCES) - extras
        assert not gone, f"coincidences no longer measured: {sorted(gone)}"


def test_kit_constraints_apply_and_probes_confirm_them(tpch_url: str) -> None:
    import duckdb

    path = tpch_url.removeprefix("duckdb:///")
    conn = duckdb.connect(path)
    try:
        conn.execute((SCRIPTS / "apply-constraints.sql").read_text(encoding="utf-8"))
    finally:
        conn.close()
    snap = SqlAdapter().reflect(_source(), tpch_url, DAY)
    declared = {
        (o.name, c.constraint_type, tuple(c.fields))
        for o in snap.objects
        for c in o.constraints or []
    }
    assert {(t, "primary_key", k) for t, k in KIT_PRIMARY.items()} <= declared
    foreign = {
        (o.name, tuple(c.fields), c.references.object, tuple(c.references.fields))
        for o in snap.objects
        for c in o.constraints or []
        if c.constraint_type == "foreign_key" and c.references is not None
    }
    assert foreign == KIT_FOREIGN
    assert all(c.enforced for o in snap.objects for c in o.constraints or [])
    committed = _committed(DAY_B)
    if committed is not None:
        assert neutral(snap) == neutral(committed)
    model = load_model(TPCH)
    queries = [(pid, render(p, "duckdb") or "") for pid, p in model.probes.items()]
    for result in measure(tpch_url, queries):
        probe = model.probes[result["probe"]]
        assert "measurement" in result, result
        for key, bounds in (probe.expected or {}).items():
            value = result["measurement"][key]
            assert bounds.min is None or value >= bounds.min, (probe.id, key, value)
            assert bounds.max is None or value <= bounds.max, (probe.id, key, value)

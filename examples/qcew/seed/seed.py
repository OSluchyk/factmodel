"""Synthetic rows for the QCEW data tables, and the real BLS code lists (D-011, D-016).

A local engine seeded by this script is a test fixture, not a platform. The `annual` and `qtrly`
rows are made up; every code they use exists in the BLS title files, which are loaded as they
are from `sources/codelists/` (public domain, committed unchanged under D-016).

What the seed reproduces, by design (the ids are those of the owner's `profile.md`):

- G1: the key (area_fips, own_code, industry_code, size_code, year, qtr) never repeats, and
  `agglvl_code` follows from it (the A4 matrix: geography digit, then industry level).
- V2: suppressed rows (`disclosure_code = 'N'`) carry 0 in employment and wages, never NULL,
  while their establishment count stays filled.
- V1, G2: the quarterly table pads MSA detail keys to four quarters with `'-'` rows whose
  measures are all 0 (2025 Q3 and Q4, after BLS stopped publishing MSA detail).
- H5: a parent disclosed while a child is suppressed (Kent County construction), and the
  reverse (Montgomery County retail suppressed, its children disclosed).
- M5: annual values are the averages and sums of the quarterly ones (12-month employment
  rounded half to even, annual wages the sum of the four quarters); every parent row (state,
  NAICS parent, domain, total, ownership total, the MSA) is the sum of its children, so
  monthly levels add up wherever nothing is suppressed, and annual averages only within
  rounding (H-0001).
- M1: `avg_wkly_wage` is quarterly wages divided by the mean of the three months, divided
  by 13, rounded half up.
- size_code is 0 only (G4); own_code 4 never occurs (Q03).

The 2024 rows carry no over-the-year values (NULL), because 2023 is not in the example; the
2025 rows carry the change from 2024. A blank disclosure code is NULL, as the owner's loader
reads an empty field.

Usage:
    python examples/qcew/seed/seed.py sqlite <file.db>
    python examples/qcew/seed/seed.py duckdb <file.duckdb>
    python examples/qcew/seed/seed.py postgres <dsn>     # for example after docker compose up
"""

import csv
import random
import sqlite3
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

SEED = 20261027
HERE = Path(__file__).resolve().parents[1]
DDL = HERE / "sources" / "ddl"
CODELISTS = HERE / "sources" / "codelists"
YEARS = ("2024", "2025")
TITLES = ("agglevel", "area", "industry", "ownership", "size")
# area code -> geography digit of agglvl_code (A4): 4 MSA, 5 state, 7 county
AREAS = {
    "10000": 5,  # Delaware
    "10001": 7,  # Kent County, DE
    "10003": 7,  # New Castle County, DE
    "10005": 7,  # Sussex County, DE
    "24000": 5,  # Maryland
    "24015": 7,  # Cecil County, MD
    "24031": 7,  # Montgomery County, MD
}
MSA = "C3798"  # Philadelphia-Camden-Wilmington, PA-NJ-DE-MD: crosses state lines
# industry code -> industry digit of agglvl_code (A4) for own_code 1 to 5
INDUSTRIES = {
    "10": 1,  # total, all industries
    "101": 2,  # domain: goods-producing
    "102": 2,  # domain: service-providing
    "1012": 3,  # supersector: construction
    "1013": 3,  # supersector: manufacturing
    "1021": 3,  # supersector: trade, transportation, and utilities
    "23": 4,  # sector: construction
    "31-33": 4,  # sector written as a range
    "42": 4,  # sector: wholesale trade
    "44-45": 4,  # sector written as a range
    "236": 5,
    "311": 5,
    "445": 5,
    "236115": 8,
    "311811": 8,
    "445110": 8,
}
SUPPRESSED = {
    ("10001", "5", "23"),  # child suppressed under a disclosed supersector (H5)
    ("24031", "5", "44-45"),  # parent suppressed over disclosed children (H5, reverse)
    ("10005", "5", "311811"),
}
ANNUAL = (
    "annual_avg_estabs",
    "annual_avg_emplvl",
    "total_annual_wages",
    "taxable_annual_wages",
    "annual_contributions",
    "annual_avg_wkly_wage",
    "avg_annual_pay",
)
QTRLY = (
    "qtrly_estabs",
    "month1_emplvl",
    "month2_emplvl",
    "month3_emplvl",
    "total_qtrly_wages",
    "taxable_qtrly_wages",
    "qtrly_contributions",
    "avg_wkly_wage",
)

Rows = dict[str, list[tuple[Any, ...]]]


def keys() -> list[tuple[str, str, str, str]]:
    """(area_fips, own_code, industry_code, agglvl_code) of every published key."""
    out = []
    for area, geo in AREAS.items():
        out.append((area, "0", "10", f"{geo}0"))
        out += [(area, own, "10", f"{geo}1") for own in ("1", "2", "3")]
        out += [(area, "5", code, f"{geo}{level}") for code, level in INDUSTRIES.items()]
    out.append((MSA, "0", "10", "40"))
    return out


MSA_DETAIL = (MSA, "5", "10", "41")  # quarterly only: MSA detail (G3)


def _half_up(value: Fraction) -> int:
    return int((value + Fraction(1, 2)).__floor__())


def _pct(change: int, prior: int) -> float:
    return float(round(Fraction(change * 100, prior), 1)) if prior else 0.0


Key = tuple[str, str, str, str]
Base = tuple[list[int], list[int], list[int]]


def _base(rng: random.Random, key: Key) -> Base:
    """Twelve monthly employment levels, four quarterly wage totals and four establishment
    counts for one key and year."""
    level = int(key[3][1])
    size = max(20, 40_000 // (2**level) + rng.randint(-500, 500) // (level + 1))
    months = [max(1, size + rng.randint(-size // 10, size // 10)) for _ in range(12)]
    wages = [sum(months[3 * q : 3 * q + 3]) * rng.randint(3_800, 5_200) for q in range(4)]
    estabs = [max(1, size // 15 + rng.randint(-3, 3)) for _ in range(4)]
    return months, wages, estabs


# Leaves the seed draws; every other row is a sum of these, as in the BLS files (M5).
LEAF_INDUSTRIES = ("236115", "311811", "445110", "42")
CHILDREN = {  # parent -> children, private ownership
    "236": ("236115",),
    "23": ("236",),
    "311": ("311811",),
    "31-33": ("311",),
    "445": ("445110",),
    "44-45": ("445",),
    "1012": ("23",),
    "1013": ("31-33",),
    "1021": ("42", "44-45"),
    "101": ("1012", "1013"),
    "102": ("1021",),
    "10": ("101", "102"),
}
STATE_OF = {
    "10001": "10000",
    "10003": "10000",
    "10005": "10000",
    "24015": "24000",
    "24031": "24000",
}
MSA_COUNTIES = ("10003", "24015")


def _add(parts: list[Base]) -> Base:
    months = [sum(p[0][i] for p in parts) for i in range(12)]
    wages = [sum(p[1][i] for p in parts) for i in range(4)]
    estabs = [sum(p[2][i] for p in parts) for i in range(4)]
    return months, wages, estabs


def _measures() -> dict[str, dict[Key, Base]]:
    """Per year and key: monthly employment, quarterly wages, quarterly establishments. Leaves
    are drawn per county; parents (industries, ownership total, states, the MSA) are the sums
    of their children, so the true values add up even where a row is shown suppressed."""
    rng = random.Random(SEED)
    level = {key[:3]: key for key in [*keys(), MSA_DETAIL]}
    out: dict[str, dict[Key, Base]] = {}
    for year in YEARS:
        values: dict[tuple[str, str, str], Base] = {}
        for county in STATE_OF:
            for own in ("1", "2", "3"):
                values[(county, own, "10")] = _base(rng, level[(county, own, "10")])
            for industry in LEAF_INDUSTRIES:
                values[(county, "5", industry)] = _base(rng, level[(county, "5", industry)])
            for parent in CHILDREN:  # in order: children come before their parents
                parts = [values[(county, "5", child)] for child in CHILDREN[parent]]
                values[(county, "5", parent)] = _add(parts)
            totals = [values[(county, own, "10")] for own in ("1", "2", "3", "5")]
            values[(county, "0", "10")] = _add(totals)
        for state in sorted(set(STATE_OF.values())):
            counties = [c for c, s in STATE_OF.items() if s == state]
            for _, own, industry in [k for k in values if k[0] == counties[0]]:
                parts = [values[(c, own, industry)] for c in counties]
                values[(state, own, industry)] = _add(parts)
        for own in ("0", "5"):
            values[(MSA, own, "10")] = _add([values[(c, own, "10")] for c in MSA_COUNTIES])
        out[year] = {key: values[key[:3]] for key in [*keys(), MSA_DETAIL]}
    return out


def _lq(rng: random.Random, n: int) -> list[float]:
    return [rng.randint(20, 300) / 100 for _ in range(n)]


def _quarter(months: list[int], wages: list[int], estabs: list[int], q: int) -> list[int]:
    m = months[3 * q : 3 * q + 3]
    w = wages[q]
    taxable = w * 3 // 10
    return [estabs[q], *m, w, taxable, taxable // 50, _half_up(Fraction(w * 3, sum(m) * 13))]


def _year(months: list[int], wages: list[int], estabs: list[int]) -> list[int]:
    total = sum(wages)
    taxable = sum(w * 3 // 10 for w in wages)
    contributions = sum(w * 3 // 10 // 50 for w in wages)
    employment = Fraction(sum(months), 12)
    return [
        round(Fraction(sum(estabs), 4)),  # half to even
        round(employment),  # half to even (M3)
        total,
        taxable,
        contributions,
        _half_up(total / employment / 52),
        _half_up(total / employment),
    ]


def rows() -> Rows:
    """Every table's rows, in insert order."""
    measures = _measures()
    rng = random.Random(SEED + 1)
    out: Rows = {"annual": [], "qtrly": []}
    values: dict[tuple[str, str, str], list[int]] = {}
    for year in YEARS:
        base = measures[year]
        for key in keys():
            area, own, industry, agglvl = key
            months, wages, estabs = base[key]
            suppressed = (area, own, industry) in SUPPRESSED
            levels = _year(months, wages, estabs)
            if suppressed:
                levels = [levels[0], 0, 0, 0, 0, 0, 0]  # V2: zeros, establishments kept
            values[(year, "A", "|".join(key))] = levels
            prior = values.get((str(int(year) - 1), "A", "|".join(key)))
            lq = [0.0] * 7 if suppressed else _lq(rng, 7)
            out["annual"].append(
                (
                    *(area, own, industry, agglvl, "0", year, "A", "N" if suppressed else None),
                    *(*levels, "N" if suppressed else None, *lq),
                    *_oty(levels, prior, suppressed),
                )
            )
        for q in range(4):
            for key in [*keys(), MSA_DETAIL]:
                area, own, industry, agglvl = key
                months, wages, estabs = base[key]
                qtr = str(q + 1)
                padded = key == MSA_DETAIL and year == "2025" and q >= 2
                suppressed = (area, own, industry) in SUPPRESSED
                levels = _quarter(months, wages, estabs, q)
                if padded:
                    levels = [0] * 8  # G2: no record for this key in this quarter
                elif suppressed:
                    levels = [levels[0]] + [0] * 7
                values[(year, qtr, "|".join(key))] = levels
                prior = values.get((str(int(year) - 1), qtr, "|".join(key)))
                code = "-" if padded else ("N" if suppressed else None)
                lq = [0.0] * 8 if padded or suppressed else _lq(rng, 8)
                oty = _oty(levels, prior, suppressed or padded)
                if padded:
                    oty = (None, *(0 if i % 2 == 0 else 0.0 for i in range(16)))
                out["qtrly"].append(
                    (
                        *(area, own, industry, agglvl, "0", year, qtr, code),
                        *(*levels, "N" if suppressed else None, *lq),
                        *oty,
                    )
                )
    return out


def _oty(levels: list[int], prior: list[int] | None, suppressed: bool) -> tuple[Any, ...]:
    if prior is None:
        return (None,) * (1 + 2 * len(levels))
    if suppressed or not any(prior[1:]):
        return ("N", *(0 if i % 2 == 0 else 0.0 for i in range(2 * len(levels))))
    out: list[Any] = [None]
    for now, then in zip(levels, prior, strict=True):
        out += [now - then, _pct(now - then, then)]
    return tuple(out)


def code_lists() -> Rows:
    """The five BLS title files, every line after the first header line, unchanged (D-016)."""
    out: Rows = {}
    for name in TITLES:
        with (CODELISTS / f"{name}_titles.csv").open(newline="", encoding="utf-8") as handle:
            out[f"{name}_titles"] = [tuple(r) for r in list(csv.reader(handle))[1:]]
    return out


def all_rows() -> Rows:
    return {**rows(), **code_lists()}


def _statements(dialect: str) -> list[str]:
    text = (DDL / f"{dialect}.sql").read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
    return [s for s in body.split(";") if s.strip()]


def load_sqlite(path: Path) -> str:
    """Create the tables and rows in a SQLite file; return its SQLAlchemy URL."""
    with sqlite3.connect(path) as conn:
        for statement in _statements("sqlite"):
            conn.execute(statement)
        for table, items in all_rows().items():
            marks = ", ".join("?" for _ in items[0])
            conn.executemany(f"INSERT INTO {table} VALUES ({marks})", items)
    return f"sqlite:///{path}"


def load_duckdb(path: Path) -> str:
    """Create the tables and rows in a DuckDB file; return its SQLAlchemy URL."""
    import duckdb

    conn = duckdb.connect(str(path))
    try:
        for statement in _statements("duckdb"):
            conn.execute(statement)
        for table, items in all_rows().items():
            marks = ", ".join("?" for _ in items[0])
            conn.executemany(f"INSERT INTO {table} VALUES ({marks})", items)
    finally:
        conn.close()
    return f"duckdb:///{path}"


def load_postgres(url: str) -> None:
    """Create the tables and rows in the database (and search path) ``url`` names."""
    from sqlalchemy import create_engine, text

    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            for statement in _statements("postgres"):
                conn.execute(text(statement))
            for table, items in all_rows().items():
                names = ", ".join(f":c{i}" for i in range(len(items[0])))
                conn.execute(
                    text(f"INSERT INTO {table} VALUES ({names})"),
                    [{f"c{i}": v for i, v in enumerate(row)} for row in items],
                )
    finally:
        engine.dispose()


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("sqlite", "duckdb", "postgres"):
        print(__doc__)
        return 2
    if argv[0] == "sqlite":
        print(load_sqlite(Path(argv[1])))
    elif argv[0] == "duckdb":
        print(load_duckdb(Path(argv[1])))
    else:
        load_postgres(argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

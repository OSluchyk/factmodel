"""Write evidence/measurements.yaml from the outputs under measurements/.

    python3 examples/qcew/scripts/measurement_evidence.py   (from the framework root)

One record per group of measurements: the counts the findings and hazards cite, read from
the .txt files that scripts/measure.py --write wrote. Status inferred: a query a person or an
agent ran, not a generated probe.
"""

from pathlib import Path

M = Path("examples/qcew/measurements")


def rows(name):
    lines = (M / f"{name}.txt").read_text().splitlines()
    cols = [c.strip() for c in lines[0].split("|")]
    return [
        {
            k: (int(v) if v.lstrip("-").isdigit() else v)
            for k, v in zip(cols, [c.strip() for c in line.split("|")], strict=True)
        }
        for line in lines[2:]
    ]


def S(rs, key, cond=lambda r: True):
    return sum(r[key] for r in rs if cond(r))


recs = {}
j = rows("cardinality-area-titles")
recs["area-titles-join"] = (
    ["cardinality-area-titles"],
    {
        "qtrly_rows": j[0]["row_count"],
        "plain_join_rows": j[1]["row_count"],
        "distinct_join_rows": j[2]["row_count"],
    },
)
z = {r["disclosure_code"]: r for r in rows("suppressed-zero")}
recs["suppressed-zero"] = (
    ["suppressed-zero"],
    {
        "n_rows": z["N"]["row_count"],
        "n_rows_employment_and_wages_zero": z["N"]["employment_and_wages_zero"],
        "n_rows_establishments_filled": z["N"]["establishments_filled"],
        "dash_rows": z["-"]["row_count"],
        "dash_rows_all_zero": z["-"]["employment_and_wages_zero"],
        "rows_with_null": S(list(z.values()), "rows_with_null"),
    },
)
k = rows("key-documented")
pq = rows("padding-by-quarter")
recs["key"] = (
    ["key-documented"],
    {
        "row_count": k[0]["row_count"],
        "distinct_documented_keys": k[0]["distinct_keys"],
        "distinct_keys_without_size_code": k[1]["distinct_keys"],
        "distinct_keys_without_qtr": k[2]["distinct_keys"],
    },
)
q3 = next(r for r in pq if (r["year"], r["qtr"]) == (2025, 3))
recs["padding"] = (
    ["padding-by-quarter"],
    {
        "row_count": S(pq, "row_count"),
        "dash_rows": S(pq, "dash_rows"),
        "rows_per_quarter_2024": pq[0]["row_count"],
        "rows_per_quarter_2025": pq[4]["row_count"],
        "msa_rows_2025q3": q3["msa_rows"],
        "msa_dash_rows_2025q3": q3["msa_dash_rows"],
        "msa_dash_rows_2025q3_and_q4": S(
            pq, "msa_dash_rows", lambda r: (r["year"], r["qtr"]) in ((2025, 3), (2025, 4))
        ),
        "records_2025q2": pq[5]["records"],
        "records_2025q3": q3["records"],
    },
)
for name in ("rollup-county-state", "rollup-naics-parent"):
    recs[name] = ([name], rows(name)[0])
sh = rows("industry-code-shapes")
tw = {r["n"]: r for r in rows("two-ways-summary")}
recs["industry-codes"] = (
    ["industry-code-shapes", "two-ways-summary"],
    {
        "distinct_codes": S(sh, "codes"),
        "codes_not_naics": S(sh, "codes", lambda r: not r["shape"].startswith("5")),
        "codes_without_prefix_parent": S(sh, "without_prefix_parent"),
        "row_count": tw[1]["row_count"],
        "level_from_shape_agree": tw[1]["agree"],
        "level_from_shape_disagree": tw[1]["disagree"],
        "level_from_length_agree": tw[2]["agree"],
        "level_from_length_disagree": tw[2]["disagree"],
    },
)
ak = rows("area-kind-two-ways")
recs["area-kind"] = (
    ["area-kind-two-ways", "two-ways-summary"],
    {
        "agree_rows": tw[3]["agree"],
        "disagree_rows": tw[3]["disagree"],
        "microsa_rows_read_as_msa": S(ak, "row_count", lambda r: r["kind_from_agglvl"] == 8),
        "special_level_rows": S(ak, "row_count", lambda r: r["kind_from_agglvl"] == 9),
    },
)
md = {r["n"]: r for r in rows("msa-double-count") if r["n"] > 1}
recs["msa-double-count"] = (
    ["msa-double-count"],
    {
        "two_states": md[2]["employment"],
        "two_states_and_msa": md[3]["employment"],
        "counted_twice": md[4]["employment"],
        "from_outside_the_two_states": md[5]["employment"],
    },
)
mc = {r["qtr"]: r for r in rows("msa-from-counties")}
recs["msa-from-counties"] = (
    ["msa-from-counties"],
    {
        "counties": mc[1]["county_rows"],
        "msa_row_2025q1": mc[1]["msa_row"],
        "sum_of_counties_2025q1": mc[1]["sum_of_counties"],
        "msa_row_2025q2": mc[2]["msa_row"],
        "sum_of_counties_2025q2": mc[2]["sum_of_counties"],
        "sum_of_counties_2025q3": mc[3]["sum_of_counties"],
        "sum_of_counties_2025q4": mc[4]["sum_of_counties"],
    },
)
recs["wage-formula"] = (["avg-weekly-wage-formula"], rows("avg-weekly-wage-formula")[0])
po = rows("prior-year-orphans")


def no(y):
    return lambda r: r["year"] == y and r["prior"].startswith("no")


recs["prior-year"] = (
    ["prior-year-orphans"],
    {
        "rows_2024_without_prior_year_row": S(po, "row_count", no(2024)),
        "rows_2025_without_prior_year_row": S(po, "row_count", no(2025)),
        "rows_2025_without_prior_year_row_oty_blank": S(
            po, "row_count", lambda r: no(2025)(r) and r["oty_disclosure_code"] == "blank"
        ),
        "oty_change_null": S(po, "oty_change_null"),
    },
)
hist = rows("annual-average-rollup-differences")
recs["annual-rollup"] = (
    ["annual-average-rollup-differences"],
    {
        "keys_compared": S(hist, "keys"),
        "exact": S(hist, "keys", lambda r: r["state_minus_counties"] == 0),
        "largest_difference": max(abs(r["state_minus_counties"]) for r in hist),
    },
)
sp = {(r["source_table"], r["year"]): r for r in rows("prior-year-split")}
recs["prior-year-split"] = (
    ["prior-year-split"],
    {
        f"{table}_{year}_{key}": sp[(table, year)][key]
        for table in ("annual", "qtrly")
        for year in (2024, 2025)
        for key in ("without_prior_row", "without_prior_row_and_oty_value", "with_oty_value")
    },
)
pc = rows("parent-child-gaps")
slug = {"county to state": "county_state", "NAICS child to parent": "naics_parent"}
short = {"employment, third month": "employment", "total wages": "wages"}
recs["parent-child"] = (
    ["parent-child-gaps"],
    {
        f"{slug[r['hierarchy']]}_{short.get(r['measure'], r['measure'])}_{key}": r[key]
        for r in pc
        for key in ("parents", "exact", "mismatch_withheld_child", "mismatch_no_withheld_child")
    },
)
tw3 = rows("industry-level-three-ways")
recs["industry-level-three-ways"] = (
    ["industry-level-three-ways"],
    {
        "row_count": S(tw3, "row_count"),
        "wrong_by_length": S(tw3, "wrong_by_length"),
        "wrong_by_shape": S(tw3, "wrong_by_shape"),
        "wrong_by_digit": S(tw3, "wrong_by_digit"),
        "length_and_digit_differ": S(tw3, "length_and_digit_differ"),
    },
)
by = rows("parent-child-gaps-by-year")
recs["parent-child-by-year"] = (
    ["parent-child-gaps-by-year"],
    {
        f"{slug[r['hierarchy']]}_{r['year']}_{key}": float(r[key]) if "pct" in key else r[key]
        for r in by
        if r["measure"] == "employment, third month"
        for key in ("parents", "exact", "mismatch_withheld_child", "gap_pct_median")
    },
)
wq = {(r["st"], r["agglvl_code"]): r for r in rows("withheld-by-quarter")}
recs["withheld-by-quarter"] = (
    ["withheld-by-quarter"],
    {
        f"{st.lower()}_level_{level}_pct_{quarter}": float(wq[(st, level)][quarter])
        for st in ("DE", "MD")
        for level in (53, 73)
        for quarter in ("2024q4", "2025q1", "2025q4")
    },
)
lc = rows("load-check")
recs["load-check"] = (
    ["load-check"],
    {
        "groups": len(lc),
        "groups_equal": sum(r["verdict"] == "equal" for r in lc),
        "raw_rows": S(lc, "raw_rows"),
        "loaded_rows": S(lc, "loaded_rows"),
        "raw_withheld_rows": S(lc, "raw_n"),
        "loaded_withheld_rows": S(lc, "loaded_n"),
        "raw_padding_rows": S(lc, "raw_dash"),
        "loaded_padding_rows": S(lc, "loaded_dash"),
    },
)
ml = [r for r in rows("msa-levels-by-quarter") if r["agglvl_code"] != 40]
QUARTERS = [f"{y}q{q}" for y in (2024, 2025) for q in (1, 2, 3, 4)]
recs["msa-levels"] = (
    ["msa-levels-by-quarter"],
    {
        **{f"rows_levels_41_to_48_{q}": S(ml, q, lambda r: r["what"] == "rows") for q in QUARTERS},
        **{
            f"records_levels_41_to_48_{q}": S(ml, q, lambda r: r["what"] == "records")
            for q in QUARTERS
        },
        "annual_rows_levels_41_to_48_2024": S(ml, "annual_2024", lambda r: r["what"] == "rows"),
        "annual_rows_levels_41_to_48_2025": S(ml, "annual_2025", lambda r: r["what"] == "rows"),
    },
)
rp = {slug[r["hierarchy"]]: r for r in rows("rollup-padding-parents")}
recs["rollup-padding"] = (
    ["rollup-padding-parents"],
    {
        f"{h}_{key}": rp[h][key]
        for h in ("county_state", "naics_parent")
        for key in ("parents_compared", "records", "padding_rows", "msa_padding_2025_q3_q4")
    },
)
pm = rows("parent-child-msa-by-quarter")
recs["parent-child-msa"] = (
    ["parent-child-msa-by-quarter"],
    {
        "parents_2024": S(pm, "parents", lambda r: r["year"] == 2024),
        "mismatch_2024": S(pm, "mismatch", lambda r: r["year"] == 2024),
        "parents_2025": S(pm, "parents", lambda r: r["year"] == 2025),
        "mismatch_2025": S(pm, "mismatch", lambda r: r["year"] == 2025),
        "quarters_of_2025_with_a_pair": sum(r["year"] == 2025 for r in pm),
    },
)
NOTES = {
    "load-check": "Measured with scripts/check_load.py: every slice under data/raw counted with "
    "the csv module, against the loaded tables; the output is measurements/load-check.txt."
}
out = ["kind: evidence", "records:"]
for key, (queries, m) in recs.items():
    out += [
        f"- id: ev-measure-{key}-2026-11-28",
        "  source: qcew-duckdb-real",
        "  pin: duckdb:qcew@2026-11-28",
        "  measurement:",
    ]
    out += [f"    {a}: {b}" for a, b in m.items()]
    files = " and ".join(f"measurements/{q}.sql" for q in queries)
    out += [
        "  status: inferred",
        "  read_on: '2026-11-28'",
        "  environment: local",
        "  data_quality: representative",
        "  note: '"
        + NOTES.get(
            key,
            f"Measured with scripts/measure.py, not by a generated probe: {files}; "
            "each output is the .txt file beside its query.",
        )
        + "'",
    ]
Path("examples/qcew/evidence/measurements.yaml").write_text("\n".join(out) + "\n", encoding="utf-8")
print(len(recs), "records")

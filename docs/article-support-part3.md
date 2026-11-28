# Article support: Part 3 on the QCEW example

The commands and outputs Part 3 of the article shows, copied from `examples/qcew` so that the
article and the repository cannot drift. One block per article section; each section ends with
the files it was taken from. The rows are the BLS QCEW open data slices read on 2026-11-28
(`examples/qcew/sources/SOURCES.md` lists every URL with its checksum): Delaware, Maryland,
their counties, the metropolitan and micropolitan areas around them and the U.S. total, 2024
and 2025, annual and quarterly, unfiltered; the County-MSA-CSA crosswalk is the BLS spreadsheet
committed under `examples/qcew/sources/codelists/`. Outputs are from a run of
`examples/qcew/scripts/reproduce.sh` on 2026-11-28 on those slices, kept as
`examples/qcew/measurements/run-reproduce.log`; the run repeats a finished one, so it says
`unchanged` where a first run says `wrote`. The seconds in an output line are that machine's.
Every measurement is a query file under `examples/qcew/measurements/` with its output beside
it. `tests/docs/test_article_support_part3.py` checks every block against its file and runs
every measurement command of this page on the seeded tables.

This page is not in the site navigation and nothing links to it.

## 1. Setup: install, fetch, load, snapshot

```bash
git clone https://github.com/OSluchyk/factmodel
cd factmodel
uv sync
source .venv/bin/activate
bash examples/qcew/scripts/fetch.sh
uv run examples/qcew/scripts/load.sh
export FACT_DSN_QCEW_REAL="duckdb:///$PWD/examples/qcew/qcew.duckdb"
fact snapshot --root examples/qcew --source qcew-duckdb-real --date 2026-11-28
```

Measured on 2026-11-28: the download is 440 slices, 92,691,103 bytes, from 510 requests, the
last one 252 seconds after the first; 70 requests were answered 404, for seven area codes BLS
publishes nothing for. Loading takes a few seconds. On a folder that already holds that
read, `fetch.sh --resume` prints:

```text
fetch: 0 requests, 0 slices (0 bytes), 0 not published, 510 kept from the last run, 1 s
fetch: wrote data/raw/MANIFEST.tsv (in examples/qcew unless FACT_QCEW_RAW is set)
fetch: against checksums.sha256: 440 same, 0 changed, 0 new, 0 missing
```

What `load.sh` and the snapshot print:

```text
annual             110,366
qtrly              486,100
agglevel_titles         56
area_titles          9,458
industry_titles      2,678
ownership_titles         8
size_titles             10
load: 1.7 s
unchanged sources/snapshots/qcew-duckdb-real@2026-11-28.yaml (7 objects)
```

The snapshot holds seven tables and no key: nothing in the slices or in the load declares one.

From: `examples/qcew/scripts/reproduce.sh` (commands), `examples/qcew/measurements/run-reproduce.log`, `examples/qcew/measurements/run-fetch-resume.log` (output lines), `examples/qcew/sources/SOURCES.md` (the read).

## 2. Grain: one question, two levels

Private employment in Delaware in March 2025, once at one aggregation level and once with no
level filter.

```bash
uv run python examples/qcew/scripts/measure.py grain-mixed-level
```

```sql
-- Private employment in Delaware, March 2025 (third month of 2025 Q1): once at one
-- aggregation level, once with no level filter.
SELECT 'agglvl_code = 51' AS level_filter, count(*) AS row_count,
  sum(month3_emplvl) AS employment
FROM qtrly
WHERE area_fips = '10000' AND own_code = '5' AND year = '2025' AND qtr = '1'
  AND agglvl_code = '51'
UNION ALL
SELECT 'none', count(*), sum(month3_emplvl)
FROM qtrly
WHERE area_fips = '10000' AND own_code = '5' AND year = '2025' AND qtr = '1'
ORDER BY row_count
```

```text
level_filter     | row_count | employment
-----------------+-----------+-----------
agglvl_code = 51 |         1 |     405199
none             |      1732 |    2999697
```

The same rows, one line per level:

```bash
uv run python examples/qcew/scripts/measure.py grain-by-level
```

```text
agglvl_code | agglvl_title                                 | row_count | suppressed_rows | employment
------------+----------------------------------------------+-----------+-----------------+-----------
51          | State, Total -- by ownership sector          |         1 |               0 |     405199
52          | State, by Domain -- by ownership sector      |         2 |               0 |     405199
53          | State, by Supersector -- by ownership sector |        11 |               4 |     363731
54          | State, NAICS Sector -- by ownership sector   |        20 |               7 |     348761
55          | State, NAICS 3-digit -- by ownership sector  |        87 |              24 |     350002
56          | State, NAICS 4-digit -- by ownership sector  |       276 |              75 |     390821
57          | State, NAICS 5-digit -- by ownership sector  |       571 |             211 |     369684
58          | State, NAICS 6-digit -- by ownership sector  |       764 |             329 |     366300
```

The same query for Maryland:

```bash
uv run python examples/qcew/scripts/measure.py grain-mixed-level-maryland
```

```sql
-- The query of grain-mixed-level for Maryland: private employment, March 2025, once at one
-- aggregation level, once with no level filter.
SELECT 'agglvl_code = 51' AS level_filter, count(*) AS row_count,
  sum(month3_emplvl) AS employment
FROM qtrly
WHERE area_fips = '24000' AND own_code = '5' AND year = '2025' AND qtr = '1'
  AND agglvl_code = '51'
UNION ALL
SELECT 'none', count(*), sum(month3_emplvl)
FROM qtrly
WHERE area_fips = '24000' AND own_code = '5' AND year = '2025' AND qtr = '1'
ORDER BY row_count
```

```text
level_filter     | row_count | employment
-----------------+-----------+-----------
agglvl_code = 51 |         1 |    2209592
none             |      2039 |   17288738
```

From: `examples/qcew/measurements/grain-mixed-level.sql`, `examples/qcew/measurements/grain-mixed-level.txt`, `examples/qcew/measurements/grain-by-level.txt`, `examples/qcew/measurements/grain-mixed-level-maryland.sql`, `examples/qcew/measurements/grain-mixed-level-maryland.txt`.

## 3. Key: what the rows propose, and the key a person names

`fact propose keys` tries single columns and pairs. The two named keys are the documented
six-field key of each data table (D-024).

```bash
fact propose keys --root examples/qcew --source qcew-duckdb-real --environment local --data-quality representative --date 2026-11-28 --key annual:area_fips,own_code,industry_code,size_code,year,qtr --key qtrly:area_fips,own_code,industry_code,size_code,year,qtr
python3 examples/qcew/scripts/summary.py examples/qcew
```

```text
7 tables, 8 key candidates, 307 queries, 7.2 s: unchanged drafts/qcew-duckdb-real/keys.yaml
  named key annual (area_fips, own_code, industry_code, size_code, year, qtr): unique, 0 duplicate rows, 110366 rows
  named key qtrly (area_fips, own_code, industry_code, size_code, year, qtr): unique, 0 duplicate rows, 486100 rows
keys: 8 candidates over 7 tables, 307 queries,
  single columns and pairs only (max_columns 2)
  agglevel_titles: (agglvl_code), (agglvl_title); documented (agglvl_code): among them
  annual: none; documented (area_fips, own_code, industry_code, size_code, year, qtr): not among them
  area_titles: none; documented (area_fips): not among them
  industry_titles: (industry_code), (industry_title); documented (industry_code): among them
  ownership_titles: (own_code), (own_title); documented (own_code): among them
  qtrly: none; documented (area_fips, own_code, industry_code, size_code, year, qtr): not among them
  size_titles: (size_code), (size_title); documented (size_code): among them
  named key annual (area_fips, own_code, industry_code, size_code, year, qtr): unique, 0 duplicate rows, 110366 rows
  named key qtrly (area_fips, own_code, industry_code, size_code, year, qtr): unique, 0 duplicate rows, 486100 rows
```

The same key with one field left out:

```bash
uv run python examples/qcew/scripts/measure.py key-documented
```

```text
key_fields                                               | row_count | distinct_keys | rows_over
---------------------------------------------------------+-----------+---------------+----------
area_fips, own_code, industry_code, size_code, year, qtr |    486100 |        486100 |         0
without size_code                                        |    486100 |        486100 |         0
without qtr                                              |    486100 |        121525 |    364575
without year                                             |    486100 |        247496 |    238604
without industry_code                                    |    486100 |          1624 |    484476
without own_code                                         |    486100 |        436180 |     49920
without area_fips                                        |    486100 |         36080 |    450020
```

The search finds no key for `annual` and `qtrly`: no column and no pair is unique. Named, the
six-field key is unique on every row. No tool finds a six-column key without being told its
columns.

From: `examples/qcew/scripts/reproduce.sh` (commands), `examples/qcew/measurements/run-reproduce.log` (output lines), `examples/qcew/measurements/key-documented.txt`.

## 4. Cardinality: the join to the area list

```bash
uv run python examples/qcew/scripts/measure.py cardinality-area-titles
```

```sql
-- Quarterly rows before a join to the area code list, after a plain join, and after a join
-- to distinct codes.
SELECT 1 AS step, 'qtrly' AS rows_of, count(*) AS row_count FROM qtrly
UNION ALL
SELECT 2, 'qtrly JOIN area_titles', count(*)
FROM qtrly AS q JOIN area_titles AS t ON q.area_fips = t.area_fips
UNION ALL
SELECT 3, 'qtrly JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles)', count(*)
FROM qtrly AS q
JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) AS t ON q.area_fips = t.area_fips
ORDER BY step
```

```text
step | rows_of                                                             | row_count
-----+---------------------------------------------------------------------+----------
   1 | qtrly                                                               |    486100
   2 | qtrly JOIN area_titles                                              |    972200
   3 | qtrly JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) |    486100
```

Why: the list as BLS serves it.

```bash
uv run python examples/qcew/scripts/measure.py area-titles-duplicates
```

```text
row_count | distinct_codes | codes_twice | codes_more_than_twice | codes_with_two_titles | header_rows
----------+----------------+-------------+-----------------------+-----------------------+------------
     9458 |           4809 |        4649 |                     0 |                     0 |           1
```

`fact propose joins` on the same rows names the target it could not use:

```bash
fact propose joins --root examples/qcew --source qcew-duckdb-real --environment local --data-quality representative --date 2026-11-28
```

```text
7 tables, 15 join candidates, 163 queries, 2.8 s: unchanged drafts/qcew-duckdb-real/joins.yaml
  skipped target area_titles.area_fips: not unique, 4649 duplicate rows of 9458; no join to it is proposed
  skipped target area_titles.area_title: not unique, 4653 duplicate rows of 9458; no join to it is proposed
joins: 15 candidates at threshold 0.999, 163 queries
  8 of the model's 10 one-column equality joins found
  not proposed: annual.area_fips = area_titles.area_fips  (annual.to-area)
  not proposed: qtrly.area_fips = area_titles.area_fips  (qtrly.to-area)
  target not unique: area_titles.area_fips, 4649 duplicate rows of 9458
  target not unique: area_titles.area_title, 4653 duplicate rows of 9458
  7 other inclusions above the threshold, for a reader to judge:
    annual.own_code = size_titles.size_code  (many_to_one)
    annual.size_code = ownership_titles.own_code  (many_to_one)
    ownership_titles.own_code = size_titles.size_code  (one_to_one)
    qtrly.own_code = size_titles.size_code  (many_to_one)
    qtrly.qtr = ownership_titles.own_code  (many_to_one)
    qtrly.qtr = size_titles.size_code  (many_to_one)
    qtrly.size_code = ownership_titles.own_code  (many_to_one)
```

From: `examples/qcew/measurements/cardinality-area-titles.sql`, `examples/qcew/measurements/cardinality-area-titles.txt`, `examples/qcew/measurements/area-titles-duplicates.txt`, `examples/qcew/scripts/reproduce.sh` (command), `examples/qcew/measurements/run-reproduce.log` (output lines).

## 5. Hierarchy that is not a tree

The industry codes in the rows, by shape, and how many have no code one character shorter in
the industry list:

```bash
uv run python examples/qcew/scripts/measure.py industry-code-shapes
```

```text
shape                               | codes | first_code | last_code | without_prefix_parent
------------------------------------+-------+------------+-----------+----------------------
1 total (10)                        |     1 | 10         | 10        |                     0
2 domain (101, 102)                 |     2 | 101        | 102       |                     0
3 supersector (10xx)                |    12 | 1011       | 1029      |                     0
4 sector written as a range (nn-nn) |     3 | 31-33      | 48-49     |                     3
5 NAICS, 2 digits                   |    18 | 11         | 99        |                     0
5 NAICS, 3 digits                   |    97 | 111        | 999       |                    41
5 NAICS, 4 digits                   |   309 | 1111       | 9999      |                     0
5 NAICS, 5 digits                   |   688 | 11111      | 99999     |                     0
5 NAICS, 6 digits                   |  1029 | 111110     | 999999    |                     0
```

The counties of the MSA that crosses the two states, from the BLS crosswalk spreadsheet:

```bash
uv run python examples/qcew/scripts/measure.py crosswalk-c3798
```

```sql
-- The counties of C3798 (Philadelphia-Camden-Wilmington, PA-NJ-DE-MD) by state, from the BLS
-- County-MSA-CSA crosswalk, sheet for data from 2024 on, and whether the slices hold them.
SELECT substr(c.county_code, 1, 2) AS state_fips,
  trim(split_part(c.county_title, ',', 2)) AS state, count(*) AS counties,
  string_agg(c.county_code || ' ' || trim(split_part(c.county_title, ',', 1)), '; '
    ORDER BY c.county_code) AS county_list,
  sum(CASE WHEN EXISTS (SELECT 1 FROM annual AS a WHERE a.area_fips = c.county_code)
    THEN 1 ELSE 0 END) AS in_the_slices
FROM crosswalk AS c
WHERE c.msa_code = 'C3798'
GROUP BY substr(c.county_code, 1, 2), trim(split_part(c.county_title, ',', 2))
ORDER BY state_fips
```

```text
state_fips | state        | counties | county_list                                                                                                         | in_the_slices
-----------+--------------+----------+---------------------------------------------------------------------------------------------------------------------+--------------
10         | Delaware     |        1 | 10003 New Castle County                                                                                             |             1
24         | Maryland     |        1 | 24015 Cecil County                                                                                                  |             1
34         | New Jersey   |        4 | 34005 Burlington County; 34007 Camden County; 34015 Gloucester County; 34033 Salem County                           |             0
42         | Pennsylvania |        5 | 42017 Bucks County; 42029 Chester County; 42045 Delaware County; 42091 Montgomery County; 42101 Philadelphia County |             0
```

How much of each state the crosswalk and the slices cover:

```bash
uv run python examples/qcew/scripts/measure.py crosswalk-coverage
```

```text
state_fips | in_area_of_kind | counties | areas | areas_with_a_slice
-----------+-----------------+----------+-------+-------------------
10         | MSA             |        2 |     2 |                  2
10         | MicroSA         |        1 |     1 |                  1
24         | MSA             |       17 |     6 |                  6
24         | MicroSA         |        4 |     4 |                  4
```

What adding the two state rows and the MSA row counts twice:

```bash
uv run python examples/qcew/scripts/measure.py msa-double-count
```

```sql
-- Total covered employment, March 2025: Delaware, Maryland, the MSA that crosses both (C3798,
-- Philadelphia-Camden-Wilmington, PA-NJ-DE-MD), and the two counties of the MSA that lie in
-- the two states. Adding the two state rows and the MSA row counts those two counties twice.
-- The rest of the MSA row is not counted twice: it is nine counties of Pennsylvania and New
-- Jersey, which belong to neither state.
WITH areas AS (
  SELECT q.area_fips, t.area_title, q.agglvl_code, q.month3_emplvl
  FROM qtrly AS q
  JOIN (SELECT DISTINCT area_fips, area_title FROM area_titles) AS t
    ON q.area_fips = t.area_fips
  WHERE q.own_code = '0' AND q.industry_code = '10' AND q.year = '2025' AND q.qtr = '1'
    AND q.area_fips IN ('10000', '24000', 'C3798', '10003', '24015')
)
SELECT 1 AS n, area_fips || ' ' || area_title AS what, agglvl_code, month3_emplvl AS employment
FROM areas
UNION ALL
SELECT 2, 'sum of the two states', '50', sum(month3_emplvl)
FROM areas WHERE area_fips IN ('10000', '24000')
UNION ALL
SELECT 3, 'the two state rows and the MSA row added', '50, 40', sum(month3_emplvl)
FROM areas WHERE area_fips IN ('10000', '24000', 'C3798')
UNION ALL
SELECT 4, 'counted twice in that sum: New Castle and Cecil', '70',
  sum(month3_emplvl)
FROM areas WHERE area_fips IN ('10003', '24015')
UNION ALL
SELECT 5, 'in the MSA row, outside the two states: nine counties of PA and NJ', '40 - 70',
  sum(CASE WHEN area_fips = 'C3798' THEN month3_emplvl
           WHEN area_fips IN ('10003', '24015') THEN -month3_emplvl ELSE 0 END)
FROM areas
ORDER BY n, what
```

```text
n | what                                                               | agglvl_code | employment
--+--------------------------------------------------------------------+-------------+-----------
1 | 10000 Delaware -- Statewide                                        | 50          |     474808
1 | 10003 New Castle County, Delaware                                  | 70          |     304770
1 | 24000 Maryland -- Statewide                                        | 50          |    2747673
1 | 24015 Cecil County, Maryland                                       | 70          |      36829
1 | C3798 Philadelphia-Camden-Wilmington, PA-NJ-DE-MD MSA              | 40          |    2879878
2 | sum of the two states                                              | 50          |    3222481
3 | the two state rows and the MSA row added                           | 50, 40      |    6102359
4 | counted twice in that sum: New Castle and Cecil                    | 70          |     341599
5 | in the MSA row, outside the two states: nine counties of PA and NJ | 40 - 70     |    2538279
```

An MSA inside one state, rebuilt from its seven counties:

```bash
uv run python examples/qcew/scripts/measure.py msa-from-counties
```

```text
qtr | msa_disclosure_code | msa_row | sum_of_counties | county_rows | suppressed_rows
----+---------------------+---------+-----------------+-------------+----------------
1   |                     | 1109757 |         1109757 |           7 |               0
2   |                     | 1130287 |         1130287 |           7 |               0
3   | -                   |       0 |         1116468 |           7 |               0
4   | -                   |       0 |         1125681 |           7 |               0
```

From: `examples/qcew/measurements/industry-code-shapes.txt`, `examples/qcew/measurements/crosswalk-c3798.sql`, `examples/qcew/measurements/crosswalk-c3798.txt`, `examples/qcew/measurements/crosswalk-coverage.txt`, `examples/qcew/measurements/msa-double-count.sql`, `examples/qcew/measurements/msa-double-count.txt`, `examples/qcew/measurements/msa-from-counties.txt`.

## 6. Two representations of one thing

Candidate A: a published parent and the sum of its children state the same quantity twice.

```bash
uv run python examples/qcew/scripts/measure.py parent-child-gaps
```

```sql
-- A published parent against the sum of its children, quarterly rows, for two hierarchies
-- (county to state by the area code, NAICS child to parent by the code one character
-- shorter) and three measures. A pair counts when the parent row is disclosed and has at
-- least one child row; padding rows are left out. The sum takes disclosed children only for
-- employment and wages, and every child for establishments, which stay filled on withheld
-- rows. gap is the parent less the sum, as a percentage of the parent, over the mismatches.
WITH pairs AS (
  SELECT 'county to state' AS hierarchy, p.area_fips, p.own_code, p.industry_code, p.year,
    p.qtr, p.month3_emplvl AS p_emp, p.total_qtrly_wages AS p_wages, p.qtrly_estabs AS p_est,
    c.disclosure_code AS c_code, c.month3_emplvl AS c_emp, c.total_qtrly_wages AS c_wages,
    c.qtrly_estabs AS c_est
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.area_fips, 1, 2) || '000' = p.area_fips AND substr(c.area_fips, 3, 3) <> '000'
    AND substr(c.area_fips, 1, 1) <= '9' AND c.own_code = p.own_code
    AND c.industry_code = p.industry_code AND c.size_code = p.size_code
    AND c.year = p.year AND c.qtr = p.qtr
  WHERE p.disclosure_code IS NULL AND (c.disclosure_code IS NULL OR c.disclosure_code = 'N')
  UNION ALL
  SELECT 'NAICS child to parent', p.area_fips, p.own_code, p.industry_code, p.year, p.qtr,
    p.month3_emplvl, p.total_qtrly_wages, p.qtrly_estabs,
    c.disclosure_code, c.month3_emplvl, c.total_qtrly_wages, c.qtrly_estabs
  FROM qtrly AS p
  JOIN qtrly AS c
    ON substr(c.industry_code, 1, length(c.industry_code) - 1) = p.industry_code
    AND length(c.industry_code) > 2 AND c.area_fips = p.area_fips AND c.own_code = p.own_code
    AND c.size_code = p.size_code AND c.year = p.year AND c.qtr = p.qtr
  WHERE p.disclosure_code IS NULL AND (c.disclosure_code IS NULL OR c.disclosure_code = 'N')
), parents AS (
  SELECT hierarchy, area_fips, own_code, industry_code, year, qtr,
    max(p_emp) AS p_emp, max(p_wages) AS p_wages, max(p_est) AS p_est,
    sum(CASE WHEN c_code IS NULL THEN c_emp ELSE 0 END) AS s_emp,
    sum(CASE WHEN c_code IS NULL THEN c_wages ELSE 0 END) AS s_wages,
    sum(c_est) AS s_est,
    sum(CASE WHEN c_code = 'N' THEN 1 ELSE 0 END) AS withheld_children
  FROM pairs
  GROUP BY hierarchy, area_fips, own_code, industry_code, year, qtr
), measured AS (
  SELECT hierarchy, 1 AS n, 'employment, third month' AS measure, p_emp AS parent,
    s_emp AS children, withheld_children FROM parents
  UNION ALL
  SELECT hierarchy, 2, 'total wages', p_wages, s_wages, withheld_children FROM parents
  UNION ALL
  SELECT hierarchy, 3, 'establishments', p_est, s_est, withheld_children FROM parents
)
SELECT hierarchy, measure, count(*) AS parents,
  sum(CASE WHEN parent = children THEN 1 ELSE 0 END) AS exact,
  sum(CASE WHEN parent <> children AND withheld_children > 0 THEN 1 ELSE 0 END)
    AS mismatch_withheld_child,
  sum(CASE WHEN parent <> children AND withheld_children = 0 THEN 1 ELSE 0 END)
    AS mismatch_no_withheld_child,
  round(median(CASE WHEN parent <> children AND parent > 0
    THEN 100.0 * (parent - children) / parent END), 1) AS gap_pct_median,
  round(quantile_cont(CASE WHEN parent <> children AND parent > 0
    THEN 100.0 * (parent - children) / parent END, 0.9), 1) AS gap_pct_p90,
  round(max(CASE WHEN parent <> children AND parent > 0
    THEN 100.0 * (parent - children) / parent END), 1) AS gap_pct_max
FROM measured
GROUP BY hierarchy, n, measure
ORDER BY hierarchy, n
```

```text
hierarchy             | measure                 | parents |  exact | mismatch_withheld_child | mismatch_no_withheld_child | gap_pct_median | gap_pct_p90 | gap_pct_max
----------------------+-------------------------+---------+--------+-------------------------+----------------------------+----------------+-------------+------------
NAICS child to parent | employment, third month |  130999 | 101073 |                   29926 |                          0 |           97.2 |         100 |         100
NAICS child to parent | total wages             |  130999 | 101061 |                   29938 |                          0 |           97.4 |         100 |         100
NAICS child to parent | establishments          |  130999 | 130999 |                       0 |                          0 |           NULL |        NULL |        NULL
county to state       | employment, third month |   27698 |   5918 |                   21780 |                          0 |           38.7 |         100 |         100
county to state       | total wages             |   27698 |   5913 |                   21785 |                          0 |           37.1 |         100 |         100
county to state       | establishments          |   27698 |  27698 |                       0 |                          0 |           NULL |        NULL |        NULL
```

Six of those rows:

```bash
uv run python examples/qcew/scripts/measure.py parent-child-examples
```

```text
area_fips | industry_title                                            | published_parent | sum_disclosed_children |   gap | gap_pct | children | withheld_children
----------+-----------------------------------------------------------+------------------+------------------------+-------+---------+----------+------------------
10000     | NAICS 62 Health care and social assistance                |            81306 |                  69379 | 11927 |    14.7 |        4 |                 2
10000     | NAICS 72 Accommodation and food services                  |            40458 |                  28288 | 12170 |    30.1 |        4 |                 2
10000     | NAICS 31-33 Manufacturing                                 |            26595 |                  11502 | 15093 |    56.8 |        4 |                 3
24000     | NAICS 62 Health care and social assistance                |           413009 |                 409057 |  3952 |       1 |       25 |                 4
24000     | NAICS 54 Professional, scientific, and technical services |           276138 |                 275326 |   812 |     0.3 |       25 |                 4
24000     | NAICS 72 Accommodation and food services                  |           217241 |                 214979 |  2262 |       1 |       25 |                 4
```

The same pairs, one line per year:

```bash
uv run python examples/qcew/scripts/measure.py parent-child-gaps-by-year
```

```text
hierarchy             | measure                 | year | parents | exact | mismatch_withheld_child | mismatch_no_withheld_child | gap_pct_median | gap_pct_p90 | gap_pct_max
----------------------+-------------------------+------+---------+-------+-------------------------+----------------------------+----------------+-------------+------------
NAICS child to parent | employment, third month | 2024 |   67393 | 51651 |                   15742 |                          0 |           97.3 |         100 |         100
NAICS child to parent | employment, third month | 2025 |   63606 | 49422 |                   14184 |                          0 |           96.9 |         100 |         100
NAICS child to parent | total wages             | 2024 |   67393 | 51646 |                   15747 |                          0 |           97.7 |         100 |         100
NAICS child to parent | total wages             | 2025 |   63606 | 49415 |                   14191 |                          0 |           97.1 |         100 |         100
NAICS child to parent | establishments          | 2024 |   67393 | 67393 |                       0 |                          0 |           NULL |        NULL |        NULL
NAICS child to parent | establishments          | 2025 |   63606 | 63606 |                       0 |                          0 |           NULL |        NULL |        NULL
county to state       | employment, third month | 2024 |   13985 |  3064 |                   10921 |                          0 |           34.9 |         100 |         100
county to state       | employment, third month | 2025 |   13713 |  2854 |                   10859 |                          0 |           43.1 |         100 |         100
county to state       | total wages             | 2024 |   13985 |  3064 |                   10921 |                          0 |           33.8 |         100 |         100
county to state       | total wages             | 2025 |   13713 |  2849 |                   10864 |                          0 |           41.3 |         100 |         100
county to state       | establishments          | 2024 |   13985 | 13985 |                       0 |                          0 |           NULL |        NULL |        NULL
county to state       | establishments          | 2025 |   13713 | 13713 |                       0 |                          0 |           NULL |        NULL |        NULL
```

The withheld share behind the gap, in percent of the rows, per aggregation level and quarter:

```bash
uv run python examples/qcew/scripts/measure.py withheld-by-quarter
```

```text
st | agglvl_code | 2024q1 | 2024q2 | 2024q3 | 2024q4 | 2025q1 | 2025q2 | 2025q3 | 2025q4
---+-------------+--------+--------+--------+--------+--------+--------+--------+-------
DE | 50          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
DE | 51          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
DE | 52          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
DE | 53          |   19.4 |   19.4 |   19.4 |   19.4 |   34.4 |   34.4 |   34.4 |   28.1
DE | 54          |   21.3 |   21.3 |   25.5 |   25.5 |   37.5 |   33.3 |   37.5 |   31.3
DE | 55          |   22.5 |   23.2 |   23.9 |   23.2 |   30.1 |   26.6 |     28 |   26.6
DE | 56          |   27.4 |   27.1 |   27.7 |     28 |   29.7 |   30.3 |   30.3 |   28.2
DE | 57          |   33.5 |   32.9 |   32.8 |   35.2 |   37.8 |   37.9 |   37.1 |   35.8
DE | 58          |   38.9 |   38.2 |   38.3 |   40.9 |   42.9 |   42.4 |   42.5 |   41.6
DE | 70          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
DE | 71          |     40 |     40 |     40 |     40 |   53.3 |   53.3 |   53.3 |   53.3
DE | 72          |   39.1 |   39.1 |   39.1 |   39.1 |   69.6 |   69.6 |   69.6 |   69.6
DE | 73          |   24.1 |   24.1 |   24.1 |   24.1 |   48.9 |   44.9 |   48.9 |   48.9
DE | 74          |   30.5 |   30.5 |   29.8 |     29 |   49.2 |   44.4 |     50 |   50.7
DE | 75          |   35.5 |   35.4 |   37.2 |   38.3 |     49 |   49.1 |   48.3 |   48.4
DE | 76          |   54.2 |   54.3 |   53.7 |   55.1 |   61.1 |   60.8 |   60.2 |   60.9
DE | 77          |   62.5 |     62 |   62.1 |   63.3 |   73.1 |   72.5 |   72.1 |   72.8
DE | 78          |   67.2 |   66.8 |   67.4 |   68.7 |   77.4 |     77 |   76.5 |   77.1
MD | 50          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
MD | 51          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
MD | 52          |     25 |     25 |     25 |     25 |     25 |     25 |     25 |     25
MD | 53          |   21.4 |   21.4 |     22 |   22.5 |     35 |   27.5 |   24.4 |   24.4
MD | 54          |     20 |   18.3 |   20.3 |   15.5 |     31 |   20.7 |   18.6 |   18.6
MD | 55          |   19.2 |   17.7 |   19.8 |   18.2 |   23.9 |   18.3 |   18.2 |   17.7
MD | 56          |   18.8 |   17.3 |   17.4 |   18.8 |   19.3 |   17.7 |   17.2 |   16.6
MD | 57          |   21.3 |   20.9 |   21.5 |   21.8 |   21.4 |   21.2 |     21 |   20.5
MD | 58          |     28 |   27.6 |   27.3 |   28.2 |   27.2 |     27 |   26.6 |   26.7
MD | 70          |      0 |      0 |      0 |      0 |      0 |      0 |      0 |      0
MD | 71          |     18 |      8 |      4 |     18 |      8 |      8 |      8 |      8
MD | 72          |   26.3 |     21 |   21.6 |   26.6 |   22.3 |   22.3 |   22.3 |   20.4
MD | 73          |   20.4 |     20 |   21.1 |   21.3 |   31.2 |   30.1 |   31.3 |   29.2
MD | 74          |   24.5 |   23.7 |   24.7 |   24.7 |   32.5 |     31 |   31.8 |   29.7
MD | 75          |   34.7 |   33.6 |   33.6 |   34.9 |   35.1 |   35.2 |   34.5 |   33.7
MD | 76          |   47.4 |   46.5 |   46.6 |   48.4 |   47.1 |   47.1 |   46.9 |   45.9
MD | 77          |   57.6 |   56.9 |   56.7 |   58.2 |   57.3 |   57.6 |   57.7 |     57
MD | 78          |   62.7 |   61.7 |   61.7 |   63.3 |   62.3 |   62.8 |   62.8 |     62
```

and per ownership and year:

```bash
uv run python examples/qcew/scripts/measure.py withheld-by-ownership-year
```

```text
st | own_code | rows_2024 | n_2024 | pct_2024 | rows_2025 | n_2025 | pct_2025
---+----------+-----------+--------+----------+-----------+--------+---------
DE | 0        |        20 |      0 |        0 |        20 |      0 |        0
DE | 1        |      2258 |      0 |        0 |      2262 |      0 |        0
DE | 2        |      1440 |   1188 |     82.5 |      1440 |   1264 |     87.8
DE | 3        |       600 |    432 |       72 |       600 |    564 |       94
DE | 5        |     27190 |  14986 |     55.1 |     27353 |  17472 |     63.9
DE | 8        |         4 |      0 |        0 |         4 |      0 |        0
MD | 0        |       104 |      0 |        0 |       104 |      0 |        0
MD | 1        |      7443 |      0 |        0 |      7454 |      0 |        0
MD | 2        |      4525 |   3446 |     76.2 |      4559 |   3551 |     77.9
MD | 3        |      5670 |   4169 |     73.5 |      5624 |   4342 |     77.2
MD | 5        |    127845 |  67695 |       53 |    129053 |  68494 |     53.1
MD | 8        |         4 |      0 |        0 |         4 |      0 |        0
```

The loaded tables against the slices as BLS served them:

```bash
python3 examples/qcew/scripts/check_load.py
```

```text
source_table | year | areas | raw_rows | loaded_rows | raw_n | loaded_n | raw_dash | loaded_dash | verdict
-------------+------+-------+----------+-------------+-------+----------+----------+-------------+--------
annual       | 2024 | DE    |     7914 |        7914 |  4446 |     4446 |        0 |           0 | equal
annual       | 2024 | MD    |    37053 |       37053 | 20840 |    20840 |        0 |           0 | equal
annual       | 2024 | other |    15696 |       15696 | 10509 |    10509 |        0 |           0 | equal
annual       | 2025 | DE    |     7970 |        7970 |  5270 |     5270 |        0 |           0 | equal
annual       | 2025 | MD    |    37227 |       37227 | 21035 |    21035 |        0 |           0 | equal
annual       | 2025 | other |     4506 |        4506 |   667 |      667 |        0 |           0 | equal
qtrly        | 2024 | DE    |    31656 |       31656 | 16606 |    16606 |      144 |         144 | equal
qtrly        | 2024 | MD    |   148212 |      148212 | 75310 |    75310 |     2621 |        2621 | equal
qtrly        | 2024 | other |    62784 |       62784 | 40445 |    40445 |      471 |         471 | equal
qtrly        | 2025 | DE    |    31880 |       31880 | 19300 |    19300 |      201 |         201 | equal
qtrly        | 2025 | MD    |   148908 |      148908 | 76387 |    76387 |     2110 |        2110 | equal
qtrly        | 2025 | other |    62660 |       62660 | 22107 |    22107 |    22377 |       22377 | equal
```

The withheld share rises in the first quarter of 2025 and stays. Rows, withheld rows and padding
rows are the same in the slices and in the tables, so the load did not cause it. No BLS page
read on 2026-11-28 states a change of the disclosure rules for 2025
(`ev-doc-confidentiality` in `examples/qcew/evidence/documents.yaml`); the cause is not known.
The median gap between a state row and the sum of its disclosed counties is 34.9 percent in
2024 and 43.1 in 2025; 38.7 is both years together.

Candidate B: the industry level of a row can be read from the length of `industry_code`, from
the shape of the code, or from the second digit of `agglvl_code`. Each reading is checked
against the title of the row's aggregation level.

```bash
uv run python examples/qcew/scripts/measure.py industry-level-three-ways
```

```sql
-- The industry level of every quarterly row, read three ways and checked against what the
-- title of its aggregation level says: from the length of industry_code, from a rule that
-- knows the shapes of the code, and from the second digit of agglvl_code. Per kind of code:
-- rows, rows each reading gets wrong, and rows where length and second digit disagree.
WITH readings AS (
  SELECT
    CASE
      WHEN q.industry_code = '10' AND q.agglvl_code >= '90' THEN '2 total (10) at levels 94 to 96'
      WHEN q.industry_code = '10' THEN '1 total (10)'
      WHEN q.industry_code IN ('101', '102') THEN '3 domain (101, 102)'
      WHEN length(q.industry_code) = 4 AND q.industry_code LIKE '10%' THEN '4 supersector (10xx)'
      WHEN q.industry_code LIKE '%-%' THEN '5 sector written as a range (nn-nn)'
      ELSE '6 NAICS, ' || length(q.industry_code) || ' digits'
    END AS kind_of_code,
    CASE
      WHEN t.agglvl_title LIKE '%Domain%' THEN 'domain'
      WHEN t.agglvl_title LIKE '%Supersector%' THEN 'supersector'
      WHEN t.agglvl_title LIKE '%NAICS Sector%' THEN 'sector'
      WHEN t.agglvl_title LIKE '%NAICS _-digit%' THEN 'naics' || substr(t.agglvl_title, strpos(t.agglvl_title, 'NAICS ') + 6, 1)
      ELSE 'total'
    END AS level_by_title,
    CASE length(q.industry_code) WHEN 2 THEN 'sector' ELSE 'naics' || length(q.industry_code) END
      AS level_by_length,
    CASE
      WHEN q.industry_code = '10' THEN 'total'
      WHEN q.industry_code IN ('101', '102') THEN 'domain'
      WHEN length(q.industry_code) = 4 AND q.industry_code LIKE '10%' THEN 'supersector'
      WHEN q.industry_code LIKE '%-%' OR length(q.industry_code) = 2 THEN 'sector'
      ELSE 'naics' || length(q.industry_code)
    END AS level_by_shape,
    CASE substr(q.agglvl_code, 2, 1)
      WHEN '0' THEN 'total' WHEN '1' THEN 'total' WHEN '2' THEN 'domain'
      WHEN '3' THEN 'supersector' WHEN '4' THEN 'sector'
      ELSE 'naics' || CAST(CAST(substr(q.agglvl_code, 2, 1) AS INTEGER) - 2 AS VARCHAR)
    END AS level_by_digit
  FROM qtrly AS q
  JOIN agglevel_titles AS t ON q.agglvl_code = t.agglvl_code
)
SELECT kind_of_code, count(*) AS row_count,
  sum(CASE WHEN level_by_length <> level_by_title THEN 1 ELSE 0 END) AS wrong_by_length,
  sum(CASE WHEN level_by_shape <> level_by_title THEN 1 ELSE 0 END) AS wrong_by_shape,
  sum(CASE WHEN level_by_digit <> level_by_title THEN 1 ELSE 0 END) AS wrong_by_digit,
  sum(CASE WHEN level_by_length <> level_by_digit THEN 1 ELSE 0 END) AS length_and_digit_differ,
  sum(CASE WHEN level_by_shape <> level_by_digit THEN 1 ELSE 0 END) AS shape_and_digit_differ
FROM readings
GROUP BY kind_of_code
ORDER BY kind_of_code
```

```text
kind_of_code                        | row_count | wrong_by_length | wrong_by_shape | wrong_by_digit | length_and_digit_differ | shape_and_digit_differ
------------------------------------+-----------+-----------------+----------------+----------------+-------------------------+-----------------------
1 total (10)                        |      1592 |            1592 |              0 |              0 |                    1592 |                      0
2 total (10) at levels 94 to 96     |        32 |              32 |              0 |             32 |                      24 |                     32
3 domain (101, 102)                 |      1596 |            1596 |              0 |              0 |                    1596 |                      0
4 supersector (10xx)                |      6628 |            6628 |              0 |              0 |                    6628 |                      0
5 sector written as a range (nn-nn) |      1504 |            1504 |              0 |              0 |                    1504 |                      0
6 NAICS, 2 digits                   |      8572 |               0 |              0 |              0 |                       0 |                      0
6 NAICS, 3 digits                   |     33480 |               0 |              0 |              0 |                       0 |                      0
6 NAICS, 4 digits                   |     84140 |               0 |              0 |              0 |                       0 |                      0
6 NAICS, 5 digits                   |    152868 |               0 |              0 |              0 |                       0 |                      0
6 NAICS, 6 digits                   |    195688 |               0 |              0 |              0 |                       0 |                      0
```

The rows of 2025 Q1 on which the second digit is wrong:

```bash
uv run python examples/qcew/scripts/measure.py industry-level-disagreements
```

```text
area_fips | own_code | industry_code | agglvl_code | agglvl_title               | level_from_code | level_from_agglvl | month3_emplvl
----------+----------+---------------+-------------+----------------------------+-----------------+-------------------+--------------
10000     | 8        | 10            | 96          | Total Government, by State | 1               | 6                 |         69609
24000     | 8        | 10            | 96          | Total Government, by State | 1               | 6                 |        538081
US000     | 8        | 10            | 95          | Total Government (U.S.)    | 1               | 5                 |      22933857
US000     | 9        | 10            | 94          | Total U.I. Covered (U.S.)  | 1               | 4                 |     151702540
```

From: `examples/qcew/measurements/parent-child-gaps.sql`, `examples/qcew/measurements/parent-child-gaps.txt`, `examples/qcew/measurements/parent-child-examples.txt`, `examples/qcew/measurements/parent-child-gaps-by-year.txt`, `examples/qcew/measurements/withheld-by-quarter.txt`, `examples/qcew/measurements/withheld-by-ownership-year.txt`, `examples/qcew/scripts/reproduce.sh` (command), `examples/qcew/measurements/load-check.txt`, `examples/qcew/measurements/industry-level-three-ways.sql`, `examples/qcew/measurements/industry-level-three-ways.txt`, `examples/qcew/measurements/industry-level-disagreements.txt`.

## 7. The layer: the model files that encode each of the above

The grain of an entity, in the physical model:

```yaml
grain: One row per area, ownership, industry, size class, year and quarter.
class: data
status: draft
meaning: QCEW quarterly counts, monthly employment and wages per key (BLS quarterly singlefile layout).
keys:
  primary:
  - area_fips
  - own_code
  - industry_code
  - size_code
  - year
  - qtr
  current_row_rule:
```

and on a measure of the layer:

```yaml
- id: employment_month3
  meaning: Employment in the third month of the quarter.
  expression: qtrly.month3_emplvl
  aggregation: sum
  grain: {entity: qtrly, fields: [area_fips, own_code, industry_code, size_code, year, qtr]}
  time: {field: qtrly.qtr, granularity: quarter}
  suppressed: exclude
  companion: suppressed_cells
  rollups:
  - {hierarchy: area_titles.in-state, field: area_fips, suppressed: suppressed}
  - {hierarchy: industry_titles.parent, field: industry_code, suppressed: suppressed}
```

A relationship with its cardinality, and the layer concept that answers it:

```yaml
- key: to-area
  to: area_titles
  join: qtrly.area_fips = area_titles.area_fips
  meaning: 'The area the row aggregates over. Many to many as published: the area code list repeats 4,649 codes (F-0001), so a row meets two identical title rows.'
  mechanism: inferred_join
  cardinality: many_to_many
  evidence:
  - ev-doc-area-codes
  - ev-doc-r1
  - ev-join-match-qtrly-to-area-2026-10-27
  - ev-join-match-qtrly-to-area-2026-11-28
```

```yaml
- id: distinct_areas
  meaning: >-
    The area code list repeats 4,649 codes (F-0001); a join to it is a join to distinct
    codes, or every row counts twice.
  distinct: [area_titles.area_fips, area_titles.area_title]
  required: true
  evidence: [ev-doc-r1, ev-key-duplicates-area-titles-2026-10-27]
```

Two hierarchy relationships: one the codes carry, one they do not.

```yaml
- key: parent
  to: industry_titles
  join: substr(industry_titles.industry_code, 1, length(industry_titles.industry_code) - 1) = industry_titles.industry_code AND length(industry_titles.industry_code) > 2
  meaning: 'A code to the code one character shorter (D-017): NAICS 6 to 5 to 4 to 3 digits, supersector to domain, domain to the total. Sector ranges and the 3-digit codes under them find no parent this way (F-0008).'
  expected:
    orphans_left: 53
    reason: The three sector ranges 31-33, 44-45 and 48-49 and the 50 three-digit codes under them have no code one character shorter; the list is built that way (F-0008).
  mechanism: inferred_join
  cardinality: many_to_one
  evidence:
  - ev-doc-v3
  - ev-doc-title-files
  - ev-fan-out-industry-titles-parent-2026-10-27
  - ev-rollup-employment-month3-industry-titles-parent-2026-10-27
  - ev-fan-out-industry-titles-parent-2026-11-28
  - ev-rollup-employment-month3-industry-titles-parent-2026-11-28
  - ev-join-match-industry-titles-parent-2026-11-28
```

```yaml
- key: in-msa
  to: area_titles
  meaning: 'A county to its MSA or MicroSA. Geography is a lattice, not a tree (H1): this link is separate from the county to state link, and an MSA crosses state lines.'
  mechanism: inferred_join
  cardinality: many_to_one
  status: unresolved
  missing: The BLS County-MSA-CSA crosswalk, which is not in the example; area codes do not encode MSA membership.
  evidence:
  - ev-doc-h1
  - ev-doc-msa-codes
```

A concept: the aggregation level is a field of the row, and the layer says why the code is not enough.

```yaml
- id: level
  meaning: >-
    Every query fixes the aggregation level. For levels 10 to 80 the first digit of agglvl_code
    is the geography and the second the industry and ownership level. Levels 94, 95 and 96 are
    special totals (all government, all UI covered); their digits mean neither, and their rows
    sit on a national or state area code. The industry code alone does not give the level
    (F-0008), so mixing levels double counts.
  field: qtrly.agglvl_code
  required: true
  evidence: [ev-doc-agglvl, ev-doc-v3]
```

From: `examples/qcew/physical/entities/qtrly.yaml`, `examples/qcew/physical/entities/industry_titles.yaml`, `examples/qcew/physical/entities/area_titles.yaml`, `examples/qcew/semantic/employment-wages/layer.yaml`.

## 8. The corpus on the published rows

```bash
fact equivalence run --root examples/qcew --layer employment-wages --date 2026-11-28
```

```text
employment-wages: 36 pass, 0 fail, 2 error of 38
share 1.000, threshold 0.9: proven
```

The head of the report:

```text
Consumer `measure-sql`, source `qcew-duckdb-real` (duckdb), 2026-11-28.

| Mode | pass | fail | error |
| --- | --- | --- | --- |
| same_rows | 34 | 0 | 2 |
| same_count | 0 | 0 | 0 |
| same_predicate | 2 | 0 | 0 |
| all | 36 | 0 | 2 |

Share passing in same_rows or same_predicate: 1.000; threshold 0.9 (D-021): proven.
Unexplained failures: none
```

The two errors are the known gaps, `msa-detail-from-counties-2025q3` and
`nation-from-states-2025q1`: the consumer gives no SQL for a request by MSA or for the nation.
Every other item names, in its `note`, the published BLS row it reads. The layer's accepted
run is the one on the seeded SQLite file, which CI reproduces.

From: `examples/qcew/scripts/reproduce.sh` (command), `examples/qcew/measurements/run-reproduce.log` (output lines), `examples/qcew/equivalence/qcew-duckdb-real@2026-11-28.md` (the report).

## 9. A bound that is not zero

A probe expects no row without a match, unless the model states a bound and the reason for it
(D-025). The industry list has 53 codes with no code one character shorter, and it is built
that way. The relationship says so:

```yaml
  expected:
    orphans_left: 53
    reason: The three sector ranges 31-33, 44-45 and 48-49 and the 50 three-digit codes under them have no code one character shorter; the list is built that way (F-0008).
```

`fact probe generate` writes the bound into the probe:

```yaml
kind: probe
id: join-match-industry-titles-parent
probe_kind: join_match
entity: industry_titles
fact: industry_titles.parent
expected:
  orphans_left:
    max: 53
```

The run on the published rows measures 53, so the result is in range and the record confirms the relationship:

```yaml
- id: ev-join-match-industry-titles-parent-2026-11-28
  source: qcew-duckdb-real
  pin: duckdb:qcew@2026-11-28
  measurement:
    source_rows: 2659
    orphans_left: 53
    orphans_right: 1409
    match_rate: 0.980068
  status: confirmed
  read_on: '2026-11-28'
  probe: join-match-industry-titles-parent
```

A probe that keeps the bound 0 and passes: every quarterly row finds its industry.

```yaml
kind: probe
id: join-match-qtrly-to-industry
probe_kind: join_match
entity: qtrly
fact: qtrly.to-industry
expected:
  orphans_left:
    max: 0
```

```yaml
- id: ev-join-match-qtrly-to-industry-2026-11-28
  source: qcew-duckdb-real
  pin: duckdb:qcew@2026-11-28
  measurement:
    source_rows: 486100
    orphans_left: 0
    orphans_right: 519
    match_rate: 1.0
  status: confirmed
  read_on: '2026-11-28'
  probe: join-match-qtrly-to-industry
```

The whole run:

```bash
fact probe run --root examples/qcew --source qcew-duckdb-real --environment local --data-quality representative --date 2026-11-28
fact probe intake --root examples/qcew examples/qcew/probes/results/qcew-duckdb-real@2026-11-28.jsonl
```

```text
49 probes run, 0 failed: probes/results/qcew-duckdb-real@2026-11-28.jsonl
47 in range, 2 out of range, 0 failed, 0 rejected; 0 files written
```

The two results out of range are findings, not failures: the area list repeats its codes
(F-0001) and `disclosure_code` holds an undocumented `-` (F-0002). A 54th code without a parent
would be the third.

From: `examples/qcew/physical/entities/industry_titles.yaml`, `examples/qcew/probes/join-match-industry-titles-parent.yaml`, `examples/qcew/evidence/probes/join-match-industry-titles-parent@2026-11-28.yaml`, `examples/qcew/probes/join-match-qtrly-to-industry.yaml`, `examples/qcew/evidence/probes/join-match-qtrly-to-industry@2026-11-28.yaml`, `examples/qcew/scripts/reproduce.sh` (commands), `examples/qcew/measurements/run-reproduce.log` (output lines).

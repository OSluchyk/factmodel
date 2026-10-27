# Code lists

The five BLS QCEW title files, committed unchanged under D-016: public domain, 511,232 bytes together, no personal data (codes and names of areas, industries, ownerships, aggregation levels and size classes). They are loaded as they are into the five title tables; their defects are findings, not something to clean (`registers/findings/`).

Citation required by BLS: "Source: U.S. Bureau of Labor Statistics, Quarterly Census of Employment and Wages." Terms: https://www.bls.gov/opub/copyright-information.htm (read 2026-10-23).

| File | URL | Read on | Bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| `agglevel_titles.csv` | https://data.bls.gov/cew/doc/titles/agglevel/agglevel_titles.csv | 2026-10-23 | 2,750 | `7de7143e739476ff4ef605a4f043550d376b4d5695260d0674f6e0c7f9f95250` |
| `area_titles.csv` | https://data.bls.gov/cew/doc/titles/area/area_titles.csv | 2026-10-23 | 343,559 | `92ec00f591bd986cd46e027a05e35b33b0d2d724f3b76c96969f0e73145698d6` |
| `industry_titles.csv` | https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv | 2026-10-23 | 164,248 | `facc122ef582f3efdbb5294f103331894d8fdab694de38e4ee7bff1b941ab8e1` |
| `ownership_titles.csv` | https://data.bls.gov/cew/doc/titles/ownership/ownership_titles.csv | 2026-10-23 | 230 | `9586b30199a494e1add8615998638801b58cc7d52dacacd5e62b41feab5b11b6` |
| `size_titles.csv` | https://data.bls.gov/cew/doc/titles/size/size_titles.csv | 2026-10-23 | 445 | `76436a799b3f3fdcf338213e9c00111f0b81eeba1a99ac26451492db056b98e8` |

The files were downloaded on 2026-10-23 by `scripts/load.sh` of the QCEW profiling notes (qcew-model) and copied into this repository; nothing was fetched again.

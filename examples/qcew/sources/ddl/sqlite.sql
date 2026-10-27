-- QCEW tables for SQLite, written for the FactModel QCEW example.
-- annual and qtrly follow the BLS singlefile layouts as loaded by the QCEW profiling notes (qcew-model)
-- scripts/load.sh (eight key fields, then the measures; codes as text, counts and money as
-- integers, ratios as doubles), with one annual table for every year. The title tables hold
-- the BLS title files as they are. Like the BLS files, nothing declares a key: keys are facts
-- the model proves with probes.

CREATE TABLE annual (
  area_fips TEXT NOT NULL,
  own_code TEXT NOT NULL,
  industry_code TEXT NOT NULL,
  agglvl_code TEXT NOT NULL,
  size_code TEXT NOT NULL,
  year TEXT NOT NULL,
  qtr TEXT NOT NULL,
  disclosure_code TEXT,
  annual_avg_estabs INTEGER,
  annual_avg_emplvl INTEGER,
  total_annual_wages INTEGER,
  taxable_annual_wages INTEGER,
  annual_contributions INTEGER,
  annual_avg_wkly_wage INTEGER,
  avg_annual_pay INTEGER,
  lq_disclosure_code TEXT,
  lq_annual_avg_estabs REAL,
  lq_annual_avg_emplvl REAL,
  lq_total_annual_wages REAL,
  lq_taxable_annual_wages REAL,
  lq_annual_contributions REAL,
  lq_annual_avg_wkly_wage REAL,
  lq_avg_annual_pay REAL,
  oty_disclosure_code TEXT,
  oty_annual_avg_estabs_chg INTEGER,
  oty_annual_avg_estabs_pct_chg REAL,
  oty_annual_avg_emplvl_chg INTEGER,
  oty_annual_avg_emplvl_pct_chg REAL,
  oty_total_annual_wages_chg INTEGER,
  oty_total_annual_wages_pct_chg REAL,
  oty_taxable_annual_wages_chg INTEGER,
  oty_taxable_annual_wages_pct_chg REAL,
  oty_annual_contributions_chg INTEGER,
  oty_annual_contributions_pct_chg REAL,
  oty_annual_avg_wkly_wage_chg INTEGER,
  oty_annual_avg_wkly_wage_pct_chg REAL,
  oty_avg_annual_pay_chg INTEGER,
  oty_avg_annual_pay_pct_chg REAL
);

CREATE TABLE qtrly (
  area_fips TEXT NOT NULL,
  own_code TEXT NOT NULL,
  industry_code TEXT NOT NULL,
  agglvl_code TEXT NOT NULL,
  size_code TEXT NOT NULL,
  year TEXT NOT NULL,
  qtr TEXT NOT NULL,
  disclosure_code TEXT,
  qtrly_estabs INTEGER,
  month1_emplvl INTEGER,
  month2_emplvl INTEGER,
  month3_emplvl INTEGER,
  total_qtrly_wages INTEGER,
  taxable_qtrly_wages INTEGER,
  qtrly_contributions INTEGER,
  avg_wkly_wage INTEGER,
  lq_disclosure_code TEXT,
  lq_qtrly_estabs REAL,
  lq_month1_emplvl REAL,
  lq_month2_emplvl REAL,
  lq_month3_emplvl REAL,
  lq_total_qtrly_wages REAL,
  lq_taxable_qtrly_wages REAL,
  lq_qtrly_contributions REAL,
  lq_avg_wkly_wage REAL,
  oty_disclosure_code TEXT,
  oty_qtrly_estabs_chg INTEGER,
  oty_qtrly_estabs_pct_chg REAL,
  oty_month1_emplvl_chg INTEGER,
  oty_month1_emplvl_pct_chg REAL,
  oty_month2_emplvl_chg INTEGER,
  oty_month2_emplvl_pct_chg REAL,
  oty_month3_emplvl_chg INTEGER,
  oty_month3_emplvl_pct_chg REAL,
  oty_total_qtrly_wages_chg INTEGER,
  oty_total_qtrly_wages_pct_chg REAL,
  oty_taxable_qtrly_wages_chg INTEGER,
  oty_taxable_qtrly_wages_pct_chg REAL,
  oty_qtrly_contributions_chg INTEGER,
  oty_qtrly_contributions_pct_chg REAL,
  oty_avg_wkly_wage_chg INTEGER,
  oty_avg_wkly_wage_pct_chg REAL
);

CREATE TABLE agglevel_titles (
  agglvl_code TEXT,
  agglvl_title TEXT
);

CREATE TABLE area_titles (
  area_fips TEXT,
  area_title TEXT
);

CREATE TABLE industry_titles (
  industry_code TEXT,
  industry_title TEXT
);

CREATE TABLE ownership_titles (
  own_code TEXT,
  own_title TEXT
);

CREATE TABLE size_titles (
  size_code TEXT,
  size_title TEXT
);

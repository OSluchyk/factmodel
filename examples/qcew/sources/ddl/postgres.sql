-- QCEW tables for PostgreSQL, written for the FactModel QCEW example.
-- annual and qtrly follow the BLS singlefile layouts as loaded by the owner's qcew-model
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
  annual_avg_estabs BIGINT,
  annual_avg_emplvl BIGINT,
  total_annual_wages BIGINT,
  taxable_annual_wages BIGINT,
  annual_contributions BIGINT,
  annual_avg_wkly_wage BIGINT,
  avg_annual_pay BIGINT,
  lq_disclosure_code TEXT,
  lq_annual_avg_estabs DOUBLE PRECISION,
  lq_annual_avg_emplvl DOUBLE PRECISION,
  lq_total_annual_wages DOUBLE PRECISION,
  lq_taxable_annual_wages DOUBLE PRECISION,
  lq_annual_contributions DOUBLE PRECISION,
  lq_annual_avg_wkly_wage DOUBLE PRECISION,
  lq_avg_annual_pay DOUBLE PRECISION,
  oty_disclosure_code TEXT,
  oty_annual_avg_estabs_chg BIGINT,
  oty_annual_avg_estabs_pct_chg DOUBLE PRECISION,
  oty_annual_avg_emplvl_chg BIGINT,
  oty_annual_avg_emplvl_pct_chg DOUBLE PRECISION,
  oty_total_annual_wages_chg BIGINT,
  oty_total_annual_wages_pct_chg DOUBLE PRECISION,
  oty_taxable_annual_wages_chg BIGINT,
  oty_taxable_annual_wages_pct_chg DOUBLE PRECISION,
  oty_annual_contributions_chg BIGINT,
  oty_annual_contributions_pct_chg DOUBLE PRECISION,
  oty_annual_avg_wkly_wage_chg BIGINT,
  oty_annual_avg_wkly_wage_pct_chg DOUBLE PRECISION,
  oty_avg_annual_pay_chg BIGINT,
  oty_avg_annual_pay_pct_chg DOUBLE PRECISION
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
  qtrly_estabs BIGINT,
  month1_emplvl BIGINT,
  month2_emplvl BIGINT,
  month3_emplvl BIGINT,
  total_qtrly_wages BIGINT,
  taxable_qtrly_wages BIGINT,
  qtrly_contributions BIGINT,
  avg_wkly_wage BIGINT,
  lq_disclosure_code TEXT,
  lq_qtrly_estabs DOUBLE PRECISION,
  lq_month1_emplvl DOUBLE PRECISION,
  lq_month2_emplvl DOUBLE PRECISION,
  lq_month3_emplvl DOUBLE PRECISION,
  lq_total_qtrly_wages DOUBLE PRECISION,
  lq_taxable_qtrly_wages DOUBLE PRECISION,
  lq_qtrly_contributions DOUBLE PRECISION,
  lq_avg_wkly_wage DOUBLE PRECISION,
  oty_disclosure_code TEXT,
  oty_qtrly_estabs_chg BIGINT,
  oty_qtrly_estabs_pct_chg DOUBLE PRECISION,
  oty_month1_emplvl_chg BIGINT,
  oty_month1_emplvl_pct_chg DOUBLE PRECISION,
  oty_month2_emplvl_chg BIGINT,
  oty_month2_emplvl_pct_chg DOUBLE PRECISION,
  oty_month3_emplvl_chg BIGINT,
  oty_month3_emplvl_pct_chg DOUBLE PRECISION,
  oty_total_qtrly_wages_chg BIGINT,
  oty_total_qtrly_wages_pct_chg DOUBLE PRECISION,
  oty_taxable_qtrly_wages_chg BIGINT,
  oty_taxable_qtrly_wages_pct_chg DOUBLE PRECISION,
  oty_qtrly_contributions_chg BIGINT,
  oty_qtrly_contributions_pct_chg DOUBLE PRECISION,
  oty_avg_wkly_wage_chg BIGINT,
  oty_avg_wkly_wage_pct_chg DOUBLE PRECISION
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

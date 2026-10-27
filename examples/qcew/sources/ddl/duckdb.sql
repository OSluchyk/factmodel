-- QCEW tables for DuckDB, written for the FactModel QCEW example.
-- annual and qtrly follow the BLS singlefile layouts as loaded by the owner's qcew-model
-- scripts/load.sh (eight key fields, then the measures; codes as text, counts and money as
-- integers, ratios as doubles), with one annual table for every year. The title tables hold
-- the BLS title files as they are. Like the BLS files, nothing declares a key: keys are facts
-- the model proves with probes.

CREATE TABLE annual (
  area_fips VARCHAR NOT NULL,
  own_code VARCHAR NOT NULL,
  industry_code VARCHAR NOT NULL,
  agglvl_code VARCHAR NOT NULL,
  size_code VARCHAR NOT NULL,
  year VARCHAR NOT NULL,
  qtr VARCHAR NOT NULL,
  disclosure_code VARCHAR,
  annual_avg_estabs BIGINT,
  annual_avg_emplvl BIGINT,
  total_annual_wages BIGINT,
  taxable_annual_wages BIGINT,
  annual_contributions BIGINT,
  annual_avg_wkly_wage BIGINT,
  avg_annual_pay BIGINT,
  lq_disclosure_code VARCHAR,
  lq_annual_avg_estabs DOUBLE,
  lq_annual_avg_emplvl DOUBLE,
  lq_total_annual_wages DOUBLE,
  lq_taxable_annual_wages DOUBLE,
  lq_annual_contributions DOUBLE,
  lq_annual_avg_wkly_wage DOUBLE,
  lq_avg_annual_pay DOUBLE,
  oty_disclosure_code VARCHAR,
  oty_annual_avg_estabs_chg BIGINT,
  oty_annual_avg_estabs_pct_chg DOUBLE,
  oty_annual_avg_emplvl_chg BIGINT,
  oty_annual_avg_emplvl_pct_chg DOUBLE,
  oty_total_annual_wages_chg BIGINT,
  oty_total_annual_wages_pct_chg DOUBLE,
  oty_taxable_annual_wages_chg BIGINT,
  oty_taxable_annual_wages_pct_chg DOUBLE,
  oty_annual_contributions_chg BIGINT,
  oty_annual_contributions_pct_chg DOUBLE,
  oty_annual_avg_wkly_wage_chg BIGINT,
  oty_annual_avg_wkly_wage_pct_chg DOUBLE,
  oty_avg_annual_pay_chg BIGINT,
  oty_avg_annual_pay_pct_chg DOUBLE
);

CREATE TABLE qtrly (
  area_fips VARCHAR NOT NULL,
  own_code VARCHAR NOT NULL,
  industry_code VARCHAR NOT NULL,
  agglvl_code VARCHAR NOT NULL,
  size_code VARCHAR NOT NULL,
  year VARCHAR NOT NULL,
  qtr VARCHAR NOT NULL,
  disclosure_code VARCHAR,
  qtrly_estabs BIGINT,
  month1_emplvl BIGINT,
  month2_emplvl BIGINT,
  month3_emplvl BIGINT,
  total_qtrly_wages BIGINT,
  taxable_qtrly_wages BIGINT,
  qtrly_contributions BIGINT,
  avg_wkly_wage BIGINT,
  lq_disclosure_code VARCHAR,
  lq_qtrly_estabs DOUBLE,
  lq_month1_emplvl DOUBLE,
  lq_month2_emplvl DOUBLE,
  lq_month3_emplvl DOUBLE,
  lq_total_qtrly_wages DOUBLE,
  lq_taxable_qtrly_wages DOUBLE,
  lq_qtrly_contributions DOUBLE,
  lq_avg_wkly_wage DOUBLE,
  oty_disclosure_code VARCHAR,
  oty_qtrly_estabs_chg BIGINT,
  oty_qtrly_estabs_pct_chg DOUBLE,
  oty_month1_emplvl_chg BIGINT,
  oty_month1_emplvl_pct_chg DOUBLE,
  oty_month2_emplvl_chg BIGINT,
  oty_month2_emplvl_pct_chg DOUBLE,
  oty_month3_emplvl_chg BIGINT,
  oty_month3_emplvl_pct_chg DOUBLE,
  oty_total_qtrly_wages_chg BIGINT,
  oty_total_qtrly_wages_pct_chg DOUBLE,
  oty_taxable_qtrly_wages_chg BIGINT,
  oty_taxable_qtrly_wages_pct_chg DOUBLE,
  oty_qtrly_contributions_chg BIGINT,
  oty_qtrly_contributions_pct_chg DOUBLE,
  oty_avg_wkly_wage_chg BIGINT,
  oty_avg_wkly_wage_pct_chg DOUBLE
);

CREATE TABLE agglevel_titles (
  agglvl_code VARCHAR,
  agglvl_title VARCHAR
);

CREATE TABLE area_titles (
  area_fips VARCHAR,
  area_title VARCHAR
);

CREATE TABLE industry_titles (
  industry_code VARCHAR,
  industry_title VARCHAR
);

CREATE TABLE ownership_titles (
  own_code VARCHAR,
  own_title VARCHAR
);

CREATE TABLE size_titles (
  size_code VARCHAR,
  size_title VARCHAR
);

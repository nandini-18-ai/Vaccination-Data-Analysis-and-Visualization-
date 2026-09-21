"""
Stage 05 — Build Fact Tables
==============================
Assembles final fact-table frames (column selection/renaming only - all cleaning
already happened in stage 02) ready for SQL load:
  Country-level: fact_coverage, fact_incidence, fact_cases, fact_vaccine_introduction,
                 fact_vaccine_schedule
  Aggregate-level: fact_coverage_aggregate, fact_incidence_aggregate, fact_cases_aggregate

Surrogate keys are added where a natural composite key is unwieldy for a relational PK,
but the original business/composite key columns are always preserved.

Input : data/clean/01_cleaned/*.parquet
Output: data/clean/04_facts/*.parquet
        logs/05_build_facts.json
"""
import pandas as pd
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1]
IN_DIR = BASE / "data" / "clean" / "01_cleaned"
OUT_DIR = BASE / "data" / "clean" / "04_facts"
LOG_DIR = BASE / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

log = {}


def build_fact_coverage(df):
    out = df.rename(columns={
        "CODE": "country_code", "YEAR_CLEAN": "year", "ANTIGEN": "antigen_code",
        "COVERAGE_CATEGORY": "coverage_category", "COVERAGE_CATEGORY_DESCRIPTION": "coverage_category_description",
        "TARGET_NUMBER": "target_number", "DOSES_RAW": "doses_raw", "DOSES_CLEAN": "doses_clean",
        "DOSES_QUALITY_FLAG": "doses_quality_flag", "COVERAGE_RAW": "coverage_raw",
        "COVERAGE_QUALITY_FLAG": "coverage_quality_flag", "COVERAGE_ANALYTICAL_EXCLUDE": "coverage_analytical_exclude",
    })[["country_code", "year", "antigen_code", "coverage_category", "coverage_category_description",
        "target_number", "doses_raw", "doses_clean", "doses_quality_flag",
        "coverage_raw", "coverage_quality_flag", "coverage_analytical_exclude"]]
    return out


def build_fact_coverage_aggregate(df):
    out = df.rename(columns={
        "GROUP": "group_type", "CODE": "entity_code", "YEAR_CLEAN": "year", "ANTIGEN": "antigen_code",
        "COVERAGE_CATEGORY": "coverage_category", "TARGET_NUMBER": "target_number",
        "DOSES_RAW": "doses_raw", "DOSES_CLEAN": "doses_clean", "DOSES_QUALITY_FLAG": "doses_quality_flag",
        "COVERAGE_RAW": "coverage_raw", "COVERAGE_QUALITY_FLAG": "coverage_quality_flag",
        "COVERAGE_ANALYTICAL_EXCLUDE": "coverage_analytical_exclude",
    })[["group_type", "entity_code", "year", "antigen_code", "coverage_category", "target_number",
        "doses_raw", "doses_clean", "doses_quality_flag", "coverage_raw", "coverage_quality_flag",
        "coverage_analytical_exclude"]]
    return out


def build_fact_incidence(df):
    out = df.rename(columns={
        "CODE": "country_code", "YEAR_CLEAN": "year", "DISEASE": "disease_code",
        "DENOMINATOR_RAW": "denominator_raw", "DENOMINATOR_STANDARDIZED": "denominator_standardized",
        "INCIDENCE_RATE": "incidence_rate",
    })[["country_code", "year", "disease_code", "denominator_raw", "denominator_standardized", "incidence_rate"]]
    return out


def build_fact_incidence_aggregate(df):
    out = df.rename(columns={
        "GROUP": "group_type", "CODE": "entity_code", "YEAR_CLEAN": "year", "DISEASE": "disease_code",
        "DENOMINATOR_RAW": "denominator_raw", "DENOMINATOR_STANDARDIZED": "denominator_standardized",
        "INCIDENCE_RATE": "incidence_rate",
    })[["group_type", "entity_code", "year", "disease_code", "denominator_raw", "denominator_standardized", "incidence_rate"]]
    return out


def build_fact_cases(df):
    out = df.rename(columns={
        "CODE": "country_code", "YEAR_CLEAN": "year", "DISEASE": "disease_code", "CASES": "cases",
    })[["country_code", "year", "disease_code", "cases"]]
    return out


def build_fact_cases_aggregate(df):
    out = df.rename(columns={
        "GROUP": "group_type", "CODE": "entity_code", "YEAR_CLEAN": "year", "DISEASE": "disease_code", "CASES": "cases",
    })[["group_type", "entity_code", "year", "disease_code", "cases"]]
    return out


def build_fact_vaccine_introduction(df):
    out = df.rename(columns={
        "ISO_3_CODE": "country_code", "YEAR_CLEAN": "year", "DESCRIPTION": "vaccine_description",
        "INTRO": "intro_status", "WHO_REGION": "who_region_raw",
    })[["country_code", "year", "vaccine_description", "intro_status", "who_region_raw"]]
    return out


def build_fact_vaccine_schedule(df):
    out = df.rename(columns={
        "ISO_3_CODE": "country_code", "YEAR_CLEAN": "year", "VACCINECODE": "vaccine_code",
        "SCHEDULEROUNDS_CLEAN": "schedule_rounds", "TARGETPOP": "target_pop",
        "TARGETPOP_DESCRIPTION": "target_pop_description", "GEOAREA": "geoarea",
        "AGEADMINISTERED": "age_administered", "SOURCECOMMENT": "source_comment",
        "WHO_REGION": "who_region_raw",
    })[["country_code", "year", "vaccine_code", "schedule_rounds", "target_pop", "target_pop_description",
        "geoarea", "age_administered", "source_comment", "who_region_raw"]]
    return out


def main():
    cov_country = pd.read_parquet(IN_DIR / "coverage_country.parquet")
    cov_agg = pd.read_parquet(IN_DIR / "coverage_aggregate.parquet")
    inc_country = pd.read_parquet(IN_DIR / "incidence_country.parquet")
    inc_agg = pd.read_parquet(IN_DIR / "incidence_aggregate.parquet")
    cas_country = pd.read_parquet(IN_DIR / "cases_country.parquet")
    cas_agg = pd.read_parquet(IN_DIR / "cases_aggregate.parquet")
    intro_df = pd.read_parquet(IN_DIR / "intro_clean.parquet")
    sched_df = pd.read_parquet(IN_DIR / "schedule_clean.parquet")

    facts = {
        "fact_coverage": build_fact_coverage(cov_country),
        "fact_coverage_aggregate": build_fact_coverage_aggregate(cov_agg),
        "fact_incidence": build_fact_incidence(inc_country),
        "fact_incidence_aggregate": build_fact_incidence_aggregate(inc_agg),
        "fact_cases": build_fact_cases(cas_country),
        "fact_cases_aggregate": build_fact_cases_aggregate(cas_agg),
        "fact_vaccine_introduction": build_fact_vaccine_introduction(intro_df),
        "fact_vaccine_schedule": build_fact_vaccine_schedule(sched_df),
    }

    for name, df in facts.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        log[name] = {"rows": len(df), "columns": list(df.columns)}
        print(f"[05_facts] {name}: {len(df)} rows, {len(df.columns)} cols")

    with open(LOG_DIR / "05_build_facts.json", "w") as f:
        json.dump(log, f, indent=2, default=str)


if __name__ == "__main__":
    main()

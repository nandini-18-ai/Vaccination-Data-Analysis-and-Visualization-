"""
Stage 03 — Build Dimensions
=============================
Builds:
  - dim_country          (canonical country list = union of country-level codes across
                           coverage/incidence/cases/intro/schedule; LEFT JOIN enrichment,
                           never an inner join, so small territories are not dropped)
  - who_region lookup     (derived from intro + schedule WHO_REGION columns, since
                           coverage/incidence/cases carry no direct WHO region on country rows;
                           conflicts between sources are detected and reported, not silently resolved)
  - dim_antigen           (69 antigen codes from coverage, all retained)
  - dim_disease           (13 disease codes shared by incidence & cases, all retained)
  - dim_vaccine_schedule_code (86 vaccine codes from schedule, all retained)
  - dim_aggregate_entity  (lookup of aggregate GROUP/CODE/NAME combinations used by the
                           *_aggregate fact tables, e.g. WHO_REGIONS/WPR/'Western Pacific Region')

Input : data/clean/01_cleaned/*.parquet
Output: data/clean/02_dimensions/*.parquet
        logs/03_build_dimensions.json
"""
import pandas as pd
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1]
IN_DIR = BASE / "data" / "clean" / "01_cleaned"
OUT_DIR = BASE / "data" / "clean" / "02_dimensions"
LOG_DIR = BASE / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

log = {}


def build_who_region_lookup(intro_df, sched_df):
    """Derive country -> WHO_REGION from intro + schedule. Detect conflicts explicitly."""
    intro_map = intro_df[["ISO_3_CODE", "WHO_REGION"]].dropna().drop_duplicates()
    sched_map = sched_df[["ISO_3_CODE", "WHO_REGION"]].dropna().drop_duplicates()

    intro_map = intro_map.groupby("ISO_3_CODE")["WHO_REGION"].apply(lambda s: sorted(set(s))).reset_index()
    sched_map = sched_map.groupby("ISO_3_CODE")["WHO_REGION"].apply(lambda s: sorted(set(s))).reset_index()

    # each source should be internally consistent (1 region per country per source) - verify
    intro_internal_conflicts = intro_map[intro_map["WHO_REGION"].apply(len) > 1]
    sched_internal_conflicts = sched_map[sched_map["WHO_REGION"].apply(len) > 1]

    intro_single = intro_map[intro_map["WHO_REGION"].apply(len) == 1].copy()
    intro_single["WHO_REGION_INTRO"] = intro_single["WHO_REGION"].apply(lambda x: x[0])
    sched_single = sched_map[sched_map["WHO_REGION"].apply(len) == 1].copy()
    sched_single["WHO_REGION_SCHED"] = sched_single["WHO_REGION"].apply(lambda x: x[0])

    merged = pd.merge(
        intro_single[["ISO_3_CODE", "WHO_REGION_INTRO"]],
        sched_single[["ISO_3_CODE", "WHO_REGION_SCHED"]],
        on="ISO_3_CODE", how="outer"
    )
    merged["CONFLICT"] = (
        merged["WHO_REGION_INTRO"].notna() & merged["WHO_REGION_SCHED"].notna() &
        (merged["WHO_REGION_INTRO"] != merged["WHO_REGION_SCHED"])
    )
    # Prefer intro (larger country coverage: 194 vs 213... schedule actually covers more,
    # but intro is the longer-running/more authoritative source table for regional assignment
    # per WHO JRF process); fall back to schedule when intro is missing. Document choice, do not hide it.
    merged["WHO_REGION_FINAL"] = merged["WHO_REGION_INTRO"].fillna(merged["WHO_REGION_SCHED"])
    merged.loc[merged["CONFLICT"], "WHO_REGION_FINAL"] = pd.NA  # do not silently pick a side on conflict

    n_mapped = int(merged["WHO_REGION_FINAL"].notna().sum())
    n_unmapped = int(merged["WHO_REGION_FINAL"].isna().sum())
    n_conflicts = int(merged["CONFLICT"].sum())

    log["who_region_lookup"] = {
        "source": "vaccine-introduction-data.xlsx (primary) and vaccine-schedule-data.xlsx (fallback when country absent from introduction)",
        "countries_mapped": n_mapped,
        "countries_unmapped": n_unmapped,
        "countries_with_conflicting_region_between_sources": n_conflicts,
        "intro_internal_inconsistencies": int(len(intro_internal_conflicts)),
        "schedule_internal_inconsistencies": int(len(sched_internal_conflicts)),
        "conflicting_countries": merged.loc[merged["CONFLICT"], "ISO_3_CODE"].tolist(),
    }
    return merged[["ISO_3_CODE", "WHO_REGION_INTRO", "WHO_REGION_SCHED", "WHO_REGION_FINAL", "CONFLICT"]]


def build_dim_country(cov_country, inc_country, cas_country, intro_df, sched_df, who_region_lookup):
    """Canonical country list = union of country codes across all 5 country-level sources.
    LEFT JOIN enrichment only - never inner join - so no country is dropped for lacking
    introduction/schedule data."""
    cov_countries = cov_country[["CODE", "NAME"]].dropna(subset=["CODE"]).drop_duplicates(subset=["CODE"])
    inc_countries = inc_country[["CODE", "NAME"]].dropna(subset=["CODE"]).drop_duplicates(subset=["CODE"])
    cas_countries = cas_country[["CODE", "NAME"]].dropna(subset=["CODE"]).drop_duplicates(subset=["CODE"])
    intro_countries = intro_df[["ISO_3_CODE", "COUNTRYNAME"]].dropna(subset=["ISO_3_CODE"]).drop_duplicates(subset=["ISO_3_CODE"]).rename(
        columns={"ISO_3_CODE": "CODE", "COUNTRYNAME": "NAME"})
    sched_countries = sched_df[["ISO_3_CODE", "COUNTRYNAME"]].dropna(subset=["ISO_3_CODE"]).drop_duplicates(subset=["ISO_3_CODE"]).rename(
        columns={"ISO_3_CODE": "CODE", "COUNTRYNAME": "NAME"})

    all_codes = pd.concat([
        cov_countries[["CODE"]], inc_countries[["CODE"]], cas_countries[["CODE"]],
        intro_countries[["CODE"]], sched_countries[["CODE"]]
    ]).drop_duplicates().reset_index(drop=True)

    # Name resolution: prefer coverage/incidence/cases name (WHO immunization naming),
    # falling back to intro/schedule COUNTRYNAME if absent there.
    name_lookup = pd.concat([cov_countries, inc_countries, cas_countries]).drop_duplicates(subset=["CODE"])
    dim_country = all_codes.merge(name_lookup, on="CODE", how="left")
    fallback_names = pd.concat([intro_countries, sched_countries]).drop_duplicates(subset=["CODE"])
    dim_country = dim_country.merge(fallback_names, on="CODE", how="left", suffixes=("", "_FALLBACK"))
    dim_country["NAME"] = dim_country["NAME"].fillna(dim_country["NAME_FALLBACK"])
    dim_country = dim_country.drop(columns=["NAME_FALLBACK"])

    dim_country = dim_country.merge(who_region_lookup, left_on="CODE", right_on="ISO_3_CODE", how="left").drop(columns=["ISO_3_CODE"])

    # presence flags per source table (useful for downstream FK-safety checks and transparency)
    dim_country["IN_COVERAGE"] = dim_country["CODE"].isin(cov_countries["CODE"])
    dim_country["IN_INCIDENCE"] = dim_country["CODE"].isin(inc_countries["CODE"])
    dim_country["IN_CASES"] = dim_country["CODE"].isin(cas_countries["CODE"])
    dim_country["IN_INTRODUCTION"] = dim_country["CODE"].isin(intro_countries["CODE"])
    dim_country["IN_SCHEDULE"] = dim_country["CODE"].isin(sched_countries["CODE"])

    dim_country = dim_country.rename(columns={"CODE": "country_code", "NAME": "country_name",
                                               "WHO_REGION_FINAL": "who_region",
                                               "WHO_REGION_INTRO": "who_region_source_intro",
                                               "WHO_REGION_SCHED": "who_region_source_schedule",
                                               "CONFLICT": "who_region_conflict"})
    log["dim_country"] = {
        "total_countries": len(dim_country),
        "in_coverage": int(dim_country["IN_COVERAGE"].sum()),
        "in_incidence": int(dim_country["IN_INCIDENCE"].sum()),
        "in_cases": int(dim_country["IN_CASES"].sum()),
        "in_introduction": int(dim_country["IN_INTRODUCTION"].sum()),
        "in_schedule": int(dim_country["IN_SCHEDULE"].sum()),
        "with_who_region": int(dim_country["who_region"].notna().sum()),
        "without_who_region": int(dim_country["who_region"].isna().sum()),
    }
    return dim_country


def build_dim_antigen(cov_country, cov_agg):
    all_cov = pd.concat([cov_country[["ANTIGEN", "ANTIGEN_DESCRIPTION"]], cov_agg[["ANTIGEN", "ANTIGEN_DESCRIPTION"]]])
    dim = all_cov.dropna(subset=["ANTIGEN"]).drop_duplicates(subset=["ANTIGEN"]).sort_values("ANTIGEN").reset_index(drop=True)
    dim = dim.rename(columns={"ANTIGEN": "antigen_code", "ANTIGEN_DESCRIPTION": "antigen_description"})
    log["dim_antigen"] = {"total_antigens": len(dim)}
    return dim


def build_dim_disease(inc_country, inc_agg, cas_country, cas_agg):
    all_dis = pd.concat([
        inc_country[["DISEASE", "DISEASE_DESCRIPTION"]], inc_agg[["DISEASE", "DISEASE_DESCRIPTION"]],
        cas_country[["DISEASE", "DISEASE_DESCRIPTION"]], cas_agg[["DISEASE", "DISEASE_DESCRIPTION"]],
    ])
    dim = all_dis.dropna(subset=["DISEASE"]).drop_duplicates(subset=["DISEASE"]).sort_values("DISEASE").reset_index(drop=True)
    dim = dim.rename(columns={"DISEASE": "disease_code", "DISEASE_DESCRIPTION": "disease_description"})
    log["dim_disease"] = {"total_diseases": len(dim)}
    return dim


def build_dim_vaccine_schedule_code(sched_df):
    dim = sched_df[["VACCINECODE", "VACCINE_DESCRIPTION"]].dropna(subset=["VACCINECODE"]).drop_duplicates(
        subset=["VACCINECODE"]).sort_values("VACCINECODE").reset_index(drop=True)
    dim = dim.rename(columns={"VACCINECODE": "vaccine_code", "VACCINE_DESCRIPTION": "vaccine_description"})
    log["dim_vaccine_schedule_code"] = {"total_vaccine_codes": len(dim)}
    return dim


def build_dim_aggregate_entity(cov_agg, inc_agg, cas_agg):
    """Lookup of aggregate GROUP/CODE/NAME combinations referenced by *_aggregate fact tables."""
    parts = []
    for df, src in [(cov_agg, "coverage"), (inc_agg, "incidence"), (cas_agg, "cases")]:
        p = df[["GROUP", "CODE", "NAME"]].drop_duplicates()
        p["source_table"] = src
        parts.append(p)
    dim = pd.concat(parts).drop_duplicates(subset=["GROUP", "CODE"]).sort_values(["GROUP", "CODE"]).reset_index(drop=True)
    dim = dim.rename(columns={"GROUP": "group_type", "CODE": "entity_code", "NAME": "entity_name"})
    log["dim_aggregate_entity"] = {"total_aggregate_entities": len(dim), "group_types": sorted(dim["group_type"].unique().tolist())}
    return dim


def main():
    cov_country = pd.read_parquet(IN_DIR / "coverage_country.parquet")
    cov_agg = pd.read_parquet(IN_DIR / "coverage_aggregate.parquet")
    inc_country = pd.read_parquet(IN_DIR / "incidence_country.parquet")
    inc_agg = pd.read_parquet(IN_DIR / "incidence_aggregate.parquet")
    cas_country = pd.read_parquet(IN_DIR / "cases_country.parquet")
    cas_agg = pd.read_parquet(IN_DIR / "cases_aggregate.parquet")
    intro_df = pd.read_parquet(IN_DIR / "intro_clean.parquet")
    sched_df = pd.read_parquet(IN_DIR / "schedule_clean.parquet")

    who_region_lookup = build_who_region_lookup(intro_df, sched_df)
    dim_country = build_dim_country(cov_country, inc_country, cas_country, intro_df, sched_df, who_region_lookup)
    dim_antigen = build_dim_antigen(cov_country, cov_agg)
    dim_disease = build_dim_disease(inc_country, inc_agg, cas_country, cas_agg)
    dim_vaccine_schedule_code = build_dim_vaccine_schedule_code(sched_df)
    dim_aggregate_entity = build_dim_aggregate_entity(cov_agg, inc_agg, cas_agg)

    outputs = {
        "dim_country": dim_country, "dim_antigen": dim_antigen, "dim_disease": dim_disease,
        "dim_vaccine_schedule_code": dim_vaccine_schedule_code, "dim_aggregate_entity": dim_aggregate_entity,
    }
    for name, df in outputs.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        print(f"[03_dims] {name}: {len(df)} rows")

    with open(LOG_DIR / "03_build_dimensions.json", "w") as f:
        json.dump(log, f, indent=2, default=str)
    print(json.dumps(log, indent=2, default=str))


if __name__ == "__main__":
    main()

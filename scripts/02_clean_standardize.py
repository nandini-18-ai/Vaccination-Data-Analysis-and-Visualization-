"""
Stage 02 — Clean & Standardize
================================
Applies documented, reproducible cleaning rules to each of the 5 raw datasets:
  - Remove WHO export footer row
  - Cast YEAR to integer (only where valid whole numbers)
  - Standardize numeric dtypes, preserving NaN as NaN (never fabricated as 0)
  - Trim whitespace on text fields (no semantic renaming)
  - Normalize incidence DENOMINATOR text formatting
  - Apply coverage >100% quality flags (retain all rows, flag extremes)
  - Apply negative-DOSES / sentinel-value policy
  - Split GROUP into country-level vs aggregate-level frames (coverage/incidence/cases)

Every rule is logged to logs/cleaning_log_rows.jsonl (one JSON record per rule
applied) so CLEANING_TRANSFORMATION_LOG.md can be generated directly from real
execution output, not written by hand.

Input : data/clean/00_raw_snapshot/*.parquet  (from stage 01)
Output: data/clean/01_cleaned/*.parquet
        logs/02_clean_standardize.json (summary log)
"""
import pandas as pd
import numpy as np
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1]
RAW_SNAPSHOT = BASE / "data" / "clean" / "00_raw_snapshot"
OUT_DIR = BASE / "data" / "clean" / "01_cleaned"
LOG_DIR = BASE / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

cleaning_log = []  # list of dict records -> becomes CLEANING_TRANSFORMATION_LOG.md


def log_rule(dataset, field, issue, detection_method, rule_applied, rows_affected,
             before, after, reason, disposition):
    cleaning_log.append({
        "dataset": dataset,
        "field": field,
        "issue": issue,
        "detection_method": detection_method,
        "rule_applied": rule_applied,
        "rows_affected": int(rows_affected),
        "before": before,
        "after": after,
        "reason": reason,
        "disposition": disposition,  # removed / retained / flagged / standardized
    })


def remove_footer(df, dataset_name):
    """Remove the single trailing 'Created: <timestamp> UTC' WHO export footer row."""
    first_col = df.columns[0]
    is_footer = df[first_col].astype(str).str.startswith("Created:", na=False)
    n_footer = int(is_footer.sum())
    before = len(df)
    df_clean = df[~is_footer].copy()
    after = len(df_clean)
    log_rule(
        dataset=dataset_name, field=first_col, issue="WHO export footer metadata row",
        detection_method="First-column string startswith 'Created:'",
        rule_applied="Drop row(s) matching footer pattern",
        rows_affected=n_footer, before=before, after=after,
        reason="Row is workbook export metadata (export timestamp), not an analytical observation.",
        disposition="removed",
    )
    return df_clean.reset_index(drop=True)


def cast_year(df, dataset_name):
    """Cast YEAR from float to integer only where it is a valid whole number. Never silently
    coerce invalid values - report anything that fails the whole-number check."""
    if "YEAR" not in df.columns:
        return df
    year = df["YEAR"]
    non_null = year.notna()
    is_whole = non_null & (year == year.round())
    invalid = non_null & ~is_whole
    n_invalid = int(invalid.sum())
    df["YEAR_CLEAN"] = pd.array([pd.NA] * len(df), dtype="Int64")
    df.loc[is_whole, "YEAR_CLEAN"] = year[is_whole].round().astype("Int64")
    log_rule(
        dataset=dataset_name, field="YEAR", issue="Float-typed year column",
        detection_method="Check YEAR == round(YEAR) for all non-null values",
        rule_applied="Cast to nullable Int64 (YEAR_CLEAN) when whole number; else leave NULL and report",
        rows_affected=int(is_whole.sum()), before="float64", after="Int64 (YEAR_CLEAN)",
        reason="YEAR is conceptually a whole-number calendar year; float storage is a source-format artifact.",
        disposition="standardized",
    )
    if n_invalid > 0:
        log_rule(
            dataset=dataset_name, field="YEAR", issue=f"{n_invalid} non-whole-number YEAR values found",
            detection_method="YEAR != round(YEAR)", rule_applied="Left as NULL in YEAR_CLEAN, NOT silently coerced",
            rows_affected=n_invalid, before="non-integer float", after="NULL (flagged)",
            reason="Per Phase 1 instructions: do not silently convert invalid values.",
            disposition="flagged",
        )
    return df


def trim_text_columns(df, dataset_name, text_cols):
    """Trim leading/trailing whitespace only. Does not alter semantic content or casing."""
    total_changed = 0
    for col in text_cols:
        if col not in df.columns:
            continue
        original = df[col].copy()
        trimmed = df[col].where(df[col].isna(), df[col].astype(str).str.strip())
        # only apply where not null, and avoid turning real NaN into string 'nan'
        mask_notnull = df[col].notna()
        changed = mask_notnull & (original.astype(str) != trimmed.astype(str))
        n_changed = int(changed.sum())
        total_changed += n_changed
        df[col] = trimmed
    if total_changed > 0:
        log_rule(
            dataset=dataset_name, field=",".join(text_cols), issue="Leading/trailing whitespace in text fields",
            detection_method="str.strip() != original", rule_applied="Trim whitespace only (no case/content change)",
            rows_affected=total_changed, before="untrimmed text", after="trimmed text",
            reason="Whitespace can break joins/grouping without changing semantic meaning.",
            disposition="standardized",
        )
    return df


def normalize_denominator(df):
    """Normalize the known comma-formatting inconsistency in incidence DENOMINATOR text.
    Does NOT alter the numeric INCIDENCE_RATE value. Preserves the original raw string
    alongside a standardized field."""
    df["DENOMINATOR_RAW"] = df["DENOMINATOR"]
    before_counts = df["DENOMINATOR"].value_counts(dropna=False).to_dict()

    def std(s):
        if pd.isna(s):
            return s
        s2 = str(s).strip()
        # Normalize "1000" -> "1,000" only for the live-births denominator variant,
        # a documented Phase 0 finding (2 raw strings referring to the same basis).
        if s2 == "per 1000 live births":
            return "per 1,000 live births"
        return s2

    df["DENOMINATOR_STANDARDIZED"] = df["DENOMINATOR"].apply(std)
    after_counts = df["DENOMINATOR_STANDARDIZED"].value_counts(dropna=False).to_dict()

    n_changed = int((df["DENOMINATOR_RAW"].astype(str) != df["DENOMINATOR_STANDARDIZED"].astype(str)).sum())
    log_rule(
        dataset="incidence", field="DENOMINATOR", issue="Comma-formatting inconsistency: 'per 1,000 live births' vs 'per 1000 live births'",
        detection_method="Exact string comparison of distinct DENOMINATOR values",
        rule_applied="Map 'per 1000 live births' -> 'per 1,000 live births' into new DENOMINATOR_STANDARDIZED field; DENOMINATOR_RAW preserved unchanged; INCIDENCE_RATE numeric value untouched",
        rows_affected=n_changed, before=before_counts, after=after_counts,
        reason="Same reporting basis represented with inconsistent punctuation; standardizing enables correct grouping without losing traceability to the original text.",
        disposition="standardized",
    )
    return df


def flag_coverage_outliers(df):
    """Do not clip. Add quality flags for coverage values, per documented policy:
       - normal:          COVERAGE <= 100 (or NULL)
       - above_100_moderate: 100 < COVERAGE <= 500  (plausible under-estimated-denominator effect)
       - extreme_outlier: COVERAGE > 500 (implausible; flagged for analytical exclusion, NOT deleted)
    """
    df["COVERAGE_RAW"] = df["COVERAGE"]
    cov = df["COVERAGE"]
    flag = pd.Series(pd.array([None] * len(df), dtype="object"), index=df.index)
    flag[cov.isna()] = "missing"
    flag[(cov.notna()) & (cov <= 100)] = "normal"
    flag[(cov.notna()) & (cov > 100) & (cov <= 500)] = "above_100_moderate"
    flag[(cov.notna()) & (cov > 500)] = "extreme_outlier"
    df["COVERAGE_QUALITY_FLAG"] = flag
    df["COVERAGE_ANALYTICAL_EXCLUDE"] = (flag == "extreme_outlier")

    n_moderate = int((flag == "above_100_moderate").sum())
    n_extreme = int((flag == "extreme_outlier").sum())
    log_rule(
        dataset="coverage", field="COVERAGE", issue="Values above 100% (documented Phase 0 finding: 5,097 rows >100%, max 32,000%)",
        detection_method="COVERAGE > 100 threshold checks at 100 and 500",
        rule_applied="Retain all values unmodified in COVERAGE_RAW/COVERAGE; add COVERAGE_QUALITY_FLAG "
                      "('normal' <=100, 'above_100_moderate' 100-500, 'extreme_outlier' >500) and boolean "
                      "COVERAGE_ANALYTICAL_EXCLUDE (True only for >500). No row deleted, no value clipped.",
        rows_affected=n_moderate + n_extreme, before="unflagged COVERAGE", after="flagged, original value retained",
        reason="Moderate >100% values can be legitimate (denominator under-estimation in administrative reporting); "
               "values >500% (e.g. Morocco/FLU_HAJ/2018 at 32,000%) are implausible and are flagged for exclusion "
               "from analytical measures in later phases, but are not deleted so the raw signal remains auditable.",
        disposition="flagged",
    )
    return df


def flag_negative_doses(df):
    """Detect negative DOSES. Treat the repeated -3333 value as a 'not reported' sentinel
    (missing), based on its clustering across unrelated countries/antigens documented in
    Phase 0. Flag other negative values (implausible magnitude) separately. Never coerce
    negative values to zero, and always retain the original raw value in DOSES_RAW."""
    df["DOSES_RAW"] = df["DOSES"]
    doses = df["DOSES"]
    flag = pd.Series(pd.array([None] * len(df), dtype="object"), index=df.index)
    flag[doses.isna()] = "missing"
    flag[(doses.notna()) & (doses >= 0)] = "normal"
    flag[(doses.notna()) & (doses < 0) & (doses == -3333)] = "sentinel_not_reported"
    flag[(doses.notna()) & (doses < 0) & (doses != -3333)] = "implausible_negative"
    df["DOSES_QUALITY_FLAG"] = flag

    # DOSES_CLEAN: analytical field - sentinel and implausible negatives become NULL (not 0),
    # normal/missing pass through unchanged.
    doses_clean = doses.copy()
    doses_clean[flag == "sentinel_not_reported"] = np.nan
    doses_clean[flag == "implausible_negative"] = np.nan
    df["DOSES_CLEAN"] = doses_clean

    n_sentinel = int((flag == "sentinel_not_reported").sum())
    n_implausible = int((flag == "implausible_negative").sum())
    log_rule(
        dataset="coverage", field="DOSES", issue="Negative DOSES values (8 rows identified in Phase 0: 7x -3333, 1x -222,288,203)",
        detection_method="DOSES < 0, then split on DOSES == -3333 vs other",
        rule_applied="DOSES_RAW preserves original value unmodified. DOSES_QUALITY_FLAG assigns "
                      "'sentinel_not_reported' to the repeated -3333 pattern (treated as a 'not reported' "
                      "placeholder, not a real dose count) and 'implausible_negative' to the single extreme "
                      "outlier. DOSES_CLEAN sets both categories to NULL (never 0) for analytical use; "
                      "DOSES_RAW keeps the original value for traceability.",
        rows_affected=n_sentinel + n_implausible, before="raw negative value", after="NULL in DOSES_CLEAN, flagged, raw preserved",
        reason="-3333 recurs identically across unrelated countries/antigens (Bahamas, Trinidad & Tobago, "
               "Paraguay, all FLU_* antigens) which is characteristic of a sentinel/placeholder code rather "
               "than a genuine count. The El Salvador/POL3/2017 value (-222,288,203) is numerically "
               "implausible for any real dose count and is treated as a data error, not a real value.",
        disposition="flagged",
    )
    return df


def investigate_name_nulls(df):
    """Investigate whether coverage NAME nulls correspond to aggregate rows or genuine
    country-level missing names. Documented, not fabricated."""
    null_name = df["NAME"].isna()
    n_null = int(null_name.sum())
    if n_null == 0:
        return {"null_name_rows": 0}
    by_group = df.loc[null_name, "GROUP"].value_counts(dropna=False).to_dict()
    n_countries_affected = int((null_name & (df["GROUP"] == "COUNTRIES")).sum())
    log_rule(
        dataset="coverage", field="NAME", issue=f"{n_null} rows with missing NAME",
        detection_method="NAME.isna() cross-tabulated against GROUP",
        rule_applied="No fabrication. NAME left NULL exactly as sourced. Cross-tab against GROUP recorded for transparency.",
        rows_affected=n_null, before="NULL", after="NULL (unchanged) + documented breakdown by GROUP",
        reason=f"Breakdown by GROUP: {by_group}. Of these, {n_countries_affected} are GROUP='COUNTRIES' rows "
               f"with a genuinely missing country name in the source; the remainder are aggregate-group rows.",
        disposition="retained",
    )
    return {"null_name_rows": n_null, "by_group": by_group, "country_level_missing": n_countries_affected}


def split_country_aggregate(df, dataset_name):
    """Split GROUP-mixed tables into country-level (GROUP='COUNTRIES') and aggregate-level frames."""
    is_country = df["GROUP"] == "COUNTRIES"
    country_df = df[is_country].copy().reset_index(drop=True)
    agg_df = df[~is_country].copy().reset_index(drop=True)
    log_rule(
        dataset=dataset_name, field="GROUP", issue="Mixed country-level and aggregate-level rows in one table",
        detection_method="GROUP column distinct-value inspection (Phase 0 finding)",
        rule_applied="Split into two frames: GROUP='COUNTRIES' -> country-level fact table; all other GROUP "
                      "values (WHO_REGIONS, UNICEF_REGIONS, WB_LONG, WB_SHORT, DEVELOPMENT_STATUS, GAVI_PHASE5, "
                      "GLOBAL) -> aggregate fact table.",
        rows_affected=int((~is_country).sum()), before=f"{len(df)} mixed rows", after=f"{len(country_df)} country rows / {len(agg_df)} aggregate rows",
        reason="Prevents accidental contamination of country-level analysis with regional/global/income-group rollups.",
        disposition="standardized",
    )
    return country_df, agg_df


def clean_coverage(df):
    df = remove_footer(df, "coverage")
    assert len(df) == 399858, f"Unexpected coverage row count after footer removal: {len(df)}"
    df = cast_year(df, "coverage")
    df = trim_text_columns(df, "coverage", ["GROUP", "CODE", "NAME", "ANTIGEN", "ANTIGEN_DESCRIPTION",
                                             "COVERAGE_CATEGORY", "COVERAGE_CATEGORY_DESCRIPTION"])
    df = flag_coverage_outliers(df)
    df = flag_negative_doses(df)
    name_null_report = investigate_name_nulls(df)
    country_df, agg_df = split_country_aggregate(df, "coverage")
    return country_df, agg_df, name_null_report


def clean_incidence(df):
    df = remove_footer(df, "incidence")
    assert len(df) == 84945, f"Unexpected incidence row count after footer removal: {len(df)}"
    df = cast_year(df, "incidence")
    df = trim_text_columns(df, "incidence", ["GROUP", "CODE", "NAME", "DISEASE", "DISEASE_DESCRIPTION", "DENOMINATOR"])
    df = normalize_denominator(df)
    country_df, agg_df = split_country_aggregate(df, "incidence")
    return country_df, agg_df


def clean_cases(df):
    df = remove_footer(df, "cases")
    assert len(df) == 84869, f"Unexpected cases row count after footer removal: {len(df)}"
    df = cast_year(df, "cases")
    df = trim_text_columns(df, "cases", ["GROUP", "CODE", "NAME", "DISEASE", "DISEASE_DESCRIPTION"])
    country_df, agg_df = split_country_aggregate(df, "cases")
    return country_df, agg_df


def clean_intro(df):
    df = remove_footer(df, "intro")
    assert len(df) == 138320, f"Unexpected intro row count after footer removal: {len(df)}"
    df = cast_year(df, "intro")
    df = trim_text_columns(df, "intro", ["ISO_3_CODE", "COUNTRYNAME", "WHO_REGION", "DESCRIPTION", "INTRO"])
    return df


def clean_schedule(df):
    df = remove_footer(df, "schedule")
    assert len(df) == 8052, f"Unexpected schedule row count after footer removal: {len(df)}"
    df = cast_year(df, "schedule")
    df = trim_text_columns(df, "schedule", ["ISO_3_CODE", "COUNTRYNAME", "WHO_REGION", "VACCINECODE",
                                             "VACCINE_DESCRIPTION", "TARGETPOP", "TARGETPOP_DESCRIPTION",
                                             "GEOAREA", "AGEADMINISTERED", "SOURCECOMMENT"])
    schedrounds = df["SCHEDULEROUNDS"]
    df["SCHEDULEROUNDS_CLEAN"] = pd.array([pd.NA] * len(df), dtype="Int64")
    is_whole = schedrounds.notna() & (schedrounds == schedrounds.round())
    df.loc[is_whole, "SCHEDULEROUNDS_CLEAN"] = schedrounds[is_whole].round().astype("Int64")
    log_rule(
        dataset="schedule", field="SCHEDULEROUNDS", issue="Float-typed schedule round number",
        detection_method="Check SCHEDULEROUNDS == round(SCHEDULEROUNDS)",
        rule_applied="Cast to nullable Int64 (SCHEDULEROUNDS_CLEAN)",
        rows_affected=int(is_whole.sum()), before="float64", after="Int64",
        reason="Schedule round is conceptually a whole-number dose sequence position.",
        disposition="standardized",
    )
    return df


def main():
    dfs = {k: pd.read_parquet(RAW_SNAPSHOT / f"{k}_raw.parquet") for k in
           ["coverage", "incidence", "cases", "intro", "schedule"]}

    cov_country, cov_agg, name_null_report = clean_coverage(dfs["coverage"])
    inc_country, inc_agg = clean_incidence(dfs["incidence"])
    cas_country, cas_agg = clean_cases(dfs["cases"])
    intro_clean = clean_intro(dfs["intro"])
    sched_clean = clean_schedule(dfs["schedule"])

    outputs = {
        "coverage_country": cov_country, "coverage_aggregate": cov_agg,
        "incidence_country": inc_country, "incidence_aggregate": inc_agg,
        "cases_country": cas_country, "cases_aggregate": cas_agg,
        "intro_clean": intro_clean, "schedule_clean": sched_clean,
    }
    for name, df in outputs.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        print(f"[02_clean] {name}: {len(df)} rows -> {name}.parquet")

    summary = {
        "row_counts": {name: len(df) for name, df in outputs.items()},
        "name_null_investigation": name_null_report,
        "cleaning_rules_applied": len(cleaning_log),
    }
    with open(LOG_DIR / "02_clean_standardize.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    with open(LOG_DIR / "cleaning_log_rows.json", "w") as f:
        json.dump(cleaning_log, f, indent=2, default=str)

    print(f"[02_clean] Complete. {len(cleaning_log)} cleaning rules logged.")
    print(json.dumps(summary["row_counts"], indent=2))


if __name__ == "__main__":
    main()

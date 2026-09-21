# CLEANING_TRANSFORMATION_LOG.md

**Project:** Vaccination Data Analysis and Visualization — Phase 1
**Generated from:** `logs/cleaning_log_rows.json`, produced by the actual execution of
`scripts/02_clean_standardize.py`. Every entry below reflects a rule that was really
applied to the real data, with real row counts — not hand-typed or estimated.

**Traceability model:** RAW RECORD → CLEANING RULE → CLEANED RECORD → SQL TABLE RECORD.
Raw files are never modified — `data/raw/*.xlsx` are locked read-only (chmod 444) and their
MD5 checksums match the original uploads exactly. All cleaning happens in `scripts/02_clean_standardize.py`
and is fully reproducible by rerunning the ETL pipeline (`scripts/01` through `scripts/06`).

## Summary of All 18 Rules Applied

| # | Dataset | Field | Issue | Rows Affected | Disposition |
|---|---|---|---|---|---|
| 1 | coverage | GROUP | WHO export footer metadata row | 1 | removed |
| 2 | coverage | YEAR | Float-typed year column | 399,858 | standardized |
| 3 | coverage | COVERAGE | Values above 100% (documented Phase 0 finding: 5,097 rows >100%, max 3... | 5,097 | flagged |
| 4 | coverage | DOSES | Negative DOSES values (8 rows identified in Phase 0: 7x -3333, 1x -222... | 8 | flagged |
| 5 | coverage | NAME | 1274 rows with missing NAME | 1,274 | retained |
| 6 | coverage | GROUP | Mixed country-level and aggregate-level rows in one table | 18,817 | standardized |
| 7 | incidence | GROUP | WHO export footer metadata row | 1 | removed |
| 8 | incidence | YEAR | Float-typed year column | 84,945 | standardized |
| 9 | incidence | DENOMINATOR | Comma-formatting inconsistency: 'per 1,000 live births' vs 'per 1000 l... | 308 | standardized |
| 10 | incidence | GROUP | Mixed country-level and aggregate-level rows in one table | 2,891 | standardized |
| 11 | cases | GROUP | WHO export footer metadata row | 1 | removed |
| 12 | cases | YEAR | Float-typed year column | 84,869 | standardized |
| 13 | cases | GROUP | Mixed country-level and aggregate-level rows in one table | 2,815 | standardized |
| 14 | intro | ISO_3_CODE | WHO export footer metadata row | 1 | removed |
| 15 | intro | YEAR | Float-typed year column | 138,320 | standardized |
| 16 | schedule | ISO_3_CODE | WHO export footer metadata row | 1 | removed |
| 17 | schedule | YEAR | Float-typed year column | 8,052 | standardized |
| 18 | schedule | SCHEDULEROUNDS | Float-typed schedule round number | 8,052 | standardized |

**Rules required by the Phase 1 specification and where they appear above:**
- Footer removal → Rules 1, 7, 11, 14, 16
- Type conversions (YEAR, SCHEDULEROUNDS) → Rules 2, 8, 12, 15, 17, 18
- Denominator normalization → Rule 9
- >100% coverage handling → Rule 3
- >500% extreme coverage handling → Rule 3 (same rule; the flag distinguishes `above_100_moderate` from `extreme_outlier`)
- -3333 sentinel handling → Rule 4
- Extreme negative dose handling → Rule 4 (same rule; the flag distinguishes `sentinel_not_reported` from `implausible_negative`)
- Country/aggregate separation → Rules 6, 10, 13
- NAME-null investigation (resolves a Phase 0 open question) → Rule 5
- WHO region derivation → documented separately in `logs/03_build_dimensions.json` (not a row-level cleaning rule; see SQL_SCHEMA.md)
- Crosswalk creation → documented separately in `logs/04_build_crosswalks.json` (analyst-derived metadata, not a cleaning rule on source data; see DATA_DICTIONARY.md and SQL_SCHEMA.md)

## Key Findings Resolved During Cleaning

**NAME-null investigation (Rule 5):** Phase 0 flagged 1,275 NAME nulls in the raw coverage
table (0.3%). After footer removal, 1,274 remain. Cross-tabulating against `GROUP` shows
**100% of these are aggregate rows** (637 `WB_LONG` + 637 `WB_SHORT` World-Bank income-group
labels) — **zero country-level (`GROUP='COUNTRIES'`) rows have a missing name.** This resolves
the Phase 0 open question: there is no genuine country-identification gap in the coverage data.

**Coverage >100% (Rule 3):** 5,097 rows exceed 100% coverage (out of 211,701 non-null country-level
`COVERAGE` values). Of these, 5,088 fall in the "moderate" 100–500% band (plausible under-estimated
denominator effect in administrative reporting, retained as normal analytical data but flagged for
transparency) and 9 fall above 500% (up to 32,000%, e.g. Morocco/FLU_HAJ/2018), flagged
`extreme_outlier` and marked `coverage_analytical_exclude = 1` for exclusion from analytical
aggregates in later phases — but the original value is never deleted or clipped.

**Negative DOSES (Rule 4):** 8 negative values found in country-level coverage data. 7 are
exactly `-3333` (Bahamas, Trinidad & Tobago, Paraguay — all `FLU_*` antigens), treated as a
"not reported" sentinel and set to NULL in the analytical `doses_clean` field (never 0). 1 is
an implausible extreme value (El Salvador/POL3/2017, `-222,288,203`), treated as a data error
and also nulled in `doses_clean`. Both categories retain the original raw value in `doses_raw`
for full traceability.

**Denominator normalization (Rule 9):** `"per 1000 live births"` (308 rows) was mapped to
`"per 1,000 live births"` (matching the 8,874-row majority spelling) in a new
`denominator_standardized` field. The original text is preserved unchanged in `denominator_raw`,
and the numeric `incidence_rate` value was never touched by this rule.

---

## 1. coverage — GROUP

- **Issue:** WHO export footer metadata row
- **Detection method:** First-column string startswith 'Created:'
- **Rule applied:** Drop row(s) matching footer pattern
- **Rows affected:** 1
- **Before:** 399859
- **After:** 399858
- **Reason:** Row is workbook export metadata (export timestamp), not an analytical observation.
- **Disposition:** removed

## 2. coverage — YEAR

- **Issue:** Float-typed year column
- **Detection method:** Check YEAR == round(YEAR) for all non-null values
- **Rule applied:** Cast to nullable Int64 (YEAR_CLEAN) when whole number; else leave NULL and report
- **Rows affected:** 399,858
- **Before:** float64
- **After:** Int64 (YEAR_CLEAN)
- **Reason:** YEAR is conceptually a whole-number calendar year; float storage is a source-format artifact.
- **Disposition:** standardized

## 3. coverage — COVERAGE

- **Issue:** Values above 100% (documented Phase 0 finding: 5,097 rows >100%, max 32,000%)
- **Detection method:** COVERAGE > 100 threshold checks at 100 and 500
- **Rule applied:** Retain all values unmodified in COVERAGE_RAW/COVERAGE; add COVERAGE_QUALITY_FLAG ('normal' <=100, 'above_100_moderate' 100-500, 'extreme_outlier' >500) and boolean COVERAGE_ANALYTICAL_EXCLUDE (True only for >500). No row deleted, no value clipped.
- **Rows affected:** 5,097
- **Before:** unflagged COVERAGE
- **After:** flagged, original value retained
- **Reason:** Moderate >100% values can be legitimate (denominator under-estimation in administrative reporting); values >500% (e.g. Morocco/FLU_HAJ/2018 at 32,000%) are implausible and are flagged for exclusion from analytical measures in later phases, but are not deleted so the raw signal remains auditable.
- **Disposition:** flagged

## 4. coverage — DOSES

- **Issue:** Negative DOSES values (8 rows identified in Phase 0: 7x -3333, 1x -222,288,203)
- **Detection method:** DOSES < 0, then split on DOSES == -3333 vs other
- **Rule applied:** DOSES_RAW preserves original value unmodified. DOSES_QUALITY_FLAG assigns 'sentinel_not_reported' to the repeated -3333 pattern (treated as a 'not reported' placeholder, not a real dose count) and 'implausible_negative' to the single extreme outlier. DOSES_CLEAN sets both categories to NULL (never 0) for analytical use; DOSES_RAW keeps the original value for traceability.
- **Rows affected:** 8
- **Before:** raw negative value
- **After:** NULL in DOSES_CLEAN, flagged, raw preserved
- **Reason:** -3333 recurs identically across unrelated countries/antigens (Bahamas, Trinidad & Tobago, Paraguay, all FLU_* antigens) which is characteristic of a sentinel/placeholder code rather than a genuine count. The El Salvador/POL3/2017 value (-222,288,203) is numerically implausible for any real dose count and is treated as a data error, not a real value.
- **Disposition:** flagged

## 5. coverage — NAME

- **Issue:** 1274 rows with missing NAME
- **Detection method:** NAME.isna() cross-tabulated against GROUP
- **Rule applied:** No fabrication. NAME left NULL exactly as sourced. Cross-tab against GROUP recorded for transparency.
- **Rows affected:** 1,274
- **Before:** NULL
- **After:** NULL (unchanged) + documented breakdown by GROUP
- **Reason:** Breakdown by GROUP: {'WB_LONG': 637, 'WB_SHORT': 637}. Of these, 0 are GROUP='COUNTRIES' rows with a genuinely missing country name in the source; the remainder are aggregate-group rows.
- **Disposition:** retained

## 6. coverage — GROUP

- **Issue:** Mixed country-level and aggregate-level rows in one table
- **Detection method:** GROUP column distinct-value inspection (Phase 0 finding)
- **Rule applied:** Split into two frames: GROUP='COUNTRIES' -> country-level fact table; all other GROUP values (WHO_REGIONS, UNICEF_REGIONS, WB_LONG, WB_SHORT, DEVELOPMENT_STATUS, GAVI_PHASE5, GLOBAL) -> aggregate fact table.
- **Rows affected:** 18,817
- **Before:** 399858 mixed rows
- **After:** 381041 country rows / 18817 aggregate rows
- **Reason:** Prevents accidental contamination of country-level analysis with regional/global/income-group rollups.
- **Disposition:** standardized

## 7. incidence — GROUP

- **Issue:** WHO export footer metadata row
- **Detection method:** First-column string startswith 'Created:'
- **Rule applied:** Drop row(s) matching footer pattern
- **Rows affected:** 1
- **Before:** 84946
- **After:** 84945
- **Reason:** Row is workbook export metadata (export timestamp), not an analytical observation.
- **Disposition:** removed

## 8. incidence — YEAR

- **Issue:** Float-typed year column
- **Detection method:** Check YEAR == round(YEAR) for all non-null values
- **Rule applied:** Cast to nullable Int64 (YEAR_CLEAN) when whole number; else leave NULL and report
- **Rows affected:** 84,945
- **Before:** float64
- **After:** Int64 (YEAR_CLEAN)
- **Reason:** YEAR is conceptually a whole-number calendar year; float storage is a source-format artifact.
- **Disposition:** standardized

## 9. incidence — DENOMINATOR

- **Issue:** Comma-formatting inconsistency: 'per 1,000 live births' vs 'per 1000 live births'
- **Detection method:** Exact string comparison of distinct DENOMINATOR values
- **Rule applied:** Map 'per 1000 live births' -> 'per 1,000 live births' into new DENOMINATOR_STANDARDIZED field; DENOMINATOR_RAW preserved unchanged; INCIDENCE_RATE numeric value untouched
- **Rows affected:** 308
- **Before:** {'per 1,000,000 total population': 61480, 'per 1,000,000 <15 population': 9130, 'per 1,000 live births': 8874, 'per 10,000 live births': 5153, 'per 1000 live births': 308}
- **After:** {'per 1,000,000 total population': 61480, 'per 1,000 live births': 9182, 'per 1,000,000 <15 population': 9130, 'per 10,000 live births': 5153}
- **Reason:** Same reporting basis represented with inconsistent punctuation; standardizing enables correct grouping without losing traceability to the original text.
- **Disposition:** standardized

## 10. incidence — GROUP

- **Issue:** Mixed country-level and aggregate-level rows in one table
- **Detection method:** GROUP column distinct-value inspection (Phase 0 finding)
- **Rule applied:** Split into two frames: GROUP='COUNTRIES' -> country-level fact table; all other GROUP values (WHO_REGIONS, UNICEF_REGIONS, WB_LONG, WB_SHORT, DEVELOPMENT_STATUS, GAVI_PHASE5, GLOBAL) -> aggregate fact table.
- **Rows affected:** 2,891
- **Before:** 84945 mixed rows
- **After:** 82054 country rows / 2891 aggregate rows
- **Reason:** Prevents accidental contamination of country-level analysis with regional/global/income-group rollups.
- **Disposition:** standardized

## 11. cases — GROUP

- **Issue:** WHO export footer metadata row
- **Detection method:** First-column string startswith 'Created:'
- **Rule applied:** Drop row(s) matching footer pattern
- **Rows affected:** 1
- **Before:** 84870
- **After:** 84869
- **Reason:** Row is workbook export metadata (export timestamp), not an analytical observation.
- **Disposition:** removed

## 12. cases — YEAR

- **Issue:** Float-typed year column
- **Detection method:** Check YEAR == round(YEAR) for all non-null values
- **Rule applied:** Cast to nullable Int64 (YEAR_CLEAN) when whole number; else leave NULL and report
- **Rows affected:** 84,869
- **Before:** float64
- **After:** Int64 (YEAR_CLEAN)
- **Reason:** YEAR is conceptually a whole-number calendar year; float storage is a source-format artifact.
- **Disposition:** standardized

## 13. cases — GROUP

- **Issue:** Mixed country-level and aggregate-level rows in one table
- **Detection method:** GROUP column distinct-value inspection (Phase 0 finding)
- **Rule applied:** Split into two frames: GROUP='COUNTRIES' -> country-level fact table; all other GROUP values (WHO_REGIONS, UNICEF_REGIONS, WB_LONG, WB_SHORT, DEVELOPMENT_STATUS, GAVI_PHASE5, GLOBAL) -> aggregate fact table.
- **Rows affected:** 2,815
- **Before:** 84869 mixed rows
- **After:** 82054 country rows / 2815 aggregate rows
- **Reason:** Prevents accidental contamination of country-level analysis with regional/global/income-group rollups.
- **Disposition:** standardized

## 14. intro — ISO_3_CODE

- **Issue:** WHO export footer metadata row
- **Detection method:** First-column string startswith 'Created:'
- **Rule applied:** Drop row(s) matching footer pattern
- **Rows affected:** 1
- **Before:** 138321
- **After:** 138320
- **Reason:** Row is workbook export metadata (export timestamp), not an analytical observation.
- **Disposition:** removed

## 15. intro — YEAR

- **Issue:** Float-typed year column
- **Detection method:** Check YEAR == round(YEAR) for all non-null values
- **Rule applied:** Cast to nullable Int64 (YEAR_CLEAN) when whole number; else leave NULL and report
- **Rows affected:** 138,320
- **Before:** float64
- **After:** Int64 (YEAR_CLEAN)
- **Reason:** YEAR is conceptually a whole-number calendar year; float storage is a source-format artifact.
- **Disposition:** standardized

## 16. schedule — ISO_3_CODE

- **Issue:** WHO export footer metadata row
- **Detection method:** First-column string startswith 'Created:'
- **Rule applied:** Drop row(s) matching footer pattern
- **Rows affected:** 1
- **Before:** 8053
- **After:** 8052
- **Reason:** Row is workbook export metadata (export timestamp), not an analytical observation.
- **Disposition:** removed

## 17. schedule — YEAR

- **Issue:** Float-typed year column
- **Detection method:** Check YEAR == round(YEAR) for all non-null values
- **Rule applied:** Cast to nullable Int64 (YEAR_CLEAN) when whole number; else leave NULL and report
- **Rows affected:** 8,052
- **Before:** float64
- **After:** Int64 (YEAR_CLEAN)
- **Reason:** YEAR is conceptually a whole-number calendar year; float storage is a source-format artifact.
- **Disposition:** standardized

## 18. schedule — SCHEDULEROUNDS

- **Issue:** Float-typed schedule round number
- **Detection method:** Check SCHEDULEROUNDS == round(SCHEDULEROUNDS)
- **Rule applied:** Cast to nullable Int64 (SCHEDULEROUNDS_CLEAN)
- **Rows affected:** 8,052
- **Before:** float64
- **After:** Int64
- **Reason:** Schedule round is conceptually a whole-number dose sequence position.
- **Disposition:** standardized

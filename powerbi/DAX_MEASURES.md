# PHASE3_DAX_MEASURES.md
**Project:** Vaccination Data Analysis and Visualization — Phase 3

All measures below reference only columns that actually exist in the Phase 3 Power BI-ready
tables (verified against `phase3_powerbi/data/*.csv` and `phase3_powerbi/logs/01_build_powerbi_datasets.json`
— no field is assumed). Every measure respects the missing-value policy: **no measure ever
substitutes 0 for a blank/null value**; Power BI's native aggregation behavior (excluding blanks)
is relied upon deliberately.

---

## 1. Core KPI Measures (Page 1 — Executive Overview)

```dax
Total Countries Represented =
DISTINCTCOUNT ( dim_country[country_code] )
```
*Static count of the country dimension (214) — does not depend on any fact filter. Use a
separate measure below if you need "countries WITH DATA for the current filter context".*

```dax
Countries With Coverage Data (Filtered) =
DISTINCTCOUNT ( fact_coverage_country[country_code] )
```
*Responds to slicers (year, antigen, coverage category). Will be smaller than the static count
above whenever a filter excludes some countries — this difference itself is a useful data-quality
KPI card, not an error.*

```dax
Year Range Label =
VAR MinYr = MIN ( dim_year[year] )
VAR MaxYr = MAX ( dim_year[year] )
RETURN MinYr & " – " & MaxYr
```

```dax
Average WUENIC Coverage % =
CALCULATE (
    AVERAGE ( fact_coverage_country[coverage_raw] ),
    fact_coverage_country[coverage_category] = "WUENIC"
)
```
*Blanks in `coverage_raw` (≈20% of WUENIC rows) are automatically excluded by AVERAGE — this is
correct and intentional, not a gap to fix.*

```dax
Data Quality Note — Extreme Outliers =
VAR ExtremeCount =
    CALCULATE (
        COUNTROWS ( fact_coverage_country ),
        fact_coverage_country[coverage_quality_flag] = "extreme_outlier"
    )
RETURN
    ExtremeCount & " rows exceed 500% coverage (data quality flag, retained not deleted — see Phase 1 documentation)"
```

## 2. Vaccination Coverage Page Measures

```dax
Coverage % (WUENIC, Excl. Extreme Outliers) =
CALCULATE (
    AVERAGE ( fact_coverage_country[coverage_raw] ),
    fact_coverage_country[coverage_category] = "WUENIC",
    fact_coverage_country[coverage_analytical_exclude] = 0
)
```
*This is the RECOMMENDED default measure for trend/comparison visuals. It excludes only the 9
rows flagged `extreme_outlier` (>500%, e.g. the Morocco/FLU_HAJ/2018 row at 32,000%) — the 5,088
rows in the 100–500% "moderate" band remain included, since Phase 1 documented these as plausibly
legitimate (denominator under-estimation), not errors.*

```dax
Coverage % (WUENIC, All Values Incl. Outliers) =
CALCULATE (
    AVERAGE ( fact_coverage_country[coverage_raw] ),
    fact_coverage_country[coverage_category] = "WUENIC"
)
```
*Provide BOTH measures on the report with a visible toggle/tooltip explaining the difference —
never silently pick one. This directly implements the Phase 1/2/3 rule "do not silently remove or
clip values above 100%."*

```dax
Selected Coverage Category = SELECTEDVALUE ( dim_coverage_category[coverage_category], "WUENIC" )

Coverage % (Category-Selectable) =
CALCULATE (
    AVERAGE ( fact_coverage_country[coverage_raw] ),
    fact_coverage_country[coverage_category] = [Selected Coverage Category]
)
```
*Pairs with a slicer on `dim_coverage_category[coverage_category]` for Page 2's category
comparison requirement.*

```dax
YoY Change (Coverage, pct points) =
VAR CurrentYearAvg = [Coverage % (WUENIC, Excl. Extreme Outliers)]
VAR PriorYearAvg =
    CALCULATE (
        [Coverage % (WUENIC, Excl. Extreme Outliers)],
        FILTER ( ALL ( dim_year ), dim_year[year] = MAX ( dim_year[year] ) - 1 )
    )
RETURN
    IF ( ISBLANK ( PriorYearAvg ) || ISBLANK ( CurrentYearAvg ), BLANK (), CurrentYearAvg - PriorYearAvg )
```
*Returns BLANK (not 0) when either year is missing data — a blank year-over-year change must
never display as "0% change", which would misleadingly imply stability.*

### Dose-Sequence Drop-off (requires a disconnected "Dose Pair" selector table)

Because comparing two different `antigen_code` values within one measure requires picking them
explicitly (DAX cannot natively "know" that DTPCV1 and DTPCV3 are a pair), create a small
disconnected table in Power Query (not related to any other table) named `DosePairSelector`:

| dose1_antigen | dose2_antigen | pair_label |
|---|---|---|
| DTPCV1 | DTPCV3 | DTP: Dose 1 → Dose 3 |
| MCV1 | MCV2 | Measles: Dose 1 → Dose 2 |
| IPV1 | IPV2 | IPV: Dose 1 → Dose 2 |

```dax
Selected Dose1 Antigen = SELECTEDVALUE ( DosePairSelector[dose1_antigen] )
Selected Dose2 Antigen = SELECTEDVALUE ( DosePairSelector[dose2_antigen] )

Dose 1 Coverage % =
CALCULATE (
    AVERAGE ( fact_coverage_country[coverage_raw] ),
    fact_coverage_country[coverage_category] = "WUENIC",
    fact_coverage_country[antigen_code] = [Selected Dose1 Antigen]
)

Dose 2/3 Coverage % =
CALCULATE (
    AVERAGE ( fact_coverage_country[coverage_raw] ),
    fact_coverage_country[coverage_category] = "WUENIC",
    fact_coverage_country[antigen_code] = [Selected Dose2 Antigen]
)

Dose Drop-off (pct points) = [Dose 1 Coverage %] - [Dose 2/3 Coverage %]
```
*Values computed in Phase 2 for validation: DTP1→3 mean drop-off 8.31 pts (n=7,949 country-years),
Measles 1→2 mean drop-off 7.89 pts (n=3,242), IPV1→2 mean drop-off 13.18 pts (n=216) — use these
to sanity-check the DAX measure once built in Power BI Desktop; they should match closely (Power
BI's filter context may include/exclude a few more recent rows depending on when data was pulled).*

## 3. Regional/Country Comparison Page Measures

```dax
Countries Missing WHO Region =
CALCULATE (
    DISTINCTCOUNT ( dim_country[country_code] ),
    ISBLANK ( dim_country[who_region] )
)
```
*Expected value: 1 (American Samoa) — display this explicitly on the page rather than letting
those countries silently vanish from region-based visuals.*

```dax
Coverage Coefficient of Variation (Within Region) =
VAR RegionAvg = [Coverage % (WUENIC, Excl. Extreme Outliers)]
VAR RegionStdDev =
    CALCULATE (
        STDEV.P ( fact_coverage_country[coverage_raw] ),
        fact_coverage_country[coverage_category] = "WUENIC",
        fact_coverage_country[coverage_analytical_exclude] = 0
    )
RETURN
    DIVIDE ( RegionStdDev, RegionAvg ) * 100
```
*Requires the report page to be filtered/grouped by `dim_country[who_region]`. `DIVIDE` (not `/`)
is used specifically to return BLANK rather than an error when RegionAvg is 0 or blank.*

## 4. Disease Incidence & Reported Cases Page Measures

```dax
Total Reported Cases =
SUM ( fact_cases_country[cases] )
```
*SUM naturally excludes blanks; a country-year with no reported figure contributes nothing to the
sum, which is CORRECT — it must never be coerced to contribute 0 explicitly, since that would
misleadingly suggest "zero cases confirmed" rather than "not reported."*

```dax
Average Incidence Rate =
AVERAGE ( fact_incidence_country[incidence_rate] )
```

```dax
Incidence Data Completeness % =
VAR TotalRows = COUNTROWS ( fact_incidence_country )
VAR NonBlankRows =
    CALCULATE ( COUNTROWS ( fact_incidence_country ), NOT ISBLANK ( fact_incidence_country[incidence_rate] ) )
RETURN
    DIVIDE ( NonBlankRows, TotalRows ) * 100
```
*Use this as a visible data-quality indicator on every incidence visual — per-disease
completeness varies from under 50% (YFEVER, POLIO, JAPENC per Phase 2 findings) to well over 90%.*

```dax
Denominator Label (Current Filter) =
SELECTEDVALUE ( fact_incidence_country[denominator_standardized], "Multiple denominators — select a single disease to see units" )
```
*Forces the report to surface a "multiple denominators" warning rather than silently showing a
number with an ambiguous or missing unit whenever more than one disease is in the current filter
context — directly implements the "clear distinction between incidence rates and case counts" and
"no misleading combined statistic" requirements.*

## 5. Vaccine Introduction & Schedule Page Measures

```dax
Countries With Vaccine Introduced ('Yes' variants) =
CALCULATE (
    DISTINCTCOUNT ( fact_vaccine_introduction[country_code] ),
    fact_vaccine_introduction[intro_status] IN
        { "Yes", "Yes (R)", "Yes (P)", "Yes (A)", "Yes (O)", "Yes (D)" }
)
```
*Uses the exact 6 affirmative values found in the actual data (Phase 2 finding) — "High risk
area" and "ND" are deliberately excluded, matching the Phase 2-validated rule. If the SQL-view
option (B) is used instead of CSV import, the pre-computed `is_introduced_yes_variant` column from
`vw_fact_vaccine_introduction` can be summed instead of using an IN-list, which is more robust to
any future new qualifier code.*

```dax
Schedule Records — Missing Target Population % =
VAR TotalRows = COUNTROWS ( fact_vaccine_schedule )
VAR BlankRows = CALCULATE ( COUNTROWS ( fact_vaccine_schedule ), ISBLANK ( fact_vaccine_schedule[target_pop] ) )
RETURN
    DIVIDE ( BlankRows, TotalRows ) * 100
```

## 6. Vaccination-Disease Association Page Measures

```dax
Selected Pair Sample Size =
SELECTEDVALUE ( fact_association_correlations[n_observations] )

Selected Pair Pearson r =
SELECTEDVALUE ( fact_association_correlations[pearson_r] )

Selected Pair Spearman rho =
SELECTEDVALUE ( fact_association_correlations[spearman_rho] )
```
*These are pass-through measures over the pre-computed Phase 2 summary table — DAX does NOT
recompute the correlation (SQLite/DAX cannot easily replicate SciPy's Pearson/Spearman
implementation reliably; Python's output is authoritative and is imported as-is). Any table/card
visual using these three measures MUST also display a static text box: "Observed association only
— not a causal effectiveness estimate. Depends on the Phase 1 analyst-derived antigen-disease
crosswalk. See PHASE3_POWERBI_REPORT_SPECIFICATION.md Page 6 for full caveats."*

## 7. Measures Deliberately NOT Created

- **No "Vaccine Effectiveness %" measure** — would require a causal estimate this data cannot
  support (no control group, no confounder adjustment). Explicitly out of scope per the project's
  analytical-integrity rule (Phase 0 onward).
- **No blended country+aggregate average** — e.g. no measure that averages `fact_coverage_country`
  and `fact_coverage_aggregate` together, since that would double-count or conflate two
  structurally different granularities.
- **No age-standardized or population-weighted coverage measure** — the source data does not
  include an underlying population figure per country-year (only `target_number`, which is
  antigen-specific and only ~16% populated at country level), so a defensible weighting cannot be
  constructed without fabricating a denominator. A simple (unweighted) mean across countries is
  used throughout instead, and every measure/chart description says so explicitly.

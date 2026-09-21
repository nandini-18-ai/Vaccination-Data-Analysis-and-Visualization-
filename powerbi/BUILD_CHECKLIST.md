# POWER_BI_BUILD_CHECKLIST.md
**Project:** Vaccination Data Analysis and Visualization — Phase 3 Finalization
Use this alongside `POWER_BI_STEP_BY_STEP_GUIDE.md` (full explanations) and
`POWER_BI_VISUAL_BUILD_ORDER.md` (exact visual sequence). Check off each item as you go — do not
skip ahead if an earlier item fails; fix it first (see `POWER_BI_TROUBLESHOOTING.md`).

## A. Data Import
- [ ] Power BI Desktop installed and open
- [ ] All 19 CSV files imported from `phase3_powerbi/data/` (8 dimensions, 2 crosswalks, 8 facts, 1 summary table)
- [ ] `DosePairSelector` table manually entered (3 rows, 3 columns — Step 5)
- [ ] All table names match their CSV filenames exactly (no renaming)
- [ ] Row counts verified against the table in Step 2 of the Step-by-Step Guide (19/19 match)

## B. Data Types
- [ ] `year` is Whole Number (not Date) in all 9 tables that have it
- [ ] All measure-eligible numeric fields (coverage_raw, target_number, doses_raw, doses_clean, incidence_rate, cases, pearson_r, spearman_rho) are Decimal Number
- [ ] All code/name/description/status fields remain Text (country_code, antigen_code, disease_code, vaccine_code, coverage_category, etc.)
- [ ] `coverage_analytical_exclude` type noted (Whole Number 0/1 or True/False) and DAX adjusted accordingly if needed

## C. Power Query Transformations
- [ ] `entity_key` custom column added to `dim_aggregate_entity`
- [ ] `entity_key` custom column added to `fact_coverage_aggregate`
- [ ] `entity_key` custom column added to `fact_incidence_aggregate`
- [ ] `entity_key` custom column added to `fact_cases_aggregate`
- [ ] `pair_label` custom column added to `fact_association_correlations` (for the Page 6 slicer)
- [ ] Close & Apply run successfully with no errors

## D. Relationships (Model View)
- [ ] All auto-detected relationships reviewed and deleted if not on the approved list
- [ ] All 25 relationships from Step 6 of the Step-by-Step Guide created manually
- [ ] Every relationship set to Many-to-one, Single cross-filter direction
- [ ] Confirmed: NO relationship exists between any `fact_*_aggregate` table and `dim_country`
- [ ] Confirmed: NO relationship exists between `fact_association_correlations` and `dim_year` or `dim_country`
- [ ] Confirmed: `DosePairSelector` has ZERO relationships to any other table
- [ ] Model view shows no red "relationship error" icons

## E. DAX Measures (24 total)
### KPI / core (Section 1, PHASE3_DAX_MEASURES.md)
- [ ] Total Countries Represented
- [ ] Countries With Coverage Data (Filtered)
- [ ] Year Range Label
- [ ] Average WUENIC Coverage %
- [ ] Data Quality Note — Extreme Outliers
### Coverage page (Section 2)
- [ ] Coverage % (WUENIC, Excl. Extreme Outliers)
- [ ] Coverage % (WUENIC, All Values Incl. Outliers)
- [ ] Selected Coverage Category
- [ ] Coverage % (Category-Selectable)
- [ ] YoY Change (Coverage, pct points)
- [ ] Selected Dose1 Antigen
- [ ] Selected Dose2 Antigen
- [ ] Dose 1 Coverage %
- [ ] Dose 2/3 Coverage %
- [ ] Dose Drop-off (pct points)
### Regional/Country page (Section 3)
- [ ] Countries Missing WHO Region
- [ ] Coverage Coefficient of Variation (Within Region)
### Disease/Cases page (Section 4)
- [ ] Total Reported Cases
- [ ] Average Incidence Rate
- [ ] Incidence Data Completeness %
- [ ] Denominator Label (Current Filter)
### Introduction/Schedule page (Section 5)
- [ ] Countries With Vaccine Introduced ('Yes' variants)
- [ ] Schedule Records — Missing Target Population %
### Association page (Section 6)
- [ ] Selected Pair Sample Size
- [ ] Selected Pair Pearson r
- [ ] Selected Pair Spearman rho
- [ ] Every measure shows no red squiggle / DAX syntax error

## F. Page 1 — Executive Overview
- [ ] KPI card: Total Countries Represented
- [ ] KPI card: Year Range
- [ ] KPI card: Average WUENIC Coverage
- [ ] Static text box: Data Quality Notes (4 bullet points per spec)
- [ ] Line chart: Global coverage trend, key antigens (DTP3/MCV1/Pol3/BCG/HepB3/PCV3)
- [ ] Filled map: Country coverage map, with local year slider

## G. Page 2 — Vaccination Coverage
- [ ] Slicer: Antigen (multi-select)
- [ ] Slicer: Year range
- [ ] Slicer: Coverage category (default WUENIC)
- [ ] Line chart: Coverage trend by antigen
- [ ] Box plot: Coverage distribution by antigen
- [ ] Bar chart: Dose-sequence drop-off (bound to DosePairSelector)
- [ ] KPI card: Coverage %
- [ ] KPI card: YoY Change
- [ ] KPI card: N Countries
- [ ] Table: Top/Bottom 10 countries

## H. Page 3 — Regional and Country Comparison
- [ ] Slicer: Antigen, Year, Category (reused pattern from Page 2)
- [ ] Filled map: Country coverage map (by WHO region)
- [ ] Bar chart: Mean coverage by WHO region
- [ ] Bar chart: Within-region CV%
- [ ] Table: Full country ranking (with quality flag column)
- [ ] KPI card: Countries Missing WHO Region (always visible, not hidden)

## I. Page 4 — Disease Incidence and Reported Cases
- [ ] Static text box: Unit-distinction warning (exact wording from spec)
- [ ] Slicer: Disease, Year range
- [ ] Line chart: Incidence rate trend (log scale, axis labeled "log scale")
- [ ] Line chart: Reported cases trend (SEPARATE visual, not combined with incidence)
- [ ] KPI card: Data Completeness %
- [ ] Bar chart: Top 15 countries by cases

## J. Page 5 — Vaccine Introduction and Schedule
- [ ] Static text box: Introduction/coverage distinction warning (exact wording from spec)
- [ ] Slicer: Vaccine description, Year, WHO Region
- [ ] Line chart: Countries introduced by year
- [ ] Bar chart: Introduction by WHO region
- [ ] Bar chart: Top 15 schedule codes (labeled "2019-2023 snapshot")
- [ ] Table: Target population / missingness (with explicit "(missing)" row, not blank)

## K. Page 6 — Vaccination-Disease Associations
- [ ] Static text box (fixed): Non-causal warning banner (top, exact wording from spec)
- [ ] Slicer: pair_label (single-select, restricted to the 14 validated pairs only)
- [ ] Bar chart: Pearson r by pair (diverging color scale centered at 0)
- [ ] Scatter plot: Coverage vs incidence (selected pair)
- [ ] KPI card: N Observations
- [ ] KPI card: Pearson r / Spearman rho
- [ ] Static text box (fixed): Methodology caption (bottom, exact wording from spec)

## L. Navigation and Interaction
- [ ] 6 navigation buttons created on Page 1, identical position on every page
- [ ] Each button's Action set to Page Navigation, correct destination
- [ ] Buttons copy-pasted onto Pages 2–6 (not rebuilt from scratch, to guarantee identical position)
- [ ] Cross-filtering between same-page visuals tested and works as expected
- [ ] Tooltips configured on both map visuals and the association scatter plot

## M. Formatting
- [ ] Coverage percentage fields use custom format `0.0"%"` (NOT the built-in Percentage type)
- [ ] Year fields show no thousands separator
- [ ] Consistent color coding applied: WUENIC=blue, ADMIN=orange, OFFICIAL=green, PAB=purple, HPV=pink
- [ ] Minimum 11pt font on KPI card labels
- [ ] Minimum 12pt font on all warning/methodology text boxes

## N. Final Validation Before Considering the Build Done
- [ ] Every page's every slicer clicked through at least once — no unexpected blank visual
- [ ] Map on Page 1 and Page 3 renders the large majority of 214 countries
- [ ] KPI cards show blank (not 0) for filter combinations with no data
- [ ] Dose Drop-off measure checked against Phase 2 reference value for at least 1 pair (DTP1→3 ≈ 8.31 pts)
- [ ] File saved as `.pbix`
- [ ] File re-opened once after saving to confirm it loads cleanly

**When every box above is checked, the Power BI Desktop build is complete.**

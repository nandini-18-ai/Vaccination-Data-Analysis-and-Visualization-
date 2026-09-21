# PHASE3_POWERBI_REPORT_SPECIFICATION.md
**Project:** Vaccination Data Analysis and Visualization — Phase 3
**Status:** Complete implementation specification. No `.pbix` file was created — see
`PHASE3_IMPLEMENTATION_GUIDE.md` Section "Power BI File Limitation" for why, and exactly what a
report builder needs to do in Power BI Desktop to turn this specification into a working report.

Every visual specified below has a **real, verified data source** — every field named is
confirmed to exist in `phase3_powerbi/data/*.csv` (see `phase3_powerbi/logs/01_build_powerbi_datasets.json`
for the source-of-truth field list). Wireframes are ASCII layout diagrams, genuinely constructed
from this specification — not decorative mockups.

---

## Page 1 — EXECUTIVE OVERVIEW

**Purpose:** Orient any viewer to the project's scope, data currency, and headline coverage
picture within 10 seconds; provide navigation to the other 5 pages.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  VACCINATION DATA ANALYSIS AND VISUALIZATION            [Nav: 1 2 3 4 5 6]│
│  Global immunization coverage, disease burden & program data, 1940-2023   │
├──────────────┬──────────────┬──────────────┬─────────────────────────────┤
│ 214           │ 1980-2023    │ 68.9%        │  ⚠ DATA QUALITY NOTES       │
│ Countries     │ Coverage/    │ Avg WUENIC   │  • WUENIC=default series    │
│ Represented   │ Incidence/   │ Coverage     │  • 5,097 rows >100% (kept,  │
│               │ Cases range  │ (excl.       │    flagged, not clipped)    │
│               │              │ outliers)    │  • Schedule = 2019-23 only  │
├──────────────┴──────────────┴──────────────┤  • 1 country (ASM) has no   │
│                                              │    WHO region               │
│   [Line chart: Global mean coverage,        │  • Xwalks = analyst-derived │
│    key antigens, 1980-2023]                 │                             │
│                                              ├─────────────────────────────┤
│                                              │  [World map: countries      │
│                                              │   with WUENIC data, current │
│                                              │   year selector]            │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Recommended visuals:** 3 KPI cards, 1 multi-row card/table (data-quality notes as static text,
  not a data visual), 1 line chart, 1 filled map.
- **Fields used:** `fact_coverage_country[coverage_raw, coverage_category, year]`,
  `dim_country[country_code, country_name, who_region]`, `dim_antigen[antigen_code]`.
- **Filters/slicers:** none page-level (this page is a fixed overview); the map has a year slider
  local to its own visual.
- **KPI definitions:** `Total Countries Represented`, `Year Range Label`, `Average WUENIC Coverage %`
  (excl. outliers) — all defined in `PHASE3_DAX_MEASURES.md` Section 1.
- **Required measures:** `Total Countries Represented`, `Year Range Label`,
  `Coverage % (WUENIC, Excl. Extreme Outliers)`.
- **Expected user interaction:** read-only landing page; click nav buttons (bookmarks) to jump to
  Pages 2–6; map year slider changes only the map.
- **Limitations:** the single "Average WUENIC Coverage %" KPI necessarily blends all antigens and
  countries into one unweighted number — it is a headline orientation figure only, explicitly
  captioned "unweighted mean across antigens/countries, WUENIC category" beneath the card, not
  presented as a definitive summary statistic.
- **Accessibility:** KPI cards use both a numeric value and a text label (not color alone); map
  uses a sequential (not red-green) color scale with a legend; minimum 11pt font on all card labels.

---

## Page 2 — VACCINATION COVERAGE

**Purpose:** Deep-dive into coverage trends, by antigen, year, category, country, and region.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ VACCINATION COVERAGE                                    [Nav: 1 2 3 4 5 6]│
├───────────────┬────────────────────────────────────────────────────────┬─┤
│ FILTERS        │  [Line chart: Coverage % trend by Year, one line per   │ │
│ ☐ Antigen      │   selected antigen — DTP3/MCV1/Pol3/BCG/HepB3/PCV3     │ │
│   (multi-sel)  │   default selection]                                  │ │
│ ☐ Year range   │                                                        │ │
│   (slider)     ├────────────────────────────────────────────────────────┤ │
│ ☐ Coverage     │  [Box plot: Coverage distribution by antigen,          │ │
│   category     │   selected year]     │ [Bar: Dose-sequence drop-off,   │ │
│   (WUENIC/     │                       │  selected dose pair]           │ │
│   ADMIN/       ├───────────────────────┴──────────────────────────────┤ │
│   OFFICIAL/    │  KPI: Coverage %  |  KPI: YoY Change  |  KPI: N       │ │
│   PAB/HPV)     │  (selectable)     |  (pct points)     |  Countries    │ │
│ ☐ WHO Region   ├────────────────────────────────────────────────────────┤ │
│                │  [Table: Top/Bottom 10 countries by mean coverage,     │ │
│                │   selected antigen, selected year range]               │ │
└───────────────┴────────────────────────────────────────────────────────┴─┘
```

- **Recommended visuals:** 1 multi-series line chart, 1 box-and-whisker (or column chart with
  error bars if box plot is unavailable in the licensed visual set), 1 bar chart (dose drop-off),
  3 KPI cards, 1 ranked table.
- **Fields used:** `fact_coverage_country[country_code, year, antigen_code, coverage_category,
  coverage_raw, coverage_quality_flag, coverage_analytical_exclude]`, `dim_antigen[antigen_code,
  antigen_description]`, `dim_country[country_code, country_name, who_region]`,
  `dim_coverage_category[coverage_category, description, is_recommended_default]`, plus the
  disconnected `DosePairSelector` table (see DAX doc Section 2).
- **Filters/slicers:** antigen (multi-select slicer on `dim_antigen[antigen_description]`), year
  range (slider on `dim_year[year]`), coverage category (slicer on
  `dim_coverage_category[coverage_category]`, default = WUENIC), WHO region (slicer on
  `dim_country[who_region]`, with an explicit "(blank)" option visible for American Samoa rather
  than hidden).
- **KPI definitions/measures:** `Coverage % (Category-Selectable)`, `YoY Change (Coverage, pct
  points)`, `Countries With Coverage Data (Filtered)`.
- **Expected user interaction:** changing the antigen slicer updates all 4 visuals; changing
  coverage category re-bases every KPI and chart to that category, with the category's
  completeness % shown in a tooltip (from `dim_coverage_category`) so users see how much data
  underlies the number they're looking at.
- **Limitations:** the box plot and top/bottom table use an **unweighted** cross-country
  comparison (no population weighting is possible — see DAX doc Section 7); dose drop-off is only
  available for 3 documented pairs (DTP1→3, Measles1→2, IPV1→2) — the selector does not offer
  pairs without a validated Phase 2 computation.
- **Accessibility:** line chart uses distinct line styles (not only color) for colorblind users;
  box plot includes data labels for median; table is sortable by any column, not just the default.

---

## Page 3 — REGIONAL AND COUNTRY COMPARISON

**Purpose:** Compare WHO regions and individual countries; surface disparities for
resource-allocation discussions.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ REGIONAL AND COUNTRY COMPARISON                          [Nav: 1 2 3 4 5 6]│
├───────────────┬────────────────────────────────────────────────────────┬─┤
│ FILTERS        │  [Filled/choropleth map: coverage_raw by country,       │ │
│ ☐ Antigen      │   selected antigen+year+category. Countries with no     │ │
│ ☐ Year         │   who_region shown in a distinct neutral color, with a  │ │
│ ☐ Coverage     │   legend note "1 country — American Samoa — has no      │ │
│   category     │   derivable WHO region (Phase 1 finding)"]              │ │
│                ├───────────────────────┬────────────────────────────────┤ │
│                │  [Bar: Mean coverage   │  [Bar: Within-region CV%        │ │
│                │   by WHO region]       │   (coefficient of variation)]   │ │
│                ├───────────────────────┴────────────────────────────────┤ │
│                │  [Table: full country ranking, coverage %, quality flag,│ │
│                │   who_region — sortable/searchable]                     │ │
└───────────────┴────────────────────────────────────────────────────────┴─┘
```

- **Recommended visuals:** 1 filled map ("map visualization only if the geographic fields support
  it" — confirmed: `dim_country` has no lat/long or ISO-2 code, only `country_code` [ISO-3];
  Power BI's built-in Map/Filled Map visual DOES support ISO-3 codes via Bing's location service,
  so this is feasible — see limitation note below), 2 bar charts, 1 detailed table.
- **Fields used:** `fact_coverage_country[...]` (same as Page 2), `dim_country[country_code,
  country_name, who_region]`.
- **Filters/slicers:** antigen, year, coverage category (same pattern as Page 2, kept consistent
  across pages for usability).
- **KPI definitions:** `Countries Missing WHO Region` (displayed as a small always-visible note,
  not hidden), `Coverage Coefficient of Variation (Within Region)`.
- **Required measures:** `Countries Missing WHO Region`, `Coverage Coefficient of Variation
  (Within Region)`, plus Page 2's `Coverage % (Category-Selectable)`.
- **Expected user interaction:** clicking a region bar cross-filters the map and table to that
  region; clicking a country on the map cross-filters the table to that country.
- **Map visualization feasibility note:** `dim_country[country_code]` is ISO-3166-1 alpha-3
  (verified in Phase 1) — Power BI's native Map/Filled Map visual can geocode ISO-3 codes via its
  "Location" field role, but geocoding accuracy for small territories (e.g. `ABW`, `AIA`) should be
  spot-checked in Power BI Desktop before publishing, since Bing's geocoder is not always precise
  for very small entities. If any country fails to geocode, the Implementation Guide recommends
  falling back to a table/bar view for that entity rather than omitting it silently.
- **Limitations:** the map plots country-level WUENIC coverage only (never the aggregate/regional
  rollup values — those belong on their own visual using `fact_coverage_aggregate`, kept
  deliberately separate per the Phase 1 aggregate-isolation rule).
- **Accessibility:** map includes a data table alternative (toggle) for screen-reader users; CV%
  bar chart is sorted ascending/descending via a visible control, not fixed.

---

## Page 4 — DISEASE INCIDENCE AND REPORTED CASES

**Purpose:** Show disease burden trends, distinguishing incidence rate from raw case counts.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ DISEASE INCIDENCE AND REPORTED CASES                     [Nav: 1 2 3 4 5 6]│
├───────────────┬────────────────────────────────────────────────────────┬─┤
│ FILTERS        │  ⚠ "Incidence Rate" and "Reported Cases" are DIFFERENT  │ │
│ ☐ Disease      │    measurements with different units — do not compare   │ │
│   (single-sel  │    directly without checking the denominator below.     │ │
│   recommended) ├────────────────────────────────────────────────────────┤ │
│ ☐ Year range   │  [Line: Median incidence rate by year, log scale]      │ │
│                │  Denominator: {dynamic label}                          │ │
│                ├────────────────────────────────────────────────────────┤ │
│                │  [Line: Total reported cases by year]                  │ │
│                ├───────────────────────┬────────────────────────────────┤ │
│                │  KPI: Data            │  [Bar: Top 15 countries by      │ │
│                │  Completeness %       │   reported cases, selected      │ │
│                │  (selected disease)   │   disease, selected years]      │ │
└───────────────┴────────────────────────────────────────────────────────┴─┘
```

- **Recommended visuals:** 1 static warning text box (not a data visual, but required — see
  purpose), 2 line charts (kept on SEPARATE visuals, never combined into one dual-axis chart, to
  avoid implying they're the same unit), 1 KPI card, 1 bar chart.
- **Fields used:** `fact_incidence_country[country_code, year, disease_code,
  denominator_standardized, incidence_rate]`, `fact_cases_country[country_code, year,
  disease_code, cases]`, `dim_disease[disease_code, disease_description]`.
- **Filters/slicers:** disease (single-select strongly recommended — see limitation), year range.
- **KPI definitions:** `Incidence Data Completeness %`.
- **Required measures:** `Average Incidence Rate`, `Total Reported Cases`, `Incidence Data
  Completeness %`, `Denominator Label (Current Filter)`.
- **Expected user interaction:** selecting a disease updates the denominator label dynamically;
  if a user selects multiple diseases at once (slicer allows multi-select), the denominator label
  measure returns the "multiple denominators" warning text rather than a misleading blended number.
- **Limitations:** per Phase 2's documented sufficiency screening, 3 diseases (YFEVER, POLIO,
  JAPENC) have <50% incidence-rate completeness — the page should display the completeness KPI
  prominently whenever one of these is selected, and could optionally show a soft warning banner
  ("This disease has limited incidence data — interpret trends with caution") when completeness
  drops below 50%, computed live from the `Incidence Data Completeness %` measure.
- **Accessibility:** log-scale line chart includes an axis label explicitly stating "log scale" to
  avoid misreading linear differences; warning text box uses both icon and text (⚠ + words), not
  icon alone.

---

## Page 5 — VACCINE INTRODUCTION AND SCHEDULE

**Purpose:** Show which vaccines are in national programs and how they're scheduled — distinct
from, and never a proxy for, actual coverage achieved.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ VACCINE INTRODUCTION AND SCHEDULE                         [Nav: 1 2 3 4 5 6]│
├───────────────┬────────────────────────────────────────────────────────┬─┤
│ FILTERS        │  ⚠ "Introduced" (this page) ≠ "Vaccinated" (Page 2) —   │ │
│ ☐ Vaccine      │    introduction is a program-status record, not a       │ │
│   description  │    coverage measurement. Schedule data covers 2019-2023 │ │
│ ☐ Year         │    only (not a historical trend).                       │ │
│ ☐ WHO Region   ├────────────────────────────────────────────────────────┤ │
│                │  [Line: Countries with vaccine introduced ('Yes'        │ │
│                │   variants), by year, top vaccines]                    │ │
│                ├───────────────────────┬────────────────────────────────┤ │
│                │  [Bar: Introduction    │  [Bar: Top 15 schedule codes   │ │
│                │   status by WHO region]│   by record frequency,         │ │
│                │                        │   2019-2023 snapshot]          │ │
│                ├────────────────────────┴────────────────────────────────┤ │
│                │  [Table: Target population distribution + missingness   │ │
│                │   for TARGETPOP/AGE_ADMINISTERED/GEOAREA]               │ │
└───────────────┴────────────────────────────────────────────────────────┴─┘
```

- **Recommended visuals:** 1 warning text box, 1 line chart, 2 bar charts, 1 table.
- **Fields used:** `fact_vaccine_introduction[country_code, year, vaccine_description,
  intro_status]`, `fact_vaccine_schedule[country_code, year, vaccine_code, schedule_rounds,
  target_pop, target_pop_description, geoarea, age_administered]`, `dim_vaccine_schedule_code`,
  `dim_country[who_region]`.
- **Filters/slicers:** vaccine description, year, WHO region.
- **KPI definitions:** `Countries With Vaccine Introduced ('Yes' variants)`, `Schedule Records —
  Missing Target Population %`.
- **Expected user interaction:** selecting a vaccine in the top-left slicer filters the
  introduction line chart and regional bar; the schedule bar/table are filtered independently by
  the (different-vocabulary) `vaccine_code` — a text note should clarify these two slicers use
  different vaccine naming systems (`vaccine_description` free text vs. `vaccine_code`), since no
  exact one-to-one crosswalk exists between them (Phase 1 finding — see `xwalk_vaccine_family` for
  the closest available concept-level bridge, optional advanced drill-through).
- **Limitations:** schedule data is a single 2019–2023 snapshot; no year-over-year schedule trend
  should be built even though a `year` field exists on `fact_vaccine_schedule` (it reflects
  multiple snapshot years of the same underlying recommendation, not program evolution over
  decades like the introduction table).
- **Accessibility:** all bars have data labels (not reliant on hover-only tooltips); target
  population table includes a "(missing)" row rather than leaving it blank/confusing.

---

## Page 6 — VACCINATION–DISEASE ASSOCIATIONS

**Purpose:** Present the 14 analyst-crosswalk-mapped correlation results, clearly labeled as
observational, non-causal findings.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ VACCINATION-DISEASE ASSOCIATIONS                          [Nav: 1 2 3 4 5 6]│
├────────────────────────────────────────────────────────────────────────────┤
│ ⚠⚠ ANALYST-DERIVED & OBSERVATIONAL ONLY — NOT A CAUSAL EFFECTIVENESS        │
│    ESTIMATE. Depends on the Phase 1 xwalk_antigen_disease crosswalk        │
│    (33/69 antigens mapped). See methodology note below every chart.        │
├───────────────┬────────────────────────────────────────────────────────┬─┤
│ FILTERS        │  [Bar: Pearson r for all 14 pairs, sorted, diverging    │ │
│ ☐ Antigen-     │   red/blue color scale centered at 0]                  │ │
│   Disease pair │                                                        │ │
│   (single-sel  ├────────────────────────────────────────────────────────┤ │
│   from the 14  │  [Scatter: coverage_raw (x) vs incidence_rate (y),      │ │
│   valid pairs  │   selected pair, one point per country-year]           │ │
│   only)        ├───────────────────────┬────────────────────────────────┤ │
│                │  KPI: N Observations  │  KPI: Pearson r | Spearman rho  │ │
│                ├────────────────────────┴────────────────────────────────┤ │
│                │  [Text box: fixed methodology/limitations caption,       │ │
│                │   same wording on every view of this page]              │ │
└───────────────┴────────────────────────────────────────────────────────┴─┘
```

- **Recommended visuals:** 1 large persistent warning banner (fixed, not filterable away), 1 bar
  chart, 1 scatter plot, 2 KPI cards, 1 fixed methodology text box.
- **Fields used:** `fact_association_correlations[antigen_code, disease_code, n_observations,
  pearson_r, spearman_rho, years_included, countries_included]`, plus for the scatter plot only,
  a drill-through to `fact_coverage_country` (WUENIC) joined at query time to
  `fact_incidence_country` for the single selected pair (this is the one visual on this page that
  needs row-level data, not just the summary table).
- **Filters/slicers:** a single-select slicer restricted to exactly the 14 valid pairs (built as a
  slicer on `fact_association_correlations[antigen_code]` + `[disease_code]` concatenated into a
  "pair_label" column in Power Query — do NOT let users select an arbitrary antigen-disease
  combination outside these 14, since no correlation was computed or validated for any other pair).
- **KPI definitions/measures:** `Selected Pair Sample Size`, `Selected Pair Pearson r`, `Selected
  Pair Spearman rho` (all defined in DAX doc Section 6).
- **Expected user interaction:** selecting a pair updates the scatter plot and both KPI cards; the
  warning banner and methodology text box are **static and do not change** regardless of
  selection — this is a deliberate design choice so the caveat is never scrollable-away or
  filterable-out.
- **Limitations (must appear verbatim in the fixed text box):** "These are Pearson and Spearman
  correlations between WUENIC coverage and disease incidence rate, computed on paired
  country-year observations (minimum 15 observations required). All 14 tested pairs show a
  negative or near-zero coefficient (higher coverage co-occurring with lower incidence). This is
  an OBSERVED ASSOCIATION, not evidence of causation — confounding factors (co-occurring public
  health interventions, healthcare system capacity, surveillance/reporting quality changes, prior
  population immunity) are not controlled for. The antigen-disease pairing itself is an
  ANALYST-DERIVED judgment call (Phase 1 `xwalk_antigen_disease`), not sourced from WHO data."
- **Accessibility:** diverging color scale on the bar chart is paired with a text data label (not
  color-only encoding of positive/negative); warning banner uses high-contrast text, minimum 12pt.

---

## Cross-Page Design Standards

- **Consistent navigation:** every page has the same top-right "[1 2 3 4 5 6]" bookmark
  navigation bar in the same position.
- **Consistent filter placement:** left-side filter pane on every page, same width, same order of
  common filters (antigen/disease → year → category/region) where applicable to that page.
- **Consistent color coding:** WUENIC = blue, ADMIN = orange, OFFICIAL = green, PAB = purple,
  HPV = pink — used identically on every page that shows a coverage-category breakdown.
- **No page uses `fact_coverage_aggregate`/`fact_incidence_aggregate`/`fact_cases_aggregate`
  together with the corresponding country-level table in the same visual** — this is checked
  explicitly in `PHASE3_VALIDATION_REPORT.md`.

# PROJECT_STATUS.md
**Project:** Vaccination Data Analysis and Visualization

## Phase Status
- **Phase 0 — COMPLETE / APPROVED** (reconnaissance; two documentation corrections applied and approved)
- **Phase 1 — COMPLETE / APPROVED** (data cleaning, standardization, crosswalks, normalized SQL database, ETL, validation, and final crosswalk structural QA — 16-table database)
- **Phase 2 — COMPLETE** (exploratory data analysis: 8 analytical datasets, 23 charts, correlation analysis, full validation)
- **Phase 3 — COMPLETE** (Power BI implementation package: 19 datasets, 10 SQL views, 6-page/34-visual dashboard specification, DAX measures, full validation — no .pbix file, as this environment cannot run Power BI Desktop; see phase3_powerbi/docs/PHASE3_IMPLEMENTATION_GUIDE.md)
- **30 assignment questions — COMPLETE** (all 30 answered in original order/wording, PDF + Markdown + CSV + audit trail; see phase4_answers/)
- **30-question PDF — COMPLETE** (`phase4_answers/30_QUESTIONS_ANSWERS.pdf`, 21 pages)
- **Final video template — NOT STARTED**

---

## Phase 1 Summary

### Project Structure Created
```
project/
├── data/
│   ├── raw/              5 source .xlsx files + PDF, checksummed, chmod 444 (read-only)
│   └── clean/
│       ├── 00_raw_snapshot/    exact parquet copies of raw Data sheets
│       ├── 01_cleaned/         footer-stripped, type-cast, flagged, country/aggregate split
│       ├── 02_dimensions/      dim_country, dim_antigen, dim_disease, dim_vaccine_schedule_code, dim_aggregate_entity
│       ├── 03_crosswalks/      xwalk_antigen_disease, xwalk_vaccine_family
│       └── 04_facts/           all 8 fact tables, SQL-load-ready
├── sql/
│   ├── schema.sql        full DDL (PK/FK/UNIQUE/CHECK/indexes)
│   └── vaccination.db    loaded SQLite database (16 tables)
├── scripts/               01_load_raw.py ... 07_validate.py (7 reproducible stages)
├── docs/                  CLEANING_TRANSFORMATION_LOG.md, DATA_DICTIONARY.md, SQL_SCHEMA.md, PHASE1_VALIDATION_REPORT.md
├── validation/            PHASE1_VALIDATION_RESULTS.json (machine-generated)
└── logs/                  one JSON log per pipeline stage
```

### Files Created
- 7 Python ETL scripts (`scripts/01_load_raw.py` through `scripts/07_validate.py`, updated during
  final QA to add `dim_vaccine_concept` construction and expanded validation checks)
- `sql/schema.sql` (DDL, now 16 tables including `dim_vaccine_concept`) and `sql/vaccination.db`
  (loaded SQLite database)
- `docs/CLEANING_TRANSFORMATION_LOG.md` — all 18 cleaning rules, generated from execution logs
- `docs/DATA_DICTIONARY.md` — every table/column documented, analyst-derived fields explicitly marked
- `docs/SQL_SCHEMA.md` — ER overview, normalization rationale, PK/FK/index documentation
- `docs/PHASE1_VALIDATION_REPORT.md` — full validation results, generated from live query output
- `validation/PHASE1_VALIDATION_RESULTS.json` — raw machine-readable validation output
- 6 JSON stage logs in `logs/`

### SQL Database: `sql/vaccination.db` (SQLite, 16 tables)
**Dimensions (6):** dim_country (214), dim_antigen (69), dim_disease (13),
dim_vaccine_schedule_code (86), dim_aggregate_entity (31), dim_vaccine_concept (23, added in Phase 1 final QA)
**Crosswalks (2, analyst-derived):** xwalk_antigen_disease (73 rows, `UNIQUE(antigen_code, disease_code)`),
xwalk_vaccine_family (208 rows, `vaccine_concept` FK-enforced against dim_vaccine_concept)
**Country-level facts (5):** fact_coverage (381,041), fact_incidence (82,054), fact_cases (82,054),
fact_vaccine_introduction (138,320), fact_vaccine_schedule (8,052)
**Aggregate-level facts (3):** fact_coverage_aggregate (18,817), fact_incidence_aggregate (2,891),
fact_cases_aggregate (2,815)

### Cleaning Rules Applied (18 total — see CLEANING_TRANSFORMATION_LOG.md)
Footer-row removal (5 files) · YEAR/SCHEDULEROUNDS float→integer casting · text trimming ·
denominator normalization (308 rows) · coverage >100%/>500% flagging (5,097 rows flagged, 0
deleted, 0 clipped) · negative-dose sentinel/error flagging (8 rows) · NAME-null investigation
(resolved: all 1,274 nulls are aggregate rows, 0 at country level) · country/aggregate separation
(3 tables split into 6).

### Validation Results — ALL PASS
Row counts (11/11) · primary keys (13/13 tables, 0 duplicates) · foreign keys (13/13
relationships, 0 orphans) · duplicates (0 on true keys; old schedule key reconciled exactly to
Phase 0's 1,319-row figure) · country-code validity (214/214 valid ISO-3) · year validity (no
nulls, no out-of-range values) · numeric sanity (0 negative values remaining in cleaned fields,
outliers correctly flagged) · aggregate isolation (country facts structurally cannot hold
aggregate rows; aggregate facts contain only the 7 documented group types) · crosswalk coverage
(antigen→disease: 33/69 mapped with documented reasons for the rest; vaccine-family: 100% of
coverage antigens, 73/86 schedule codes, 20/21 introduction descriptions mapped) · ETL
idempotency (identical row counts across two consecutive full rebuilds).

### Issues Found and Fixed During Phase 1
1. A bool/NaN type-conversion bug during SQL load (American Samoa's missing WHO-region conflict
   flag caused a crash) — fixed by using nullable Int64 conversion.
2. A regex bug in the vaccine-family crosswalk ("tetanus tox" was too narrow a pattern, missing
   "tetanus-containing" and "neonatal tetanus" phrasing) — fixed; verified all 4 affected antigens
   (PAB, TTCV4, TTCV5, TTCV6) now map correctly.
3. **(Final QA pass)** `xwalk_vaccine_family.vaccine_concept` was a bare, repeated text value with
   no declared referential integrity — it worked as a join key by convention, not by enforced
   design. Fixed by adding `dim_vaccine_concept` as a proper dimension and making `vaccine_concept`
   an enforced foreign key. Additionally, `xwalk_antigen_disease` had no uniqueness constraint at
   all; added `UNIQUE(antigen_code, disease_code)` (not `antigen_code` alone, since 2 antigens
   legitimately map to multiple diseases). Both fixes were additive only — all 208 + 73 existing
   crosswalk rows, confidence levels, rationales, and unmapped records were preserved unchanged.

Both issues were caught and resolved before declaring Phase 1 complete, not left as open defects.

### Known Limitations
- `dim_country.who_region` is NULL for American Samoa (ASM) — absent from both source tables
  used to derive WHO region; not fabricated.
- `xwalk_antigen_disease` maps 47.8% of antigens; the remainder target diseases genuinely absent
  from the 13-disease incidence/cases list (TB, Hepatitis B, pneumococcal disease, rotavirus,
  HPV-associated disease, influenza, malaria) — a data-availability gap, not an analytical gap.
- `xwalk_vaccine_family` leaves 13 rare/travel schedule vaccine codes and 1 introduction
  description unmapped (no concept keyword defined for CCHF, Ebola, Hepatitis A, HFRS,
  Leptospirosis, Mpox, TBE, Tularemia, Zoster).
- All Phase 0 data-availability limitations remain unchanged (no gender, education, urban/rural,
  population density, seasonal/monthly granularity, vaccine supply, within-country socioeconomic
  grouping, or delivery-strategy data exists anywhere in the source).
- Both crosswalks are analyst-derived and must continue to be clearly labeled as such in any
  future phase that uses them.

## What Phase 2 Should Do Next
_(superseded — Phase 2 is now complete; see summary below)_

---

## Phase 2 Summary

### Files Created
- 10 Python scripts (`phase2_eda/scripts/01_verify_phase1.py` through `10_validate_phase2.py`)
- 8 analytical datasets in `phase2_eda/outputs/analytical_datasets/` (381,041-row
  `country_year_coverage.csv` down to the derived `vaccination_disease_association.csv`), each
  with a documented join/filter/exclusion "dataset card"
- 41 result tables in `phase2_eda/outputs/tables/`
- 4 files in `phase2_eda/outputs/statistical_results/` (profiling, descriptive stats,
  missingness, category completeness)
- **23 charts** in `phase2_eda/outputs/charts/` (exceeds the 15-chart requirement)
- `phase2_eda/reports/PHASE2_EDA_REPORT.md` — the full EDA report (19 sections)
- `phase2_eda/reports/PHASE2_EDA_VALIDATION_REPORT.md` — validation results
- `phase2_eda/reports/CHART_INVENTORY.md` — chart-by-chart documentation
- `phase2_eda/reports/EDA_SUPPORT_MATERIALS.md` — reference material for an external EDA notebook
- `phase2_eda/PHASE2_EDA_RESULTS.json` — machine-readable validation output
- `phase2_eda/README.md` — Phase 2 reproducibility guide
- 12 JSON execution logs in `phase2_eda/logs/`

### Analytical Areas Completed
Vaccination coverage analysis (trends, regional/country comparison, dose-sequence drop-off,
category comparison, >100% handling via Phase 1 quality flags) · disease incidence analysis
(trends, sufficiency screening, extremes, missingness heatmap) · reported-cases analysis (trends,
country comparison, incidence-vs-cases overlap check) · vaccination-disease association analysis
(14 crosswalk-mapped antigen-disease pairs, Pearson + Spearman correlation, all n≥15) · vaccine
introduction analysis (country/region/vaccine trends, status-value handling) · vaccine schedule
analysis (code frequency, target-population distribution, missingness, concept mapping) ·
statistical/comparative analysis (year-over-year change, coefficient of variation, correlation
matrix).

### Validation Results — ALL PASS
All 8 analytical datasets present and correctly built · zero duplicates on every documented
analytical key · country-level and aggregate-level data structurally separated (verified by
column-presence check, not just convention) · all join row counts documented (8/8 dataset cards
complete) · missing values confirmed never zero-filled (null counts >0 in every checked field) ·
zero unsupported variables introduced (checked against the Phase 0/1 absent-variable list) · all
23 charts confirmed present on disk · reproducibility rerun test passed (byte-identical output) ·
raw source files and Phase 1 database confirmed unmodified (checksum match against original
uploads).

### Issues Found and Fixed During Phase 2
1. `intro_status` values like "Yes (R)", "Yes (P)", "Yes (A)", "Yes (O)", "Yes (D)" were not
   caught by an initial exact-match filter — fixed with a prefix match, while deliberately keeping
   "High risk area" and "ND" as distinct, uncounted statuses (not silently merged into "Yes").
2. A NaN-to-string conversion bug in a schedule target-population chart — fixed by explicit
   `(missing)` labeling rather than allowing a raw float NaN into a categorical axis.

Both were caught and fixed during script development, before the validation suite was run.

### Known Limitations (Phase 2, in addition to all Phase 0/1 limitations which remain unchanged)
- `MCV2X2` antigen has zero country-level coverage rows (aggregate-only) — a genuine data
  characteristic, documented, not fabricated around.
- 3 diseases (YFEVER, POLIO, JAPENC) have <50% incidence-rate completeness and were excluded from
  the incidence trend chart specifically to avoid presenting an unreliable trend line.
- The vaccination-disease association analysis and the schedule concept-mapping analysis both
  depend on Phase 1's analyst-derived crosswalks — every such result is explicitly labeled.
- All correlation results describe observed association only; no causal vaccine-effectiveness
  claim is made anywhere in Phase 2 output.

## What Phase 3 Should Do Next
_(superseded — Phase 3 is now complete; see summary below)_

---

## Phase 3 Summary

### Files Created
- 2 Python scripts (`phase3_powerbi/scripts/01_build_powerbi_datasets.py`,
  `02_visual_inventory_and_validate.py`)
- **19 Power BI-ready CSV datasets** in `phase3_powerbi/data/` (star-schema shaped: 8 dimensions,
  2 analyst-derived crosswalks, 8 fact tables, 1 pre-computed correlation summary table)
- `phase3_powerbi/data/vaccination_powerbi_views.db` — an isolated COPY of the Phase 1 database
  with 10 additional read-only SQL views (the approved original `sql/vaccination.db` is
  byte-identical before/after Phase 3, verified by MD5 checksum)
- `phase3_powerbi/sql/views.sql` — the 10 view definitions
- `phase3_powerbi/docs/PHASE3_POWERBI_REPORT_SPECIFICATION.md` — 6 dashboard pages, ASCII
  wireframes, visual-by-visual specifications
- `phase3_powerbi/docs/PHASE3_DATA_MODEL.md` — star schema, relationships, date-table rationale
- `phase3_powerbi/docs/PHASE3_DAX_MEASURES.md` — 20+ DAX measures with rationale and limitations
- `phase3_powerbi/docs/PHASE3_IMPLEMENTATION_GUIDE.md` — step-by-step Power BI Desktop build guide
  and the explicit "no .pbix" limitation statement
- `phase3_powerbi/docs/PHASE3_VALIDATION_REPORT.md` — full validation results
- `phase3_powerbi/docs/PHASE3_VISUAL_INVENTORY.csv` — machine-readable inventory of all 34 visuals
- `phase3_powerbi/logs/01_build_powerbi_datasets.json` — dataset cards for all 19 datasets
- `phase3_powerbi/PHASE3_VALIDATION_RESULTS.json` — machine-readable validation output

### Dashboard Pages Designed (6, matching all required coverage areas)
1. Executive Overview · 2. Vaccination Coverage · 3. Regional and Country Comparison ·
4. Disease Incidence and Reported Cases · 5. Vaccine Introduction and Schedule ·
6. Vaccination-Disease Associations — **34 visuals total**, every one backed by a verified,
existing field in a verified, existing table (0 field-reference failures on validation).

### DAX Measures Created
20+ measures across 6 categories (KPIs, coverage, regional comparison, disease, introduction/
schedule, association), including a documented disconnected-table pattern for dose-sequence
drop-off comparison and an explicit list of measures deliberately NOT created (no causal
"effectiveness" measure, no population-weighted average, no blended country+aggregate average).

### Validation Results — ALL PASS
All referenced tables/fields exist · all 19 dataset cards documented · zero unsupported variables
introduced · missing values confirmed never zero-filled · country/aggregate structurally
separated (6/6 tables) · all 17 countable tables match Phase 1/2 validated row counts exactly ·
original Phase 1 database confirmed unmodified (checksum match) · SQL views confirmed isolated to
the copy database only (0 views in the original).

### What Can Be Imported Directly Into Power BI
All 19 CSVs via Get Data > Text/CSV (no manual cleaning needed), OR the 10 SQL views + 6
dimension/crosswalk tables via an ODBC connection to `vaccination_powerbi_views.db` (requires a
SQLite ODBC driver, not bundled with Power BI Desktop).

### What Must Still Be Done Manually in Power BI Desktop
This environment cannot run Power BI Desktop (Windows-only application) — no `.pbix` file exists
or is claimed to exist. A human must: import the data, build the composite-key relationship for
the 3 aggregate fact tables (Power Query custom column, documented step-by-step), create the
disconnected `DosePairSelector` table, enter all DAX measures, build all 34 visuals per the page
specifications, set up bookmark navigation, apply formatting (especially the coverage-percentage
custom format), add the 3 required static warning/methodology text boxes, and test ISO-3 map
geocoding for small territories. Every one of these steps is specified in exact, actionable detail
in `PHASE3_IMPLEMENTATION_GUIDE.md`.

### Known Limitations
- No `.pbix` file — stated explicitly, not glossed over (see Implementation Guide's "Power BI File
  Limitation" section).
- The composite `(group_type, entity_code)` key for aggregate tables requires a manual Power Query
  step in Power BI Desktop (single-column relationships are Power BI's native limitation).
- Map geocoding accuracy for small territories (e.g. Aruba, Anguilla) should be spot-checked by a
  human in Power BI Desktop before publishing.
- All Phase 0/1/2 data limitations remain unchanged and apply identically to every Phase 3 dataset
  (no gender/education/urban-rural/density/seasonal data; analyst-derived crosswalks explicitly
  labeled; no causal vaccine-effectiveness claim anywhere in the specification).

## What Phase 4 Should Do Next
_(superseded — Phase 4's 30-question deliverable is now complete; see summary below)_

---

## Phase 4 Summary

### Files Created
- `phase4_answers/30_QUESTIONS_ANSWERS.md` — all 30 questions answered in original order/wording,
  with methodology, tables, and limitations for every answer
- `phase4_answers/30_QUESTIONS_ANSWERS.pdf` — 21-page professionally formatted PDF (title page,
  table of contents, section headings, tables, page numbers), built via pandoc + xelatex
- `phase4_answers/30_QUESTIONS_VALIDATION_REPORT.md` — confirms all 30 answered, reconciles
  classifications with Phase 0, documents 3 corrections made during development
- `phase4_answers/phase4_all_30_answers.csv` — machine-readable answer summary
- `phase4_answers/PHASE4_CALCULATION_AUDIT.csv` — question-by-question data source, calculation,
  result, classification, and limitations
- `phase4_answers/scripts/01_compute_answers_data.py` — reproducible computation script
- 15 supporting-output CSV files in `phase4_answers/supporting_outputs/tables/`

### Feasibility Classification (reconciled exactly with Phase 0, unchanged)
A=4, B=8, C=9, D=9 (30 total). No classification was silently altered.

### Quality Control Performed
- Exactly 30 question headings confirmed in `30_QUESTIONS_ANSWERS.md`, correct order, no
  duplicates/gaps (Easy Q9's duplicate wording is from the **original source PDF**, not an error
  introduced here — answered by cross-reference to Easy Q1).
- Every numeric result traced to a specific SQL query or existing Phase 2 output file.
- 3 genuine issues found and corrected during development: a booster-antigen query that
  targeted the wrong coverage category (WUENIC has zero rows for these antigens — now a
  documented finding), a `numpy.int64`/SQLite parameter-binding bug, and one interpretive
  correction where initial text was rewritten to match actual computed data (Scenario Q2's case
  trend spiked rather than declined smoothly).
- No causal vaccine-effectiveness language found on manual review.
- No missing value zero-filled; no country/aggregate mixing in any query.

### Part B — dim_country.csv Recovery (verification, no regeneration needed)
`phase3_powerbi/data/dim_country.csv` was located intact at its expected path: 214 rows, 11
columns, 0 duplicate `country_code` keys, 0 null `country_code` values, 1 null `who_region`
(American Samoa — the same, expected Phase 1 finding). Matches the Phase 1 `dim_country` table
exactly. No regeneration was necessary. All 19 Phase 3 Power BI datasets confirmed present.

### Known Limitations
- 9 questions remain genuinely unanswerable (D) — the required variable does not exist anywhere
  in the source data (gender, education, urban/rural, population density, sub-annual date
  granularity, influenza incidence, delivery-strategy data, within-country socioeconomic data).
- 9 questions are partially supported (C) — each answer states exactly what is and isn't
  supported and why.
- Scenario 3 and 6's trend extrapolations are explicitly labeled as rough, non-authoritative
  projections (R²=0.043 and R²=0.67 respectively), not demand forecasts or official WHO targets.

## What Phase 5 Should Do Next
Phase 5 (not started) should proceed only once the human-built Power BI `.pbix` report from Phase
3 is complete: create the final video template, and any remaining project presentation/conclusion
materials. No causal effectiveness language should be introduced at that stage either.





# DATA_DICTIONARY.md
**Project:** Vaccination Data Analysis and Visualization — Phase 1
**Database:** `sql/vaccination.db` (SQLite)

This dictionary documents every table and column in the Phase 1 database. **Analyst-derived
fields and tables are explicitly marked "DERIVED"** — they are not present in the WHO source
data and represent judgment calls made during this project, not sourced fact. Everything else
is a direct, type-cast, or flagged representation of a real source field.

---

## Dimensions

### `dim_country`
Canonical country list = union of country-level codes across all 5 source tables (LEFT JOIN
enrichment; never an inner join, so no country is dropped for lacking introduction/schedule data).

| Column | Type | Source | Definition | Nullable | Key | Notes |
|---|---|---|---|---|---|---|
| country_code | TEXT | coverage/incidence/cases.CODE, intro/schedule.ISO_3_CODE | ISO-3166-1 alpha-3 code | No | PK | |
| country_name | TEXT | coverage/incidence/cases.NAME (preferred), falls back to intro/schedule.COUNTRYNAME | Country display name | Yes | | 0 nulls in final dim (all resolved via fallback) |
| who_region | TEXT | **DERIVED** — built from intro.WHO_REGION (primary) with schedule.WHO_REGION as fallback | WHO region code (AFRO/AMRO/EMRO/EURO/SEARO/WPRO) | Yes | | 1 country (American Samoa, ASM) has no source data in either table, so this is NULL — not fabricated |
| who_region_source_intro | TEXT | intro.WHO_REGION | Raw value from introduction table, for traceability | Yes | | |
| who_region_source_schedule | TEXT | schedule.WHO_REGION | Raw value from schedule table, for traceability | Yes | | |
| who_region_conflict | INTEGER (0/1) | **DERIVED** | 1 if intro and schedule disagreed on this country's region | Yes | | 0 conflicts found in this dataset; NULL for ASM (no source to conflict) |
| in_coverage / in_incidence / in_cases / in_introduction / in_schedule | INTEGER (0/1) | **DERIVED** | Presence flag per source table | No | | Transparency aid — shows exactly why join counts differ across tables |

### `dim_antigen`
All 69 antigen codes retained, including dose-sequence and booster variants.

| Column | Type | Source | Definition | Nullable | Key |
|---|---|---|---|---|---|
| antigen_code | TEXT | coverage.ANTIGEN | Antigen/vaccine-dose identifier (e.g. `DTPCV1`, `MCV2`) | No | PK |
| antigen_description | TEXT | coverage.ANTIGEN_DESCRIPTION | Full description | Yes | |

### `dim_disease`
All 13 disease codes shared by incidence and cases tables.

| Column | Type | Source | Definition | Nullable | Key |
|---|---|---|---|---|---|
| disease_code | TEXT | incidence/cases.DISEASE | Disease identifier | No | PK |
| disease_description | TEXT | incidence/cases.DISEASE_DESCRIPTION | Full description | Yes | |

### `dim_vaccine_schedule_code`
All 86 vaccine codes from the schedule table.

| Column | Type | Source | Definition | Nullable | Key |
|---|---|---|---|---|---|
| vaccine_code | TEXT | schedule.VACCINECODE | Vaccine/formulation identifier | No | PK |
| vaccine_description | TEXT | schedule.VACCINE_DESCRIPTION | Full description | Yes | |

### `dim_aggregate_entity`
Lookup of the non-country `GROUP`/`CODE`/`NAME` combinations used by the `*_aggregate` fact
tables (regional, income-group, development-status, and global rollups).

| Column | Type | Source | Definition | Nullable | Key |
|---|---|---|---|---|---|
| group_type | TEXT | coverage/incidence/cases.GROUP | Aggregate category (WHO_REGIONS, UNICEF_REGIONS, WB_LONG, WB_SHORT, DEVELOPMENT_STATUS, GAVI_PHASE5, GLOBAL) | No | PK (composite) |
| entity_code | TEXT | coverage/incidence/cases.CODE | Entity identifier within that group type | No | PK (composite) |
| entity_name | TEXT | coverage/incidence/cases.NAME | Entity display name | Yes | |
| source_table | TEXT | **DERIVED** | Which source table this entity was first observed in | Yes | |

### `dim_vaccine_concept` **(added in Phase 1 final QA)**
A proper dimension for the vaccine "concept" labels used to bridge the three incompatible
vaccine vocabularies (coverage `ANTIGEN`, schedule `VACCINECODE`, introduction `DESCRIPTION`).
Previously `xwalk_vaccine_family.vaccine_concept` was a bare, repeated text value joined only
implicitly (an unenforced text self-join); it is now an **enforced foreign key** into this table.

| Column | Type | Definition | Nullable | Key |
|---|---|---|---|---|
| vaccine_concept | TEXT | Concept name (e.g. "Polio (IPV/OPV)", "Measles-Mumps-Rubella") — **DERIVED**, one of 23 documented concepts | No | PK |
| keyword_patterns | TEXT | **DERIVED** — the exact regex keyword(s) used to classify a code into this concept, stored for full auditability | Yes | |

---

## Crosswalks — **ANALYST-DERIVED METADATA, NOT SOURCE FACT**

Neither of these tables exists in the WHO source data. Both are built by explicit, documented,
programmatic rules (not one-off manual guesses) and are fully reviewable. Any analysis that
depends on these tables inherits their derived, judgment-based nature — this must be disclosed
whenever they are used in later phases.

### `xwalk_antigen_disease`
Links coverage `ANTIGEN` codes to incidence/cases `DISEASE` codes where a specific, defensible
clinical relationship exists. **33 of 69 antigens (47.8%) are mapped; 36 are explicitly left
unmapped** because their target disease (e.g. TB, Hepatitis B, pneumococcal disease, rotavirus,
HPV-associated disease, influenza, malaria) is not present in the 13-disease incidence/cases
list — this is a data-availability gap, not an oversight, and is documented per-antigen.

**Key structure (added/verified in Phase 1 final QA):** `UNIQUE (antigen_code, disease_code)`.
`antigen_code` alone is **intentionally not unique** — 2 antigens (`DTPCV1`, `DTPCV3`) legitimately
map to 3 diseases each (diphtheria, tetanus, pertussis, since DTP is a combination vaccine), so
each antigen-disease pair is its own row. The composite pair is what must be unique, and this is
now enforced structurally.

| Column | Type | Definition | Nullable |
|---|---|---|---|
| antigen_code | TEXT | FK → dim_antigen | No |
| disease_code | TEXT | FK → dim_disease; NULL when mapping_status='unmapped' | Yes |
| mapping_status | TEXT | 'mapped' or 'unmapped' | No |
| confidence | TEXT | 'high' / 'medium' / 'n/a' (combination vaccines like DTP get 'medium' since one antigen dose implies 3 diseases) | Yes |
| rationale | TEXT | Human-readable justification for the mapping (or the specific reason it was left unmapped) | Yes |
| notes | TEXT | Standing disclosure that this is analyst-derived, not source data | Yes |

### `xwalk_vaccine_family`
Links coverage `ANTIGEN`, schedule `VACCINECODE`, and introduction `DESCRIPTION` — three tables
that share **no common identifier** in the source data — via keyword/regex matching against each
code's own description text, against a documented list of 23 vaccine "concepts" (e.g.
"Measles-Mumps-Rubella", "Diphtheria-Tetanus-Pertussis", "Polio (IPV/OPV)"), stored in the
**`dim_vaccine_concept`** dimension table. A code matching more than one concept (a genuine
combination vaccine, e.g. a DTaP-Hib-IPV formulation) gets one row per matched concept, flagged
`combination_component`, rather than being forced into a single misleading link.

**Structural fix applied in Phase 1 final QA:** `vaccine_concept` was originally a bare, repeated
text value with no declared referential integrity — joining coverage to schedule required an
unenforced free-text self-join (`WHERE a.vaccine_concept = b.vaccine_concept`) with no protection
against typos or drift between rows. It is now a **foreign key into `dim_vaccine_concept`**,
enforced by SQLite's `PRAGMA foreign_keys=ON` at load time (verified: loading a row with an
undefined concept value fails). **How to reliably join the three vocabularies today:**

```sql
-- Antigens and their possible schedule-code equivalents, via the shared, FK-enforced concept:
SELECT cov.source_code AS antigen_code, sch.source_code AS schedule_vaccine_code, cov.vaccine_concept
FROM xwalk_vaccine_family cov
JOIN xwalk_vaccine_family sch ON cov.vaccine_concept = sch.vaccine_concept
WHERE cov.source_table = 'coverage_antigen' AND sch.source_table = 'schedule_vaccinecode';
```
This reaches all 69/69 coverage antigens (verified in Phase 1 validation) and is now backed by an
enforced FK rather than an implicit text match. Note this is still a **concept-level** bridge —
it groups codes by shared vaccine family, not a precise one-to-one equivalence — because a true
1:1 mapping does not exist for combination vaccines in the source vocabularies.

| Column | Type | Definition | Nullable |
|---|---|---|---|
| vaccine_family_xwalk_id | INTEGER | Surrogate key | No (PK) |
| source_table | TEXT | 'coverage_antigen' / 'schedule_vaccinecode' / 'introduction_description' | No |
| source_code | TEXT | The antigen code / vaccine code / vaccine description string being classified | No |
| source_description | TEXT | The description text the keyword match was run against | Yes |
| vaccine_concept | TEXT | FK → dim_vaccine_concept; NULL if unmapped | Yes |
| mapping_status | TEXT | 'mapped' (single concept) / 'combination_component' (multiple concepts) / 'unmapped' (no keyword match) | No |
| confidence | TEXT | 'high' (single match) / 'medium' (combination) / 'n/a' (unmapped) | Yes |
| rationale | TEXT | Which keyword(s) matched, or why nothing matched | Yes |
| notes | TEXT | Standing disclosure that this is analyst-derived (keyword-based), not source data | Yes |

**Coverage:** all 69 coverage antigens matched at least one concept (100%); 73/86 schedule
vaccine codes matched (13 unmapped — rare/travel vaccines like CCHF, Ebola, Hepatitis A,
Leptospirosis, Mpox, TBE, Tularemia, Zoster, for which no concept was defined, left transparently
unmapped rather than guessed); 20/21 introduction vaccine descriptions matched (Hepatitis A
unmapped, same reason). All three source-code populations (69/86/21) are confirmed **fully
preserved** in the crosswalk table — every code appears at least once, whether mapped or not.

---

## Country-Level Fact Tables

### `fact_coverage`
Source: `coverage-data.xlsx`, rows where `GROUP='COUNTRIES'`.

| Column | Type | Source | Definition | Nullable | Notes |
|---|---|---|---|---|---|
| coverage_id | INTEGER | **DERIVED** | Surrogate PK | No | |
| country_code | TEXT | CODE | FK → dim_country | No | |
| year | INTEGER | YEAR (cast from float) | Calendar year | No | |
| antigen_code | TEXT | ANTIGEN | FK → dim_antigen | No | |
| coverage_category | TEXT | COVERAGE_CATEGORY | WUENIC/PAB/OFFICIAL/ADMIN/HPV | No | All 5 categories retained, none collapsed |
| coverage_category_description | TEXT | COVERAGE_CATEGORY_DESCRIPTION | Full description | Yes | |
| target_number | REAL | TARGET_NUMBER | Target population count | Yes | 84.2% NULL at country level (source limitation, never fabricated) |
| doses_raw | REAL | DOSES | Original dose count, **including negative sentinel/error values, untouched** | Yes | |
| doses_clean | REAL | **DERIVED** from DOSES | Analytical dose count; NULL where doses_raw is the -3333 sentinel or the one implausible extreme negative | Yes | Never coerced to 0 |
| doses_quality_flag | TEXT | **DERIVED** | 'missing' / 'normal' / 'sentinel_not_reported' / 'implausible_negative' | No | |
| coverage_raw | REAL | COVERAGE | Original coverage %, **unclipped, may exceed 100** | Yes | |
| coverage_quality_flag | TEXT | **DERIVED** | 'missing' / 'normal' (≤100) / 'above_100_moderate' (100–500) / 'extreme_outlier' (>500) | No | |
| coverage_analytical_exclude | INTEGER (0/1) | **DERIVED** | 1 only when coverage_quality_flag='extreme_outlier' (9 rows) | No | Row retained regardless; this only flags analytical exclusion |

**Unique constraint:** (country_code, year, antigen_code, coverage_category) — verified 0 duplicates.

### `fact_coverage_aggregate`
Same structure as `fact_coverage` but for `GROUP != 'COUNTRIES'` rows, keyed by
(group_type, entity_code) → `dim_aggregate_entity` instead of country_code → `dim_country`.
**Never joined into country-level analysis.**

### `fact_incidence`
Source: `incidence-rate-data.xlsx`, `GROUP='COUNTRIES'`.

| Column | Type | Source | Definition | Nullable |
|---|---|---|---|---|
| incidence_id | INTEGER | **DERIVED** | Surrogate PK | No |
| country_code | TEXT | CODE | FK → dim_country | No |
| year | INTEGER | YEAR | Calendar year | No |
| disease_code | TEXT | DISEASE | FK → dim_disease | No |
| denominator_raw | TEXT | DENOMINATOR | Original reporting-basis text, unmodified | Yes |
| denominator_standardized | TEXT | **DERIVED** from DENOMINATOR | Comma-formatting normalized (e.g. "per 1000 live births" → "per 1,000 live births") | Yes |
| incidence_rate | REAL | INCIDENCE_RATE | Cases per denominator unit | Yes | 28.2% NULL at country level, never fabricated as 0 |

**Unique constraint:** (country_code, year, disease_code) — verified 0 duplicates.

### `fact_incidence_aggregate`
Same structure, `GROUP != 'COUNTRIES'` rows.

### `fact_cases`
Source: `reported-cases-data.xlsx`, `GROUP='COUNTRIES'`.

| Column | Type | Source | Definition | Nullable |
|---|---|---|---|---|
| cases_id | INTEGER | **DERIVED** | Surrogate PK | No |
| country_code | TEXT | CODE | FK → dim_country | No |
| year | INTEGER | YEAR | Calendar year | No |
| disease_code | TEXT | DISEASE | FK → dim_disease | No |
| cases | REAL | CASES | Reported case count | Yes | 23.6% NULL at country level, never fabricated as 0 |

**Unique constraint:** (country_code, year, disease_code) — verified 0 duplicates.

### `fact_cases_aggregate`
Same structure, `GROUP != 'COUNTRIES'` rows.

### `fact_vaccine_introduction`
Source: `vaccine-introduction-data.xlsx` (country-only table, no aggregate split needed).

| Column | Type | Source | Definition | Nullable |
|---|---|---|---|---|
| introduction_id | INTEGER | **DERIVED** | Surrogate PK | No |
| country_code | TEXT | ISO_3_CODE | FK → dim_country | No |
| year | INTEGER | YEAR | Calendar year (source range 1940–2023) | No |
| vaccine_description | TEXT | DESCRIPTION | Vaccine family name (free text) | No |
| intro_status | TEXT | INTRO | Introduction status as sourced — **not reinterpreted as a "campaign"** | Yes |
| who_region_raw | TEXT | WHO_REGION | Raw WHO region as sourced, kept alongside dim_country.who_region for traceability | Yes |

**Unique constraint:** (country_code, year, vaccine_description) — verified 0 duplicates.

### `fact_vaccine_schedule`
Source: `vaccine-schedule-data.xlsx` (country-only, 2019–2023 snapshot).

| Column | Type | Source | Definition | Nullable |
|---|---|---|---|---|
| schedule_id | INTEGER | **DERIVED** | Surrogate PK | No |
| country_code | TEXT | ISO_3_CODE | FK → dim_country | No |
| year | INTEGER | YEAR | Calendar year | No |
| vaccine_code | TEXT | VACCINECODE | FK → dim_vaccine_schedule_code | No |
| schedule_rounds | INTEGER | SCHEDULEROUNDS (cast from float) | Dose/round sequence number | No |
| target_pop | TEXT | TARGETPOP | Target population segment (part of the composite key — see below) | Yes | 52.9% NULL, preserved |
| target_pop_description | TEXT | TARGETPOP_DESCRIPTION | Full description of target population | Yes |
| geoarea | TEXT | GEOAREA | NATIONAL / SUBNATIONAL | Yes |
| age_administered | TEXT | AGEADMINISTERED | Age/timing of dose | Yes |
| source_comment | TEXT | SOURCECOMMENT | Free-text notes | Yes |
| who_region_raw | TEXT | WHO_REGION | Raw WHO region as sourced | Yes |

**Unique constraint:** (country_code, year, vaccine_code, schedule_rounds, target_pop) — the
Phase-0-verified composite key. **Using the key without `target_pop` produces 898 duplicate
groups / 1,319 extra rows** (confirmed identically in Phase 1 validation) because a single
vaccine/round can target multiple distinct populations in the same country-year.

---

## Notes on What Was Deliberately NOT Added

Per the approved Phase 0 scope, this database contains **no fabricated fields**. The following
remain absent, exactly as found in the source: gender/sex, education level, urban/rural
classification, population density, month/seasonal date granularity (only annual `year` exists),
vaccine availability/supply, within-country socioeconomic grouping, vaccination delivery
strategy, and general population demographic breakdowns. No campaign start/end dates were
invented — `fact_vaccine_introduction.intro_status` is preserved exactly as sourced and is not
reinterpreted as a campaign event.

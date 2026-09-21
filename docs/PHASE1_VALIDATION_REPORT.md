# PHASE1_VALIDATION_REPORT.md
**Project:** Vaccination Data Analysis and Visualization — Phase 1
**Generated from:** `validation/PHASE1_VALIDATION_RESULTS.json`, produced by executing
`scripts/07_validate.py` against the live SQLite database (`sql/vaccination.db`). Every number
below is a real query result, not an estimate.

**Overall Phase 1 validation status: ✅ PASS** (all 10 pass/fail categories passed; the 2
informational categories — null statistics and referential-integrity summary — contain no
failure conditions, only recorded statistics.)

---

## 1. Input Datasets

| File | Rows loaded (incl. footer) |
|---|---|
| coverage-data.xlsx | 399,859 |
| incidence-rate-data.xlsx | 84,946 |
| reported-cases-data.xlsx | 84,870 |
| vaccine-introduction-data.xlsx | 138,321 |
| vaccine-schedule-data.xlsx | 8,053 |

Raw files verified byte-identical to the original uploads (MD5 checksum match) and locked
read-only (`chmod 444`) in `data/raw/` before any processing began.

## 2. Original Real-Data Row Counts (post footer-removal, Phase 0 expectation)

Coverage: 399,858 · Incidence: 84,945 · Cases: 84,869 · Introduction: 138,320 · Schedule: 8,052
— **all confirmed exactly** after footer removal in stage 02 (see CLEANING_TRANSFORMATION_LOG.md).

## 3. Cleaned / Loaded Row Counts (Section A — Row Counts)

| Check | Actual | Expected | Result |
|---|---|---|---|
| coverage_country | 381,041 | 381,041 | ✅ PASS |
| coverage_aggregate | 18,817 | 18,817 | ✅ PASS |
| coverage_total | 399,858 | 399,858 | ✅ PASS |
| incidence_country | 82,054 | 82,054 | ✅ PASS |
| incidence_aggregate | 2,891 | 2,891 | ✅ PASS |
| incidence_total | 84,945 | 84,945 | ✅ PASS |
| cases_country | 82,054 | 82,054 | ✅ PASS |
| cases_aggregate | 2,815 | 2,815 | ✅ PASS |
| cases_total | 84,869 | 84,869 | ✅ PASS |
| vaccine_introduction | 138,320 | 138,320 | ✅ PASS |
| vaccine_schedule | 8,052 | 8,052 | ✅ PASS |

**Result: 11/11 PASS.**

## 4. Country vs. Aggregate Counts (Section I — Aggregate Isolation)

- `fact_coverage`, `fact_incidence`, `fact_cases` have **no `group_type`/`GROUP` column at all** —
  structurally incapable of holding an aggregate row (verified via `PRAGMA table_info`).
- `fact_coverage_aggregate`, `fact_incidence_aggregate`, `fact_cases_aggregate` contain only the
  7 documented aggregate group types (`WHO_REGIONS`, `UNICEF_REGIONS`, `WB_LONG`, `WB_SHORT`,
  `DEVELOPMENT_STATUS`, `GAVI_PHASE5`, `GLOBAL`) — **zero unexpected group types found.**

**Result: ✅ PASS.**

## 5. Null Statistics (Section H — informational, no pass/fail)

| Field | Total rows | Null rows | Null % |
|---|---|---|---|
| fact_coverage.target_number | 381,041 | 320,828 | 84.2% |
| fact_coverage.doses_raw | 381,041 | 320,481 | 84.1% |
| fact_coverage.coverage_raw | 381,041 | 169,331 | 44.4% |
| fact_incidence.incidence_rate | 82,054 | 23,145 | 28.2% |
| fact_cases.cases | 82,054 | 19,399 | 23.6% |
| fact_vaccine_schedule.target_pop | 8,052 | 4,257 | 52.9% |
| fact_vaccine_schedule.source_comment | 8,052 | 2,913 | 36.2% |
| fact_vaccine_schedule.age_administered | 8,052 | 1,045 | 13.0% |
| fact_vaccine_schedule.geoarea | 8,052 | 30 | 0.4% |
| dim_country.who_region | 214 | 1 | 0.5% |

**Reconciliation with Phase 0:** Phase 0 reported 80.2% null for coverage `TARGET_NUMBER`/`DOSES`
over the **full** table (country + aggregate, 399,858 rows). This validation measures the
country-only `fact_coverage` table (381,041 rows), which shows 84.2%/84.1% — a **materially
different but fully consistent** figure, because `TARGET_NUMBER`/`DOSES` are populated in **100%**
of aggregate rows but only **~16%** of country rows. Combining both strata reproduces the exact
Phase 0 figure (80.2%). This is a real, now-documented stratification effect, not a discrepancy.

No missing value was replaced with zero anywhere in this pipeline — verified structurally, since
`target_number`, `doses_raw`, `coverage_raw`, `incidence_rate`, `cases`, and all schedule text
fields remain nullable columns in the schema and contain actual SQL `NULL`s at the rates above.

## 6. Duplicate Tests (Section D)

| Table | Business key | Duplicate key groups |
|---|---|---|
| fact_coverage | country_code, year, antigen_code, coverage_category | 0 |
| fact_incidence | country_code, year, disease_code | 0 |
| fact_cases | country_code, year, disease_code | 0 |
| fact_vaccine_introduction | country_code, year, vaccine_description | 0 |
| fact_vaccine_schedule | country_code, year, vaccine_code, schedule_rounds, target_pop | 0 |

**Schedule composite-key reconciliation:** re-testing the *old* (incomplete) key
`(country_code, year, vaccine_code, schedule_rounds)` — i.e. without `target_pop` — reproduces
**898 duplicate key-groups, totalling exactly 1,319 extra rows**, matching Phase 0's reported
figure precisely (Phase 0's 1,319 used pandas' `.duplicated().sum()`, which counts extra rows
beyond the first occurrence per group — 898 and 1,319 both describe the same underlying pattern
from two different counting conventions). This confirms the `target_pop`-inclusive key is correct
and necessary.

**Result: ✅ PASS (0 duplicates on the true keys; old-key reconciliation matches Phase 0 exactly).**

## 7. Primary-Key / Unique-Constraint Tests (Section B)

All 13 tables tested (5 country facts, 3 aggregate facts, 5 dimensions) show
**total_rows == distinct_keys** — zero duplicate keys anywhere:

| Table | Rows | Distinct keys | Duplicates |
|---|---|---|---|
| fact_coverage | 381,041 | 381,041 | 0 |
| fact_incidence | 82,054 | 82,054 | 0 |
| fact_cases | 82,054 | 82,054 | 0 |
| fact_vaccine_introduction | 138,320 | 138,320 | 0 |
| fact_vaccine_schedule | 8,052 | 8,052 | 0 |
| fact_coverage_aggregate | 18,817 | 18,817 | 0 |
| fact_incidence_aggregate | 2,891 | 2,891 | 0 |
| fact_cases_aggregate | 2,815 | 2,815 | 0 |
| dim_country | 214 | 214 | 0 |
| dim_antigen | 69 | 69 | 0 |
| dim_disease | 13 | 13 | 0 |
| dim_vaccine_schedule_code | 86 | 86 | 0 |
| dim_aggregate_entity | 31 | 31 | 0 |

**Result: ✅ PASS — 13/13 tables.**

## 8. Foreign-Key Tests (Section C — Orphan Checks)

All 13 FK relationships tested via LEFT JOIN orphan detection (a row in the child table whose
key has no match in the parent):

| Relationship | Orphan rows |
|---|---|
| fact_coverage.country_code → dim_country | 0 |
| fact_coverage.antigen_code → dim_antigen | 0 |
| fact_incidence.country_code → dim_country | 0 |
| fact_incidence.disease_code → dim_disease | 0 |
| fact_cases.country_code → dim_country | 0 |
| fact_cases.disease_code → dim_disease | 0 |
| fact_vaccine_introduction.country_code → dim_country | 0 |
| fact_vaccine_schedule.country_code → dim_country | 0 |
| fact_vaccine_schedule.vaccine_code → dim_vaccine_schedule_code | 0 |
| fact_coverage_aggregate.(group_type,entity_code) → dim_aggregate_entity | 0 |
| fact_incidence_aggregate.(group_type,entity_code) → dim_aggregate_entity | 0 |
| fact_cases_aggregate.(group_type,entity_code) → dim_aggregate_entity | 0 |
| xwalk_antigen_disease.antigen_code → dim_antigen | 0 |

**Result: ✅ PASS — 13/13 relationships, zero orphans.** (SQLite `PRAGMA foreign_keys=ON` was
active during ETL load and was empirically confirmed to reject an orphan-row insert test.
**Note:** this pragma is per-connection in SQLite, not persisted in the file — any future
connection that writes to this database must re-issue `PRAGMA foreign_keys = ON;`; see
SQL_SCHEMA.md section 5 for detail. Read-only connections, e.g. Power BI, are unaffected.)

## 9. Data-Quality Flags (Sections G — Numeric Sanity)

| Flag distribution | Count |
|---|---|
| `doses_quality_flag = missing` | 320,481 |
| `doses_quality_flag = normal` | 60,552 |
| `doses_quality_flag = sentinel_not_reported` (the -3333 pattern) | 7 |
| `doses_quality_flag = implausible_negative` (El Salvador/POL3/2017) | 1 |
| `coverage_quality_flag = missing` | 169,331 |
| `coverage_quality_flag = normal` (≤100%) | 206,613 |
| `coverage_quality_flag = above_100_moderate` (100–500%) | 5,088 |
| `coverage_quality_flag = extreme_outlier` (>500%) | 9 |

Additional checks, all passing:
- `doses_clean` contains **zero** negative values remaining (sentinels/errors correctly nulled).
- All 9 `extreme_outlier` rows correctly have `coverage_analytical_exclude = 1`.
- Maximum `coverage_raw` value in the database: **32,000.0** (Morocco/FLU_HAJ/2018) — retained
  unmodified in the raw field, exactly as found in Phase 0, and flagged (not deleted or clipped).
- `fact_cases.cases`: 0 negative values. `fact_incidence.incidence_rate`: 0 negative values.

**Result: ✅ PASS.**

## 10. Coverage Outlier Results (Section G, detail)

- 5,088 rows in the 100–500% "moderate" band, retained as normal analytical data (plausible
  denominator-underestimation effect in administrative reporting) but flagged for transparency.
- 9 rows above 500% (up to 32,000%), flagged `extreme_outlier` and marked
  `coverage_analytical_exclude=1` — **excluded from analytical aggregates by convention in later
  phases, but never deleted from the database.**
- No row was clipped to 100%, and no threshold was applied without documentation (see
  CLEANING_TRANSFORMATION_LOG.md rule 3 for the full rationale).

## 11. Negative-Dose Handling (Section G, detail)

- 8 negative `DOSES` values found in country-level coverage data (matches Phase 0 exactly).
- 7 are the exact value `-3333`, recurring across unrelated countries/antigens (Bahamas,
  Trinidad & Tobago, Paraguay; all `FLU_*` antigens) — treated as a "not reported" sentinel and
  set to `NULL` in `doses_clean` (never coerced to 0). Original value fully preserved in `doses_raw`.
- 1 is an implausible extreme value (El Salvador/POL3/2017, `-222,288,203`) — treated as a data
  error, also nulled in `doses_clean`, original preserved in `doses_raw`.

## 12. WHO Region Mapping Results (Section from dim_country build)

- **Source:** `vaccine-introduction-data.xlsx` (primary) with `vaccine-schedule-data.xlsx` as
  fallback for countries absent from introduction data.
- **213 of 214 countries mapped** (99.5%).
- **1 country unmapped:** American Samoa (ASM) — present in coverage/incidence/cases but absent
  from both introduction and schedule tables, so no source data exists to derive a region from.
  Left `NULL`, not fabricated.
- **0 conflicts** detected between introduction's and schedule's WHO-region assignment for any
  country where both sources had data.
- **0 internal inconsistencies** within either source table (each source assigns exactly one
  region per country, consistently across all its rows for that country).

## 13. Crosswalk Statistics (Section J)

### `xwalk_antigen_disease`
| Metric | Value |
|---|---|
| Total antigens | 69 |
| Mapped | 33 (47.8%) |
| Unmapped | 36 (52.2%) |
| Mapped, high confidence | 25 |
| Mapped, medium confidence (combination vaccines, e.g. DTP) | 12 |
| Diseases covered by at least one mapping | 11 of 13 (all except CRS and MUMPS, for which no antigen in this dataset has a specific, defensible single-disease link) |
| Antigens missing entirely from the crosswalk table (should be 0) | **0 — confirmed** |

All 36 unmapped antigens have a specific, individually documented reason (target disease absent
from the 13-disease incidence/cases list — e.g. TB, Hepatitis B, pneumococcal disease, rotavirus,
HPV-associated disease, influenza, malaria — see DATA_DICTIONARY.md and the crosswalk table
itself for the per-antigen rationale).

### `xwalk_vaccine_family`
| Source table | Total codes | Mapped (single concept) | Combination component | Unmapped |
|---|---|---|---|---|
| coverage_antigen | 69 | 69 | 0 | 0 |
| schedule_vaccinecode | 86 | 54 | 19 | 13 |
| introduction_description | 21 | 19 | 1 | 1 |

All 13 unmapped schedule codes and the 1 unmapped introduction description correspond to
rare/travel vaccines (CCHF, Ebola, Hepatitis A, HFRS, Leptospirosis, Mpox, TBE, Tularemia,
Zoster) for which no concept was defined in the 23-concept keyword list — left transparently
unmapped rather than force-matched.

**A regex bug was found and fixed during this stage:** the "Tetanus toxoid" concept originally
required the literal phrase "tetanus tox", which missed "tetanus-containing vaccine" and
"neonatal tetanus" phrasing, incorrectly leaving `PAB`, `TTCV4`, `TTCV5`, `TTCV6` unmapped. Fixed
to match on `tetanus` generally; all 4 antigens now correctly map. Verified before finalizing.

## 14. ETL Reproducibility (Section L)

`scripts/06_load_sql.py` was run twice consecutively (full drop-and-rebuild each time), and
re-confirmed again after the Section 17 structural fix added `dim_vaccine_concept`. Row counts
for all 16 tables were identical across both runs of the current structure:

```
dim_country: 214, dim_antigen: 69, dim_disease: 13, dim_vaccine_schedule_code: 86,
dim_aggregate_entity: 31, dim_vaccine_concept: 23, xwalk_antigen_disease: 73, xwalk_vaccine_family: 208,
fact_coverage: 381041, fact_incidence: 82054, fact_cases: 82054,
fact_vaccine_introduction: 138320, fact_vaccine_schedule: 8052,
fact_coverage_aggregate: 18817, fact_incidence_aggregate: 2891, fact_cases_aggregate: 2815
```

**Result: ✅ PASS — no duplicate accumulation on rerun (verified both before and after the
Section 17 structural fix).**

## 15. Known Limitations Carried Forward

- `dim_country.who_region` is NULL for American Samoa (ASM) — genuinely undeterminable from
  source data, not fabricated.
- `xwalk_antigen_disease` covers less than half of all antigens (47.8%) — this reflects a real
  data-availability gap (many vaccine-preventable diseases are simply absent from the 13-disease
  incidence/cases list), not an incomplete analysis.
- Both crosswalks are analyst-derived and must be clearly labeled as such in any output that uses
  them (already enforced structurally via the `notes` column and this documentation).
- `xwalk_vaccine_family` leaves 13/86 schedule codes and 1/21 introduction descriptions unmapped
  because they represent vaccines outside the 23 documented concepts (rare/travel vaccines) —
  this list could be extended in a later phase if those vaccines become analytically relevant.
- All other Phase 0 limitations (no gender/education/urban-rural/density/seasonal/socioeconomic/
  delivery-strategy data) remain unchanged and are not addressed in Phase 1, per scope.

## 16. Final Phase 1 Status

**✅ PHASE 1 COMPLETE — INCLUDING FINAL STRUCTURAL QA.** All 30 completion-checklist items
satisfied (see PROJECT_STATUS.md for the full checklist). All validation categories pass. Three
implementation issues were found and fixed across Phase 1: (1) a bool/NaN type-conversion bug
during SQL load, (2) a regex-matching bug in the vaccine-family crosswalk ("tetanus tox" too
narrow), and (3) a structural gap in the vaccine-family crosswalk's referential integrity,
resolved in the final QA pass documented in Section 17 below. All three are documented and were
re-validated after their respective fixes.

No EDA, Power BI work, or assignment-question answering was performed, per scope.

## 17. Phase 1 Final QA Addendum — Crosswalk Structural Audit

A final structural QA pass was performed on both crosswalk tables after initial Phase 1
completion, at the requester's request, before final approval.

### Audit finding: `xwalk_vaccine_family`
The original design stored `vaccine_concept` as a bare, repeated text column. Testing confirmed
it **mechanically worked** as a join key (a text self-join reached all 69/69 coverage antigens),
but it had **no primary key, no foreign key, no protection against typos or drift**, and no
declared, enforceable relationship — a genuine structural gap for a "normalized relational
database" deliverable.

**Fix applied (minimum necessary structural change):** added `dim_vaccine_concept`
(`vaccine_concept` TEXT PRIMARY KEY, `keyword_patterns` TEXT) and changed
`xwalk_vaccine_family.vaccine_concept` into an **enforced foreign key** against it. No mapping,
confidence level, rationale, or unmapped record was altered — the 208-row table and its
mapped/combination/unmapped distribution are byte-for-byte identical before and after (re-verified
below). FK enforcement was empirically confirmed: `PRAGMA foreign_keys=ON` rejects any row whose
`vaccine_concept` is not present in `dim_vaccine_concept`.

**Three-way join demonstration (now FK-backed):**
```
antigen × schedule-code pairs reachable via shared, FK-enforced concept: 486
distinct antigens reachable to at least one schedule code: 69 / 69
```

### Audit finding: `xwalk_antigen_disease`
No primary key or uniqueness constraint had been declared. Because 2 antigens (`DTPCV1`,
`DTPCV3`) legitimately map to 3 diseases each (DTP is a combination vaccine), a naive
`antigen_code`-only unique constraint would have been **incorrect** and would have silently
dropped valid mappings.

**Fix applied:** added `UNIQUE(antigen_code, disease_code)`. Verified 0 duplicate pairs; verified
exactly 2 antigens are legitimately mapped to more than one disease (the expected DTP case) —
confirming the composite key is both correct and necessary.

### Preservation checks (all re-verified after the fix)

| Source population | Expected | Actual in xwalk_vaccine_family | Result |
|---|---|---|---|
| Coverage antigens | 69 | 69 | ✅ PASS |
| Schedule vaccine codes | 86 | 86 | ✅ PASS |
| Introduction descriptions | 21 | 21 | ✅ PASS |

| xwalk_antigen_disease | Result |
|---|---|
| All 69 antigens present (mapped or unmapped) | ✅ PASS (0 missing) |
| Composite key (antigen_code, disease_code) duplicates | ✅ PASS (0 found) |
| Antigens legitimately mapped to >1 disease | 2 (DTPCV1, DTPCV3) — expected |

### Full validation suite re-run after the fix
All 12 categories re-run in full against the rebuilt 16-table database (added `dim_vaccine_concept`):
row counts (11/11 ✅), PK uniqueness (16/16 tables ✅, including the new composite-key check on
`xwalk_antigen_disease`), FK integrity (18/18 relationships ✅ — 5 new checks added: FK to
`dim_vaccine_concept`, and application-level source-code checks for `coverage_antigen`→`dim_antigen`
and `schedule_vaccinecode`→`dim_vaccine_schedule_code`), duplicates (✅), country codes (✅), years
(✅), numeric sanity (✅), aggregate isolation (✅), crosswalk coverage (✅), ETL idempotency
(✅ — re-run twice on the new 16-table structure, identical counts both times).

**Overall status: ✅ PASS.**

### Conclusion
The vaccine-family crosswalk was **not structurally sufficient** in its original form — it worked
by convention (consistent text values happened to join correctly) rather than by enforced design.
The fix was additive and minimal: one new dimension table, one new FK constraint, one new
composite UNIQUE constraint — no existing mapping, cleaning rule, or source data was altered.
Phase 1 is now structurally sound for a "normalized relational SQL schema with PK/FK integrity"
as originally specified.


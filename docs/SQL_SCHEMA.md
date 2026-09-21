# SQL_SCHEMA.md
**Project:** Vaccination Data Analysis and Visualization — Phase 1
**Engine:** SQLite (`sql/vaccination.db`), built from `sql/schema.sql`
**Why SQLite:** no server/install dependency in this environment, full SQL DDL support
(PK/FK/UNIQUE/CHECK constraints, indexes), and the schema is written in portable standard SQL
so it can be ported to PostgreSQL/MySQL with minimal changes (mainly `INTEGER PRIMARY KEY`
autoincrement syntax) if a later phase needs a different engine for Power BI connectivity.

---

## 1. Entity-Relationship Overview

```
dim_country ──┬──< fact_coverage >──── dim_antigen ──< xwalk_antigen_disease >──── dim_disease
              ├──< fact_incidence >───────────────────────────────────────────────< dim_disease
              ├──< fact_cases >───────────────────────────────────────────────────< dim_disease
              ├──< fact_vaccine_introduction
              └──< fact_vaccine_schedule >──── dim_vaccine_schedule_code

dim_aggregate_entity ──< fact_coverage_aggregate  >──── dim_antigen
                     ──< fact_incidence_aggregate >──── dim_disease
                     ──< fact_cases_aggregate     >──── dim_disease

dim_antigen ──┬──< xwalk_vaccine_family (source_table='coverage_antigen')       ─┐
dim_vaccine_  │                                                                  │
 schedule_code┼──< xwalk_vaccine_family (source_table='schedule_vaccinecode')   ─┼──> dim_vaccine_concept
(intro desc.) └──< xwalk_vaccine_family (source_table='introduction_description')┘   (FK: vaccine_concept)
```

`xwalk_vaccine_family` bridges the three vaccine vocabularies through a proper dimension,
**`dim_vaccine_concept`** — each of the 208 crosswalk rows carries a `vaccine_concept` value that
is now an **enforced foreign key** into that dimension (added in Phase 1 final QA; previously an
unenforced repeated text value). Two `xwalk_vaccine_family` rows from different `source_table`
values that share the same `vaccine_concept` represent the same vaccine family — joining on that
shared, FK-validated value is the correct way to cross-reference coverage/schedule/introduction
codes (see worked example in DATA_DICTIONARY.md). This is still a **concept-level** classification
bridge, not a precise 1:1 code equivalence — true 1:1 does not exist for combination vaccines in
the source data.

## 2. Normalization Rationale

The schema follows a star-schema-like dimension/fact pattern:

- **Dimensions** (`dim_country`, `dim_antigen`, `dim_disease`, `dim_vaccine_schedule_code`,
  `dim_aggregate_entity`, `dim_vaccine_concept`) hold each entity's descriptive attributes exactly
  once, eliminating the repetition that existed in the flat source spreadsheets (e.g.
  `ANTIGEN_DESCRIPTION` was repeated on every one of 399,858 coverage rows in the source; it now
  lives once per antigen in `dim_antigen`). `dim_vaccine_concept` was added in Phase 1 final QA to
  replace a previously unenforced repeated text value with a proper, FK-referenced dimension.
- **Facts** hold only foreign keys and measures, at the natural grain of each source table.
- **Crosswalks** are kept as separate, clearly labeled tables rather than being merged into the
  fact tables, so that analyst-derived judgment calls never silently become indistinguishable from
  sourced fact. Any query using them must explicitly join to them.
- **No denormalized "everything table"** was created, per the Phase 1 instructions — every join a
  future Power BI report needs is achievable through the star-schema relationships above.

## 3. The Country vs. Aggregate Split (Critical Design Decision)

Phase 0 found that `coverage-data.xlsx`, `incidence-rate-data.xlsx`, and `reported-cases-data.xlsx`
mix true country rows (`GROUP='COUNTRIES'`) with regional/income/global rollup rows
(`WHO_REGIONS`, `UNICEF_REGIONS`, `WB_LONG`, `WB_SHORT`, `DEVELOPMENT_STATUS`, `GAVI_PHASE5`,
`GLOBAL`) in the same source sheet. To prevent this from silently contaminating country-level
analysis:

- Country-level facts (`fact_coverage`, `fact_incidence`, `fact_cases`) contain **only**
  `GROUP='COUNTRIES'` rows and have **no `group_type` column at all** — they are structurally
  incapable of holding an aggregate row.
- Aggregate-level facts (`fact_coverage_aggregate`, `fact_incidence_aggregate`,
  `fact_cases_aggregate`) hold everything else, keyed by `(group_type, entity_code)` against
  `dim_aggregate_entity`, and are never joined to `dim_country`.
- Validation confirms (Phase 1 validation report, section I) that no unexpected `group_type`
  value exists in the aggregate tables and that the country fact tables have no way to hold one.

**Any future Power BI relationship must connect country-level visuals to the country-level fact
tables via `dim_country`, and regional/global rollup visuals to the aggregate fact tables via
`dim_aggregate_entity`. These two families should not be combined in a single visual without an
explicit, deliberate decision to do so.**

## 4. Primary Keys

| Table | Primary Key |
|---|---|
| dim_country | country_code |
| dim_antigen | antigen_code |
| dim_disease | disease_code |
| dim_vaccine_schedule_code | vaccine_code |
| dim_aggregate_entity | (group_type, entity_code) |
| dim_vaccine_concept | vaccine_concept |
| fact_coverage | coverage_id (surrogate); UNIQUE(country_code, year, antigen_code, coverage_category) |
| fact_incidence | incidence_id (surrogate); UNIQUE(country_code, year, disease_code) |
| fact_cases | cases_id (surrogate); UNIQUE(country_code, year, disease_code) |
| fact_vaccine_introduction | introduction_id (surrogate); UNIQUE(country_code, year, vaccine_description) |
| fact_vaccine_schedule | schedule_id (surrogate); UNIQUE(country_code, year, vaccine_code, schedule_rounds, target_pop) |
| fact_coverage_aggregate | coverage_agg_id (surrogate); UNIQUE(group_type, entity_code, year, antigen_code, coverage_category) |
| fact_incidence_aggregate | incidence_agg_id (surrogate); UNIQUE(group_type, entity_code, year, disease_code) |
| fact_cases_aggregate | cases_agg_id (surrogate); UNIQUE(group_type, entity_code, year, disease_code) |
| xwalk_antigen_disease | UNIQUE(antigen_code, disease_code) — antigen_code alone intentionally not unique (2 antigens map to multiple diseases; see section 7) |
| xwalk_vaccine_family | vaccine_family_xwalk_id (surrogate); vaccine_concept is a FK to dim_vaccine_concept, not part of the row's own key |

Surrogate integer keys are used for fact tables purely for engine convenience (SQLite
`INTEGER PRIMARY KEY` rowid aliasing); **the real business key is always the UNIQUE constraint**,
and that is what all validation and future joins should rely on semantically.

### The Schedule Composite Key — Why `target_pop` Is Required

Phase 0 found that `(country_code, year, vaccine_code, schedule_rounds)` alone produces
**898 duplicate key-groups (1,319 extra rows)** because a single vaccine/round can legitimately
target multiple distinct populations (e.g. "Health workers" and "Risk group(s)" both receiving
`HEPB_ADULT` round 1 in the same country-year). Adding `target_pop` to the key produces **zero**
duplicates. This was re-verified independently in Phase 1 validation (section D), including a
reconciliation of the exact 1,319-row figure using the same counting method Phase 0 used.

## 5. Foreign Keys

All fact-to-dimension foreign keys are declared in `sql/schema.sql` with `PRAGMA foreign_keys=ON`
enforced during ETL load, and independently re-verified with LEFT-JOIN orphan checks in the
Phase 1 validation suite (zero orphans found across all 13 FK relationships tested). See
PHASE1_VALIDATION_REPORT.md section 8 for the full list and results.

> **Operational note for later phases / Power BI:** SQLite's `foreign_keys` pragma is a
> **per-connection** setting, not a property persisted in the database file. A fresh connection
> (e.g. Power BI's SQLite connector, or a new `sqlite3.connect()` call) defaults to
> `foreign_keys = OFF` and will silently allow constraint-violating writes unless the pragma is
> explicitly re-enabled on that connection. This was confirmed empirically: an orphan-row insert
> attempt succeeded until `PRAGMA foreign_keys = ON;` was issued on that connection, after which
> it correctly failed. **Any tool or script that writes to this database must issue
> `PRAGMA foreign_keys = ON;` immediately after connecting** if constraint enforcement is
> required; read-only reporting tools (Power BI) are unaffected since they do not write.

## 6. Indexes

In addition to the PK/UNIQUE indexes created automatically, explicit secondary indexes were
added for the join patterns expected in later Power BI/EDA phases:
- `idx_fact_coverage_country_year`, `idx_fact_coverage_antigen`
- `idx_fact_incidence_country_year`
- `idx_fact_cases_country_year`
- `idx_fact_intro_country_year`
- `idx_fact_schedule_country_year`

## 7. Crosswalk Architecture

Both crosswalks (`xwalk_antigen_disease`, `xwalk_vaccine_family`) are **analyst-derived metadata,
not source-provided fact** — see DATA_DICTIONARY.md for full column definitions and the exact
rule sets used to build them. Architecturally:
- Every antigen in `dim_antigen` has **at least one row** in `xwalk_antigen_disease`, whether
  mapped or explicitly marked unmapped with a documented reason — no antigen is silently absent.
- `xwalk_antigen_disease` enforces `UNIQUE(antigen_code, disease_code)`. **`antigen_code` alone is
  deliberately not unique** — `DTPCV1` and `DTPCV3` each map to 3 diseases (diphtheria, tetanus,
  pertussis), since DTP is a combination vaccine; forcing antigen-level uniqueness would have
  silently dropped 2 of those 3 correct links per dose.
- `xwalk_vaccine_family` uses a "concept" as the unit of linkage rather than a direct row-to-row
  FK between the three vaccine tables, because coverage/schedule/introduction use three
  incompatible vocabularies with no shared key in the source data. **As of Phase 1 final QA, that
  concept is a real dimension (`dim_vaccine_concept`) with an enforced foreign key**, not a bare
  repeated text value — this closes a structural gap identified during final QA: the original
  design "worked" (a text self-join could reach all 69 antigens), but had no referential
  integrity, no protection against typos, and no declared, queryable relationship. The fix was
  additive only: one new dimension table and one new FK column constraint, with every existing
  mapping, confidence level, rationale, and unmapped record preserved unchanged (re-verified: all
  208 crosswalk rows and all confidence/status values identical before and after the change).
- Both tables carry `confidence` and `rationale` columns specifically so that any Power BI report
  or later analysis built on top of them can visually distinguish high-confidence single-antigen
  mappings from lower-confidence combination-vaccine inferences, or filter out low-confidence rows
  entirely.

## 8. Expected Future Power BI Relationship Strategy

(Documented for planning purposes only — no Power BI work is performed in Phase 1.)

- Import `dim_country`, `dim_antigen`, `dim_disease`, `dim_vaccine_schedule_code` as lookup
  tables with one-to-many relationships to their respective fact tables, filtering
  cross-filter direction as "single" from dimension to fact.
- Keep `fact_*` and `fact_*_aggregate` tables as **separate visual contexts** — do not blend them
  into one table or relationship in Power BI, to preserve the country/aggregate isolation
  established in this schema. A slicer or bookmark-based toggle between "Country view" and
  "Regional/Global view" is recommended over a single combined table.
- `xwalk_antigen_disease` and `xwalk_vaccine_family` should be imported as separate lookup
  tables with an explicit visual/report note that they are derived metadata; consider exposing
  the `confidence` field as a filter so report users can choose to view only high-confidence
  mappings.
- `who_region` on `dim_country` is the recommended field for regional slicers/maps at the country
  level; the separate `fact_*_aggregate` tables (keyed by `dim_aggregate_entity`) are the
  recommended source for pre-aggregated regional/global rollup visuals instead of summing country
  rows, since WHO's own rollup methodology may not be a simple sum (this was not verified in
  Phase 1 and should be treated as an open question for later phases).

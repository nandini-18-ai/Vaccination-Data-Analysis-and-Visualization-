"""
Stage 06 — Create Schema & Load SQL Database
===============================================
Builds the SQLite database from sql/schema.sql, then loads every dimension,
crosswalk, and fact table from the parquet outputs of stages 03-05.

Idempotent / rerunnable: the database file is dropped and rebuilt from scratch
each run (DELETE + CREATE, not INSERT-only), so running this script twice in a
row produces byte-for-byte identical row counts - no duplicate accumulation.
This IS the ETL's reproducibility mechanism, verified explicitly in stage 07.

Output: sql/vaccination.db
        logs/06_load_sql.json
"""
import sqlite3
import pandas as pd
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1]
DIM_DIR = BASE / "data" / "clean" / "02_dimensions"
XWALK_DIR = BASE / "data" / "clean" / "03_crosswalks"
FACT_DIR = BASE / "data" / "clean" / "04_facts"
SQL_DIR = BASE / "sql"
LOG_DIR = BASE / "logs"
DB_PATH = SQL_DIR / "vaccination.db"
SCHEMA_PATH = SQL_DIR / "schema.sql"

log = {}


def rebuild_schema(conn):
    """Drop and recreate the database from schema.sql -- ensures idempotency."""
    with open(SCHEMA_PATH) as f:
        ddl = f.read()
    cur = conn.cursor()
    # Drop all known tables first (order doesn't matter with FK enforcement off during drop)
    cur.execute("PRAGMA foreign_keys = OFF;")
    tables = [
        "fact_cases_aggregate", "fact_incidence_aggregate", "fact_coverage_aggregate",
        "fact_vaccine_schedule", "fact_vaccine_introduction", "fact_cases", "fact_incidence", "fact_coverage",
        "xwalk_vaccine_family", "xwalk_antigen_disease", "dim_vaccine_concept",
        "dim_aggregate_entity", "dim_vaccine_schedule_code", "dim_disease", "dim_antigen", "dim_country",
    ]
    for t in tables:
        cur.execute(f"DROP TABLE IF EXISTS {t};")
    conn.commit()
    cur.executescript(ddl)
    conn.commit()


def load_table(conn, df, table_name, dtype_bool_cols=None):
    """Load a dataframe into an existing SQL table via pandas.to_sql (append, since
    schema/PK/FK constraints are already defined by the DDL)."""
    df = df.copy()
    if dtype_bool_cols:
        for c in dtype_bool_cols:
            if c in df.columns:
                # Use nullable Int64 so True/False/NaN all convert safely; NaN stays NULL in SQL.
                df[c] = df[c].astype("boolean").astype("Int64")
    # Convert pandas nullable Int64 / boolean to plain python types sqlite understands
    for c in df.columns:
        if str(df[c].dtype) in ("Int64", "boolean"):
            df[c] = df[c].astype(object).where(df[c].notna(), None)
    df.to_sql(table_name, conn, if_exists="append", index=False)
    return len(df)


def main():
    conn = sqlite3.connect(DB_PATH)
    rebuild_schema(conn)

    # --- Dimensions ---
    dim_country = pd.read_parquet(DIM_DIR / "dim_country.parquet")
    dim_country = dim_country.rename(columns={
        "IN_COVERAGE": "in_coverage", "IN_INCIDENCE": "in_incidence", "IN_CASES": "in_cases",
        "IN_INTRODUCTION": "in_introduction", "IN_SCHEDULE": "in_schedule",
    })
    dim_country = dim_country[[
        "country_code", "country_name", "who_region", "who_region_source_intro",
        "who_region_source_schedule", "who_region_conflict",
        "in_coverage", "in_incidence", "in_cases", "in_introduction", "in_schedule",
    ]]
    n = load_table(conn, dim_country, "dim_country",
                    dtype_bool_cols=["who_region_conflict", "in_coverage", "in_incidence", "in_cases", "in_introduction", "in_schedule"])
    log["dim_country"] = n

    dim_antigen = pd.read_parquet(DIM_DIR / "dim_antigen.parquet")
    log["dim_antigen"] = load_table(conn, dim_antigen, "dim_antigen")

    dim_disease = pd.read_parquet(DIM_DIR / "dim_disease.parquet")
    log["dim_disease"] = load_table(conn, dim_disease, "dim_disease")

    dim_vsc = pd.read_parquet(DIM_DIR / "dim_vaccine_schedule_code.parquet")
    log["dim_vaccine_schedule_code"] = load_table(conn, dim_vsc, "dim_vaccine_schedule_code")

    dim_agg_entity = pd.read_parquet(DIM_DIR / "dim_aggregate_entity.parquet")
    log["dim_aggregate_entity"] = load_table(conn, dim_agg_entity, "dim_aggregate_entity")

    dim_vaccine_concept = pd.read_parquet(XWALK_DIR / "dim_vaccine_concept.parquet")
    log["dim_vaccine_concept"] = load_table(conn, dim_vaccine_concept, "dim_vaccine_concept")

    # --- Crosswalks ---
    xwalk_ad = pd.read_parquet(XWALK_DIR / "xwalk_antigen_disease.parquet")
    log["xwalk_antigen_disease"] = load_table(conn, xwalk_ad, "xwalk_antigen_disease")

    xwalk_vf = pd.read_parquet(XWALK_DIR / "xwalk_vaccine_family.parquet")
    log["xwalk_vaccine_family"] = load_table(conn, xwalk_vf, "xwalk_vaccine_family")

    # --- Country-level facts ---
    fact_coverage = pd.read_parquet(FACT_DIR / "fact_coverage.parquet")
    log["fact_coverage"] = load_table(conn, fact_coverage, "fact_coverage", dtype_bool_cols=["coverage_analytical_exclude"])

    fact_incidence = pd.read_parquet(FACT_DIR / "fact_incidence.parquet")
    log["fact_incidence"] = load_table(conn, fact_incidence, "fact_incidence")

    fact_cases = pd.read_parquet(FACT_DIR / "fact_cases.parquet")
    log["fact_cases"] = load_table(conn, fact_cases, "fact_cases")

    fact_intro = pd.read_parquet(FACT_DIR / "fact_vaccine_introduction.parquet")
    log["fact_vaccine_introduction"] = load_table(conn, fact_intro, "fact_vaccine_introduction")

    fact_sched = pd.read_parquet(FACT_DIR / "fact_vaccine_schedule.parquet")
    log["fact_vaccine_schedule"] = load_table(conn, fact_sched, "fact_vaccine_schedule")

    # --- Aggregate facts ---
    fact_coverage_agg = pd.read_parquet(FACT_DIR / "fact_coverage_aggregate.parquet")
    log["fact_coverage_aggregate"] = load_table(conn, fact_coverage_agg, "fact_coverage_aggregate", dtype_bool_cols=["coverage_analytical_exclude"])

    fact_incidence_agg = pd.read_parquet(FACT_DIR / "fact_incidence_aggregate.parquet")
    log["fact_incidence_aggregate"] = load_table(conn, fact_incidence_agg, "fact_incidence_aggregate")

    fact_cases_agg = pd.read_parquet(FACT_DIR / "fact_cases_aggregate.parquet")
    log["fact_cases_aggregate"] = load_table(conn, fact_cases_agg, "fact_cases_aggregate")

    conn.commit()

    # Report actual row counts back from SQL (not just what we intended to insert)
    cur = conn.cursor()
    sql_counts = {}
    for t in log.keys():
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        sql_counts[t] = cur.fetchone()[0]
    conn.close()

    log["_sql_verified_counts"] = sql_counts
    with open(LOG_DIR / "06_load_sql.json", "w") as f:
        json.dump(log, f, indent=2, default=str)

    print(json.dumps(sql_counts, indent=2))
    mismatches = {t: (log[t], sql_counts[t]) for t in sql_counts if log[t] != sql_counts[t]}
    if mismatches:
        print("MISMATCHES:", mismatches)
    else:
        print("[06_load_sql] All table row counts match intended load counts.")


if __name__ == "__main__":
    main()

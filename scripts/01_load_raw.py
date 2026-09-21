"""
Stage 01 — Load Raw
====================
Loads the 5 source 'Data' sheets exactly as supplied, with zero transformation.
Serves as the traceable starting point: RAW RECORD -> ... -> SQL TABLE RECORD.

Input : data/raw/*.xlsx  (read-only, never modified)
Output: data/clean/00_raw_snapshot/*.parquet (exact copy of raw data, for fast reuse
        by later stages without re-reading Excel every run)
"""
import pandas as pd
from pathlib import Path
import json

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "clean" / "00_raw_snapshot"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "coverage": "coverage-data.xlsx",
    "incidence": "incidence-rate-data.xlsx",
    "cases": "reported-cases-data.xlsx",
    "intro": "vaccine-introduction-data.xlsx",
    "schedule": "vaccine-schedule-data.xlsx",
}

EXPECTED_REAL_ROWS = {
    # from Phase 0 (post footer-removal expectation), used only for validation logging here
    "coverage": 399858,
    "incidence": 84945,
    "cases": 84869,
    "intro": 138320,
    "schedule": 8052,
}


def load_raw():
    log = []
    dfs = {}
    for key, fname in FILES.items():
        path = RAW_DIR / fname
        df = pd.read_excel(path, sheet_name="Data", engine="openpyxl")
        raw_row_count = len(df)
        dfs[key] = df
        df.to_parquet(OUT_DIR / f"{key}_raw.parquet", index=False)
        log.append({
            "dataset": key,
            "source_file": fname,
            "raw_row_count_incl_footer": raw_row_count,
            "raw_columns": list(df.columns),
            "expected_real_rows_after_footer_removal": EXPECTED_REAL_ROWS[key],
        })
        print(f"[01_load_raw] {key}: loaded {raw_row_count} rows (incl. footer) from {fname}")

    with open(LOG_DIR / "01_load_raw.json", "w") as f:
        json.dump(log, f, indent=2)
    return dfs


if __name__ == "__main__":
    load_raw()
    print("[01_load_raw] Complete. Raw snapshots written to data/clean/00_raw_snapshot/")

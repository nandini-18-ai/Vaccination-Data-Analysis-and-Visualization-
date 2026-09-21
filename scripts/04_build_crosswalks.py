"""
Stage 04 — Build Crosswalks (ANALYST-DERIVED METADATA, NOT SOURCE FACT)
=========================================================================
Neither crosswalk exists in the source data. Both are built here by an explicit,
reviewable, keyword/domain-knowledge-based rule set, applied programmatically so the
result is reproducible and auditable (not hand-typed one-off guesses). Every mapping
row carries mapping_status, confidence, and rationale so downstream users can see
exactly why a link was or was not made.

xwalk_antigen_disease:
    Maps coverage ANTIGEN codes to incidence/cases DISEASE codes where a specific,
    defensible clinical link exists. Antigens targeting diseases NOT present in the
    13-disease incidence/cases list (e.g. BCG->TB, HEPB*->Hepatitis B, PCV*->pneumococcal
    disease, ROTA*->rotavirus, HPV*->HPV-associated disease, FLU_*->influenza,
    MALARIA*->malaria, HIB3->Hib disease) are explicitly left UNMAPPED with a note
    explaining the disease is absent from the source disease list - never invented.

xwalk_vaccine_family:
    Links coverage ANTIGEN, schedule VACCINECODE, and introduction DESCRIPTION by
    keyword-matching each against a documented list of vaccine "concepts" (e.g.
    "Measles-containing", "Diphtheria-Tetanus-Pertussis", "Polio (IPV)"). A code that
    matches more than one concept (a combination vaccine, e.g. DTaP-Hib-IPV) receives
    one row per concept, each flagged 'combination_component' with reduced confidence,
    rather than being forced into a single misleading one-to-one link. Codes matching
    no concept keyword are left unmapped and reported, not guessed at.

Input : data/clean/01_cleaned/*.parquet, data/clean/02_dimensions/*.parquet
Output: data/clean/03_crosswalks/xwalk_antigen_disease.parquet
        data/clean/03_crosswalks/xwalk_vaccine_family.parquet
        logs/04_build_crosswalks.json
"""
import pandas as pd
from pathlib import Path
import json
import re

BASE = Path(__file__).resolve().parents[1]
DIM_DIR = BASE / "data" / "clean" / "02_dimensions"
OUT_DIR = BASE / "data" / "clean" / "03_crosswalks"
LOG_DIR = BASE / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

log = {}

# ---------------------------------------------------------------------------
# ANTIGEN -> DISEASE crosswalk
# ---------------------------------------------------------------------------
# Only the 13 diseases actually present in incidence/cases can be a valid target:
# CRS, DIPHTHERIA, INVASIVE_MENING, JAPENC, MEASLES, MUMPS, NTETANUS, PERTUSSIS,
# POLIO, RUBELLA, TTETANUS, TYPHOID, YFEVER
#
# Format: antigen_code -> list of (disease_code, confidence, rationale)
ANTIGEN_DISEASE_MAP = {
    "DIPHCV4": [("DIPHTHERIA", "high", "Diphtheria booster dose (4th DTP-containing dose)")],
    "DIPHCV5": [("DIPHTHERIA", "high", "Diphtheria booster dose (5th)")],
    "DIPHCV6": [("DIPHTHERIA", "high", "Diphtheria booster dose (6th)")],
    "DTPCV1": [
        ("DIPHTHERIA", "medium", "DTP is a combination vaccine (diphtheria+tetanus+pertussis); dose 1"),
        ("TTETANUS", "medium", "DTP combination component; dose 1"),
        ("PERTUSSIS", "medium", "DTP combination component; dose 1"),
    ],
    "DTPCV3": [
        ("DIPHTHERIA", "medium", "DTP is a combination vaccine (diphtheria+tetanus+pertussis); dose 3"),
        ("TTETANUS", "medium", "DTP combination component; dose 3"),
        ("PERTUSSIS", "medium", "DTP combination component; dose 3"),
    ],
    "IPV1": [("POLIO", "high", "Inactivated polio vaccine, dose 1")],
    "IPV1_FRAC": [("POLIO", "high", "Fractional-dose IPV, dose 1")],
    "IPV2": [("POLIO", "high", "Inactivated polio vaccine, dose 2")],
    "IPV2_FRAC": [("POLIO", "high", "Fractional-dose IPV, dose 2")],
    "POL3": [("POLIO", "high", "Oral/inactivated polio vaccine, dose 3")],
    "JAPENC": [("JAPENC", "high", "Antigen code and disease code both denote Japanese encephalitis directly")],
    "JAPENC_1": [("JAPENC", "high", "Japanese encephalitis vaccine, dose 1")],
    "JAPENC_C": [("JAPENC", "high", "Japanese encephalitis vaccine, completed/booster dose")],
    "MCV1": [("MEASLES", "high", "Measles-containing vaccine, dose 1")],
    "MCV2": [("MEASLES", "high", "Measles-containing vaccine, dose 2")],
    "MCV2X2": [("MEASLES", "high", "Measles-containing vaccine, 2nd dose variant")],
    "MENACYW_C": [("INVASIVE_MENING", "medium", "Meningococcal ACYW conjugate vaccine; INVASIVE_MENING covers invasive meningococcal disease broadly, not serogroup-specific")],
    "MENA_C": [("INVASIVE_MENING", "medium", "Meningococcal A conjugate vaccine")],
    "MENB_C": [("INVASIVE_MENING", "medium", "Meningococcal B vaccine")],
    "MEN_ACYW_CONJ": [("INVASIVE_MENING", "medium", "Meningococcal ACYW conjugate vaccine")],
    "MEN_A_CONJ": [("INVASIVE_MENING", "medium", "Meningococcal A conjugate vaccine")],
    "MEN_B": [("INVASIVE_MENING", "medium", "Meningococcal B vaccine")],
    "PAB": [("NTETANUS", "high", "Protection-at-birth estimate is specifically a proxy for maternal/neonatal tetanus protection")],
    "PERCV4": [("PERTUSSIS", "high", "Pertussis-containing booster dose 4")],
    "PERCV_PW": [("PERTUSSIS", "high", "Pertussis vaccination of pregnant women (protects newborn against pertussis)")],
    "RCV1": [("RUBELLA", "high", "Rubella-containing vaccine, dose 1")],
    "TT2PLUS": [("TTETANUS", "high", "Tetanus toxoid, 2+ doses")],
    "TTCV4": [("TTETANUS", "high", "Tetanus toxoid-containing vaccine, dose 4")],
    "TTCV5": [("TTETANUS", "high", "Tetanus toxoid-containing vaccine, dose 5")],
    "TTCV6": [("TTETANUS", "high", "Tetanus toxoid-containing vaccine, dose 6")],
    "TYPHOID": [("TYPHOID", "high", "Typhoid vaccine")],
    "TYPHOID_CONJ": [("TYPHOID", "high", "Typhoid conjugate vaccine")],
    "YFV": [("YFEVER", "high", "Yellow fever vaccine")],
}

# Antigens with NO valid mapping target in the 13-disease list - explicitly documented,
# never forced. unmapped_reason explains exactly why.
ANTIGEN_UNMAPPED_REASON = {
    "BCG": "Targets tuberculosis; TB is not present in the incidence/cases disease list (Phase 0 finding).",
    "HEPB3": "Targets Hepatitis B; Hepatitis B is not present in the incidence/cases disease list.",
    "HEPB_BD": "Targets Hepatitis B (birth dose); Hepatitis B is not present in the incidence/cases disease list.",
    "HEPB_BDALL": "Targets Hepatitis B (birth dose, all facilities); Hepatitis B is not present in the incidence/cases disease list.",
    "HIB3": "Targets Haemophilus influenzae type b; Hib disease is not present in the incidence/cases disease list (INVASIVE_MENING is meningococcal-specific, a different organism).",
    "PCV1": "Targets pneumococcal disease; pneumococcal disease is not present in the incidence/cases disease list.",
    "PCV2": "Targets pneumococcal disease; pneumococcal disease is not present in the incidence/cases disease list.",
    "PCV3": "Targets pneumococcal disease; pneumococcal disease is not present in the incidence/cases disease list.",
    "ROTA1": "Targets rotavirus; rotavirus disease is not present in the incidence/cases disease list.",
    "ROTAC": "Targets rotavirus (completed schedule); rotavirus disease is not present in the incidence/cases disease list.",
    "VAD1": "Vitamin A supplementation dose - not a vaccine against an infectious disease in this list.",
    "MALARIA1": "Targets malaria; malaria is not present in the incidence/cases disease list.",
    "MALARIA3": "Targets malaria; malaria is not present in the incidence/cases disease list.",
    "MALARIA4": "Targets malaria; malaria is not present in the incidence/cases disease list.",
}
# HPV and FLU variants share one reason each - generated programmatically below.


def build_antigen_disease_crosswalk(dim_antigen):
    rows = []
    all_reasons = dict(ANTIGEN_UNMAPPED_REASON)
    for code in dim_antigen["antigen_code"]:
        if code.startswith(("15HPV", "HPV", "PRHPV")):
            all_reasons[code] = "Targets HPV; no HPV-associated disease (e.g. cervical cancer) is present in the incidence/cases disease list."
        if code.startswith("FLU_"):
            all_reasons[code] = "Targets seasonal influenza; influenza is not present in the incidence/cases disease list (Phase 0 finding)."

    for _, r in dim_antigen.iterrows():
        code = r["antigen_code"]
        if code in ANTIGEN_DISEASE_MAP:
            for disease_code, confidence, rationale in ANTIGEN_DISEASE_MAP[code]:
                rows.append({
                    "antigen_code": code, "disease_code": disease_code,
                    "mapping_status": "mapped", "confidence": confidence, "rationale": rationale,
                    "notes": "Analyst-derived mapping; not present in source data.",
                })
        else:
            reason = all_reasons.get(code, "No confident, specific clinical mapping to a disease in the 13-disease incidence/cases list could be established.")
            rows.append({
                "antigen_code": code, "disease_code": None,
                "mapping_status": "unmapped", "confidence": "n/a", "rationale": reason,
                "notes": "Analyst-derived assessment; not present in source data. No mapping forced.",
            })

    xwalk = pd.DataFrame(rows)
    mapped_antigens = xwalk.loc[xwalk["mapping_status"] == "mapped", "antigen_code"].nunique()
    unmapped_antigens = xwalk.loc[xwalk["mapping_status"] == "unmapped", "antigen_code"].nunique()
    log["xwalk_antigen_disease"] = {
        "total_antigens": dim_antigen["antigen_code"].nunique(),
        "antigens_mapped": int(mapped_antigens),
        "antigens_unmapped": int(unmapped_antigens),
        "total_mapping_rows": len(xwalk),
        "confidence_distribution": xwalk.loc[xwalk["mapping_status"] == "mapped", "confidence"].value_counts().to_dict(),
        "diseases_covered_by_mapping": sorted(xwalk["disease_code"].dropna().unique().tolist()),
    }
    return xwalk


# ---------------------------------------------------------------------------
# VACCINE FAMILY crosswalk (coverage ANTIGEN <-> schedule VACCINECODE <-> intro DESCRIPTION)
# ---------------------------------------------------------------------------
# Keyword-based concept matching. Each concept has a set of case-insensitive keywords
# that must appear in the code's own description text. A code matching >1 concept is a
# combination vaccine and gets one row per concept (confidence 'medium', status
# 'combination_component'). A code matching exactly 1 concept gets 'high' confidence,
# status 'mapped'. A code matching 0 concepts is 'unmapped'.
CONCEPTS = {
    "BCG": [r"\bBCG\b", r"tuberculos"],
    "Diphtheria-Tetanus-Pertussis": [r"\bDTP\b", r"\bDT\b", r"\bDTAP\b", r"\bDTWP\b", r"diphtheria", r"pertussis", r"\bTD\b"],
    "Tetanus toxoid (adult/maternal)": [r"tetanus", r"\bTT\b"],
    "Polio (IPV/OPV)": [r"\bIPV\b", r"\bOPV\b", r"polio"],
    "Measles-Mumps-Rubella": [r"measles", r"\bMMR\b", r"\bMR\b", r"mumps", r"rubella"],
    "Hepatitis B": [r"hepatitis ?b", r"\bHEPB\b", r"\bHEP-B\b", r"\bHB\b"],
    "Hib (Haemophilus influenzae type b)": [r"\bHIB\b", r"haemophilus"],
    "Pneumococcal (PCV)": [r"pneumococcal", r"\bPCV\b"],
    "Rotavirus": [r"rotavirus", r"\bROTA\b"],
    "HPV": [r"\bHPV\b", r"papillomavirus"],
    "Yellow Fever": [r"yellow fever", r"\bYFV\b"],
    "Meningococcal": [r"meningococcal", r"\bMEN[ABC]?\b", r"meningitis"],
    "Typhoid": [r"typhoid"],
    "Japanese Encephalitis": [r"japanese encephalitis", r"\bJAPENC\b", r"\bJE\b"],
    "Influenza (seasonal)": [r"influenza", r"\bFLU\b"],
    "Malaria": [r"malaria"],
    "Cholera": [r"cholera"],
    "Varicella": [r"varicella", r"chickenpox"],
    "Vitamin A": [r"vitamin a"],
    "Dengue": [r"dengue"],
    "Anthrax": [r"anthrax"],
    "Rabies": [r"rabies"],
    "COVID-19": [r"covid", r"sars-cov-2", r"coronavirus"],
}
COMPILED_CONCEPTS = {name: [re.compile(k, re.IGNORECASE) for k in kws] for name, kws in CONCEPTS.items()}


def match_concepts(text):
    if not isinstance(text, str) or not text.strip():
        return []
    matched = []
    for concept, patterns in COMPILED_CONCEPTS.items():
        if any(p.search(text) for p in patterns):
            matched.append(concept)
    return matched


def build_vaccine_family_crosswalk(dim_antigen, dim_vaccine_schedule_code, intro_df):
    rows = []

    def emit(source_table, source_code, source_description):
        concepts = match_concepts(source_description)
        if len(concepts) == 0:
            rows.append({
                "source_table": source_table, "source_code": source_code, "source_description": source_description,
                "vaccine_concept": None, "mapping_status": "unmapped", "confidence": "n/a",
                "rationale": "No keyword match against the documented concept list.",
                "notes": "Analyst-derived (keyword-based); not present in source data. Left unmapped rather than guessed.",
            })
        elif len(concepts) == 1:
            rows.append({
                "source_table": source_table, "source_code": source_code, "source_description": source_description,
                "vaccine_concept": concepts[0], "mapping_status": "mapped", "confidence": "high",
                "rationale": f"Single unambiguous keyword match: '{concepts[0]}'.",
                "notes": "Analyst-derived (keyword-based); not present in source data.",
            })
        else:
            for c in concepts:
                rows.append({
                    "source_table": source_table, "source_code": source_code, "source_description": source_description,
                    "vaccine_concept": c, "mapping_status": "combination_component", "confidence": "medium",
                    "rationale": f"Description matched multiple concepts {concepts}; likely a combination vaccine. "
                                 f"Each component concept is listed as a separate row rather than forcing one link.",
                    "notes": "Analyst-derived (keyword-based); not present in source data. Combination vaccine - "
                             "do not treat as an exact one-to-one equivalence with single-antigen concepts.",
                })

    for _, r in dim_antigen.iterrows():
        emit("coverage_antigen", r["antigen_code"], r["antigen_description"])
    for _, r in dim_vaccine_schedule_code.iterrows():
        emit("schedule_vaccinecode", r["vaccine_code"], r["vaccine_description"])
    intro_desc = intro_df[["DESCRIPTION"]].dropna().drop_duplicates().sort_values("DESCRIPTION")
    for _, r in intro_desc.iterrows():
        emit("introduction_description", r["DESCRIPTION"], r["DESCRIPTION"])

    xwalk = pd.DataFrame(rows)
    xwalk.insert(0, "vaccine_family_xwalk_id", range(1, len(xwalk) + 1))

    # --- dim_vaccine_concept -----------------------------------------------------
    # STRUCTURAL FIX (Phase 1 final QA): previously 'vaccine_concept' was a bare free-text
    # column repeated across rows, joined only implicitly (a self-join on matching text with
    # no PK/FK enforcement, no protection against typos/drift, no declared referential
    # integrity). This promotes vaccine_concept into a proper dimension table with a real
    # primary key, and xwalk_vaccine_family.vaccine_concept becomes an enforced foreign key
    # into it. The keyword pattern used to derive each concept is stored for full
    # reproducibility/auditability of this analyst-derived classification.
    concept_rows = []
    for concept_name, patterns in CONCEPTS.items():
        concept_rows.append({
            "vaccine_concept": concept_name,
            "keyword_patterns": "; ".join(patterns),
        })
    dim_vaccine_concept = pd.DataFrame(concept_rows).sort_values("vaccine_concept").reset_index(drop=True)

    summary_by_table = {}
    for tbl in xwalk["source_table"].unique():
        sub = xwalk[xwalk["source_table"] == tbl]
        codes = sub["source_code"].nunique()
        mapped = sub.loc[sub["mapping_status"] == "mapped", "source_code"].nunique()
        combo = sub.loc[sub["mapping_status"] == "combination_component", "source_code"].nunique()
        unmapped = sub.loc[sub["mapping_status"] == "unmapped", "source_code"].nunique()
        summary_by_table[tbl] = {"total_codes": int(codes), "mapped_single_concept": int(mapped),
                                  "combination_multi_concept": int(combo), "unmapped": int(unmapped)}

    log["xwalk_vaccine_family"] = {
        "method": "Keyword/regex concept matching against each code's own description text "
                  f"({len(CONCEPTS)} documented vaccine concepts, now backed by dim_vaccine_concept). "
                  "Reproducible and reviewable, but NOT a source-provided mapping - purely analyst-derived.",
        "total_rows": len(xwalk),
        "by_source_table": summary_by_table,
        "concepts_defined": sorted(CONCEPTS.keys()),
        "structural_note": "vaccine_concept is now an enforced FK to dim_vaccine_concept (added in Phase 1 "
                            "final QA) rather than a bare repeated text value.",
    }
    return xwalk, dim_vaccine_concept


def main():
    dim_antigen = pd.read_parquet(DIM_DIR / "dim_antigen.parquet")
    dim_vaccine_schedule_code = pd.read_parquet(DIM_DIR / "dim_vaccine_schedule_code.parquet")
    intro_df = pd.read_parquet(BASE / "data" / "clean" / "01_cleaned" / "intro_clean.parquet")

    xwalk_ad = build_antigen_disease_crosswalk(dim_antigen)
    xwalk_vf, dim_vaccine_concept = build_vaccine_family_crosswalk(dim_antigen, dim_vaccine_schedule_code, intro_df)

    # Build-time integrity check: xwalk_antigen_disease composite key (antigen_code, disease_code)
    # must have zero duplicates. One antigen legitimately maps to multiple diseases (e.g. DTP ->
    # 3 diseases), so antigen_code alone is NOT unique by design - the pair must be.
    dup_pairs = xwalk_ad.duplicated(subset=["antigen_code", "disease_code"]).sum()
    log["xwalk_antigen_disease"]["composite_key_duplicate_check"] = {
        "key": "(antigen_code, disease_code)",
        "duplicates_found": int(dup_pairs),
        "pass": bool(dup_pairs == 0),
    }
    assert dup_pairs == 0, f"xwalk_antigen_disease has {dup_pairs} duplicate (antigen_code, disease_code) pairs"

    # Build-time check: every vaccine_concept value used in xwalk_vaccine_family must exist in
    # dim_vaccine_concept (referential integrity before it's even loaded into SQL).
    used_concepts = set(xwalk_vf["vaccine_concept"].dropna().unique())
    defined_concepts = set(dim_vaccine_concept["vaccine_concept"].unique())
    orphan_concepts = used_concepts - defined_concepts
    log["xwalk_vaccine_family"]["concept_referential_check"] = {
        "used_concepts": len(used_concepts), "defined_concepts": len(defined_concepts),
        "orphan_concepts": sorted(orphan_concepts), "pass": len(orphan_concepts) == 0,
    }
    assert len(orphan_concepts) == 0, f"Orphan vaccine_concept values not in dim_vaccine_concept: {orphan_concepts}"

    xwalk_ad.to_parquet(OUT_DIR / "xwalk_antigen_disease.parquet", index=False)
    xwalk_vf.to_parquet(OUT_DIR / "xwalk_vaccine_family.parquet", index=False)
    dim_vaccine_concept.to_parquet(OUT_DIR / "dim_vaccine_concept.parquet", index=False)

    with open(LOG_DIR / "04_build_crosswalks.json", "w") as f:
        json.dump(log, f, indent=2, default=str)

    print(f"[04_crosswalks] dim_vaccine_concept: {len(dim_vaccine_concept)} rows")
    print(f"[04_crosswalks] xwalk_antigen_disease: {len(xwalk_ad)} rows")
    print(f"[04_crosswalks] xwalk_vaccine_family: {len(xwalk_vf)} rows")
    print(json.dumps(log, indent=2, default=str))


if __name__ == "__main__":
    main()

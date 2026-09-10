"""Deterministic MTB draft data for legacy GRCh37/hg19 tumor-only jobs."""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .legacy_oncogenicity import annotate, is_high_risk

TSO500_PANEL_MB = 1.94
TMB_POPULATION_AF_MAX = 0.001


def _rows(path, limit=None, delimiter=","):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    return rows[:limit] if limit else rows


def _number(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _coding(row):
    value = str(row.get("Consequence") or row.get("ExonicFunc.refGene") or "").casefold()
    excluded = ("intron", "intergenic", "upstream", "downstream", "utr", "non_coding")
    return bool(value) and not any(term in value for term in excluded)


def estimate_tso500_tmb(rows):
    selected = {}
    for row in rows:
        if not _coding(row):
            continue
        population = [_number(row.get(key)) for key in ("AF", "AF_popmax", "AF_eas")]
        population = [value for value in population if value is not None]
        if population and max(population) > TMB_POPULATION_AF_MAX:
            continue
        key = tuple(str(row.get(name) or "") for name in ("Chr", "Start", "Ref", "Alt"))
        if all(key):
            selected[key] = row
    count = len(selected)
    return {
        "status": "exploratory_not_clinically_validated",
        "assay_profile": "Illumina TruSight Oncology 500 proxy",
        "genome_build": "GRCh37/hg19",
        "panel_size_mb": TSO500_PANEL_MB,
        "tmb_numerator_variants": count,
        "tmb_proxy_mut_per_mb": round(count / TSO500_PANEL_MB, 2),
        "population_af_max": TMB_POPULATION_AF_MAX,
        "method": "Unique coding SNVs/indels in the existing quality-filtered legacy output, including synonymous and non-synonymous variants, after population-frequency germline-proxy exclusion; divided by the published 1.94 Mb TSO500 panel size.",
        "limitations": [
            "No sample-specific callable/capture BED was supplied; 1.94 Mb is the published total TSO500 panel size, not measured callable territory.",
            "Tumor-only analysis cannot completely remove private germline variants.",
            "This proxy does not reproduce Illumina DRAGEN TSO500 proprietary filtering and is not calibrated to an approved clinical assay.",
            "No TMB-high or TMB-low clinical category is assigned.",
        ],
    }


def _signature(directory):
    path = directory / "mutSig" / "Assignment" / "Assignment_Solution" / "Activities" / "Assignment_Solution_Activities.txt"
    rows = _rows(path, limit=5, delimiter="\t")
    if not rows:
        return []
    output = []
    for row in rows:
        for key, value in row.items():
            if key.startswith("SBS") and (_number(value) or 0) > 0:
                output.append({"signature": key, "activity": value})
    return sorted(output, key=lambda item: float(item["activity"]), reverse=True)[:10]


def generate(directory):
    merged = sorted(directory.glob("*_main_vep_annovar_merge.csv"))
    source = merged[0] if merged else directory / "somatic_result.csv"
    if not source.is_file():
        raise FileNotFoundError("Legacy tumor-only merged result is not available")
    all_rows = _rows(source)
    oncogenicity_path = directory / "legacy_candidates.oncogenicity.tsv"
    oncogenicity_summary = directory / "legacy_candidates.oncogenicity.summary.json"
    if not oncogenicity_path.exists() or oncogenicity_path.stat().st_mtime < source.stat().st_mtime:
        annotated, onco_summary = annotate(source, oncogenicity_path, oncogenicity_summary)
    else:
        annotated = _rows(oncogenicity_path, delimiter="\t")
        onco_summary = json.loads(oncogenicity_summary.read_text()) if oncogenicity_summary.is_file() else {}
    high_risk = [row for row in annotated if is_high_risk(row)]
    files = {
        "actionable": "somatic_result.csv", "hereditary": "heredity.csv",
        "germline_prediction": "heridty1.csv", "cosmic": "COSMIC.csv",
        "prediction": "suspect.csv", "multiple_snp_cosmic": "drug_combinations_cosmic.csv",
        "multiple_snp_civic": "mutiSNP_analysis_civic.csv",
        "potential_treatment": "potential_treatment_df.csv",
    }
    sections = {name: {"available": (directory / filename).is_file(), "count": len(_rows(directory / filename))} for name, filename in files.items()}
    sections.update({
        "mutation_signature": {"available": bool(_signature(directory)), "count": len(_signature(directory))},
        "fusion_gene": {"available": any(directory.glob("fusion_gene*/*")), "count": None},
        "cancer_type_prediction": {"available": any(directory.glob("*cancer*prediction*.csv")), "count": None},
        "pathway": {"available": any(directory.glob("*pathway*")), "count": None},
    })
    tmb = estimate_tso500_tmb(all_rows)
    genes = sorted({str(row.get("SYMBOL") or row.get("Gene.refGene") or row.get("Gene") or "").strip() for row in high_risk} - {""})
    return {
        "status": "draft", "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_id": directory.name, "genome_build": "GRCh37/hg19",
        "reporting_gate": "non-synonymous AND (ClinVar P/LP OR oncogenicity O/LO)",
        "quality_filter": "unchanged legacy tumor-only pipeline settings",
        "summary": {
            "high_risk_count": len(high_risk), "high_risk_genes": genes,
            "oncogenicity_candidates": onco_summary.get("variants", len(annotated)),
            "estimated_tmb": tmb["tmb_proxy_mut_per_mb"],
        },
        "tmb_estimate": tmb, "high_risk": high_risk[:100],
        "mutational_signatures": _signature(directory), "sections": sections,
        "disclaimer": "Draft for molecular tumor board review. Legacy hg19 tumor-only findings, actionability, TMB proxy, and downstream analyses require professional review and appropriate confirmatory testing.",
    }

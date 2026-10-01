"""Deterministic MTB draft data for legacy GRCh37/hg19 tumor-only jobs."""
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from .legacy_oncogenicity import annotate, is_high_risk
from .legacy_quality import number as _number, passes as passes_quality, settings as quality_settings
from .mtb_report import REPORT_FIELDS, _fallback, _model_summary
from .storage import read_json, write_json

TSO500_PANEL_MB = 1.94
TMB_POPULATION_AF_MAX = 0.001
REQUIRED_RESULT_FILES = {
    "actionable": "somatic_result.csv", "hereditary": "heredity.csv",
    "germline_prediction": "heridty1.csv", "cosmic": "COSMIC.csv",
    "prediction": "suspect.csv", "multiple_snp_cosmic": "drug_combinations_cosmic.csv",
    "multiple_snp_civic": "mutiSNP_analysis_civic.csv",
    "potential_treatment": "potential_treatment_df.csv",
}


def _rows(path, limit=None, delimiter=","):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    return rows[:limit] if limit else rows


def _coding(row):
    value = str(row.get("Consequence") or row.get("ExonicFunc.refGene") or "").casefold()
    accepted = ("synonymous", "missense", "frameshift", "stop_gained", "stopgain", "stop_lost", "start_lost", "splice", "inframe", "protein_altering", "nonsynonymous")
    return any(term in value for term in accepted)


def _snv_or_indel(row):
    ref, alt = str(row.get("Ref") or ""), str(row.get("Alt") or "")
    return bool(ref and alt) and not (len(ref) > 1 and len(alt) > 1)


def estimate_tso500_tmb(rows, thresholds=None):
    thresholds = thresholds or {"min_dp": 0, "min_vaf": 0, "population_af_max": 1}
    selected = {}
    for row in rows:
        tmb_thresholds = {**thresholds, "population_af_max": TMB_POPULATION_AF_MAX}
        if not _coding(row) or not _snv_or_indel(row) or not passes_quality(row, tmb_thresholds):
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
        "method": "Unique recognized coding SNVs/indels passing the sample DP/VAF gate, including synonymous and non-synonymous variants, after population-frequency germline-proxy exclusion; divided by the published 1.94 Mb TSO500 panel size.",
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
    thresholds = quality_settings(directory)
    cached_summary = json.loads(oncogenicity_summary.read_text()) if oncogenicity_summary.is_file() else {}
    if not oncogenicity_path.exists() or oncogenicity_path.stat().st_mtime < source.stat().st_mtime or not isinstance(cached_summary.get("quality_filter"), dict):
        annotated, onco_summary = annotate(source, oncogenicity_path, oncogenicity_summary, thresholds)
    else:
        annotated = _rows(oncogenicity_path, delimiter="\t")
        onco_summary = json.loads(oncogenicity_summary.read_text()) if oncogenicity_summary.is_file() else {}
    high_risk = [row for row in annotated if is_high_risk(row)]
    sections = {name: {"available": (directory / filename).is_file(), "count": len(_rows(directory / filename)) if (directory / filename).is_file() else None} for name, filename in REQUIRED_RESULT_FILES.items()}
    sections.update({
        "mutation_signature": {"available": bool(_signature(directory)), "count": len(_signature(directory))},
        "fusion_gene": {"available": any(directory.glob("fusion_gene*/*")), "count": None},
        "cancer_type_prediction": {"available": any(directory.glob("*cancer*prediction*.csv")), "count": None},
        "pathway": {"available": any(directory.glob("*pathway*")), "count": None},
    })
    missing = [filename for filename in REQUIRED_RESULT_FILES.values() if not (directory / filename).is_file()]
    tmb = estimate_tso500_tmb(all_rows, thresholds)
    genes = sorted({str(row.get("SYMBOL") or row.get("Gene.refGene") or row.get("Gene") or "").strip() for row in high_risk} - {""})
    return {
        "status": "incomplete" if missing else "draft", "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_id": directory.name, "genome_build": "GRCh37/hg19",
        "reporting_gate": "sample quality gate AND non-synonymous AND (ClinVar P/LP OR oncogenicity O/LO)",
        "quality_filter": thresholds, "missing_result_files": missing,
        "summary": {
            "high_risk_count": len(high_risk), "high_risk_genes": genes,
            "oncogenicity_candidates": onco_summary.get("variants", len(annotated)),
            "estimated_tmb": tmb["tmb_proxy_mut_per_mb"],
        },
        "tmb_estimate": tmb, "high_risk": high_risk[:100],
        "mutational_signatures": _signature(directory), "sections": sections,
        "disclaimer": "Draft for molecular tumor board review. Legacy hg19 tumor-only findings, actionability, TMB proxy, and downstream analyses require professional review and appropriate confirmatory testing.",
    }


def _clean_variant(row):
    aa_change = str(row.get("AAChange.refGene") or "")
    protein = ""
    coding = ""
    if aa_change:
        first = aa_change.split(",", 1)[0]
        protein_match = re.search(r":(p\.[^:,]+)", first)
        coding_match = re.search(r":(c\.[^:,]+)", first)
        protein = protein_match.group(1) if protein_match else ""
        coding = coding_match.group(1) if coding_match else ""
    annotations = " | ".join(str(row.get(key) or "").strip() for key in ("oncoKB_annotation", "CGI_annotation", "CIVIC_annotation") if str(row.get(key) or "").strip() not in ("", "."))
    return {
        "gene": str(row.get("SYMBOL") or row.get("Gene.refGene") or row.get("Gene") or "").strip(),
        "hgvsp": protein,
        "hgvsc": coding,
        "consequence": str(row.get("Consequence") or row.get("ExonicFunc.refGene") or "").strip(),
        "clinvar": str(row.get("ClinVar_CLNSIG") or row.get("CLNSIG") or "").strip(),
        "oncogenicity": str(row.get("oncogenicity_classification") or "").strip(),
        "oncogenicity_score": str(row.get("oncogenicity_score") or "").strip(),
        "oncogenicity_criteria": str(row.get("oncogenicity_criteria") or "").strip(),
        "variant": ":".join(str(row.get(key) or "").strip() for key in ("Chr", "Start", "Ref", "Alt")),
        "vaf": str(row.get("VAF") or "").strip(),
        "depth": str(row.get("DP") or "").strip(),
        "drug": annotations[:2000],
        "source": "legacy treatment databases" if annotations else "",
    }


def _ai_payload(directory):
    base = generate(directory)
    try:
        metadata = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        metadata = {}
    signatures = base.get("mutational_signatures", [])
    total = sum(_number(item.get("activity")) or 0 for item in signatures)
    signatures = [{**item, "proportion": ((_number(item.get("activity")) or 0) / total if total else 0)} for item in signatures]
    actionable = [_clean_variant(row) for row in _rows(directory / "actionable.csv", limit=100)]
    diagnosis = str(metadata.get("diagnosis") or "").strip()
    matched, other = [], []
    for row in actionable:
        evidence = row.get("drug", "").casefold()
        (matched if diagnosis and diagnosis.casefold() in evidence else other).append(row)
    return {
        "sample_id": directory.name,
        "analysis_id": directory.name,
        "protocol": "Illumina TSO500-style legacy tumor-only",
        "genome_build": "GRCh37/hg19",
        "cancer_type": diagnosis,
        "clinical_history": "",
        "high_risk_variants": [_clean_variant(row) for row in base.get("high_risk", [])],
        "actionable_matched": matched,
        "actionable_other_cancers": other,
        "hereditary_high_risk": [_clean_variant(row) for row in _rows(directory / "heredity.csv", limit=50)],
        "cosmic_candidates": [_clean_variant(row) for row in _rows(directory / "COSMIC.csv", limit=50)],
        "prediction_candidates": [_clean_variant(row) for row in _rows(directory / "suspect.csv", limit=50)],
        "potential_treatment_candidates": [_clean_variant(row) for row in _rows(directory / "potential_treatment_df.csv", limit=50)],
        "estimated_tmb": base.get("tmb_estimate", {}),
        "top_mutational_signatures": signatures,
        "analysis_inventory": base.get("sections", {}),
        "base_report": base,
    }


def _target(directory):
    return directory / "legacy_mtb_draft_report.json"


def cached_assisted(directory):
    report = read_json(_target(directory), {"status": "not_generated", "draft": True})
    report["data"] = _ai_payload(directory)
    return report


def generate_assisted(directory, refresh=False):
    target = _target(directory)
    if target.is_file() and not refresh:
        existing = read_json(target, {})
        if existing.get("status") in ("gemma_generated", "gemma_corrected"):
            existing["data"] = _ai_payload(directory)
            return existing
    data = _ai_payload(directory)
    narrative = _fallback(data)
    status = "template_only"
    warning = ""
    try:
        narrative = _model_summary(data)
        corrected = narrative.pop("_template_corrected_fields", [])
        status = "gemma_corrected" if corrected else "gemma_generated"
        if corrected:
            warning = "Gemma output required deterministic correction for: " + ", ".join(corrected)
    except Exception as exc:
        warning = f"Gemma summary unavailable; deterministic Traditional Chinese template used: {exc}"[:500]
    report = {
        "status": status, "draft": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": os.environ.get("MTB_REPORT_LLM_MODEL", "gemma4:e4b") if status in ("gemma_generated", "gemma_corrected") else None,
        "warning": warning, "data": data, "narrative": narrative,
        "disclaimer": "MTB 初步草稿，所有內容均須由合格臨床專業人員審閱及核准後方可使用。",
    }
    write_json(target, report)
    return report


def save_assisted_edits(directory, narrative):
    report = read_json(_target(directory), {})
    if not report or report.get("status") == "not_generated":
        raise ValueError("Generate the MTB draft before editing it")
    if not isinstance(narrative, dict):
        raise ValueError("Narrative must be an object")
    cleaned = {}
    for key in REPORT_FIELDS[:-1]:
        value = str(narrative.get(key, "")).strip()
        if len(value) > 4000:
            raise ValueError(f"{key} is too long")
        cleaned[key] = value
    limitations = narrative.get("limitations", [])
    if not isinstance(limitations, list) or len(limitations) > 20:
        raise ValueError("Limitations must contain at most 20 items")
    cleaned["limitations"] = [str(item).strip()[:1000] for item in limitations if str(item).strip()]
    report.update({"status": "manually_edited", "narrative": cleaned, "edited_at": datetime.now(timezone.utc).isoformat()})
    write_json(_target(directory), report)
    report["data"] = _ai_payload(directory)
    return report

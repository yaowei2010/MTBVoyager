"""Programmatic oncogenicity annotation for the legacy hg19 tumor-only result."""
import ast
import csv
import importlib.util
import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from .legacy_quality import passes as passes_quality, settings as quality_settings

LEGACY_PROFILE = "legacy_hg19_gene_protein_to_oncovi_v0.1"
EXTRA_FIELDS = [
    "oncogenicity_score", "oncogenicity_classification", "oncogenicity_criteria",
    "oncogenicity_review_required", "oncogenicity_evidence", "oncogenicity_profile",
    "oncovi_resource_commit", "oncovi_2026_score", "oncovi_2026_classification",
    "oncovi_2026_criteria", "oncovi_2026_evidence", "oncovi_2026_profile",
    "oncovi_2026_validation_status", "oncogenicity_profile_difference",
    "oncogenicity_input_scope", "oncogenicity_coordinate_build", "oncogenicity_limitations",
]


def _dict(value):
    try:
        parsed = ast.literal_eval(str(value or "{}"))
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, SyntaxError):
        return {}


def _consequence(change):
    change = str(change or "")
    if "fs" in change: return "frameshift_variant"
    if "del" in change: return "inframe_deletion"
    if "ins" in change or "dup" in change: return "inframe_insertion"
    if change.endswith("*"): return "stop_gained"
    return "missense_variant" if re.fullmatch(r"[A-Za-z*]\d+[A-Za-z*]", change) else "protein_altering_variant"


def _clean(value):
    return str(value or "").strip()


def _protein_change(row):
    direct = _clean(row.get("Amino acid change"))
    if direct:
        return direct.removeprefix("p.")
    amino = _clean(row.get("Amino_acids"))
    position = re.split(r"[-/]", _clean(row.get("Protein_position")), maxsplit=1)[0]
    if "/" in amino and position:
        ref, alt = amino.split("/", 1)
        return f"{ref}{position}{alt}" if ref and alt else ""
    match = re.search(r"(?:p\.)?([A-Za-z*]\d+[A-Za-z*])", _clean(row.get("HGVSp")))
    return match.group(1) if match else ""


def is_non_synonymous(row):
    consequence = _clean(row.get("Consequence") or row.get("ExonicFunc.refGene")).casefold()
    if not consequence:
        return bool(_protein_change(row))
    if "nonsynonymous" in consequence:
        return True
    excluded = ("synonymous", "intron", "intergenic", "upstream", "downstream", "utr", "non_coding")
    return bool(consequence) and not any(term in consequence for term in excluded)


def clinvar_pathogenic(row):
    value = _clean(row.get("CLIN_SIG") or row.get("CLNSIG"))
    if not value:
        value = _clean(_dict(row.get("Pathogenicity")).get("CLNSIG"))
    normalized = value.replace("_", " ").casefold()
    return "pathogenic" in normalized and "conflict" not in normalized


def is_high_risk(row):
    return is_non_synonymous(row) and (
        clinvar_pathogenic(row)
        or _clean(row.get("oncogenicity_classification")) in ("Oncogenic", "Likely Oncogenic")
    )


def adapt_legacy_row(row):
    """Map only evidence actually present in the old CSV; never infer missing VEP fields."""
    change = _protein_change(row)
    match = re.fullmatch(r"([A-Za-z*])(\d+)([A-Za-z*])", change)
    maf, prediction, pathogenicity = _dict(row.get("MAF")), _dict(row.get("Prediction")), _dict(row.get("Pathogenicity"))
    adapted = dict(row)
    adapted.update({
        "SYMBOL": row.get("SYMBOL") or row.get("Gene.refGene") or row.get("Gene", ""),
        "Consequence": row.get("Consequence") or _consequence(change),
        "HGVSp": f"p.{change}" if change else row.get("HGVSp", ""),
        "CLIN_SIG": pathogenicity.get("CLNSIG") or row.get("CLNSIG", ""),
    })
    if match:
        adapted.update({"Amino_acids": f"{match[1].upper()}/{match[3].upper()}", "Protein_position": match[2]})
    population_af = maf.get("gnomAD", row.get("AF"))
    if population_af not in (None, "", "."):
        adapted["gnomADe_AF"] = population_af
    cadd = prediction.get("CADD", row.get("CADD_phred"))
    if cadd not in (None, "", "."):
        adapted["CADD_phred"] = cadd
    return adapted


@lru_cache(maxsize=1)
def engine():
    path = Path(os.environ.get("WGS_SOMATIC_PIPELINE_SOURCE", "/opt/wgs-somatic-pipeline")) / "bin" / "calculate_oncogenicity.py"
    spec = importlib.util.spec_from_file_location("wgs_somatic_oncogenicity", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def resources():
    root = os.environ.get("WGS_ONCOVI_RESOURCES", "/miRTI/media/oncovi/resources")
    return engine().Resources(root)


def annotate(input_csv, output_tsv, summary_json, thresholds=None):
    module, res = engine(), resources()
    with Path(input_csv).open(encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle); fields = [field for field in (reader.fieldnames or []) if field]
        rows = [row for row in reader if is_non_synonymous(row) and (thresholds is None or passes_quality(row, thresholds))]
    counts, reference_counts, output = Counter(), Counter(), []
    for original in rows:
        source = adapt_legacy_row(original)
        score, label, evidence, dual = module.evaluate(source, res)
        ref_score, ref_label, ref_evidence = module.evaluate_reference(source, res, evidence)
        met = [item["code"] for item in evidence if item["status"] == "met"]
        ref_met = [item["code"] for item in ref_evidence if item["status"] == "met"]
        strict_status = {item["code"]: item["status"] for item in evidence}
        ref_status = {item["code"]: item["status"] for item in ref_evidence}
        limitations = "Legacy input is GRCh37/hg19 and lacks complete GRCh38 VEP, ClinVar review-status, splice, conservation and tumor-type evidence; manual review is required."
        annotated = dict(original)
        annotated.update({
            "oncogenicity_score": score, "oncogenicity_classification": label,
            "oncogenicity_criteria": "|".join(met), "oncogenicity_review_required": "true",
            "oncogenicity_evidence": json.dumps(evidence, ensure_ascii=False, separators=(",", ":")),
            "oncogenicity_profile": LEGACY_PROFILE, "oncovi_resource_commit": module.COMMIT,
            "oncovi_2026_score": ref_score, "oncovi_2026_classification": ref_label,
            "oncovi_2026_criteria": "|".join(ref_met),
            "oncovi_2026_evidence": json.dumps(ref_evidence, ensure_ascii=False, separators=(",", ":")),
            "oncovi_2026_profile": module.REFERENCE_PROFILE,
            "oncovi_2026_validation_status": "legacy_input_not_part_of_grch38_benchmark",
            "oncogenicity_profile_difference": "|".join(code for code in module.POINTS if strict_status[code] != ref_status[code]),
            "oncogenicity_input_scope": "legacy_hg19_gene_protein_annotation",
            "oncogenicity_coordinate_build": "GRCh37/hg19", "oncogenicity_limitations": limitations,
        })
        output.append(annotated); counts[label] += 1; reference_counts[ref_label] += 1
    output_tsv, summary_json = Path(output_tsv), Path(summary_json)
    output_tsv.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_tsv.with_suffix(output_tsv.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + EXTRA_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader(); writer.writerows(output)
    os.replace(tmp, output_tsv)
    summary = {"profile": LEGACY_PROFILE, "coordinate_build": "GRCh37/hg19", "variants": len(output),
               "classification_counts": dict(counts), "oncovi_2026_classification_counts": dict(reference_counts),
               "review_required": len(output), "quality_filter": thresholds,
               "limitations": output[0]["oncogenicity_limitations"] if output else ""}
    tmp = summary_json.with_suffix(summary_json.suffix + ".tmp"); tmp.write_text(json.dumps(summary, indent=2) + "\n"); os.replace(tmp, summary_json)
    return output, summary

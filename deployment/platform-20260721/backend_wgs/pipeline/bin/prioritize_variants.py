#!/usr/bin/env python3
"""Create conservative, auditable SNV/INDEL clinical review buckets."""
import argparse
import csv
import gzip
import json
import re
from pathlib import Path


MISSING = {"", "-", ".", "not provided", "not specified", "no assertion provided"}
POPULATION_FIELDS = {
    "eas": ["gnomADe_EAS_AF", "gnomADg_EAS_AF", "gnomAD_EAS_AF"],
    "afr": ["gnomADe_AFR_AF", "gnomADg_AFR_AF", "gnomAD_AFR_AF"],
    "amr": ["gnomADe_AMR_AF", "gnomADg_AMR_AF", "gnomAD_AMR_AF"],
    "asj": ["gnomADe_ASJ_AF", "gnomADg_ASJ_AF", "gnomAD_ASJ_AF"],
    "fin": ["gnomADe_FIN_AF", "gnomADg_FIN_AF", "gnomAD_FIN_AF"],
    "nfe": ["gnomADe_NFE_AF", "gnomADg_NFE_AF", "gnomAD_NFE_AF"],
    "sas": ["gnomADe_SAS_AF", "gnomADg_SAS_AF", "gnomAD_SAS_AF"],
    "global": ["gnomADe_AF", "gnomADg_AF", "gnomAD_AF"],
}


def value(row, names):
    for name in names:
        item = str(row.get(name, "")).strip()
        if item.casefold() not in MISSING:
            return item
    return ""


def number(item):
    try:
        return float(str(item).split("&")[0])
    except (TypeError, ValueError):
        return None


def genes(path):
    if not path:
        return set()
    result = set()
    with Path(path).open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            symbol = line.strip().split("\t")[0]
            if symbol and symbol.lower() not in {"gene", "genes"} and not symbol.startswith("#"):
                result.add(symbol.upper())
    return result


def review_stars(review):
    text = review.casefold().replace("_", " ")
    if "practice guideline" in text:
        return 4
    if "expert panel" in text:
        return 3
    if "multiple submitters" in text and "no conflict" in text:
        return 2
    if "criteria provided" in text and "single submitter" in text:
        return 1
    return 0


def pathogenicity(row):
    raw = value(row, ["CLIN_SIG", "ClinVar_CLNSIG", "clinvar_clnsig", "CLNSIG"])
    review = value(row, ["CLINVAR_REVIEW_STATUS", "ClinVar_CLNREVSTAT", "CLNREVSTAT"])
    normalized = re.sub(r"[_-]+", " ", raw.casefold())
    conflict = "conflict" in normalized or "conflict" in review.casefold()
    assertions = {x.strip() for x in re.split(r"[|/,;&]+", normalized) if x.strip()}
    pathogenic = "pathogenic" in assertions
    likely = "likely pathogenic" in assertions
    valid_review = review.casefold() not in MISSING and "no assertion" not in review.casefold()
    eligible = (pathogenic or likely) and not conflict and valid_review
    return {
        "eligible": eligible,
        "classification": "P/LP" if pathogenic and likely else "P" if pathogenic else "LP" if likely else "",
        "raw": raw,
        "review": review,
        "stars": review_stars(review),
        "conflict": conflict,
    }


def damaging_votes(row):
    votes = []
    for key, threshold in {
        "REVEL_score": 0.7, "CADD_phred": 20.0, "ClinPred_score": 0.5,
        "PrimateAI_score": 0.8, "AlphaMissense_score": 0.564,
    }.items():
        score = number(row.get(key))
        if score is not None and score >= threshold:
            votes.append(key)
    for key in ("SIFT_pred", "Polyphen2_HDIV_pred", "Polyphen2_HVAR_pred", "MutationTaster_pred"):
        if any(flag in str(row.get(key, "")).upper().split("&") for flag in ("D", "A")):
            votes.append(key)
    splice = max((number(row.get(key)) or 0 for key in ("SpliceAI_pred_DS_AG", "SpliceAI_pred_DS_AL", "SpliceAI_pred_DS_DG", "SpliceAI_pred_DS_DL")), default=0)
    if splice >= 0.2:
        votes.append("SpliceAI")
    return votes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--gene-list")
    parser.add_argument("--acmg-genes")
    parser.add_argument("--population", choices=sorted(POPULATION_FIELDS), default="eas")
    parser.add_argument("--population-af-max", type=float, default=0.01)
    parser.add_argument("--predictor-min", type=int, default=7)
    args = parser.parse_args()
    phenotype_genes = genes(args.gene_list)
    acmg_genes = genes(args.acmg_genes)

    opener = gzip.open if args.input.endswith(".gz") else open
    header, records = None, []
    with opener(args.input, "rt", newline="") as handle:
        for line in handle:
            if line.startswith("##"):
                continue
            if line.startswith("#"):
                header = line.lstrip("#").rstrip("\n").split("\t")
                continue
            if not line.strip() or not header:
                continue
            row = dict(zip(header, line.rstrip("\n").split("\t")))
            gene = value(row, ["SYMBOL", "Gene_Name", "Gene"]).upper()
            af = number(value(row, POPULATION_FIELDS[args.population]))
            if af is not None and af >= args.population_af_max:
                continue
            clinical = pathogenicity(row)
            votes = damaging_votes(row)
            categories = []
            if clinical["eligible"]:
                categories.append("KNOWN_CLINVAR_PLP")
                if gene in phenotype_genes:
                    categories.append("PHENOTYPE_VARIANT")
                if gene in acmg_genes:
                    categories.append("ACMG_SF")
            if len(votes) >= args.predictor_min:
                categories.append("INSILICO_CANDIDATE")
            if not categories:
                continue
            row.update({
                "sample_id": args.sample,
                "population": args.population,
                "population_af": "" if af is None else str(af),
                "population_af_filter_pass": "true",
                "normalized_pathogenicity": clinical["classification"],
                "clinvar_clinical_significance_raw": clinical["raw"],
                "clinvar_review_status": clinical["review"],
                "clinvar_review_stars": str(clinical["stars"]),
                "clinvar_conflict": str(clinical["conflict"]).lower(),
                "clinvar_id": value(row, ["ClinVar", "ClinVar_ID", "VariationID", "CLNVI"]),
                "clinvar_evaluation_date": value(row, ["ClinVar_CLNDNINCL", "CLNVC", "ClinVar_EvaluationDate"]),
                "damaging_predictor_count": str(len(votes)),
                "damaging_predictors": ",".join(votes),
                "candidate_categories": ",".join(categories),
            })
            records.append(row)

    extra = ["sample_id", "population", "population_af", "population_af_filter_pass", "normalized_pathogenicity", "clinvar_clinical_significance_raw", "clinvar_review_status", "clinvar_review_stars", "clinvar_conflict", "clinvar_id", "clinvar_evaluation_date", "damaging_predictor_count", "damaging_predictors", "candidate_categories"]
    fields = (header or []) + [item for item in extra if item not in (header or [])]
    buckets = {
        "all_candidates": records,
        "known_clinvar_plp": [r for r in records if "KNOWN_CLINVAR_PLP" in r["candidate_categories"]],
        "phenotype_variants": [r for r in records if "PHENOTYPE_VARIANT" in r["candidate_categories"]],
        "acmg_sf": [r for r in records if "ACMG_SF" in r["candidate_categories"]],
        "insilico": [r for r in records if "INSILICO_CANDIDATE" in r["candidate_categories"]],
    }
    for suffix, rows in buckets.items():
        with open(f"{args.output_prefix}.{suffix}.tsv", "w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    Path(f"{args.output_prefix}.prioritization.summary.json").write_text(json.dumps({name: len(rows) for name, rows in buckets.items()}, indent=2) + "\n")


if __name__ == "__main__":
    main()

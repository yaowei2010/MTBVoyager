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
GLOBAL_AF_FIELDS = ["gnomADe_AF", "gnomADg_AF", "gnomAD_AF"]
PROTEIN_ALTERING_CONSEQUENCES = {
    "transcript_ablation", "splice_acceptor_variant", "splice_donor_variant",
    "stop_gained", "frameshift_variant", "stop_lost", "start_lost",
    "inframe_insertion", "inframe_deletion", "missense_variant",
    "protein_altering_variant", "coding_sequence_variant",
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


def numbers(item):
    result = []
    for token in re.split(r"[,&]", str(item)):
        try:
            result.append(float(token.strip()))
        except (TypeError, ValueError):
            pass
    return result


def max_number(row, names):
    """Return the largest AF and its source, preserving missingness for audit."""
    observed = []
    for name in names:
        observed.extend((score, name) for score in numbers(row.get(name, "")))
    return max(observed, default=(None, ""), key=lambda item: item[0])


def functional_consequences(row):
    raw = value(row, ["Consequence", "consequence"])
    consequences = {item.strip() for item in re.split(r"[,&]", raw) if item.strip()}
    return consequences, consequences & PROTEIN_ALTERING_CONSEQUENCES


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


def acmg_rules(path):
    if not path:
        return {}
    result = {}
    with Path(path).open(encoding="utf-8", errors="replace") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            gene = (row.get("gene") or "").strip().upper()
            if gene:
                result[gene] = row
    return result


def zygosity(row):
    raw = value(row, ["ZYG", "Zygosity", "zygosity", "GT"]).upper()
    if raw in {"HET", "HETEROZYGOUS", "0/1", "1/0", "0|1", "1|0"}:
        return "HET"
    if raw in {"HOM", "HOMOZYGOUS", "1/1", "1|1"}:
        return "HOM"
    if raw in {"HEMI", "HEMIZYGOUS", "1", "1/."}:
        return "HEMI"
    return "UNKNOWN"


def is_hfe_c282y(row):
    text = " ".join(value(row, [key]) for key in
                    ("HGVSp", "HGVSp_short", "Protein_position", "Amino_acids", "HGVSc"))
    normalized = text.casefold().replace("%3d", "=")
    return any(token in normalized for token in ("cys282tyr", "c282y", "c.845g>a"))


def annotate_acmg_inheritance(records, rules):
    candidates = [row for row in records if row.get("SYMBOL", row.get("Gene", "")).upper() in rules
                  and "ACMG_SF" in row.get("candidate_categories", "")]
    by_gene = {}
    for row in candidates:
        gene = value(row, ["SYMBOL", "Gene_Name", "Gene"]).upper()
        by_gene.setdefault(gene, []).append(row)

    matched = []
    for gene, rows in by_gene.items():
        rule = rules[gene]
        zygs = [zygosity(row) for row in rows]
        unique_het = {value(row, ["Uploaded_variation", "Location"]) for row in rows
                      if zygosity(row) == "HET"}
        for row, zyg in zip(rows, zygs):
            code = rule["variant_rule"]
            status, reason = "not_matched", "genotype does not satisfy the ACMG-SF v3.3 rule"
            if zyg == "UNKNOWN":
                status, reason = "unable_to_assess", "ZYG/GT is absent from the VEP result"
            elif code == "ALL_P_LP" and zyg in {"HET", "HOM", "HEMI"}:
                status, reason = "matched", "one P/LP allele satisfies an autosomal-dominant rule"
            elif code == "ALL_HEMI_HET_HOM_P_LP" and zyg in {"HET", "HOM", "HEMI"}:
                status, reason = "matched", "zygosity is explicitly reportable for this X-linked rule"
            elif code in {"TWO_P_LP", "HEMI_HOM_OR_TWO_HET"}:
                if zyg == "HOM" or (code == "HEMI_HOM_OR_TWO_HET" and zyg == "HEMI"):
                    status, reason = "matched", "homozygous/hemizygous genotype satisfies the rule"
                elif zyg == "HET" and len(unique_het) >= 2:
                    status, reason = "possible_unphased", "two heterozygous P/LP variants found; trans phase is not established"
                elif zyg == "HET":
                    status, reason = "carrier", "only one heterozygous P/LP variant found"
            elif code == "C282Y_HOM_ONLY" and zyg == "HOM" and is_hfe_c282y(row):
                status, reason = "matched", "HFE p.C282Y homozygous genotype satisfies the v3.3 exception"
            elif code == "TRUNCATING_P_LP_ONLY" and zyg in {"HET", "HOM", "HEMI"}:
                consequences, _ = functional_consequences(row)
                truncating = {"transcript_ablation", "splice_acceptor_variant", "splice_donor_variant",
                              "stop_gained", "frameshift_variant"}
                if consequences & truncating:
                    status, reason = "matched", "P/LP truncating TTN variant satisfies the v3.3 rule"
            row.update({
                "acmg_sf_disease": rule["disease"],
                "acmg_sf_inheritance": rule["inheritance"],
                "acmg_sf_variant_rule": code,
                "zygosity": zyg,
                "inheritance_status": status,
                "inheritance_reason": reason,
                "acmg_sf_source": rule["source"],
            })
            if status == "matched":
                matched.append(row.copy())
    return matched


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
    normalized_review = re.sub(r"[_-]+", " ", review.casefold())
    assertions = {x.strip() for x in re.split(r"[|/,;&]+", normalized) if x.strip()}
    pathogenic = "pathogenic" in assertions
    likely = "likely pathogenic" in assertions
    incompatible = {"benign", "likely benign", "uncertain significance"}
    review_conflict = "conflict" in normalized_review and not re.search(r"\bno conflicts?\b", normalized_review)
    conflict = ("conflict" in normalized or review_conflict
                or bool(assertions & incompatible) and (pathogenic or likely))
    valid_review = review.casefold() not in MISSING and "no assertion" not in review.casefold()
    # VEP's colocated-variant CLIN_SIG does not include CLNREVSTAT. A pure
    # P/LP assertion without an incompatible classification remains eligible;
    # review status is retained and scored whenever a richer ClinVar source is
    # available.
    eligible = (pathogenic or likely) and not conflict
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
        "PrimateAI": 0.8, "PrimateAI_score": 0.8,
        "am_pathogenicity": 0.564, "AlphaMissense_score": 0.564,
    }.items():
        scores = numbers(row.get(key))
        if scores and max(scores) >= threshold:
            votes.append(key)
    sift = value(row, ["SIFT", "SIFT_pred"]).casefold()
    if "deleterious" in sift:
        votes.append("SIFT")
    polyphen = value(row, ["PolyPhen", "Polyphen2_HDIV_pred", "Polyphen2_HVAR_pred"]).casefold()
    if "probably_damaging" in polyphen or "possibly_damaging" in polyphen:
        votes.append("PolyPhen")
    if "likely_pathogenic" in value(row, ["am_class"]).casefold():
        votes.append("AlphaMissense_class")
    for key in ("MutationTaster_pred",):
        if any(flag in str(row.get(key, "")).upper().split("&") for flag in ("D", "A")):
            votes.append(key)
    splice_scores = []
    combined_splice = value(row, ["SpliceAI_pred"])
    if combined_splice:
        parts = combined_splice.split("|")
        for token in parts[1:5]:
            try:
                splice_scores.append(float(token))
            except ValueError:
                pass
    splice_scores.extend(number(row.get(key)) or 0 for key in
                         ("SpliceAI_pred_DS_AG", "SpliceAI_pred_DS_AL", "SpliceAI_pred_DS_DG", "SpliceAI_pred_DS_DL"))
    splice = max(splice_scores, default=0)
    if splice >= 0.2:
        votes.append("SpliceAI")
    # A predictor can be represented by a score and a class; count it once.
    normalized = []
    families = set()
    for vote in votes:
        family = "AlphaMissense" if vote in {"am_pathogenicity", "AlphaMissense_score", "AlphaMissense_class"} else vote
        family = "PrimateAI" if vote == "PrimateAI_score" else family
        if family not in families:
            families.add(family)
            normalized.append(family)
    return normalized


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--gene-list")
    parser.add_argument("--acmg-genes")
    parser.add_argument("--acmg-rules")
    parser.add_argument("--population", choices=sorted(POPULATION_FIELDS), default="eas")
    parser.add_argument("--population-af-max", type=float, default=0.01)
    parser.add_argument("--predictor-min", type=int, default=7)
    args = parser.parse_args()
    phenotype_genes = genes(args.gene_list)
    acmg_genes = genes(args.acmg_genes)
    rules = acmg_rules(args.acmg_rules)

    opener = gzip.open if args.input.endswith(".gz") else open
    header, records_by_variant = None, {}
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
            selected_af, selected_source = max_number(row, POPULATION_FIELDS[args.population])
            global_af, global_source = max_number(row, GLOBAL_AF_FIELDS)
            observed_af = [(score, source) for score, source in (
                (selected_af, selected_source), (global_af, global_source)
            ) if score is not None]
            af, af_source = max(observed_af, default=(None, ""), key=lambda item: item[0])
            # "maximum AF" is inclusive: exactly the configured cutoff passes.
            if af is not None and af > args.population_af_max:
                continue
            clinical = pathogenicity(row)
            votes = damaging_votes(row)
            consequences, relevant_consequences = functional_consequences(row)
            if not relevant_consequences:
                continue
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
                "population_af_source": af_source,
                "population_af_status": "assumed_rare" if af is None else "observed",
                "population_af_filter_pass": "true",
                "functional_consequences": ",".join(sorted(relevant_consequences)),
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
            variant_key = (value(row, ["Uploaded_variation", "Location"]), gene, value(row, ["Allele"]))
            rank = (len(votes), row.get("PICK") == "1", bool(value(row, ["MANE_SELECT"])),
                    row.get("CANONICAL") == "YES")
            previous = records_by_variant.get(variant_key)
            if previous is None or rank > previous[0]:
                records_by_variant[variant_key] = (rank, row)

    records = [item[1] for item in records_by_variant.values()]

    inheritance_matched = annotate_acmg_inheritance(records, rules)
    extra = ["sample_id", "population", "population_af", "population_af_source", "population_af_status", "population_af_filter_pass", "functional_consequences", "normalized_pathogenicity", "clinvar_clinical_significance_raw", "clinvar_review_status", "clinvar_review_stars", "clinvar_conflict", "clinvar_id", "clinvar_evaluation_date", "damaging_predictor_count", "damaging_predictors", "candidate_categories", "acmg_sf_disease", "acmg_sf_inheritance", "acmg_sf_variant_rule", "zygosity", "inheritance_status", "inheritance_reason", "acmg_sf_source"]
    fields = (header or []) + [item for item in extra if item not in (header or [])]
    buckets = {
        "all_candidates": records,
        "known_clinvar_plp": [r for r in records if "KNOWN_CLINVAR_PLP" in r["candidate_categories"]],
        "phenotype_variants": [r for r in records if "PHENOTYPE_VARIANT" in r["candidate_categories"]],
        "acmg_sf": [r for r in records if "ACMG_SF" in r["candidate_categories"]],
        "acmg_sf_inheritance_matched": inheritance_matched,
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

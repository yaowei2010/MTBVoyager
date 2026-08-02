#!/usr/bin/env python3
"""Deterministically join PharmCAT calls to ClinPGx annotations.

Free-text evidence is retained but never parsed into an allele interpretation.
Only structured ClinPGx allele/genotype fields can produce ``allele_match``.
"""
import argparse
import csv
import json
import re
from pathlib import Path


MISSING = {"", "-", ".", "n/a", "null", "none"}
ALIASES = {
    "annotation_id": ("annotation_id", "id", "Variant Annotation ID", "Clinical Annotation ID"),
    "gene": ("gene", "geneSymbol", "Gene"),
    "variant": ("variant", "variantName", "Variant/Haplotypes", "Variant"),
    "allele": ("allele", "alleles", "genotype", "Allele", "Alleles", "Genotype"),
    "drug": ("drug", "chemical", "chemicals", "Drug(s)", "Drug"),
    "category": ("phenotypeCategory", "phenotype_category", "Phenotype Category"),
    "direction": ("direction", "association", "Direction", "Association"),
    "significance": ("significance", "Significance"),
    "evidence_level": ("levelOfEvidence", "evidenceLevel", "Level of Evidence"),
    "score": ("score", "Score"),
    "sentence": ("sentence", "summary", "Sentence", "Annotation Text"),
    "pmid": ("pmid", "PMID"),
    "url": ("url", "URL"),
}
OUTPUT_FIELDS = [
    "sample_id", "gene", "diplotype", "phenotype", "called_alleles",
    "variant", "sample_genotype", "clinpgx_allele", "drug",
    "phenotype_category", "direction", "significance", "evidence_level",
    "annotation_score", "match_status", "annotation_type", "annotation_id",
    "sentence", "pmid", "source_url", "clinpgx_release",
]


def scalar(item):
    if isinstance(item, dict):
        for key in ("symbol", "name", "label", "id", "accessionId"):
            if item.get(key) is not None:
                return scalar(item[key])
        return ""
    if isinstance(item, list):
        return ",".join(filter(None, (scalar(value) for value in item)))
    return "" if item is None else str(item).strip()


def pick(row, names):
    for name in names:
        if name in row and scalar(row[name]).casefold() not in MISSING:
            return scalar(row[name])
    return ""


def flatten(row, annotation_type):
    base = {key: pick(row, names) for key, names in ALIASES.items()}
    base["annotation_type"] = annotation_type
    base["gene"] = base["gene"] or scalar(row.get("genes") or row.get("relatedGenes"))
    base["drug"] = base["drug"] or scalar(row.get("chemicals") or row.get("relatedChemicals"))
    base["variant"] = base["variant"] or scalar(row.get("variant") or row.get("variants"))
    allele_values = row.get("allelePhenotypes") or row.get("alleleAssociations")
    if not isinstance(allele_values, list):
        return [base]
    expanded = []
    for item in allele_values:
        copy = dict(base)
        copy["allele"] = pick(item, ALIASES["allele"]) or scalar(item.get("allele"))
        copy["direction"] = pick(item, ALIASES["direction"]) or base["direction"]
        copy["sentence"] = pick(item, ALIASES["sentence"]) or base["sentence"]
        expanded.append(copy)
    return expanded


def load_annotations(path, annotation_type):
    if not path:
        return []
    source = Path(path)
    if source.suffix.casefold() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("data") or payload.get("content") or payload.get("results") or []
        if isinstance(rows, dict):
            rows = rows.get("content") or rows.get("data") or []
    else:
        with source.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    return [item for row in rows for item in flatten(row, annotation_type)]


def tokens(value):
    return {token.casefold() for token in re.split(r"\s*[,;/|]\s*", value) if token.strip()}


def pharmcat_calls(path):
    reports = json.loads(Path(path).read_text(encoding="utf-8")).get("geneReports", {})
    calls = []
    for gene, report in reports.items():
        diplotypes = report.get("sourceDiplotypes") or report.get("recommendationDiplotypes") or [{}]
        for diplotype in diplotypes:
            allele1 = scalar((diplotype.get("allele1") or {}).get("name"))
            allele2 = scalar((diplotype.get("allele2") or {}).get("name"))
            base = {
                "gene": gene, "diplotype": scalar(diplotype.get("label")),
                "phenotype": scalar(diplotype.get("phenotypes")),
                "called_alleles": ",".join(filter(None, (allele1, allele2))),
            }
            calls.append({**base, "variant": "", "sample_genotype": ""})
            for variant in report.get("variants") or []:
                calls.append({
                    **base,
                    "variant": scalar(variant.get("dbSnpId")) or f"{variant.get('chromosome')}:{variant.get('position')}",
                    "sample_genotype": scalar(variant.get("call")),
                })
    return calls


def match(call, annotation):
    genes = tokens(annotation["gene"])
    if genes and call["gene"].casefold() not in genes:
        return None
    variant = annotation["variant"].casefold()
    if variant and call["variant"] and call["variant"].casefold() not in tokens(variant):
        return None
    if variant and not call["variant"] and "*" not in variant:
        return None
    structured = tokens(annotation["allele"])
    if not structured:
        return "variant_match_allele_unresolved"
    observed = tokens(call["sample_genotype"]) | tokens(call["called_alleles"]) | tokens(call["diplotype"])
    observed |= {item.split()[-1].strip("()") for item in observed}
    return "allele_match" if structured & observed else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pharmcat-phenotype", required=True)
    parser.add_argument("--variant-annotations")
    parser.add_argument("--clinical-annotations")
    parser.add_argument("--sample", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--output-prefix", required=True)
    args = parser.parse_args()
    annotations = load_annotations(args.variant_annotations, "variant")
    annotations += load_annotations(args.clinical_annotations, "clinical")
    rows, seen = [], set()
    for call in pharmcat_calls(args.pharmcat_phenotype):
        for annotation in annotations:
            status = match(call, annotation)
            if not status:
                continue
            key = (call["gene"], call["diplotype"], call["variant"], annotation["annotation_id"], annotation["allele"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "sample_id": args.sample, **call, "clinpgx_allele": annotation["allele"],
                "drug": annotation["drug"], "phenotype_category": annotation["category"],
                "direction": annotation["direction"], "significance": annotation["significance"],
                "evidence_level": annotation["evidence_level"], "annotation_score": annotation["score"],
                "match_status": status, "annotation_type": annotation["annotation_type"],
                "annotation_id": annotation["annotation_id"], "sentence": annotation["sentence"],
                "pmid": annotation["pmid"], "source_url": annotation["url"],
                "clinpgx_release": args.release,
            })
    with open(f"{args.output_prefix}.clinpgx.tsv", "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, OUTPUT_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)
    resolved = sum(row["match_status"] == "allele_match" for row in rows)
    summary = {"sample_id": args.sample, "clinpgx_release": args.release,
               "annotation_count": len(rows), "allele_matched": resolved,
               "allele_unresolved": len(rows) - resolved,
               "method": "deterministic_structured_join", "ai_inference": False}
    Path(f"{args.output_prefix}.clinpgx.json").write_text(json.dumps({"summary": summary, "annotations": rows}, indent=2) + "\n")
    Path(f"{args.output_prefix}.clinpgx.summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()

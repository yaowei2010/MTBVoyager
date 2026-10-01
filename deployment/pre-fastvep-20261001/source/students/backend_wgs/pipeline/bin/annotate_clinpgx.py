#!/usr/bin/env python3
"""Join called PharmCAT PGx variants to a versioned ClinPGx snapshot."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

FIELDS = [
    "sample_id", "gene", "diplotype", "phenotype", "variant", "sample_genotype",
    "clinpgx_allele", "comparison", "drug", "phenotype_category", "association",
    "annotation_id", "sentence", "pmid", "source_url", "match_status", "clinpgx_release",
]


def scalar(value):
    if isinstance(value, list):
        return ", ".join(filter(None, (scalar(item) for item in value)))
    if isinstance(value, dict):
        for key in ("symbol", "name", "term", "label", "accessionId", "id", "resourceId"):
            if value.get(key) not in (None, ""):
                return scalar(value[key])
        return ""
    return "" if value is None else str(value).strip()


def load_rows(path):
    source = Path(path)
    if source.suffix.lower() == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return payload
        return payload.get("data") or payload.get("results") or payload.get("content") or []
    with source.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def locations(annotation):
    location = annotation.get("location") or {}
    if isinstance(location, list):
        location = location[0] if location else {}
    genes = location.get("genes") or annotation.get("genes") or annotation.get("relatedGenes") or annotation.get("Gene") or []
    if not isinstance(genes, list):
        genes = [genes]
    gene_names = {token.upper() for g in genes for token in re.split(r"\s*[,;/]\s*", scalar(g)) if token}
    fingerprints = (location.get("fingerprints") or location.get("fingerprint") or annotation.get("variant")
                    or annotation.get("Variant/Haplotypes") or [])
    if not isinstance(fingerprints, list):
        fingerprints = [fingerprints]
    return gene_names, {token.lower() for v in fingerprints for token in re.split(r"\s*[,;/]\s*", scalar(v)) if token}


def annotation_row(item):
    chemicals = item.get("relatedChemicals") or item.get("chemicals") or item.get("Drug(s)") or []
    categories = item.get("phenotypeCategories") or item.get("Phenotype Category") or []
    literature = item.get("literature") or {}
    association = "associated" if item.get("isAssociated") is True else "not associated" if item.get("isAssociated") is False else ""
    return {
        "clinpgx_allele": scalar(item.get("alleleGenotype") or item.get("allele") or item.get("Alleles")),
        "comparison": scalar(item.get("comparison") or item.get("Comparison Allele(s) or Genotype(s)")), "drug": scalar(chemicals),
        "phenotype_category": scalar(categories), "association": association,
        "annotation_id": scalar(item.get("id") or item.get("accessionId") or item.get("Variant Annotation ID")),
        "sentence": scalar(item.get("sentence") or item.get("description") or item.get("Sentence")),
        "pmid": scalar(literature) or scalar(item.get("PMID")),
        "source_url": scalar(item.get("@id") or item.get("url")),
    }


def calls(path):
    reports = json.loads(Path(path).read_text(encoding="utf-8")).get("geneReports", {})
    output = []
    for gene, report in reports.items():
        diplotypes = report.get("recommendationDiplotypes") or report.get("sourceDiplotypes") or [{}]
        variants = report.get("variants") or []
        for diplotype in diplotypes:
            base = {"gene": gene, "diplotype": scalar(diplotype.get("label")), "phenotype": scalar(diplotype.get("phenotypes"))}
            for allele_key in ("allele1", "allele2"):
                allele = scalar((diplotype.get(allele_key) or {}).get("name"))
                if allele and allele != "Unknown":
                    output.append({**base, "variant": f"{gene}{allele}", "sample_genotype": base["diplotype"]})
            for variant in variants:
                output.append({**base, "variant": scalar(variant.get("dbSnpId")), "sample_genotype": scalar(variant.get("call"))})
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pharmcat-phenotype", required=True)
    parser.add_argument("--variant-annotations", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--output-prefix", required=True)
    args = parser.parse_args()
    annotation_index = {}
    for item in load_rows(args.variant_annotations):
        genes, fingerprints = locations(item)
        for gene in genes:
            for fingerprint in fingerprints:
                annotation_index.setdefault((gene, fingerprint.replace(" ", "")), []).append(item)
    rows = []
    for call in calls(args.pharmcat_phenotype):
        normalized = call["variant"].lower().replace(" ", "")
        for item in annotation_index.get((call["gene"].upper(), normalized), []):
            detail = annotation_row(item)
            observed = [part.strip().upper() for part in call["sample_genotype"].replace("|", "/").split("/") if part.strip()]
            expected = [part.strip().upper() for part in detail["clinpgx_allele"].replace("|", "/").split("/") if part.strip()]
            exact_diplotype = len(expected) == 2 and Counter(expected) == Counter(observed)
            if not exact_diplotype:
                continue
            rows.append({"sample_id": args.sample, **call, **detail, "match_status": "exact_diplotype_match",
                         "clinpgx_release": args.release})
    unique = list({(row["gene"], row["diplotype"], row["annotation_id"], row["clinpgx_allele"]): row for row in rows}.values())
    with Path(f"{args.output_prefix}.clinpgx.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader(); writer.writerows(unique)
    summary = {"sample_id": args.sample, "clinpgx_release": args.release, "annotation_count": len(unique),
               "exact_diplotype_matched": len(unique), "single_allele_annotations_included": False,
               "method": "deterministic_exact_diplotype_join", "ai_inference": False}
    Path(f"{args.output_prefix}.clinpgx.json").write_text(json.dumps({"summary": summary, "annotations": unique}, indent=2) + "\n")
    Path(f"{args.output_prefix}.clinpgx.summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()

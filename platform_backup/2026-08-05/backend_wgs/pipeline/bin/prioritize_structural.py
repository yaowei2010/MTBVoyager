#!/usr/bin/env python3
import argparse
import csv
import gzip
import json
import re
import shutil
from pathlib import Path


def load_genes(path):
    result = set()
    if not path:
        return result
    for line in Path(path).read_text(errors="replace").splitlines():
        symbol = line.split("\t")[0].strip().upper()
        if symbol and symbol not in {"GENE", "GENES"} and not symbol.startswith("#"):
            result.add(symbol)
    return result


def parse_info(text):
    result = {}
    for item in text.split(";"):
        key, _, value = item.partition("=")
        result[key] = value if _ else "true"
    return result


def clinical(info):
    raw = next((info.get(k, "") for k in ("CLNSIG", "CLIN_SIG", "ClinVar_CLNSIG") if info.get(k)), "")
    review = next((info.get(k, "") for k in ("CLNREVSTAT", "CLINVAR_REVIEW_STATUS") if info.get(k)), "")
    normalized = re.sub(r"[_-]+", " ", raw.lower())
    conflict = "conflict" in normalized or "conflict" in review.lower()
    plp = ("pathogenic" in normalized) and not conflict and bool(review) and "no assertion" not in review.lower()
    return plp, raw, review, conflict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sv", required=True)
    parser.add_argument("--cnv", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--acmg-genes")
    args = parser.parse_args()
    acmg = load_genes(args.acmg_genes)
    known, acmg_rows = [], []
    opener = gzip.open if args.sv.endswith(".gz") else open
    with opener(args.sv, "rt", errors="replace") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 8:
                continue
            info = parse_info(fields[7])
            plp, raw, review, conflict = clinical(info)
            if not plp:
                continue
            gene = next((info.get(k, "") for k in ("SYMBOL", "GENE", "Gene_name") if info.get(k)), "").split(",")[0].upper()
            row = {"sample_id": args.sample, "chromosome": fields[0], "position": fields[1], "id": fields[2], "ref": fields[3], "alt": fields[4], "filter": fields[6], "gene": gene, "svtype": info.get("SVTYPE", ""), "end": info.get("END", ""), "clinvar_clinical_significance_raw": raw, "clinvar_review_status": review, "clinvar_conflict": str(conflict).lower(), "normalized_pathogenicity": "P/LP"}
            known.append(row)
            if gene in acmg:
                acmg_rows.append(row)
    fields = ["sample_id", "chromosome", "position", "id", "ref", "alt", "filter", "gene", "svtype", "end", "clinvar_clinical_significance_raw", "clinvar_review_status", "clinvar_conflict", "normalized_pathogenicity"]
    for suffix, rows in (("known_pathogenic", known), ("acmg_sf", acmg_rows)):
        with open(f"{args.output_prefix}.sv.{suffix}.tsv", "w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
            writer.writeheader(); writer.writerows(rows)
    shutil.copyfile(args.cnv, f"{args.output_prefix}.cnv.input.vcf.gz")
    Path(f"{args.output_prefix}.structural.summary.json").write_text(json.dumps({"known_pathogenic_sv": len(known), "acmg_sf_sv": len(acmg_rows)}, indent=2) + "\n")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Reduce an Ensembl GFF3 to one representative transcript per gene.

Selection is deterministic and clinical-report oriented:
MANE Select > MANE Plus Clinical > Ensembl canonical > protein coding >
APPRIS > TSL > CCDS > transcript length > transcript identifier.
"""

import argparse
import gzip
import re
from collections import Counter
from pathlib import Path

CANONICAL_CONTIGS = {str(value) for value in range(1, 23)} | {"X", "Y", "MT", "M"}


def canonical_contig(value):
    return value.removeprefix("chr") in CANONICAL_CONTIGS


def open_text(path, mode="rt"):
    return gzip.open(path, mode) if str(path).endswith(".gz") else open(path, mode)


def attributes(text):
    result = {}
    for item in text.rstrip().split(";"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


def plain_id(value):
    return value.split(":", 1)[-1] if value else ""


def tags(attrs):
    return {tag.strip().lower().replace(" ", "_") for tag in attrs.get("tag", "").split(",") if tag}


def appris_rank(attrs):
    for tag in tags(attrs):
        match = re.search(r"appris_(?:principal|p)_?(\d+)$", tag)
        if match:
            return int(match.group(1))
        match = re.search(r"appris_(?:alternative|alt|a)_?(\d+)$", tag)
        if match:
            return 10 + int(match.group(1))
    return 100


def tsl_rank(attrs):
    match = re.search(r"\d+", attrs.get("transcript_support_level", ""))
    return int(match.group()) if match else 100


def transcript_rank(attrs, start, end):
    transcript_tags = tags(attrs)
    biotype = attrs.get("biotype", attrs.get("transcript_biotype", ""))
    return (
        "mane_select" not in transcript_tags,
        "mane_plus_clinical" not in transcript_tags,
        "ensembl_canonical" not in transcript_tags,
        biotype != "protein_coding",
        appris_rank(attrs),
        tsl_rank(attrs),
        not bool(attrs.get("ccdsid")),
        -(end - start + 1),
        plain_id(attrs.get("ID", attrs.get("transcript_id", ""))),
    )


def choose_transcripts(gff3):
    selected = {}
    transcript_to_gene = {}
    counts = Counter()
    with open_text(gff3) as source:
        for line in source:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] not in {"mRNA", "transcript"}:
                continue
            if not canonical_contig(fields[0]):
                counts["noncanonical_contig_transcripts"] += 1
                continue
            attrs = attributes(fields[8])
            transcript = plain_id(attrs.get("ID", attrs.get("transcript_id", "")))
            gene = plain_id(attrs.get("Parent", attrs.get("gene_id", ""))).split(",", 1)[0]
            if not transcript or not gene:
                counts["malformed_transcripts"] += 1
                continue
            transcript_to_gene[transcript] = gene
            candidate = (transcript_rank(attrs, int(fields[3]), int(fields[4])), transcript)
            if gene not in selected or candidate < selected[gene]:
                selected[gene] = candidate
            counts["input_transcripts"] += 1
    return {item[1] for item in selected.values()}, set(selected), transcript_to_gene, counts


def filter_gff3(source_path, output_path, selected_transcripts, selected_genes, transcript_to_gene, counts):
    temporary = Path(str(output_path) + ".partial")
    with open_text(source_path) as source, open_text(temporary, "wt") as target:
        for line in source:
            if line.startswith("#"):
                target.write(line)
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9:
                continue
            if not canonical_contig(fields[0]):
                continue
            attrs = attributes(fields[8])
            feature = fields[2]
            keep = False
            if feature == "gene":
                keep = plain_id(attrs.get("ID", attrs.get("gene_id", ""))) in selected_genes
            elif feature in {"mRNA", "transcript"}:
                keep = plain_id(attrs.get("ID", attrs.get("transcript_id", ""))) in selected_transcripts
            elif "Parent" in attrs:
                parents = {plain_id(parent) for parent in attrs["Parent"].split(",")}
                keep = bool(parents & selected_transcripts)
            else:
                # Preserve chromosome/region records required by some GFF readers.
                keep = feature in {"chromosome", "region", "supercontig"}
            if keep:
                target.write(line)
                counts["output_features"] += 1
    temporary.replace(output_path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_gff3")
    parser.add_argument("output_gff3")
    args = parser.parse_args()
    selected, genes, transcript_to_gene, counts = choose_transcripts(args.input_gff3)
    filter_gff3(args.input_gff3, args.output_gff3, selected, genes, transcript_to_gene, counts)
    print(f"genes={len(genes)} selected_transcripts={len(selected)} "
          f"input_transcripts={counts['input_transcripts']} output_features={counts['output_features']}")


if __name__ == "__main__":
    main()

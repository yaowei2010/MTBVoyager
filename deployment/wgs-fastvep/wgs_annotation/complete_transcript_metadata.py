#!/usr/bin/env python3
"""Add explicitly marked GFF-only transcripts to the baseline metadata export."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote


def complete(metadata, gff3, output):
    rows = {}
    for line in Path(metadata).open():
        row = json.loads(line)
        row["_metadata_source"] = "vep112_cache"
        rows[row["Feature"]] = row
    genes, lengths, coding_lengths = {}, defaultdict(int), defaultdict(int)
    additions = {}
    with Path(gff3).open() as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            cols = line.rstrip().split("\t")
            if len(cols) != 9:
                continue
            attrs = dict(part.split("=", 1) for part in cols[8].split(";") if "=" in part)
            ident = attrs.get("ID", "")
            if ident.startswith("gene:"):
                genes[ident.removeprefix("gene:")] = unquote(attrs.get("Name", ""))
            if cols[2] in ("exon", "CDS"):
                for parent in attrs.get("Parent", "").split(","):
                    target = coding_lengths if cols[2] == "CDS" else lengths
                    target[parent.removeprefix("transcript:")] += int(cols[4]) - int(cols[3]) + 1
            if ident.startswith("transcript:"):
                tid = ident.removeprefix("transcript:")
                if tid in rows:
                    continue
                tags = attrs.get("tag", "").split(",")
                gene = attrs.get("Parent", "").removeprefix("gene:")
                additions[tid] = {"Feature": tid, "Gene": gene, "SYMBOL": genes.get(gene, ""),
                                  "BIOTYPE": attrs.get("biotype", ""),
                                  "CANONICAL": "YES" if "Ensembl_canonical" in tags else "",
                                  "MANE_SELECT": "MANE_Select" if "MANE_Select" in tags else "",
                                  "MANE_PLUS_CLINICAL": "MANE_Plus_Clinical" if "MANE_Plus_Clinical" in tags else "",
                                  "CCDS": attrs.get("ccdsid", ""), "TSL": "", "APPRIS": "",
                                  "_cache_release": 112, "_assembly": "GRCh38", "_metadata_source": "gff3_only"}
    for tid, row in additions.items():
        row["_length"] = coding_lengths[tid] or lengths[tid]
        rows[tid] = row
    with Path(output).open("w") as handle:
        for tid in sorted(rows):
            handle.write(json.dumps(rows[tid], sort_keys=True) + "\n")
    print(json.dumps({"baseline_transcripts": len(rows) - len(additions), "gff3_only_transcripts": len(additions)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--gff3", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    complete(args.metadata, args.gff3, args.output)

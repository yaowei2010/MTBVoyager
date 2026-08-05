#!/usr/bin/env python3
"""Build the platform MONDO autocomplete and Monarch gene-association TSVs.

Inputs are the official MONDO OBO Graph JSON and a Monarch disease-gene TSV.
The association parser accepts common Monarch column names and preserves the
source release metadata supplied on the command line.
"""
import argparse
import csv
import gzip
import json
from collections import defaultdict, deque
from pathlib import Path


def compact(identifier):
    return identifier.rsplit("/", 1)[-1].replace("_", ":")


def first(row, names):
    for name in names:
        if row.get(name):
            return row[name].strip()
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mondo-json", required=True)
    parser.add_argument("--gene-associations", required=True)
    parser.add_argument("--mondo-rare-json", help="Official MONDO rare-disease subset OBO Graph JSON")
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--mondo-release", required=True)
    parser.add_argument("--monarch-release", required=True)
    args = parser.parse_args()
    output = Path(args.outdir)
    output.mkdir(parents=True, exist_ok=True)

    graph_data = json.loads(Path(args.mondo_json).read_text(encoding="utf-8"))
    graph = graph_data["graphs"][0]
    terms, parents = {}, defaultdict(set)
    for node in graph.get("nodes", []):
        mondo_id = compact(node.get("id", ""))
        if not mondo_id.startswith("MONDO:") or node.get("meta", {}).get("deprecated"):
            continue
        synonyms = [item.get("val", "") for item in node.get("meta", {}).get("synonyms", []) if item.get("val")]
        terms[mondo_id] = {"label": node.get("lbl", mondo_id), "synonyms": synonyms}
    for edge in graph.get("edges", []):
        if edge.get("pred") == "is_a":
            child, parent = compact(edge.get("sub", "")), compact(edge.get("obj", ""))
            if child in terms and parent in terms:
                parents[child].add(parent)

    rare_ids = set()
    if args.mondo_rare_json:
        rare_data = json.loads(Path(args.mondo_rare_json).read_text(encoding="utf-8"))
        for rare_graph in rare_data.get("graphs", []):
            for node in rare_graph.get("nodes", []):
                mondo_id = compact(node.get("id", ""))
                if mondo_id in terms:
                    rare_ids.add(mondo_id)

    associations = set()
    genes_by_term = defaultdict(set)
    association_path = Path(args.gene_associations)
    opener = gzip.open if association_path.suffix == ".gz" else open
    with opener(association_path, "rt", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            if "Gene" in row.get("subject_category", ""):
                disease = compact(first(row, ["object", "disease_id"]))
                gene = first(row, ["subject_label", "gene_symbol", "gene"]).upper()
            else:
                disease = compact(first(row, ["subject", "disease_id", "subject_id"]))
                gene = first(row, ["object_label", "gene_symbol", "gene"]).upper()
            if disease not in terms or not gene:
                continue
            genes_by_term[disease].add(gene)
            associations.add((disease, disease, gene))
            queue, visited = deque(parents[disease]), set()
            while queue:
                ancestor = queue.popleft()
                if ancestor in visited:
                    continue
                visited.add(ancestor)
                associations.add((disease, ancestor, gene))
                queue.extend(parents[ancestor])

    with (output / "mondo_terms.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "label", "synonyms", "gene_count", "is_rare_disease"], delimiter="\t")
        writer.writeheader()
        for mondo_id, term in sorted(terms.items(), key=lambda item: item[1]["label"].casefold()):
            writer.writerow({
                "id": mondo_id,
                "label": term["label"],
                "synonyms": "|".join(term["synonyms"]),
                "gene_count": len(genes_by_term[mondo_id]),
                "is_rare_disease": "true" if mondo_id in rare_ids else "false",
            })
    with (output / "mondo_gene_associations.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["mondo_id", "ancestor_mondo_id", "gene_symbol"])
        writer.writerows(sorted(associations))
    (output / "release.json").write_text(json.dumps({"mondo": args.mondo_release, "monarch": args.monarch_release}, indent=2) + "\n")


if __name__ == "__main__":
    main()

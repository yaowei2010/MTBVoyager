#!/usr/bin/env python3
"""Populate the local literature RAG database for a bounded gene list."""
import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uploadfunction.settings")

from wgs_germline.literature import _pubmed_articles  # noqa: E402
from wgs_germline.literature_store import statistics, store_articles  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--genes", required=True, help="Text file containing one HGNC gene symbol per line")
    parser.add_argument("--phenotype", action="append", default=[], help="Optional disease/phenotype label; repeatable")
    parser.add_argument("--retmax", type=int, default=12)
    parser.add_argument("--database", help="Override LITERATURE_RAG_DB")
    args = parser.parse_args()
    if args.database:
        os.environ["LITERATURE_RAG_DB"] = str(Path(args.database).resolve())
    genes = []
    for line in Path(args.genes).read_text(encoding="utf-8").splitlines():
        gene = line.strip().upper()
        if gene and not gene.startswith("#") and gene not in genes:
            genes.append(gene)
    for index, gene in enumerate(genes, 1):
        query, articles = _pubmed_articles(gene, args.phenotype, limit=max(1, min(args.retmax, 50)))
        store_articles(gene, query, args.phenotype, articles)
        print(f"[{index}/{len(genes)}] {gene}: {len(articles)} articles", flush=True)
    print(statistics())


if __name__ == "__main__":
    main()

import csv
import json
import os
from functools import lru_cache
from pathlib import Path


QUERY_ALIASES = {
    "遺傳性癌症": "hereditary cancer",
}


@lru_cache(maxsize=1)
def _terms():
    path = Path(os.environ.get("MONDO_TERMS_TSV", "/wgs_reference/mondo/mondo_terms.tsv"))
    if not path.exists():
        return []
    with path.open(encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def search(query: str, limit: int):
    needle = query.casefold().strip()
    if not needle:
        return []
    needle = QUERY_ALIASES.get(needle, needle)
    ranked = []
    for row in _terms():
        mondo_id = row.get("id", "")
        label = row.get("label", "")
        synonyms = row.get("synonyms", "")
        haystack = f"{mondo_id} {label} {synonyms}".casefold()
        if needle in haystack:
            score = 0 if label.casefold().startswith(needle) else 1
            ranked.append((score, label.casefold(), {
                "id": mondo_id,
                "label": label,
                "synonyms": [x for x in synonyms.split("|") if x],
                "gene_count": int(row.get("gene_count") or 0),
                "is_rare_disease": row.get("is_rare_disease", "").lower() in {"1", "true", "yes"},
            }))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in ranked[:limit]]


def resolve_genes(phenotypes, include_descendants: bool):
    association_path = Path(os.environ.get("MONDO_GENE_ASSOCIATIONS_TSV", "/wgs_reference/mondo/mondo_gene_associations.tsv"))
    selected = {p.get("mondo_id") for p in phenotypes if p.get("mondo_id")}
    genes = set()
    if association_path.exists() and selected:
        with association_path.open(encoding="utf-8", errors="replace") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                if row.get("mondo_id") in selected or (include_descendants and row.get("ancestor_mondo_id") in selected):
                    genes.add((row.get("gene_symbol") or "").upper())
    genes.discard("")
    release_file = Path(os.environ.get("MONDO_RELEASE_FILE", "/wgs_reference/mondo/release.json"))
    release = {"mondo": "unknown", "monarch": "unknown"}
    if release_file.exists():
        try:
            release.update(json.loads(release_file.read_text()))
        except json.JSONDecodeError:
            pass
    return sorted(genes), release

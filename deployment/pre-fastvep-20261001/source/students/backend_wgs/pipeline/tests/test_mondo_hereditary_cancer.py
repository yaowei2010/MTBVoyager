from pathlib import Path

from wgs_germline import mondo


ROOT = Path(__file__).parents[4]
MONDO_DIR = ROOT / "database" / "mondo"


def test_hereditary_cancer_mondo_descendant_resolution(monkeypatch):
    monkeypatch.setenv("MONDO_TERMS_TSV", str(MONDO_DIR / "mondo_terms.tsv"))
    monkeypatch.setenv("MONDO_GENE_ASSOCIATIONS_TSV", str(MONDO_DIR / "mondo_gene_associations.tsv"))
    monkeypatch.setenv("MONDO_RELEASE_FILE", str(MONDO_DIR / "release.json"))
    mondo._terms.cache_clear()

    matches = mondo.search("hereditary cancer", 20)
    concept = next(item for item in matches if item["id"] == "MONDO:0015356")
    assert concept["label"] == "hereditary neoplastic syndrome"

    direct, release = mondo.resolve_genes([{"mondo_id": concept["id"]}], False)
    descendants, _ = mondo.resolve_genes([{"mondo_id": concept["id"]}], True)
    assert direct == []
    assert len(descendants) == 94
    assert {"APC", "ATM", "BRCA1", "BRCA2", "MLH1", "MSH2", "MSH6", "PALB2", "PMS2", "TP53"} <= set(descendants)
    assert release == {"mondo": "2026-07-06", "monarch": "2026-04-07"}


def test_chinese_hereditary_cancer_alias_resolves(monkeypatch):
    monkeypatch.setenv("MONDO_TERMS_TSV", str(MONDO_DIR / "mondo_terms.tsv"))
    mondo._terms.cache_clear()
    matches = mondo.search("遺傳性癌症", 20)
    assert any(item["id"] == "MONDO:0015356" for item in matches)

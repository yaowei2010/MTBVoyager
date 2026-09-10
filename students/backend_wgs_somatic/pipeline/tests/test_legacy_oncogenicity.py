import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT.parent / "wgs_somatic" / "legacy_oncogenicity.py"
SPEC = importlib.util.spec_from_file_location("legacy_oncogenicity", HELPER)
legacy = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(legacy)


def test_adapter_uses_only_available_legacy_fields():
    row = legacy.adapt_legacy_row({"Gene": "KRAS", "Amino acid change": "G12D",
        "MAF": "{'gnomAD': 0.0}", "Prediction": "{'CADD': 25.3}",
        "Pathogenicity": "{'CLNSIG': 'Pathogenic'}"})
    assert {key: row[key] for key in ("SYMBOL", "Consequence", "HGVSp", "CLIN_SIG", "Amino_acids", "Protein_position", "gnomADe_AF", "CADD_phred")} == {
        "SYMBOL": "KRAS", "Consequence": "missense_variant", "HGVSp": "p.G12D",
        "CLIN_SIG": "Pathogenic", "Amino_acids": "G/D", "Protein_position": "12",
        "gnomADe_AF": 0.0, "CADD_phred": 25.3}
    assert "ClinVar_review_status" not in row


def test_adapter_accepts_complete_legacy_merge_rows():
    row = legacy.adapt_legacy_row({"SYMBOL": "BRAF", "Consequence": "missense_variant",
        "Amino_acids": "V/E", "Protein_position": "600", "HGVSp": "ENSP:p.V600E",
        "CLNSIG": "Pathogenic", "AF": "0.0001", "CADD_phred": "31"})
    assert row["SYMBOL"] == "BRAF"
    assert row["Consequence"] == "missense_variant"
    assert row["Amino_acids"] == "V/E"
    assert row["Protein_position"] == "600"
    assert row["CLIN_SIG"] == "Pathogenic"
    assert row["gnomADe_AF"] == "0.0001"


def test_high_risk_matches_wgs_core_gate():
    assert legacy.is_high_risk({"Consequence": "missense_variant", "CLNSIG": "Likely_pathogenic"})
    assert legacy.is_high_risk({"Consequence": "frameshift_variant", "oncogenicity_classification": "Oncogenic"})
    assert not legacy.is_high_risk({"Consequence": "synonymous_variant", "CLNSIG": "Pathogenic"})
    assert not legacy.is_high_risk({"Consequence": "missense_variant", "CLNSIG": "Conflicting_classifications_of_pathogenicity"})


def test_annotation_is_persisted_and_marks_hg19_limitations(tmp_path, monkeypatch):
    source = tmp_path / "somatic_result.csv"
    with source.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Location", "Gene", "Amino acid change", "MAF", "Prediction", "Pathogenicity"])
        writer.writeheader(); writer.writerow({"Location": "chr12:25398284_25398284C>T", "Gene": "KRAS",
            "Amino acid change": "G12D", "MAF": "{'gnomAD': 0.0}", "Prediction": "{'CADD': 25.3}",
            "Pathogenicity": "{'CLNSIG': 'Pathogenic'}"})
    monkeypatch.setenv("WGS_SOMATIC_PIPELINE_SOURCE", str(ROOT))
    monkeypatch.setenv("WGS_ONCOVI_RESOURCES", str(ROOT / "tests" / "data" / "oncovi_resources"))
    legacy.engine.cache_clear(); legacy.resources.cache_clear()
    rows, summary = legacy.annotate(source, tmp_path / "result.tsv", tmp_path / "summary.json")
    assert rows[0]["oncogenicity_coordinate_build"] == "GRCh37/hg19"
    assert rows[0]["oncogenicity_review_required"] == "true"
    assert rows[0]["oncogenicity_profile"] == legacy.LEGACY_PROFILE
    assert summary["variants"] == 1
    assert (tmp_path / "result.tsv").is_file() and (tmp_path / "summary.json").is_file()

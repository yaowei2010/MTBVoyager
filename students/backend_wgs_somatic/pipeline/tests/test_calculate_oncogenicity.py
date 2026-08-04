import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("calculate_oncogenicity", ROOT / "bin" / "calculate_oncogenicity.py")
oncogenicity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(oncogenicity)
RESOURCES = oncogenicity.Resources(ROOT / "tests" / "data" / "oncovi_resources")


def evidence_map(row):
    score, label, evidence, dual = oncogenicity.evaluate(row, RESOURCES)
    return score, label, {item["code"]: item for item in evidence}, dual


def test_score_boundaries_follow_2022_sop():
    expected = {10: "Oncogenic", 9: "Likely Oncogenic", 6: "Likely Oncogenic",
                5: "VUS", 0: "VUS", -1: "Likely Benign", -6: "Likely Benign", -7: "Benign"}
    assert {score: oncogenicity.classify(score) for score in expected} == expected


def test_exact_braf_v600e_applies_os1_without_double_counting_hotspot():
    score, label, evidence, _ = evidence_map({
        "SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/E",
        "Protein_position": "600", "gnomADe_AF": "0.00001"
    })
    assert evidence["OS1"]["status"] == "met"
    assert evidence["OS3"]["status"] == "excluded"
    assert evidence["OS2"]["status"] == "not_assessable"
    assert score == 5
    assert label == "VUS"


def test_population_evidence_is_not_double_counted():
    _, _, evidence, _ = evidence_map({
        "SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/K",
        "Protein_position": "600", "gnomADe_AF": "0.2", "gnomADe_EAS_AF": "0.2"
    })
    assert evidence["SBVS1"]["status"] == "met"
    assert evidence["SBS1"]["status"] == "excluded"


def test_op1_requires_all_available_predictor_groups_to_agree():
    _, _, evidence, _ = evidence_map({
        "SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/K",
        "Protein_position": "600", "CADD_phred": "30", "REVEL_score": "0.9",
        "SpliceAI_cutoff": "FAIL"
    })
    assert evidence["OP1"]["status"] == "not_met"


def test_ovs1_uses_null_variant_in_bona_fide_tsg():
    score, label, evidence, _ = evidence_map({
        "SYMBOL": "TP53", "Consequence": "frameshift_variant", "gnomADe_AF": "0.00001"
    })
    assert evidence["OVS1"]["status"] == "met"
    assert score == 9
    assert label == "Likely Oncogenic"

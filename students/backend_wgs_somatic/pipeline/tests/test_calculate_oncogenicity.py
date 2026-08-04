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


def test_oncovi_2026_reference_uses_upstream_predictor_or_rule():
    _, _, strict, _ = evidence_map({
        "SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/E",
        "Protein_position": "600", "gnomADe_AF": "0.00001",
        "phyloP100way_vertebrate_rankscore": "0.95", "SpliceAI_cutoff": "FAIL"
    })
    score, label, evidence = oncogenicity.evaluate_reference({}, RESOURCES, list(strict.values()))
    assert {item["code"]: item["status"] for item in evidence}["OP1"] == "not_met"

    row = {"SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/E",
           "Protein_position": "600", "gnomADe_AF": "0.00001",
           "phyloP100way_vertebrate_rankscore": "0.95", "SpliceAI_cutoff": "FAIL"}
    strict_score, _, strict_evidence, _ = oncogenicity.evaluate(row, RESOURCES)
    score, label, evidence = oncogenicity.evaluate_reference(row, RESOURCES, strict_evidence)
    assert strict_score == 5
    assert score == 6
    assert label == "Likely Oncogenic"


def test_oncovi_2026_reference_reproduces_population_double_counting():
    row = {"SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/K",
           "Protein_position": "600", "gnomADe_AF": "0.2", "gnomADe_EAS_AF": "0.2"}
    _, _, strict_evidence, _ = oncogenicity.evaluate(row, RESOURCES)
    _, _, evidence = oncogenicity.evaluate_reference(row, RESOURCES, strict_evidence)
    statuses = {item["code"]: item["status"] for item in evidence}
    assert statuses["SBVS1"] == "met"
    assert statuses["SBS1"] == "met"


def test_op3_requires_the_exact_substitution_to_exist():
    row = {"SYMBOL": "BRAF", "Consequence": "missense_variant", "Amino_acids": "V/K",
           "Protein_position": "600", "gnomADe_AF": "0.00001"}
    _, _, evidence, _ = oncogenicity.evaluate(row, RESOURCES)
    assert {item["code"]: item["status"] for item in evidence}["OP3"] == "met"
    row["Amino_acids"] = "V/R"
    _, _, evidence, _ = oncogenicity.evaluate(row, RESOURCES)
    assert {item["code"]: item["status"] for item in evidence}["OP3"] == "not_met"


def test_frameshift_hgvsp_is_converted_to_one_letter_cgi_key():
    assert oncogenicity.protein_key({"HGVSp": "NP_006209.2:p.Asn1068LysfsTer5"}) == "N1068Kfs*5"


def test_reference_op4_follows_upstream_either_dataset_rule():
    row={"SYMBOL":"BRAF","Consequence":"missense_variant","Amino_acids":"V/K","Protein_position":"600",
         "gnomADe_AF":"0.00148","gnomADg_AF":"0.01329"}
    _,_,strict,_=oncogenicity.evaluate(row,RESOURCES)
    _,_,reference=oncogenicity.evaluate_reference(row,RESOURCES,strict)
    assert {item["code"]:item["status"] for item in strict}["OP4"] == "not_met"
    assert {item["code"]:item["status"] for item in reference}["OP4"] == "met"

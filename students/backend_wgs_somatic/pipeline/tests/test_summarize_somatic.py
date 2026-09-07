import argparse
import csv
import gzip
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "summarize_somatic.py"
spec = importlib.util.spec_from_file_location("summarize_somatic", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_truthy_requires_explicit_evidence():
    assert module.truthy({"CLIN_SIG": "Pathogenic"}, ["CLIN_SIG"])
    assert not module.truthy({"CLIN_SIG": "uncertain_significance"}, ["CLIN_SIG"])


def test_gzip_opener(tmp_path):
    path = tmp_path / "input.tsv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("a\tb\n1\t2\n")
    with module.opener(path) as handle:
        assert handle.readline().strip() == "a\tb"


def test_protein_change_is_one_letter_exact():
    assert module.protein_change({"Amino_acids": "V/E", "Protein_position": "600"}) == "V600E"
    assert module.protein_change({"HGVSp": "ENSP0001:p.Val600Glu"}) == "V600E"


def test_tumor_context_is_explicit():
    rows = [{"source": "CIViC", "disease": "Lung Adenocarcinoma"}]
    assert module.mark_tumor_context(rows, "lung")[0]["tumor_type_match"] == "true"


def test_vep_annotations_collapse_to_pick_per_allele():
    rows = [
        {"#Uploaded_variation": "chr7_1_A/T", "PICK": "-", "HGVSp": "wrong"},
        {"#Uploaded_variation": "chr7_1_A/T", "PICK": "1", "HGVSp": "picked"},
    ]
    selected = module.collapse_vep_annotations(rows)
    assert len(selected) == 1
    assert selected[0]["HGVSp"] == "picked"


def test_reportable_gate_requires_non_synonymous_and_high_risk():
    assert module.reportable_high_risk({"Consequence": "missense_variant", "CLIN_SIG": "Pathogenic"})
    assert module.reportable_high_risk({"Consequence": "frameshift_variant", "oncogenicity_classification": "Likely Oncogenic"})
    assert not module.reportable_high_risk({"Consequence": "synonymous_variant", "CLIN_SIG": "Pathogenic"})
    assert not module.reportable_high_risk({"Consequence": "missense_variant", "CLIN_SIG": "Uncertain_significance"})
    assert not module.reportable_high_risk({"Consequence": "missense_variant", "oncogenicity_classification": "VUS"})


def test_conflicting_clinvar_is_not_high_risk():
    row = {"Consequence": "missense_variant", "CLIN_SIG": "Conflicting_classifications_of_pathogenicity"}
    assert not module.clinvar_pathogenic(row)
    assert not module.reportable_high_risk(row)


def test_mixed_consequence_is_retained_when_one_term_is_non_synonymous():
    row = {"Consequence": "synonymous_variant&splice_region_variant", "CLIN_SIG": "Likely_pathogenic"}
    assert module.reportable_high_risk(row)


def test_drug_matching_runs_only_for_reportable_high_risk(monkeypatch, tmp_path):
    class FakeEvidence:
        calls = []

        def __init__(self, _directory): pass

        def snv(self, row):
            self.calls.append(row["#Uploaded_variation"])
            return [{"source": "test", "actionable": True}]

        def manifest(self): return {"matching": "test"}

    monkeypatch.setattr(module, "CancerEvidence", FakeEvidence)
    source = tmp_path / "variants.tsv"
    source.write_text(
        "#Uploaded_variation\tConsequence\tCLIN_SIG\toncogenicity_classification\n"
        "chr1_1_A/T\tmissense_variant\tPathogenic\tVUS\n"
        "chr1_2_A/T\tmissense_variant\t\tVUS\n"
        "chr1_3_A/T\tsynonymous_variant\tPathogenic\tOncogenic\n"
    )
    genes = tmp_path / "genes.txt"
    genes.write_text("TP53\n")
    prefix = tmp_path / "sample"
    args = argparse.Namespace(input=source, cancer_db=tmp_path, cancer_type="", population_af_max=.01,
                              acmg_genes=genes, output_prefix=str(prefix), sample="sample")
    module.snv(args)

    with open(f"{prefix}.snv.reportable.tsv", newline="") as handle:
        reportable = list(csv.DictReader(handle, delimiter="\t"))
    with open(f"{prefix}.snv.actionable.tsv", newline="") as handle:
        actionable = list(csv.DictReader(handle, delimiter="\t"))
    assert FakeEvidence.calls == ["chr1_1_A/T"]
    assert [row["#Uploaded_variation"] for row in reportable] == ["chr1_1_A/T"]
    assert [row["#Uploaded_variation"] for row in actionable] == ["chr1_1_A/T"]

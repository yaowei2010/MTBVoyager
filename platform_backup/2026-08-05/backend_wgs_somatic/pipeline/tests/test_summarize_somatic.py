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

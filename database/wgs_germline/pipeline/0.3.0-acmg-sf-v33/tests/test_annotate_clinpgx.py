import csv
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "annotate_clinpgx.py"


def test_structured_allele_join_and_unresolved_text(tmp_path):
    phenotype = {
        "geneReports": {
            "ABCG2": {
                "sourceDiplotypes": [{
                    "label": "rs2231142 reference (G)/rs2231142 variant (T)",
                    "allele1": {"name": "rs2231142 reference (G)"},
                    "allele2": {"name": "rs2231142 variant (T)"},
                    "phenotypes": ["Decreased Function"],
                }],
                "variants": [{"dbSnpId": "rs2231142", "call": "G/T"}],
            }
        }
    }
    variant_annotations = {"data": [
        {"id": "VA1", "gene": "ABCG2", "variant": "rs2231142", "allele": "T",
         "drug": "rosuvastatin", "phenotypeCategory": "Dosage",
         "direction": "decreased function", "sentence": "Curated structured evidence."},
        {"id": "VA2", "gene": "ABCG2", "variant": "rs2231142",
         "drug": "rosuvastatin", "sentence": "Free text mentions T but must not be parsed."},
        {"id": "VA3", "gene": "ABCG2", "variant": "rs2231142", "allele": "C",
         "drug": "rosuvastatin", "sentence": "Non-matching allele."},
    ]}
    clinical_annotations = {"data": []}
    phenotype_path = tmp_path / "sample.phenotype.json"
    variant_path = tmp_path / "variant.json"
    clinical_path = tmp_path / "clinical.json"
    phenotype_path.write_text(json.dumps(phenotype))
    variant_path.write_text(json.dumps(variant_annotations))
    clinical_path.write_text(json.dumps(clinical_annotations))

    subprocess.run([
        sys.executable, str(SCRIPT), "--pharmcat-phenotype", str(phenotype_path),
        "--variant-annotations", str(variant_path), "--clinical-annotations", str(clinical_path),
        "--sample", "S1", "--release", "2026-08-02",
        "--output-prefix", str(tmp_path / "S1"),
    ], check=True)

    with (tmp_path / "S1.clinpgx.tsv").open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [(row["annotation_id"], row["match_status"]) for row in rows] == [
        ("VA1", "allele_match"), ("VA2", "variant_match_allele_unresolved")
    ]
    summary = json.loads((tmp_path / "S1.clinpgx.summary.json").read_text())
    assert summary == {
        "sample_id": "S1", "clinpgx_release": "2026-08-02",
        "annotation_count": 2, "allele_matched": 1, "allele_unresolved": 1,
        "method": "deterministic_structured_join", "ai_inference": False,
    }


def test_tsv_input_is_supported(tmp_path):
    phenotype_path = tmp_path / "sample.phenotype.json"
    phenotype_path.write_text(json.dumps({"geneReports": {"CYP2C19": {
        "sourceDiplotypes": [{"label": "*1/*2", "allele1": {"name": "*1"},
                               "allele2": {"name": "*2"}, "phenotypes": ["Intermediate Metabolizer"]}],
        "variants": [],
    }}}))
    annotations = tmp_path / "clinical.tsv"
    annotations.write_text(
        "Clinical Annotation ID\tGene\tVariant/Haplotypes\tAllele\tDrug(s)\tPhenotype Category\n"
        "CA1\tCYP2C19\tCYP2C19*1,CYP2C19*2\t*2\tclopidogrel\tEfficacy\n"
    )
    empty = tmp_path / "variant.tsv"
    empty.write_text("Variant Annotation ID\tGene\n")
    subprocess.run([
        sys.executable, str(SCRIPT), "--pharmcat-phenotype", str(phenotype_path),
        "--variant-annotations", str(empty), "--clinical-annotations", str(annotations),
        "--sample", "S2", "--release", "r1", "--output-prefix", str(tmp_path / "S2"),
    ], check=True)
    rows = list(csv.DictReader((tmp_path / "S2.clinpgx.tsv").open(), delimiter="\t"))
    assert len(rows) == 1
    assert rows[0]["match_status"] == "allele_match"
    assert rows[0]["drug"] == "clopidogrel"

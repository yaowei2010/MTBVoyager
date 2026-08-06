import csv
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "prioritize_variants.py"
ACMG_GENES = Path(__file__).parents[1] / "assets" / "acmg_sf_gene_disease.tsv"
ACMG_RULES = Path(__file__).parents[1] / "assets" / "acmg_sf_v3.3_rules.tsv"


def test_existing_vep_fields_and_conflict_filter(tmp_path):
    fields = [
        "Uploaded_variation", "Location", "Allele", "SYMBOL", "Consequence", "CLIN_SIG",
        "CLINVAR_REVIEW_STATUS", "gnomADe_EAS_AF", "gnomADe_AF", "PICK", "MANE_SELECT", "CANONICAL",
        "SIFT", "PolyPhen", "am_class", "am_pathogenicity", "PrimateAI",
        "SpliceAI_pred", "CADD_phred", "ClinPred_score", "REVEL_score",
    ]
    rows = [
        ["chr1_10_A/G", "chr1:10", "G", "BRCA1", "missense_variant", "likely_pathogenic", "", "0.0001", "0.0002", "1", "NM_1", "YES",
         "deleterious(0.01)", "probably_damaging(0.99)", "likely_pathogenic", "0.9", "0.95",
         "BRCA1|0.30|0.00|0.00|0.00|1|2|3|4", "30", "0.9", "0.95,0.90"],
        ["chr1_20_C/T", "chr1:20", "T", "BRCA2", "missense_variant", "benign,pathogenic", "criteria_provided", "0.0001", "0.0002", "1", "NM_2", "YES",
         "deleterious(0.01)", "probably_damaging(0.99)", "likely_pathogenic", "0.9", "0.95",
         "BRCA2|0.30|0.00|0.00|0.00|1|2|3|4", "30", "0.9", "0.95"],
    ]
    source = tmp_path / "vep.tsv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["#" + fields[0], *fields[1:]])
        writer.writerows(rows)
    acmg = tmp_path / "acmg.tsv"
    acmg.write_text("genes\tACMG\nBRCA1\tACMG\nBRCA2\tACMG\n")
    prefix = tmp_path / "sample"
    subprocess.run([
        sys.executable, str(SCRIPT), "--input", str(source), "--sample", "sample",
        "--output-prefix", str(prefix), "--acmg-genes", str(acmg), "--predictor-min", "7",
    ], check=True)
    summary = json.loads((tmp_path / "sample.prioritization.summary.json").read_text())
    assert summary == {
        "all_candidates": 2, "known_clinvar_plp": 1,
        "phenotype_variants": 0, "acmg_sf": 1,
        "acmg_sf_inheritance_matched": 0, "insilico": 2,
    }
    with (tmp_path / "sample.all_candidates.tsv").open() as handle:
        result = next(csv.DictReader(handle, delimiter="\t"))
    assert result["SYMBOL"] == "BRCA1"
    assert result["clinvar_conflict"] == "false"
    assert int(result["damaging_predictor_count"]) >= 7


def test_common_af_functional_filter_and_missing_af_audit(tmp_path):
    fields = [
        "Uploaded_variation", "Location", "Allele", "SYMBOL", "Consequence",
        "CLIN_SIG", "CLINVAR_REVIEW_STATUS", "gnomADe_EAS_AF", "gnomADe_AF",
        "PICK", "MANE_SELECT", "CANONICAL",
    ]
    rows = [
        # EAS-common: excluded even though global AF is rare.
        ["v1", "chr1:1", "G", "BRCA1", "missense_variant", "pathogenic", "expert_panel", "0.02", "0.0001", "1", "NM_1", "YES"],
        # Globally common: excluded even though EAS AF is rare.
        ["v2", "chr1:2", "G", "BRCA1", "missense_variant", "pathogenic", "expert_panel", "0.0001", "0.02", "1", "NM_1", "YES"],
        # Exactly at the configured maximum is retained.
        ["v3", "chr1:3", "G", "BRCA1", "missense_variant", "pathogenic", "expert_panel", "0.01", "0.001", "1", "NM_1", "YES"],
        # Synonymous-only annotation is not a functional candidate.
        ["v4", "chr1:4", "G", "BRCA1", "synonymous_variant", "pathogenic", "expert_panel", "0.0001", "0.0001", "1", "NM_1", "YES"],
        # Missing AF is retained but explicitly auditable.
        ["v5", "chr1:5", "G", "BRCA1", "splice_donor_variant", "pathogenic", "expert_panel", "", "", "1", "NM_1", "YES"],
    ]
    source = tmp_path / "vep.tsv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["#" + fields[0], *fields[1:]])
        writer.writerows(rows)
    prefix = tmp_path / "sample"
    subprocess.run([
        sys.executable, str(SCRIPT), "--input", str(source), "--sample", "sample",
        "--output-prefix", str(prefix), "--population", "eas",
        "--population-af-max", "0.01",
    ], check=True)
    with (tmp_path / "sample.known_clinvar_plp.tsv").open() as handle:
        results = list(csv.DictReader(handle, delimiter="\t"))
    assert [row["Uploaded_variation"] for row in results] == ["v3", "v5"]
    assert results[0]["population_af"] == "0.01"
    assert results[0]["population_af_source"] == "gnomADe_EAS_AF"
    assert results[1]["population_af_status"] == "assumed_rare"
    assert results[1]["functional_consequences"] == "splice_donor_variant"


def test_hereditary_cancer_phenotype_and_acmg_sf_are_independent(tmp_path):
    """Model MONDO:0015356 (hereditary neoplastic syndrome) candidates."""
    fields = [
        "Uploaded_variation", "Location", "Allele", "SYMBOL", "Consequence",
        "CLIN_SIG", "CLINVAR_REVIEW_STATUS", "gnomADe_EAS_AF", "gnomADe_AF",
        "PICK", "MANE_SELECT", "CANONICAL",
    ]
    rows = [
        # BRCA1 belongs to both hereditary-cancer phenotype and ACMG SF.
        ["both", "chr1:1", "G", "BRCA1", "frameshift_variant", "pathogenic", "expert_panel", "0.00001", "0.00001", "1", "NM_1", "YES"],
        # ATM is a hereditary-cancer phenotype gene but is not on ACMG SF v3.3.
        ["phenotype", "chr1:2", "G", "ATM", "missense_variant", "likely_pathogenic", "criteria_provided,_multiple_submitters,_no_conflicts", "0.0001", "0.0001", "1", "NM_2", "YES"],
        # LDLR is ACMG SF but unrelated to the hereditary-cancer phenotype.
        ["acmg", "chr1:3", "G", "LDLR", "missense_variant", "pathogenic", "expert_panel", "0.0001", "0.0001", "1", "NM_3", "YES"],
        # A common cancer-gene variant must enter neither bucket.
        ["common", "chr1:4", "G", "TP53", "missense_variant", "pathogenic", "expert_panel", "0.02", "0.001", "1", "NM_4", "YES"],
        # A synonymous-only cancer-gene variant must enter neither bucket.
        ["synonymous", "chr1:5", "G", "MSH2", "synonymous_variant", "pathogenic", "expert_panel", "0.0001", "0.0001", "1", "NM_5", "YES"],
        # Phenotype membership alone is insufficient without P/LP evidence.
        ["vus", "chr1:6", "G", "BAP1", "missense_variant", "uncertain_significance", "expert_panel", "0.0001", "0.0001", "1", "NM_6", "YES"],
    ]
    source = tmp_path / "vep.tsv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["#" + fields[0], *fields[1:]])
        writer.writerows(rows)
    phenotype_genes = tmp_path / "hereditary_cancer_genes.txt"
    phenotype_genes.write_text("BRCA1\nATM\nTP53\nMSH2\nBAP1\n")
    prefix = tmp_path / "sample"
    subprocess.run([
        sys.executable, str(SCRIPT), "--input", str(source), "--sample", "sample",
        "--output-prefix", str(prefix), "--population", "eas",
        "--population-af-max", "0.01", "--gene-list", str(phenotype_genes),
        "--acmg-genes", str(ACMG_GENES),
    ], check=True)

    def ids(suffix):
        with (tmp_path / f"sample.{suffix}.tsv").open() as handle:
            return {row["Uploaded_variation"] for row in csv.DictReader(handle, delimiter="\t")}

    assert ids("phenotype_variants") == {"both", "phenotype"}
    assert ids("acmg_sf") == {"both", "acmg"}
    assert ids("known_clinvar_plp") == {"both", "phenotype", "acmg"}


def test_acmg_sf_v33_gene_asset():
    genes = {
        line.split("\t")[0] for line in ACMG_GENES.read_text().splitlines()[1:]
        if line and not line.startswith("#")
    }
    assert len(genes) == 84
    assert {"ABCD1", "CYP27A1", "PLN"} <= genes
    with ACMG_RULES.open() as handle:
        rules = list(csv.DictReader(handle, delimiter="\t"))
    assert len(rules) == 84
    assert {row["gene"] for row in rules} == genes
    assert {row["source"] for row in rules} == {"PMID:40568962"}
    assert {row["variant_rule"] for row in rules} == {
        "ALL_P_LP", "TWO_P_LP", "ALL_HEMI_HET_HOM_P_LP",
        "HEMI_HOM_OR_TWO_HET", "C282Y_HOM_ONLY", "TRUNCATING_P_LP_ONLY",
    }


def test_acmg_sf_v33_inheritance_and_special_rules(tmp_path):
    fields = [
        "Uploaded_variation", "Location", "Allele", "SYMBOL", "Consequence", "HGVSp",
        "CLIN_SIG", "CLINVAR_REVIEW_STATUS", "gnomADe_EAS_AF", "gnomADe_AF", "ZYG",
    ]
    rows = [
        ["brca", "chr1:1", "G", "BRCA1", "frameshift_variant", "p.X1fs", "pathogenic", "expert_panel", "0.0001", "0.0001", "HET"],
        ["mutyh_hom", "chr1:2", "G", "MUTYH", "missense_variant", "p.Gly1Asp", "pathogenic", "expert_panel", "0.0001", "0.0001", "HOM"],
        ["atp7b_1", "chr1:3", "G", "ATP7B", "missense_variant", "p.Gly1Asp", "pathogenic", "expert_panel", "0.0001", "0.0001", "HET"],
        ["atp7b_2", "chr1:4", "T", "ATP7B", "missense_variant", "p.Gly2Asp", "likely_pathogenic", "expert_panel", "0.0001", "0.0001", "HET"],
        ["hfe_wrong", "chr1:5", "G", "HFE", "missense_variant", "p.His63Asp", "pathogenic", "expert_panel", "0.0001", "0.0001", "HOM"],
        ["hfe_c282y", "chr1:6", "A", "HFE", "missense_variant", "p.Cys282Tyr", "pathogenic", "expert_panel", "0.0001", "0.0001", "HOM"],
        ["ttn_missense", "chr1:7", "G", "TTN", "missense_variant", "p.Gly1Asp", "pathogenic", "expert_panel", "0.0001", "0.0001", "HET"],
        ["ttn_trunc", "chr1:8", "G", "TTN", "stop_gained", "p.Gly2Ter", "pathogenic", "expert_panel", "0.0001", "0.0001", "HET"],
        ["abcd1_carrier", "chrX:9", "G", "ABCD1", "missense_variant", "p.Gly1Asp", "pathogenic", "expert_panel", "0.0001", "0.0001", "HET"],
        ["abcd1_hemi", "chrX:10", "G", "ABCD1", "missense_variant", "p.Gly2Asp", "pathogenic", "expert_panel", "0.0001", "0.0001", "HEMI"],
    ]
    source = tmp_path / "vep.tsv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["#" + fields[0], *fields[1:]])
        writer.writerows(rows)
    prefix = tmp_path / "sample"
    subprocess.run([
        sys.executable, str(SCRIPT), "--input", str(source), "--sample", "sample",
        "--output-prefix", str(prefix), "--acmg-genes", str(ACMG_GENES),
        "--acmg-rules", str(ACMG_RULES),
    ], check=True)

    with (tmp_path / "sample.acmg_sf_inheritance_matched.tsv").open() as handle:
        matched = {row["Uploaded_variation"] for row in csv.DictReader(handle, delimiter="\t")}
    assert matched == {"brca", "mutyh_hom", "hfe_c282y", "ttn_trunc", "abcd1_hemi"}

    with (tmp_path / "sample.acmg_sf.tsv").open() as handle:
        candidates = {row["Uploaded_variation"]: row for row in csv.DictReader(handle, delimiter="\t")}
    assert candidates["atp7b_1"]["inheritance_status"] == "possible_unphased"
    assert candidates["atp7b_2"]["inheritance_status"] == "possible_unphased"
    assert candidates["hfe_wrong"]["inheritance_status"] == "not_matched"
    assert candidates["ttn_missense"]["inheritance_status"] == "not_matched"
    assert candidates["abcd1_carrier"]["inheritance_status"] == "carrier"

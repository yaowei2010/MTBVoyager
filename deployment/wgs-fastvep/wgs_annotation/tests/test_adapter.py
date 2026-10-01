import csv
import gzip
import importlib.util
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

import pysam

SCRIPT = Path(__file__).resolve().parents[1] / "fastvep_to_mtb.py"
spec = importlib.util.spec_from_file_location("adapter", SCRIPT)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def table(directory, name, header, rows):
    path = directory / name
    raw = directory / (name + ".txt")
    raw.write_text("#" + "\t".join(header) + "\n" + "".join("\t".join(map(str, r)) + "\n" for r in rows))
    pysam.tabix_compress(str(raw), str(path), force=True)
    pysam.tabix_index(str(path), seq_col=0, start_col=1, end_col=1, force=True)


def fixture(root):
    """Synthetic test data, with one damaging missense and a nonzero allele AF."""
    plugins = root / "plugins"
    plugins.mkdir()
    table(plugins, "dbNSFP5.3.1a_grch38.gz",
          ["chr", "pos(1-based)", "ref", "alt", "aaref", "aaalt"] + adapter.DB_FIELDS +
          ["Ensembl_transcriptid", "SIFT_score", "SIFT_pred", "Polyphen2_HDIV_score", "Polyphen2_HDIV_pred"],
          [["1", 5, "A", "G", "K", "R", .8, 25, .9, .8, .7, "SYNTH_T1", .01, "D", .99, "D"]])
    table(plugins, "AlphaMissense_hg38.tsv.gz",
          ["CHROM", "POS", "REF", "ALT", "protein_variant", "am_pathogenicity", "am_class"],
          [["chr1", 5, "A", "G", "K2R", .9, "likely_pathogenic"]])
    table(plugins, "PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz",
          ["chr", "pos", "ref", "alt", "primateDL_score"], [["chr1", 5, "A", "G", .9]])
    for name in ("spliceai_scores.raw.snv.hg38.vcf.gz", "spliceai_scores.raw.indel.hg38.vcf.gz"):
        raw = root / (name + ".vcf")
        raw.write_text('##fileformat=VCFv4.2\n##INFO=<ID=SpliceAI,Number=.,Type=String,Description="SpliceAI">\n'
                       '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n'
                       'chr1\t5\t.\tA\tG\t.\t.\tSpliceAI=G|GENEA|0.6|0|0|0|1|0|0|0\n')
        path = plugins / name
        pysam.tabix_compress(str(raw), str(path), force=True)
        pysam.tabix_index(str(path), preset="vcf", force=True)
    cache = root / "cache" / "homo_sapiens" / "112_GRCh38"
    (cache / "1").mkdir(parents=True)
    columns = ["variation_name", "failed", "somatic", "start", "end", "allele_string", "strand",
               "clin_sig", "phenotype_or_disease", "clin_sig_allele", "pubmed", "gnomADe", "gnomADg", "gnomADg_EAS"]
    (cache / "info.txt").write_text("species\thomo_sapiens\nassembly\tGRCh38\nvariation_cols\t" + ",".join(columns) + "\n")
    with gzip.open(cache / "1" / "1-1000000_var.gz", "wt") as f:
        f.write(" ".join(["rsSYNTH", "", "", "5", "5", "A/G/T", "1", "pathogenic,benign", "1", "G:pathogenic;T:benign", "", "G:0.005", "G:0.002,T:0.8", "G:0"]) + "\n")
    metadata = root / "transcripts.jsonl"
    metadata.write_text(json.dumps({"Feature": "SYNTH_T1", "Gene": "SYNTH_G1", "SYMBOL": "GENEA",
                                   "BIOTYPE": "protein_coding", "CANONICAL": "YES", "MANE_SELECT": "NM_SYNTH.1",
                                   "_length": 18, "_cache_release": 112, "_assembly": "GRCh38"}) + "\n")
    vcf = root / "input.vcf"
    vcf.write_text('##fileformat=VCFv4.2\n##contig=<ID=chr1,length=248956422>\n'
                  '##FILTER=<ID=PASS,Description="Pass">\n'
                  '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">\n'
                  '##FORMAT=<ID=DP,Number=1,Type=Integer,Description="Depth">\n'
                  '##FORMAT=<ID=GQ,Number=1,Type=Integer,Description="Quality">\n'
                  '##FORMAT=<ID=AD,Number=R,Type=Integer,Description="Allelic depth">\n'
                  '#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tCALLER_SAMPLE\n'
                  'chr1\t5\t.\tA\tG\t100\tPASS\t.\tGT:DP:GQ:AD\t0|1:40:99:25,15\n')
    obj = {"seq_region_name": "chr1", "start": 5, "end": 5, "allele_string": "A/G",
           "transcript_consequences": [{"gene_id": "SYNTH_G1", "transcript_id": "SYNTH_T1",
             "gene_symbol": "GENEA", "biotype": "protein_coding", "variant_allele": "G",
             "consequence_terms": ["missense_variant"], "impact": "MODERATE", "amino_acids": "K/R",
             "protein_start": 2, "protein_end": 2, "hgvsc": "SYNTH_T1:c.5A>G", "hgvsp": "SYNTH_P1:p.Lys2Arg"}]}
    annotation = root / "input.json"
    annotation.write_text(json.dumps([obj]))
    reference = root / "reference.fa"
    reference.write_text(">chr1\nATGAAAGCCGAATACTAA" + "A" * 22 + "\n")
    pysam.faidx(str(reference))
    gff = root / "reference.gff3"
    gff.write_text("##gff-version 3\n"
                  "chr1\ttest\tgene\t1\t18\t.\t+\t.\tID=gene:SYNTH_G1;Name=GENEA;biotype=protein_coding\n"
                  "chr1\ttest\tmRNA\t1\t18\t.\t+\t.\tID=transcript:SYNTH_T1;Parent=gene:SYNTH_G1;biotype=protein_coding;tag=Ensembl_canonical;version=1\n"
                  "chr1\ttest\texon\t1\t18\t.\t+\t.\tParent=transcript:SYNTH_T1;rank=1\n"
                  "chr1\ttest\tCDS\t1\t18\t.\t+\t0\tParent=transcript:SYNTH_T1;protein_id=SYNTH_P1\n")
    args = Namespace(input_json=str(annotation), vcf=str(vcf), vcf_sample=None,
                     output=str(root / "output.tsv.gz"), summary=str(root / "summary.json"),
                     plugin_data=str(plugins), variation_cache=str(cache), transcript_metadata=str(metadata))
    return args, obj


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.args, self.obj = fixture(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def rows(self):
        with gzip.open(self.args.output, "rt") as f:
            return list(csv.DictReader((line for line in f if not line.startswith("##")), delimiter="\t"))

    def test_complete_annotation_preserves_phased_genotype_and_allele_af(self):
        adapter.run(self.args)
        row = self.rows()[0]
        self.assertEqual(row["#Uploaded_variation"], "chr1_5_A/G")
        self.assertEqual((row["GT"], row["ZYG"], row["IND"]), ("0|1", "HET", "CALLER_SAMPLE"))
        self.assertEqual(row["gnomADg_AF"], "0.002")
        self.assertEqual(row["gnomADg_EAS_AF"], "0.0")
        self.assertEqual(row["CLIN_SIG"], "pathogenic")
        self.assertEqual(row["PICK"], "1")
        self.assertEqual(row["MANE_SELECT"], "NM_SYNTH.1")
        self.assertEqual(row["CADD_phred"], "25")
        self.assertEqual(row["SpliceAI_cutoff"], "PASS")
        self.assertEqual(row["am_class"], "likely_pathogenic")
        summary = json.loads(Path(self.args.summary).read_text())
        self.assertEqual(summary["counts"], {"variants": 1, "transcript_rows": 1})

    def test_missing_database_is_an_error_not_an_empty_score(self):
        Path(self.args.plugin_data, "dbNSFP5.3.1a_grch38.gz.tbi").unlink()
        with self.assertRaisesRegex(ValueError, "Missing indexed"):
            adapter.run(self.args)
        self.assertFalse(Path(self.args.output).exists())

    def test_record_loss_and_reordering_fail_without_partial_output(self):
        for annotations in ([], [dict(self.obj, start=6)]):
            Path(self.args.input_json).write_text(json.dumps(annotations))
            with self.assertRaises(ValueError):
                adapter.run(self.args)
            self.assertFalse(Path(self.args.output).exists())
            self.assertFalse(Path(self.args.output + ".partial").exists())

    def test_gene_and_peptide_specific_plugins_do_not_leak(self):
        sources = adapter.Supplementary(self.args.plugin_data, self.args.variation_cache, self.args.transcript_metadata)
        v = next(adapter.read_vcf(self.args.vcf))
        self.obj["transcript_consequences"][0]["amino_acids"] = "K/L"
        rows = adapter.convert_record(self.obj, v, sources)
        self.assertEqual(rows[0]["am_pathogenicity"], "")
        self.assertEqual(rows[0]["CADD_phred"], "")
        rows[0]["SYMBOL"] = "GENEB"
        self.assertFalse(any(x[1] == "GENEB" for x in sources.variant_data(v)["splice"]))

    def test_pick_is_per_gene_and_retains_all_transcripts(self):
        rows = [dict(Feature="A", Gene="G1", Allele="T", Consequence="stop_gained", MANE_SELECT=""),
                dict(Feature="B", Gene="G1", Allele="T", Consequence="missense_variant", MANE_SELECT="NM_B"),
                dict(Feature="C", Gene="G2", Allele="T", Consequence="missense_variant", MANE_SELECT="")]
        adapter.mark_pick(rows)
        self.assertEqual(len(rows), 3)
        self.assertEqual([r["Feature"] for r in rows if r.get("PICK")], ["B", "C"])

    def test_unsupported_multiallelic_and_multisample_input_rejected(self):
        original = Path(self.args.vcf).read_text()
        Path(self.args.vcf).write_text(original.replace("\tA\tG\t100", "\tA\tG,T\t100"))
        with self.assertRaisesRegex(ValueError, "single-ALT"):
            list(adapter.read_vcf(self.args.vcf))
        Path(self.args.vcf).write_text(original.replace("\tCALLER_SAMPLE\n", "\tCALLER_SAMPLE\tSECOND\n")
                                     .replace("0|1:40:99:25,15\n", "0|1:40:99:25,15\t1/1:40:99:0,40\n"))
        with self.assertRaisesRegex(ValueError, "Multi-sample"):
            list(adapter.read_vcf(self.args.vcf))

    def test_indel_shape_uses_unanchored_coordinates(self):
        self.assertEqual(adapter.fastvep_shape(10, "A", "AT"), (11, 10, "-/T"))
        self.assertEqual(adapter.fastvep_shape(10, "AT", "A"), (11, 11, "T/-"))
        self.assertEqual(adapter.minimal(10, "ACT", "AT"), (11, "C", "-"))

    def test_missing_variation_block_is_fatal(self):
        Path(self.args.variation_cache, "1", "1-1000000_var.gz").unlink()
        with self.assertRaisesRegex(ValueError, "Missing variation cache block"):
            adapter.run(self.args)
        self.assertFalse(Path(self.args.output).exists())

    def test_clinvar_assertions_are_specific_to_the_matched_allele(self):
        cache = adapter.VariationCache(self.args.variation_cache)
        v = next(adapter.read_vcf(self.args.vcf))
        self.assertEqual(cache.annotate(v)["CLIN_SIG"], "pathogenic")
        self.assertEqual(cache.annotate(dict(v, alt="T"))["CLIN_SIG"], "benign")


if __name__ == "__main__":
    unittest.main()

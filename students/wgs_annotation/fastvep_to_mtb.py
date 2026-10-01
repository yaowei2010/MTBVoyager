#!/usr/bin/env python3
"""Stream fastVEP JSON into MTB's transcript TSV using the existing GRCh38 data.

No Ensembl consequence caller is invoked. Required databases are opened before
output, and every JSON record is paired with and checked against the normalized
single-ALT VCF. Memory is bounded by one variant and the current database blocks.
"""
import argparse
import csv
import gzip
import hashlib
import itertools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import ijson
import pysam

ADAPTER_VERSION = "0.1.0"
FASTVEP_COMMIT = "ac2e2b64a9c4c27163a3df16e0a559113af19625"
DB_FIELDS = ["REVEL_score", "CADD_phred", "ClinPred_score",
             "phyloP100way_vertebrate_rankscore", "phastCons100way_vertebrate_rankscore"]
POPS = ["AFR", "AMR", "ASJ", "EAS", "FIN", "NFE", "OTH", "SAS", "AMI", "MID"]
AF_FIELDS = [prefix + suffix + "_AF" for prefix in ("gnomADe", "gnomADg")
             for suffix in [""] + ["_" + p for p in POPS]]
FIELDS = ["#Uploaded_variation", "Location", "Allele", "Gene", "Feature", "Feature_type",
          "Consequence", "cDNA_position", "CDS_position", "Protein_position", "Amino_acids",
          "Codons", "Existing_variation", "IMPACT", "SYMBOL", "BIOTYPE", "EXON", "INTRON",
          "HGVSc", "HGVSp", "HGVSg", "CANONICAL", "MANE_SELECT", "MANE_PLUS_CLINICAL",
          "APPRIS", "TSL", "CCDS", "ENSP", "PICK", "DISTANCE", "STRAND", "SIFT", "PolyPhen",
          "CLIN_SIG", "SOMATIC", "PHENO", "PUBMED", "AF"] + AF_FIELDS + DB_FIELDS + [
          "am_pathogenicity", "am_class", "PrimateAI", "SpliceAI_pred", "SpliceAI_cutoff",
          "SpliceAI_pred_DS_AG", "SpliceAI_pred_DS_AL", "SpliceAI_pred_DS_DG", "SpliceAI_pred_DS_DL",
          "GT", "ZYG", "IND", "REF", "ALT", "ANNOTATION_ENGINE", "ANNOTATION_VERSION",
          "ANNOTATION_DATA_STATUS", "TRANSCRIPT_METADATA_SOURCE"]
SO_ORDER = """transcript_ablation splice_acceptor_variant splice_donor_variant stop_gained
frameshift_variant stop_lost start_lost transcript_amplification feature_elongation
feature_truncation inframe_insertion inframe_deletion missense_variant protein_altering_variant
splice_region_variant splice_donor_5th_base_variant splice_donor_region_variant
splice_polypyrimidine_tract_variant incomplete_terminal_codon_variant start_retained_variant
stop_retained_variant synonymous_variant coding_sequence_variant mature_miRNA_variant
5_prime_UTR_variant 3_prime_UTR_variant non_coding_transcript_exon_variant intron_variant
NMD_transcript_variant non_coding_transcript_variant coding_transcript_variant upstream_gene_variant
downstream_gene_variant TFBS_ablation TFBS_amplification TF_binding_site_variant
regulatory_region_ablation regulatory_region_amplification regulatory_region_variant
intergenic_variant sequence_variant""".split()
SO_RANK = {name: rank for rank, name in enumerate(SO_ORDER, 1)}
DB_CONSEQUENCES = {"missense_variant", "stop_lost", "stop_gained", "start_lost"}


def clean(value):
    return "" if value is None or str(value) in ("", ".", "-") else str(value)


def chrom_key(chrom):
    body = chrom.removeprefix("chr")
    return "MT" if body in ("M", "MT") else body


def aliases(chrom):
    body = chrom_key(chrom)
    return [chrom, body, "chr" + body] + (["M", "chrM"] if body == "MT" else [])


def minimal(pos, ref, alt):
    """Unanchored minimal pair; insertion end is start-1, as in VEP."""
    ref, alt = ref.replace("-", ""), alt.replace("-", "")
    while ref and alt and ref[-1] == alt[-1]:
        ref, alt = ref[:-1], alt[:-1]
    while ref and alt and ref[0] == alt[0]:
        pos += 1
        ref, alt = ref[1:], alt[1:]
    return pos, ref or "-", alt or "-"


def fastvep_shape(pos, ref, alt):
    # The pinned parser removes one shared anchor for a single-ALT indel.
    if len(ref) != len(alt) and ref[0] == alt[0]:
        pos += 1
        ref, alt = ref[1:] or "-", alt[1:] or "-"
    end = pos - 1 if ref == "-" else pos + len(ref) - 1
    return pos, end, ref + "/" + alt


def read_vcf(path, requested_sample=None):
    opener = gzip.open if str(path).endswith((".gz", ".bgz")) else open
    with opener(path, "rt") as handle:
        sample_index = None
        sample = ""
        for line in handle:
            if line.startswith("#CHROM"):
                samples = line.rstrip().split("\t")[9:]
                if requested_sample:
                    if requested_sample not in samples:
                        raise ValueError("Requested VCF sample is absent")
                    sample_index = samples.index(requested_sample)
                elif len(samples) == 1:
                    sample_index = 0
                elif len(samples) > 1:
                    raise ValueError("Multi-sample VCF requires explicit --vcf-sample")
                if sample_index is not None:
                    sample = samples[sample_index]
                continue
            if line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 8:
                raise ValueError("Malformed input VCF")
            chrom, pos, ident, ref, alt = cols[:5]
            if "," in alt or not re.fullmatch("[ACGTN]+", ref) or not re.fullmatch("[ACGTN]+", alt):
                raise ValueError("fastVEP WGS requires normalized single-ALT SNV/INDEL records")
            gt = ""
            if sample_index is not None:
                values = dict(zip(cols[8].split(":"), cols[9 + sample_index].split(":")))
                gt = values.get("GT", "")
            yield {"chrom": chrom, "pos": int(pos), "ref": ref, "alt": alt,
                   "id": ident, "sample": sample, "gt": gt}


def zygosity(gt):
    alleles = re.split(r"[/|]", gt)
    if not gt or "." in alleles:
        return "UNKNOWN"
    if len(alleles) == 1:
        return "HEMI" if alleles[0] == "1" else "UNKNOWN"
    if all(a == "1" for a in alleles):
        return "HOM"
    return "HET" if "1" in alleles and "0" in alleles else "UNKNOWN"


class IndexedTable:
    """One tabix window in memory. A missing chromosome is not a failed source."""
    def __init__(self, path, required, position, window=16384):
        self.path = Path(path)
        if not self.path.is_file() or not any(Path(str(path) + ext).is_file() for ext in (".tbi", ".csi")):
            raise ValueError(f"Missing indexed annotation source: {self.path.name}")
        self.handle = pysam.TabixFile(str(path))
        headers = [h.lstrip("#").split("\t") for h in self.handle.header]
        self.header = next((h for h in headers if set(required) <= set(h)), None)
        if self.header is None:
            raise ValueError(f"Required header fields absent: {self.path.name}")
        self.cols = {name: i for i, name in enumerate(self.header)}
        self.position = self.cols[position]
        self.window = window
        self.block = None
        self.records = {}

    def at(self, chrom, pos):
        mapped = next((c for c in aliases(chrom) if c in self.handle.contigs), None)
        if mapped is None:
            return []
        start = (pos - 1) // self.window * self.window
        block = (mapped, start)
        if block != self.block:
            records = defaultdict(list)
            for line in self.handle.fetch(mapped, start, start + self.window):
                cols = line.split("\t")
                if len(cols) != len(self.header):
                    raise ValueError(f"Malformed row in {self.path.name}")
                records[int(cols[self.position])].append(cols)
            self.block, self.records = block, records
        return self.records.get(pos, [])

    def value(self, record, field):
        return clean(record[self.cols[field]])


class SpliceTable:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_file() or not Path(str(path) + ".tbi").is_file():
            raise ValueError(f"Missing indexed annotation source: {self.path.name}")
        self.handle = pysam.TabixFile(str(path))
        if not any("ID=SpliceAI," in h for h in self.handle.header):
            raise ValueError("SpliceAI INFO header is absent")
        self.block = None
        self.records = {}

    def at(self, v):
        chrom = next((c for c in aliases(v["chrom"]) if c in self.handle.contigs), None)
        if chrom is None:
            return []
        start = (v["pos"] - 1) // 16384 * 16384
        if (chrom, start) != self.block:
            records = defaultdict(list)
            for line in self.handle.fetch(chrom, start, start + 16384):
                fields = line.split("\t")
                records[int(fields[1])].append(fields)
            self.records, self.block = records, (chrom, start)
        entries = []
        for fields in self.records.get(v["pos"], []):
            if fields[3] != v["ref"] or fields[4] != v["alt"]:
                continue
            info = dict(token.split("=", 1) for token in fields[7].split(";") if "=" in token)
            for entry in info.get("SpliceAI", "").split(","):
                pieces = entry.split("|")
                if len(pieces) == 10 and pieces[0] == v["alt"]:
                    entries.append(pieces)
        return entries


class VariationCache:
    """Read the current VEP 112 plain gzip blocks without altering the cache."""
    def __init__(self, path):
        self.path = Path(path)
        info = {}
        for line in (self.path / "info.txt").read_text().splitlines():
            if "\t" in line and not line.startswith("#"):
                key, value = line.split("\t", 1)
                info[key] = value
        if info.get("assembly") != "GRCh38":
            raise ValueError("Variation cache must be GRCh38")
        if info.get("var_type") == "tabix":
            raise ValueError("This adapter requires the original VEP gzip-block cache")
        self.columns = info["variation_cols"].split(",")
        required = {"start", "end", "allele_string", "variation_name", "clin_sig", "gnomADe", "gnomADg"}
        if not required <= set(self.columns):
            raise ValueError("Variation cache lacks required ClinVar/gnomAD columns")
        self.columns_index = {name: i for i, name in enumerate(self.columns)}
        self.info = info
        self.block = None
        self.records = {}

    def at(self, v):
        pos, ref, alt = minimal(v["pos"], v["ref"], v["alt"])
        chrom = next((c for c in aliases(v["chrom"]) if (self.path / c).is_dir()), None)
        if chrom is None:
            raise ValueError(f"Variation cache has no chromosome {v['chrom']}")
        # Include an insertion's adjacent base and a deletion's span at block boundaries.
        results = []
        for block_index in sorted({(max(1, pos - 1) - 1) // 1000000, (pos - 1) // 1000000}):
            block = (chrom, block_index)
            if block != self.block:
                start = block_index * 1000000 + 1
                path = self.path / chrom / f"{start}-{start + 999999}_var.gz"
                if not path.is_file():
                    raise ValueError(f"Missing variation cache block: {chrom}/{path.name}")
                records = defaultdict(list)
                with gzip.open(path, "rt") as handle:
                    for line in handle:
                        raw = line.rstrip("\n")
                        if raw.count(" ") != len(self.columns) - 1:
                            raise ValueError(f"Unexpected variation cache schema: {path.name}")
                        # Index the raw row, not 37 separately allocated strings.
                        # Only records at the variant's position need full decoding.
                        values = raw.split(" ", self.columns_index["start"] + 1)
                        rec_start = int(values[self.columns_index["start"]])
                        records[rec_start].append(raw)
                self.records, self.block = records, block
            results.extend(self.records.get(pos, []))
        matched = []
        for record in results:
            data = dict(zip(self.columns, (clean(x) for x in record.split(" "))))
            if data.get("failed") not in ("", "0"):
                continue
            cached = data["allele_string"].split("/")
            if len(cached) < 2:
                continue
            end = int(data["end"] or data["start"])
            wanted_end = pos - 1 if ref == "-" else pos + len(ref) - 1
            if int(data["start"]) != pos or end != wanted_end:
                continue
            for candidate in cached[1:]:
                r, a = cached[0], candidate
                if data.get("strand") == "-1":
                    r, a = reverse_complement(r), reverse_complement(a)
                if r == ref and a == alt:
                    matched.append((data, candidate))
                    break
        return matched

    def annotate(self, v):
        matches = self.at(v)
        result = {}
        for field in ("variation_name", "clin_sig", "somatic", "phenotype_or_disease", "pubmed"):
            values = []
            for data, allele in matches:
                # The cache's ClinVar assertion is allele-specific when a list is provided.
                if field == "clin_sig" and data.get("clin_sig_allele"):
                    for assertion in data["clin_sig_allele"].split(";"):
                        if ":" in assertion:
                            asserted_allele, significance = assertion.split(":", 1)
                            if asserted_allele == allele:
                                values.extend(significance.split(","))
                    continue
                values.extend(data.get(field, "").split(","))
            target = {"variation_name": "Existing_variation", "clin_sig": "CLIN_SIG",
                      "somatic": "SOMATIC", "phenotype_or_disease": "PHENO", "pubmed": "PUBMED"}[field]
            result[target] = ",".join(dict.fromkeys(x for x in values if x))
        for source in ["AF"] + [f.removesuffix("_AF") for f in AF_FIELDS]:
            values = []
            for data, allele in matches:
                for token in data.get(source, "").split(","):
                    if ":" in token:
                        a, score = token.rsplit(":", 1)
                        if a == allele:
                            values.append(float(score))
            target = source if source == "AF" else source + "_AF"
            if values:
                result[target] = str(max(values))
        return result


def reverse_complement(value):
    return value.translate(str.maketrans("ACGTN", "TGCAN"))[::-1]


class Supplementary:
    def __init__(self, plugin_dir, cache, metadata):
        directory = Path(plugin_dir)
        self.db = IndexedTable(directory / "dbNSFP5.3.1a_grch38.gz",
                               ["pos(1-based)", "ref", "alt", "aaref", "aaalt"] + DB_FIELDS, "pos(1-based)")
        self.alpha = IndexedTable(directory / "AlphaMissense_hg38.tsv.gz",
                                  ["POS", "REF", "ALT", "protein_variant", "am_pathogenicity", "am_class"], "POS")
        self.primate = IndexedTable(directory / "PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz",
                                    ["pos", "ref", "alt", "primateDL_score"], "pos")
        self.splice_snv = SpliceTable(directory / "spliceai_scores.raw.snv.hg38.vcf.gz")
        self.splice_indel = SpliceTable(directory / "spliceai_scores.raw.indel.hg38.vcf.gz")
        self.variation = VariationCache(cache)
        self.metadata = {}
        with gzip.open(metadata, "rt") if str(metadata).endswith(".gz") else open(metadata) as handle:
            for line in handle:
                data = json.loads(line)
                if data.get("_cache_release") != 112 or data.get("_assembly") != "GRCh38":
                    raise ValueError("Transcript metadata must be Ensembl 112 GRCh38")
                self.metadata[data["Feature"]] = data
        if not self.metadata:
            raise ValueError("Transcript metadata is empty")
        self.sources = {"variation_cache": str(cache), "transcript_metadata": str(metadata),
                        **{name: str(table.path) for name, table in (("dbNSFP", self.db), ("AlphaMissense", self.alpha),
                        ("PrimateAI", self.primate), ("SpliceAI_snv", self.splice_snv), ("SpliceAI_indel", self.splice_indel))}}

    def variant_data(self, v):
        snv = len(v["ref"]) == len(v["alt"]) == 1
        # Fetch once per variant; transcript matching is performed below.
        return {"known": self.variation.annotate(v),
                "db": self.db.at(v["chrom"], v["pos"]) if snv else [],
                "alpha": self.alpha.at(v["chrom"], v["pos"]) if snv else [],
                "primate": self.primate.at(v["chrom"], v["pos"]) if snv else [],
                "splice": (self.splice_snv if snv else self.splice_indel).at(v)}

    def annotate(self, row, v, data):
        row.update(data["known"])
        transcript = self.metadata.get(row["Feature"])
        if row["Feature"] not in ("", "-") and transcript is None:
            raise ValueError(f"Transcript absent from baseline metadata: {row['Feature']}")
        if transcript:
            if transcript.get("Gene") and transcript["Gene"] != row["Gene"]:
                raise ValueError(f"Transcript gene differs from baseline metadata: {row['Feature']}")
            row["TRANSCRIPT_METADATA_SOURCE"] = transcript.get("_metadata_source", "vep112_cache")
            for key in ("SYMBOL", "CANONICAL", "MANE_SELECT", "MANE_PLUS_CLINICAL", "APPRIS",
                        "TSL", "CCDS", "ENSP", "BIOTYPE", "_length"):
                row[key] = clean(transcript.get(key))
        terms = set(row["Consequence"].split(","))
        peptide = row["Amino_acids"]
        for entry in data["db"]:
            if not terms & DB_CONSEQUENCES:
                break
            if self.db.value(entry, "ref") != v["ref"] or self.db.value(entry, "alt") != v["alt"]:
                continue
            aa = (self.db.value(entry, "aaref") + "/" + self.db.value(entry, "aaalt")).replace("X", "*")
            if aa != peptide:
                continue
            for field in DB_FIELDS:
                row[field] = self.db.value(entry, field).replace(";", ",").replace("|", "&")
            # These replace cache-based SIFT/PolyPhen only in this new engine;
            # use transcript-indexed values and retain the explicit source in summary.
            for source, target, prediction in (("SIFT", "SIFT", {"D": "deleterious", "T": "tolerated"}),
                    ("Polyphen2_HDIV", "PolyPhen", {"D": "probably_damaging", "P": "possibly_damaging", "B": "benign"})):
                score_field, pred_field = source + "_score", source + "_pred"
                if all(x in self.db.cols for x in (score_field, pred_field, "Ensembl_transcriptid")):
                    ids = self.db.value(entry, "Ensembl_transcriptid").split(";")
                    if row["Feature"] in ids:
                        idx = ids.index(row["Feature"])
                        scores = self.db.value(entry, score_field).split(";")
                        preds = self.db.value(entry, pred_field).split(";")
                        if len(scores) == len(preds) == len(ids) and clean(scores[idx]):
                            row[target] = f"{prediction.get(preds[idx], preds[idx])}({scores[idx]})"
            break
        if "missense_variant" in terms:
            aa = peptide.split("/")
            position = row["Protein_position"]
            protein_variant = aa[0] + position + aa[1] if len(aa) == 2 else ""
            for entry in data["alpha"]:
                if (self.alpha.value(entry, "REF") == v["ref"] and self.alpha.value(entry, "ALT") == v["alt"]
                        and self.alpha.value(entry, "protein_variant") == protein_variant):
                    row["am_pathogenicity"] = self.alpha.value(entry, "am_pathogenicity")
                    row["am_class"] = self.alpha.value(entry, "am_class")
                    break
        for entry in data["primate"]:
            if self.primate.value(entry, "alt") == v["alt"] and self.primate.value(entry, "ref") == v["ref"]:
                row["PrimateAI"] = self.primate.value(entry, "primateDL_score")
                break
        for entry in data["splice"]:
            if entry[1] != row["SYMBOL"]:
                continue
            row["SpliceAI_pred"] = "|".join(entry[1:])
            scores = [float(x) for x in entry[2:6]]
            row["SpliceAI_cutoff"] = "PASS" if max(scores) >= 0.5 else "FAIL"
            for field, score in zip(("AG", "AL", "DG", "DL"), entry[2:6]):
                row["SpliceAI_pred_DS_" + field] = score
            break


def position(tc, prefix):
    start, end = tc.get(prefix + "_start"), tc.get(prefix + "_end")
    if start is None:
        return ""
    return str(start) if end in (None, start) else f"{start}-{end}"


def pick_key(row):
    appris = row.get("APPRIS", "").lower()
    match = re.search(r"(?:principal|p)(\d+)", appris)
    if match:
        appris_rank = int(match[1])
    else:
        match = re.search(r"(?:alternative|alt|a)(\d+)", appris)
        appris_rank = 10 + int(match[1]) if match else 100
    tsl = re.search(r"\d+", row.get("TSL", ""))
    return (not bool(row.get("MANE_SELECT")), not bool(row.get("MANE_PLUS_CLINICAL")),
            row.get("CANONICAL") != "YES", appris_rank, int(tsl[0]) if tsl else 100,
            row.get("BIOTYPE") != "protein_coding", not bool(row.get("CCDS")),
            min((SO_RANK.get(t, 1000) for t in row["Consequence"].split(",")), default=1000),
            -int(row.get("_length") or 0), row["Feature"])


def mark_pick(rows):
    groups = defaultdict(list)
    for row in rows:
        if row["Gene"] not in ("", "-"):
            groups[(row["Allele"], row["Gene"])].append(row)
    for group in groups.values():
        min(group, key=pick_key)["PICK"] = "1"


def convert_record(obj, v, sources):
    start, end, alleles = fastvep_shape(v["pos"], v["ref"], v["alt"])
    if (chrom_key(obj.get("seq_region_name", "")) != chrom_key(v["chrom"])
            or obj.get("start") != start or obj.get("end") != end or obj.get("allele_string") != alleles):
        raise ValueError(f"fastVEP/VCF record mismatch at {v['chrom']}:{v['pos']}")
    rows = []
    transcripts = obj.get("transcript_consequences", [])
    if not transcripts:
        transcripts = [{"consequence_terms": ["intergenic_variant"], "impact": "MODIFIER"}]
    data = sources.variant_data(v)
    for tc in transcripts:
        row = {field: "" for field in FIELDS}
        row.update({"#Uploaded_variation": f"{v['chrom']}_{v['pos']}_{v['ref']}/{v['alt']}",
                    "Location": f"{v['chrom']}:{start}" if start == end else f"{v['chrom']}:{start}-{end}",
                    "Allele": tc.get("variant_allele", alleles.split("/")[1]),
                    "Gene": tc.get("gene_id", ""), "Feature": tc.get("transcript_id", ""),
                    "Feature_type": "Transcript" if tc.get("transcript_id") not in (None, "-") else "",
                    "Consequence": ",".join(tc["consequence_terms"]), "IMPACT": tc["impact"],
                    "GT": v["gt"], "ZYG": zygosity(v["gt"]), "IND": v["sample"],
                    "REF": v["ref"], "ALT": v["alt"], "ANNOTATION_ENGINE": "fastvep",
                    "ANNOTATION_VERSION": "0.3.0-" + FASTVEP_COMMIT[:7], "ANNOTATION_DATA_STATUS": "sources_loaded"})
        mapping = {"gene_symbol": "SYMBOL", "biotype": "BIOTYPE", "hgvsc": "HGVSc", "hgvsp": "HGVSp",
                   "hgvsg": "HGVSg", "amino_acids": "Amino_acids", "codons": "Codons", "exon": "EXON",
                   "intron": "INTRON", "distance": "DISTANCE", "strand": "STRAND"}
        for source, target in mapping.items():
            row[target] = clean(tc.get(source))
        for source, target in (("cdna", "cDNA_position"), ("cds", "CDS_position"), ("protein", "Protein_position")):
            row[target] = position(tc, source)
        sources.annotate(row, v, data)
        rows.append(row)
    mark_pick(rows)
    return rows


def run(args):
    sources = Supplementary(args.plugin_data, args.variation_cache, args.transcript_metadata)
    output = Path(args.output)
    temporary = output.with_name(output.name + ".partial")
    counts, nonmissing, metadata_sources = Counter(), Counter(), Counter()
    sentinel = object()
    try:
        with open(args.input_json, "rb") as source, gzip.open(temporary, "wt", newline="") as target:
            target.write("## annotation_engine=fastvep\n## adapter_version=" + ADAPTER_VERSION + "\n")
            target.write("## fastvep_commit=" + FASTVEP_COMMIT + "\n")
            writer = csv.DictWriter(target, fieldnames=FIELDS, delimiter="\t", extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            for obj, v in itertools.zip_longest(ijson.items(source, "item", use_float=True),
                                               read_vcf(args.vcf, args.vcf_sample), fillvalue=sentinel):
                if obj is sentinel or v is sentinel:
                    raise ValueError("fastVEP/VCF record counts differ")
                rows = convert_record(obj, v, sources)
                writer.writerows({k: value or "-" for k, value in row.items()} for row in rows)
                counts["variants"] += 1
                counts["transcript_rows"] += len(rows)
                for row in rows:
                    nonmissing.update(k for k in FIELDS if clean(row.get(k)))
                    metadata_sources[row.get("TRANSCRIPT_METADATA_SOURCE") or "intergenic"] += 1
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    summary = {"annotation_engine": "fastvep", "fastvep_version": "0.3.0", "fastvep_commit": FASTVEP_COMMIT,
               "adapter_version": ADAPTER_VERSION, "genome_build": "GRCh38", "ensembl_release": 112,
               "status": "complete", "counts": dict(counts), "nonmissing_rows": dict(nonmissing),
               "transcript_metadata_sources": dict(metadata_sources),
               "sources": sources.sources, "variation_cache_releases": sources.variation.info,
               "transcript_metadata_sha256": hashlib.sha256(Path(args.transcript_metadata).read_bytes()).hexdigest(),
               "sift_polyphen_source": "dbNSFP transcript-matched; differs from VEP transcript-cache predictors",
               "pick_tie_breaker": "transcript_id (deterministic; exact VEP ties require validation)"}
    Path(args.summary).write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input-json", "vcf", "output", "summary", "plugin-data", "variation-cache", "transcript-metadata"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--vcf-sample")
    run(parser.parse_args())

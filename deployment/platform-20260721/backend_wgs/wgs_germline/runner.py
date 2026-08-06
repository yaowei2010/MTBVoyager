import csv
import os
import subprocess
import sys
from pathlib import Path

from .storage import install_pipeline, job_dir, write_json


POPULATION_MAP = {
    "gnomAD_EAS": "eas", "gnomAD_AFR": "afr", "gnomAD_AMR": "amr",
    "gnomAD_ASJ": "asj", "gnomAD_FIN": "fin", "gnomAD_NFE": "nfe",
    "gnomAD_SAS": "sas", "gnomAD_GLOBAL": "global",
}


def launch(job_id: str, metadata: dict) -> int:
    directory = job_dir(job_id)
    pipeline = install_pipeline()
    inputs = directory / "inputs"
    output = directory / "results"
    work = directory / "work"
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)

    gene_file = directory / "phenotype_genes.txt"
    gene_file.write_text("".join(f"{g}\n" for g in metadata["resolved_genes"]), encoding="utf-8")
    sheet = directory / "samplesheet.csv"
    with sheet.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample_id", "snv_vcf", "sv_vcf", "cnv_vcf", "gene_list", "sex"])
        writer.writeheader()
        writer.writerow({
            "sample_id": metadata["subject"]["subject_id"],
            "snv_vcf": inputs / metadata["files"]["snv"],
            "sv_vcf": inputs / metadata["files"]["sv"],
            "cnv_vcf": inputs / metadata["files"]["cnv"],
            "gene_list": gene_file,
            "sex": metadata["subject"].get("gender", "unknown"),
        })

    reference = os.environ.get("WGS_REFERENCE_FASTA", "/wgs_reference/hg38.fa")
    cmd = [
        "nextflow", "run", str(pipeline / "main.nf"), "-profile", "docker",
        "-work-dir", str(work), "--input", str(sheet), "--outdir", str(output),
        "--reference", reference,
        "--vep_cache", os.environ.get("WGS_VEP_CACHE", "/wgs_reference/vep"),
        "--vep_plugin_data", os.environ.get("WGS_VEP_PLUGIN_DATA", "/wgs_reference/vep/Plugins"),
        "--vep_plugin_args", os.environ.get("WGS_VEP_PLUGIN_ARGS", ""),
        "--annotsv_annotations", os.environ.get("WGS_ANNOTSV_ANNOTATIONS", "/wgs_reference/annotsv"),
        "--vep_max_parallel", os.environ.get("WGS_VEP_MAX_PARALLEL", "8"),
        "--vep_fork_per_shard", os.environ.get("WGS_VEP_FORK_PER_SHARD", "1"),
        "--dp_min", str(metadata["settings"]["min_dp_cutoff"]),
        "--vaf_min", str(metadata["settings"]["min_vaf"]),
        "--population", POPULATION_MAP.get(metadata["settings"]["population"], "eas"),
        "--population_af_max", str(metadata["settings"]["maf_cutoff"]),
        "--pass_only", str(metadata["settings"]["pass_only"]).lower(),
        "--acmg_genes", str(pipeline / "assets" / "acmg_sf_gene_disease.tsv"),
        "-ansi-log", "false",
    ]
    log = (directory / "nextflow.log").open("ab", buffering=0)
    process = subprocess.Popen(cmd, cwd=pipeline, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    subprocess.Popen(
        [sys.executable, "-m", "wgs_germline.monitor", job_id, str(process.pid)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    return process.pid

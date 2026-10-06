"""WGS annotation engine arguments; shared contract for both runners."""
import os
from pathlib import Path


def annotation_arguments():
    engine = os.environ.get("WGS_ANNOTATION_ENGINE", "fastvep")
    if engine not in {"vep", "fastvep"}:
        raise ValueError("WGS_ANNOTATION_ENGINE must be vep or fastvep")
    args = ["--annotation_engine", engine]
    if engine == "fastvep":
        reference = os.environ.get("WGS_FASTVEP_REFERENCE_ROOT", "/home/hpz8g5/tools/fastVEP/data/reference")
        cache = Path(os.environ.get("WGS_VEP_CACHE", "/wgs_reference/vep"))
        data_root = cache.parents[1] if str(cache).endswith("/VEP/database") else cache.parent
        variation_index = str(data_root / "fastvep/vep112-normalized-variation-v1")
        for parameter, env, default in (
            ("fastvep_image", "WGS_FASTVEP_IMAGE", "mtb-wgs-fastvep:0.1.3"),
            ("fastvep_gff3", "WGS_FASTVEP_GFF3", reference + "/Homo_sapiens.GRCh38.112.gff3"),
            ("fastvep_transcript_cache", "WGS_FASTVEP_TRANSCRIPT_CACHE", reference + "/grch38_ensembl112.mtb.cache"),
            ("fastvep_transcript_metadata", "WGS_FASTVEP_TRANSCRIPT_METADATA", reference + "/vep112.transcript_metadata.complete.jsonl"),
            ("fastvep_variation_index", "WGS_FASTVEP_VARIATION_INDEX", variation_index),
            ("fastvep_max_parallel", "WGS_FASTVEP_MAX_PARALLEL", "2"),
            ("fastvep_cpus", "WGS_FASTVEP_CPUS", "8"),
            ("fastvep_memory", "WGS_FASTVEP_MEMORY", "20 GB"),
        ):
            args.extend(["--" + parameter, os.environ.get(env, default)])
    return args

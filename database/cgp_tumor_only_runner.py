#!/usr/bin/env python3
"""Run one CGP sample through the local legacy MTB tumor-only pipeline."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "/miRTI")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uploadfunction.settings")

import django

django.setup()

from hw1.models import existJobs
from hw1 import views
from django.test import RequestFactory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--group", choices=("CRC", "GYN"), required=True)
    parser.add_argument("--vcf", required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--maf-cutoff", type=float, default=0.01)
    parser.add_argument("--min-aaf", type=float, default=0.05)
    parser.add_argument("--min-dp", type=int, default=20)
    args = parser.parse_args()

    job_dir = Path("/miRTI/media/patient") / args.job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_vcf = job_dir / "main.vcf"
    source_vcf = Path(args.vcf)
    if source_vcf.resolve() != input_vcf.resolve():
        shutil.copy2(source_vcf, input_vcf)

    vep_dir = Path("/VEP/newjobid") / args.job_id
    vep_dir.mkdir(parents=True, exist_ok=True)
    vep_dir.chmod(0o777)
    shutil.copy2(input_vcf, vep_dir / "main.vcf")
    (vep_dir / "main.vcf").chmod(0o666)

    metadata = {
        "subject_id": args.sample_id,
        "cohort": args.group,
        "diagnosis": args.group,
        "protocol": "MTB legacy tumor-only",
        "genome_build": "hg19",
        "maf_cutoff": args.maf_cutoff,
        "min_aaf": args.min_aaf,
        "min_dp_cutoff": args.min_dp,
        "execution": "local-only",
    }
    (job_dir / "file.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (job_dir / "summary.json").write_text(json.dumps(metadata, indent=2) + "\n")

    defaults = dict(
        subject_id=args.sample_id,
        name="Tumor-Only",
        dob="",
        gender="unknown",
        history=f"CGP {args.group}",
        uploadFile_url=str(input_vcf),
        resultFile_url=str(job_dir / "main_vep_annovar_merge.csv"),
        status="running",
        user_id="N/A",
        diagnosis=args.group,
        genome_build="hg19",
    )
    record = existJobs.jobs.filter(jobID=args.job_id).first()
    if record is None:
        record = existJobs.jobs.create(jobID=args.job_id, **defaults)
    else:
        for key, value in defaults.items():
            setattr(record, key, value)
        record.save()

    original_run_and_log = views.run_and_log

    def local_limited_run(command, logger, env=None, cwd=None):
        if isinstance(command, list) and command[:2] == ["docker", "run"]:
            command = list(command)
            command[2:2] = ["--network", "none"]
            for i, token in enumerate(command[:-1]):
                if token == "--fork":
                    command[i + 1] = str(args.threads)
        elif isinstance(command, str):
            command = command.replace("--thread 16", f"--thread {args.threads}")
        return original_run_and_log(command, logger, env=env, cwd=cwd)

    views.run_and_log = local_limited_run
    try:
        merged = job_dir / "main_vep_annovar_merge.csv"
        if not merged.exists() or merged.stat().st_size == 0:
            views.run_vep_and_annovar(
                args.job_id,
                "main.vcf",
                args.maf_cutoff,
                str(input_vcf),
                args.min_aaf,
                args.min_dp,
                "EAS",
            )

        body = {"newjobid": args.job_id, "diagnosis": args.group}
        factory = RequestFactory()
        for endpoint, function in (
            ("somatic_result", views.somatic_result),
            ("process_cosmic", views.process_cosmic),
            ("mutisnp_civic", views.mutisnp_civic),
            ("postgresql", views.postgresql),
            ("mutational_signature", views.mutation_signature),
        ):
            function(factory.post(f"/{endpoint}", body, content_type="application/json"))
    except Exception:
        existJobs.jobs.filter(jobID=args.job_id).update(status="failed")
        (job_dir / "pipeline_failed.json").write_text(
            json.dumps({**metadata, "job_id": args.job_id, "status": "failed"}, indent=2) + "\n"
        )
        raise
    else:
        existJobs.jobs.filter(jobID=args.job_id).update(
            status="finished",
            resultFile_url=str(job_dir / "main_vep_annovar_merge.csv"),
        )

    vep_output = job_dir / "vep_intermediates"
    if vep_output.exists():
        shutil.rmtree(vep_output)
    shutil.copytree(vep_dir, vep_output)
    platform_log = Path("/miRTI/logs") / f"pipeline_{args.job_id}.log"
    if platform_log.exists():
        shutil.copy2(platform_log, job_dir / "platform_pipeline.log")
    (job_dir / "pipeline_complete.json").write_text(
        json.dumps({**metadata, "job_id": args.job_id, "status": "complete"}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

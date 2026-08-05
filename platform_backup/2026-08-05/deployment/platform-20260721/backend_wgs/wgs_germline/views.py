import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from hw1.models import existJobs

from .mondo import resolve_genes, search
from .literature import summarize
from .literature_store import statistics as literature_statistics
from .runner import launch
from .storage import (
    draft_dir, job_dir, new_id, read_json, save_upload, tsv_rows,
    validate_id, write_json,
)


SUFFIXES = {
    "snv": ".hard-filtered.vcf.gz",
    "sv": ".sv.vcf.gz",
    "cnv": ".cnv.vcf.gz",
}
SNV_FILES = {
    "phenotype": "phenotype_variants",
    "known_pathogenic": "known_clinvar_plp",
    "acmg_sf": "acmg_sf",
    "in_silico": "insilico",
}
SV_FILES = {"known_pathogenic": "known_pathogenic", "acmg_sf": "acmg_sf"}


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON body") from exc


def _error(detail, status=400):
    return JsonResponse({"detail": str(detail)}, status=status)


@csrf_exempt
def subject(request):
    if request.method != "POST":
        return _error("POST required", 405)
    try:
        data = _json_body(request)
        subject_id = str(data.get("subject_id", "")).strip()
        if not subject_id or len(subject_id) > 80:
            raise ValueError("Subject ID is required and must be at most 80 characters")
        draft_id = new_id("draft")
        directory = draft_dir(draft_id)
        directory.mkdir(parents=True, exist_ok=False)
        metadata = {
            "draft_id": draft_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "subject": {
                "subject_id": subject_id,
                "dob": str(data.get("dob", ""))[:20],
                "gender": str(data.get("gender", "unknown"))[:20],
                "history": str(data.get("history", ""))[:10000],
                "user_id": str(data.get("user_id") or "N/A")[:100],
                "protocol": "WGS Germline",
                "genome_build": "hg38",
            },
        }
        write_json(directory / "metadata.json", metadata)
        return JsonResponse({"draft_id": draft_id}, status=201)
    except ValueError as exc:
        return _error(exc)


@csrf_exempt
def upload(request):
    if request.method != "POST":
        return _error("POST required", 405)
    try:
        draft_id = validate_id(request.POST.get("draft_id", ""), "draft")
        directory = draft_dir(draft_id)
        metadata = read_json(directory / "metadata.json")
        if not metadata:
            return _error("Draft not found", 404)
        upload_id = new_id("upload")
        files = {}
        for key, suffix in SUFFIXES.items():
            item = request.FILES.get(key)
            if not item or not item.name.lower().endswith(suffix):
                raise ValueError(f"{key.upper()} file must end with {suffix}")
            if item.size <= 0:
                raise ValueError(f"{key.upper()} file is empty")
            filename = f"{key}{suffix}"
            save_upload(item, directory / "uploads" / upload_id / filename)
            files[key] = filename
        metadata.update({"upload_id": upload_id, "files": files})
        write_json(directory / "metadata.json", metadata)
        return JsonResponse({"upload_id": upload_id}, status=201)
    except ValueError as exc:
        return _error(exc)


def mondo_search(request):
    if request.method != "GET":
        return _error("GET required", 405)
    try:
        limit = min(max(int(request.GET.get("limit", 20)), 1), 50)
    except ValueError:
        limit = 20
    return JsonResponse({"results": search(request.GET.get("q", ""), limit)})


def literature_status(request):
    if request.method != "GET":
        return _error("GET required", 405)
    return JsonResponse({"backend": "sqlite-fts5", **literature_statistics()})


@csrf_exempt
def literature_summary(request, analysis_id):
    if request.method != "POST":
        return _error("POST required", 405)
    directory, metadata = _metadata(analysis_id)
    if not metadata:
        return _error("Analysis not found", 404)
    try:
        data = _json_body(request)
        result = summarize(directory, metadata, str(data.get("gene", "")),
                           str(data.get("variant", "")), bool(data.get("refresh", False)))
        return JsonResponse(result)
    except ValueError as exc:
        return _error(exc)
    except Exception as exc:
        return _error(f"Literature retrieval failed: {exc}", 502)


@csrf_exempt
def jobs(request):
    if request.method != "POST":
        return _error("POST required", 405)
    try:
        data = _json_body(request)
        draft_id = validate_id(data.get("draft_id", ""), "draft")
        upload_id = validate_id(data.get("upload_id", ""), "upload")
        source = draft_dir(draft_id)
        metadata = read_json(source / "metadata.json")
        if not metadata or metadata.get("upload_id") != upload_id:
            return _error("Upload session not found", 404)
        population = data.get("population", "gnomAD_EAS")
        allowed_populations = {"gnomAD_EAS", "gnomAD_AFR", "gnomAD_AMR", "gnomAD_ASJ", "gnomAD_FIN", "gnomAD_NFE", "gnomAD_SAS", "gnomAD_GLOBAL"}
        if population not in allowed_populations:
            raise ValueError("Unsupported gnomAD population")
        settings = {
            "pass_only": bool(data.get("pass_only", True)),
            "min_dp_cutoff": max(0, int(data.get("min_dp_cutoff", 20))),
            "min_vaf": min(max(float(data.get("min_vaf", 0.2)), 0), 1),
            "maf_cutoff": min(max(float(data.get("maf_cutoff", 0.01)), 0), 1),
            "population": population,
            "phenotype_include_descendants": bool(data.get("phenotype_include_descendants", True)),
            "phenotypes": data.get("phenotypes") or [],
        }
        genes, releases = resolve_genes(settings["phenotypes"], settings["phenotype_include_descendants"])
        job_id = new_id("wgs")
        destination = job_dir(job_id)
        destination.mkdir(parents=True, exist_ok=False)
        shutil.move(str(source / "uploads" / upload_id), str(destination / "inputs"))
        metadata.update({
            "analysis_id": job_id, "status": "starting", "settings": settings,
            "resolved_genes": genes, "ontology_releases": releases,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })
        write_json(destination / "metadata.json", metadata)
        subject_data = metadata["subject"]
        record = existJobs.jobs.create(
            jobID=job_id, subject_id=subject_data["subject_id"], name="WGS Germline",
            dob=subject_data.get("dob", ""), gender=subject_data.get("gender", ""),
            history=subject_data.get("history", ""),
            uploadFile_url=str(destination / "inputs"), resultFile_url=str(destination / "pipeline.finished"),
            user_id=subject_data.get("user_id", "N/A"), genome_build="hg38", status="running",
        )
        try:
            pid = launch(job_id, metadata)
        except Exception:
            record.status = "failed"
            record.save(update_fields=["status"])
            metadata["status"] = "failed"
            write_json(destination / "metadata.json", metadata)
            raise
        record.processID = str(pid)
        record.save(update_fields=["processID"])
        metadata.update({"status": "running", "process_id": pid})
        write_json(destination / "metadata.json", metadata)
        shutil.rmtree(source, ignore_errors=True)
        return JsonResponse({"analysis_id": job_id, "status": "running"}, status=202)
    except (ValueError, TypeError) as exc:
        return _error(exc)
    except Exception as exc:
        return _error(f"Unable to start WGS pipeline: {exc}", 500)


def _metadata(analysis_id):
    try:
        directory = job_dir(analysis_id)
    except ValueError:
        return None, None
    metadata = read_json(directory / "metadata.json")
    if not metadata:
        return directory, None
    sample = metadata.get("subject", {}).get("subject_id", "")
    complete = directory / "results" / sample / "pipeline_complete.json"
    pid = metadata.get("process_id")
    if complete.exists() and metadata.get("status") != "finished":
        metadata["status"] = "finished"
        write_json(directory / "metadata.json", metadata)
        marker = directory / "pipeline.finished"
        marker.touch()
        existJobs.jobs.filter(jobID=analysis_id).update(status="finished", resultFile_url=str(marker))
    elif metadata.get("status") == "running" and pid and not Path(f"/proc/{pid}").exists():
        metadata["status"] = "failed"
        write_json(directory / "metadata.json", metadata)
        existJobs.jobs.filter(jobID=analysis_id).update(status="failed")
    return directory, metadata


def job_detail(request, analysis_id):
    directory, metadata = _metadata(analysis_id)
    if not metadata:
        return _error("Analysis not found", 404)
    safe = {key: metadata.get(key) for key in ("analysis_id", "status", "started_at", "settings", "ontology_releases")}
    safe["subject"] = metadata.get("subject", {})
    safe["phenotype_gene_count"] = len(metadata.get("resolved_genes", []))
    safe["log_available"] = (directory / "nextflow.log").exists()
    return JsonResponse(safe)


def _sample_result_path(metadata, directory, section, suffix):
    sample = metadata["subject"]["subject_id"]
    return directory / "results" / sample / section / f"{sample}.{suffix}.tsv"


def snv_results(request, analysis_id):
    category = request.GET.get("category", "")
    if category not in SNV_FILES:
        return _error("Unsupported SNV category")
    directory, metadata = _metadata(analysis_id)
    if not metadata:
        return _error("Analysis not found", 404)
    path = _sample_result_path(metadata, directory, "candidates", SNV_FILES[category])
    return JsonResponse({"results": tsv_rows(path), "status": metadata["status"]})


def sv_results(request, analysis_id):
    category = request.GET.get("category", "")
    if category not in SV_FILES:
        return _error("Unsupported SV category")
    directory, metadata = _metadata(analysis_id)
    if not metadata:
        return _error("Analysis not found", 404)
    path = _sample_result_path(metadata, directory, "sv", f"sv.{SV_FILES[category]}")
    return JsonResponse({"results": tsv_rows(path), "status": metadata["status"]})


def pharmcat_results(request, analysis_id):
    directory, metadata = _metadata(analysis_id)
    if not metadata:
        return _error("Analysis not found", 404)
    sample = metadata["subject"]["subject_id"]
    root = directory / "results" / sample / "pharmcat"
    rows = []
    for path in root.rglob("*.phenotype.json") if root.exists() else []:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for gene, gene_report in report.get("geneReports", {}).items():
            drugs = []
            for drug in gene_report.get("relatedDrugs") or []:
                drugs.append(str(drug.get("name") or drug.get("drugName") or drug.get("id") or drug) if isinstance(drug, dict) else str(drug))
            diplotypes = gene_report.get("recommendationDiplotypes") or gene_report.get("sourceDiplotypes") or [{}]
            for diplotype in diplotypes:
                rows.append({
                    "gene": gene,
                    "star_allele": diplotype.get("label") or "",
                    "phenotype": ", ".join(diplotype.get("phenotypes") or []),
                    "activity_score": diplotype.get("activityScore") if diplotype.get("activityScore") is not None else "",
                    "drugs": ", ".join(drugs),
                    "call_source": gene_report.get("callSource", ""),
                    "messages": "; ".join(str(item) for item in (gene_report.get("messages") or [])),
                    "source_file": path.name,
                })
    for path in root.rglob("*.tsv") if root.exists() else []:
        for row in tsv_rows(path):
            row["source_file"] = path.name
            rows.append(row)
    return JsonResponse({"results": rows[:10000], "status": metadata["status"]})

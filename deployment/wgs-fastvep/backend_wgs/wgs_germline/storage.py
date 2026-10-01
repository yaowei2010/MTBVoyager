import csv
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile


SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def root() -> Path:
    path = Path(os.environ.get("WGS_DATA_ROOT", "/miRTI/media/wgs_germline")).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def validate_id(value: str, prefix: str | None = None) -> str:
    if not value or not SAFE_ID.fullmatch(value) or (prefix and not value.startswith(prefix + "_")):
        raise ValueError("Invalid identifier")
    return value


def draft_dir(draft_id: str) -> Path:
    return root() / "drafts" / validate_id(draft_id, "draft")


def job_dir(job_id: str) -> Path:
    return root() / "jobs" / validate_id(job_id, "wgs")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def save_upload(upload: UploadedFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as handle:
        for chunk in upload.chunks():
            handle.write(chunk)


def install_pipeline() -> Path:
    source = Path(os.environ.get("WGS_PIPELINE_SOURCE", "/opt/wgs-germline-pipeline"))
    version = (source / "VERSION").read_text().strip()
    destination = root() / "pipeline" / version
    if not destination.exists():
        temporary = destination.with_name(destination.name + ".tmp")
        shutil.rmtree(temporary, ignore_errors=True)
        # The image may contain Nextflow artefacts from pipeline validation.
        # Work entries commonly contain absolute symlinks and must never become
        # part of the immutable pipeline installation used by platform jobs.
        shutil.copytree(
            source,
            temporary,
            ignore=shutil.ignore_patterns(
                "work", ".nextflow", ".nextflow.log*", "results",
                "dag-*.html", "report-*.html", "timeline-*.html", "trace-*.txt",
            ),
        )
        os.replace(temporary, destination)
    return destination


def tsv_rows(path: Path, limit: int = 10000):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))[:limit]

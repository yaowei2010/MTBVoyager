#!/usr/bin/env python3
"""Sequentially warm the WGS result-page literature cache for ACMG SF genes."""
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/home/hpz8g5/project/MTB")
JOB_ID = sys.argv[1] if len(sys.argv) > 1 else "wgs_25a00001cafe2026"
GENES_FILE = ROOT / "students/backend_wgs/pipeline/assets/acmg_sf_gene_disease.tsv"
JOB_CACHE = ROOT / "database/wgs_germline/jobs" / JOB_ID / "literature"
STATUS_FILE = JOB_CACHE / "precache_status.json"
URL = f"http://localhost:3002/ncku_hospital/wgs-germline/jobs/{JOB_ID}/literature"


def write_status(payload):
    JOB_CACHE.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    temporary = STATUS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(STATUS_FILE)


def cached_result(gene):
    for path in JOB_CACHE.glob(f"{gene}.*.json"):
        try:
            result = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if result.get("status") in {"complete", "no_evidence"}:
            return result
        if result.get("status") == "model_unavailable":
            path.unlink(missing_ok=True)
    return None


with GENES_FILE.open(newline="", encoding="utf-8") as handle:
    genes = list(dict.fromkeys(row["genes"].strip().upper() for row in csv.DictReader(handle, delimiter="\t") if row.get("genes")))

state = {"job_id": JOB_ID, "state": "running", "total": len(genes), "completed": 0, "failed": 0, "current_gene": "", "results": {}}
write_status(state)

for gene in genes:
    state["current_gene"] = gene
    existing = cached_result(gene)
    if existing:
        state["results"][gene] = existing.get("status")
        state["completed"] += 1
        write_status(state)
        continue

    outcome = None
    for attempt in range(1, 4):
        request = urllib.request.Request(
            URL,
            data=json.dumps({"gene": gene, "variant": "", "refresh": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=360) as response:
                outcome = json.loads(response.read())
        except Exception as exc:
            outcome = {"status": "request_failed", "detail": str(exc)[:200]}
        if outcome.get("status") in {"complete", "no_evidence"}:
            break
        for path in JOB_CACHE.glob(f"{gene}.*.json"):
            path.unlink(missing_ok=True)
        time.sleep(5 * attempt)

    status = outcome.get("status", "unknown")
    state["results"][gene] = status
    if status in {"complete", "no_evidence"}:
        state["completed"] += 1
    else:
        state["failed"] += 1
    write_status(state)

state["state"] = "complete" if state["failed"] == 0 else "complete_with_errors"
state["current_gene"] = ""
write_status(state)

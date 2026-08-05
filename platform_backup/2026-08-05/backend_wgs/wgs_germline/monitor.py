import os
import sys
import time
from pathlib import Path

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uploadfunction.settings")
django.setup()

from hw1.models import existJobs
from .storage import job_dir, read_json, write_json


def process_is_running(pid: int) -> bool:
    """Return false once a process exits, including an unreaped zombie."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().split()
        return len(fields) > 2 and fields[2] != "Z"
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return False


def main():
    job_id, pid_text = sys.argv[1:3]
    pid = int(pid_text)
    while process_is_running(pid):
        time.sleep(10)
    directory = job_dir(job_id)
    metadata = read_json(directory / "metadata.json", {})
    sample = metadata.get("subject", {}).get("subject_id", "")
    success = (directory / "results" / sample / "pipeline_complete.json").exists()
    metadata["status"] = "finished" if success else "failed"
    write_json(directory / "metadata.json", metadata)
    if success:
        marker = directory / "pipeline.finished"
        marker.touch()
        existJobs.jobs.filter(jobID=job_id).update(status="finished", resultFile_url=str(marker))
    else:
        existJobs.jobs.filter(jobID=job_id).update(status="failed")


if __name__ == "__main__":
    main()

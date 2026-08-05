#!/usr/bin/env python3
"""Patch the legacy Somatic endpoint bundled in the backend base image.

The base image owns /miRTI/hw1/views.py.  Keep this patch strict so a future
base-image change fails during docker build instead of silently reintroducing
jobs that remain in the ``running`` state forever.
"""

from pathlib import Path
import sys


target = Path(sys.argv[1] if len(sys.argv) > 1 else "/miRTI/hw1/views.py")
source = target.read_text(encoding="utf-8")

success_old = '''        # ---------------- 完成 & 回傳 ----------------
        t2 = time.time()
        logger.info(f"=== vep_test_page4 END: total {t2 - t0:.2f}s ===")
        response_data["log_path"] = log_path
        return JsonResponse(response_data)
'''

success_new = '''        # ---------------- 完成、驗證結果並更新 Job 狀態 ----------------
        result_path = tmp_annovar_merge_vep
        if not os.path.isfile(result_path) or os.path.getsize(result_path) == 0:
            raise RuntimeError(f"Result file missing or empty: {result_path}")

        # A Somatic request can run for tens of minutes.  Refresh the database
        # connection before the final write so stale connections cannot leave
        # the platform row stuck at ``running``.
        from django.db import close_old_connections
        close_old_connections()
        updated = existJobs.jobs.filter(jobID=newJobID).update(
            status="finished",
            resultFile_url=result_path,
        )
        if updated != 1:
            raise RuntimeError(
                f"Unable to update job status: jobID={newJobID}, updated={updated}"
            )
        logger.info(
            f"[JOB STATUS] jobID={newJobID} -> finished; result={result_path}"
        )

        t2 = time.time()
        logger.info(f"=== vep_test_page4 END: total {t2 - t0:.2f}s ===")
        response_data["log_path"] = log_path
        return JsonResponse(response_data)
'''

error_old = '''    except Exception as e:
        # 任何錯誤都寫入 log 並回傳 log 路徑
        logger.error(f"[ERROR] {e}", exc_info=True)
        return JsonResponse({"error": str(e), "log_path": log_path}, status=500)
'''

error_new = '''    except Exception as e:
        # Keep the Job Table consistent with the actual pipeline outcome.
        logger.error(f"[ERROR] {e}", exc_info=True)
        try:
            from django.db import close_old_connections
            close_old_connections()
            existJobs.jobs.filter(jobID=newJobID).update(status="failed")
            logger.info(f"[JOB STATUS] jobID={newJobID} -> failed")
        except Exception:
            logger.exception("[JOB STATUS] failed to update database")
        return JsonResponse({"error": str(e), "log_path": log_path}, status=500)
'''

for label, old, new in (
    ("success path", success_old, success_new),
    ("error path", error_old, error_new),
):
    count = source.count(old)
    if count != 1:
        raise SystemExit(
            f"Refusing to patch {target}: expected one {label}, found {count}"
        )
    source = source.replace(old, new, 1)

target.write_text(source, encoding="utf-8")
print(f"Patched legacy Somatic job status handling: {target}")

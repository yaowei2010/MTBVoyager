from __future__ import annotations

import os
import uuid
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from ..postgressql_setting.dbpool import PgConn
from .blacklist_clinvar_web import (
    _schema_for_user,
    build_query_from_rowlike,
    get_clinvar_url_by_entrez,
    build_term_url,
    fetch_clinvar_latest_one,
    _ensure_output_tables,
    _upsert_lookup,
    _upsert_latest,
)

# ============================================================================


def _get_logger():
    logger = logging.getLogger("blacklist.clinvar_progress")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        os.makedirs("/miRTI/logs", exist_ok=True)
        fh = RotatingFileHandler(
            "/miRTI/logs/blacklist.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


logger = _get_logger()


# ============================================================================


def _parse_json_body(request) -> dict:
    """
    統一處理 POST JSON body：
      - 先嘗試 request.json（若有）
      - 再嘗試 json.loads(request.body)
      - 失敗時回傳 {}
    """
    body = None
    try:
        body = request.json if hasattr(request, "json") else None
    except Exception:
        body = None
    if body is None:
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            body = {}
    return body


# ============================================================================


def _insert_job(user_id: int, mode: str, resolve_mode: str, scrape: bool) -> str:
    job_id = str(uuid.uuid4())
    try:
        with PgConn(autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO public.clinvar_crawl_job
                  (job_id, user_id, mode, resolve_mode, scrape, status)
                VALUES (%s, %s, %s, %s, %s, 'pending')
                """,
                [job_id, user_id, mode, resolve_mode, scrape],
            )
        logger.info(
            "insert job ok | job_id=%s user_id=%s mode=%s resolve_mode=%s scrape=%s",
            job_id,
            user_id,
            mode,
            resolve_mode,
            scrape,
        )
    except Exception:
        logger.exception(
            "insert job fail | user_id=%s mode=%s resolve_mode=%s scrape=%s",
            user_id,
            mode,
            resolve_mode,
            scrape,
        )
        raise
    return job_id


def _update_job(job_id: str, **fields):
    if not fields:
        return
    try:
        sets = []
        vals = []
        for k, v in fields.items():
            sets.append(sql.SQL("{} = %s").format(sql.Identifier(k)))
            vals.append(v)
        q = sql.Composed(
            [
                sql.SQL("UPDATE public.clinvar_crawl_job SET "),
                sql.SQL(", ").join(sets),
                sql.SQL(" WHERE job_id = %s"),
            ]
        )
        with PgConn(autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(q, [*vals, job_id])
    except Exception:
        logger.exception("update job fail | job_id=%s fields=%s", job_id, fields)
        raise


def _get_job(job_id: str):
    try:
        with PgConn(autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM public.clinvar_crawl_job WHERE job_id = %s", [job_id]
            )
            row = cur.fetchone()
            if not row:
                return None
            cols = [c.name for c in cur.description]
            return dict(zip(cols, row))
    except Exception:
        logger.exception("get job fail | job_id=%s", job_id)
        raise


# ============================================================================


def _ensure_job_items_table():
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS public.clinvar_crawl_job_items (
              job_id      UUID NOT NULL,
              schema_name TEXT NOT NULL,
              mode        TEXT NOT NULL,           -- intersect / diff
              "Chr"       TEXT,
              "Start"     BIGINT,
              "End"       BIGINT,
              "Ref"       TEXT,
              "Alt"       TEXT,
              occurrence_count BIGINT,
              case_count BIGINT,
              analysis_case_total BIGINT,
              case_ratio NUMERIC,
              payload     JSONB,
              created_at  TIMESTAMPTZ,
              updated_at  TIMESTAMPTZ
            )
            """
        )
        for addcol in (
            "ALTER TABLE public.clinvar_crawl_job_items ADD COLUMN IF NOT EXISTS occurrence_count BIGINT",
            "ALTER TABLE public.clinvar_crawl_job_items ADD COLUMN IF NOT EXISTS case_count BIGINT",
            "ALTER TABLE public.clinvar_crawl_job_items ADD COLUMN IF NOT EXISTS analysis_case_total BIGINT",
            "ALTER TABLE public.clinvar_crawl_job_items ADD COLUMN IF NOT EXISTS case_ratio NUMERIC",
        ):
            cur.execute(addcol)
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_items_job ON public.clinvar_crawl_job_items(job_id)"
        )


def _snapshot_items(schema: str, mode: str, job_id: str, limit: int | None) -> int:
    """
    把 {schema}.blacklist_compare_{mode} 的當前內容拍快照到 public.clinvar_crawl_job_items
    """
    src_table = f"blacklist_compare_{'intersect' if mode == 'intersect' else 'diff'}"
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM public.clinvar_crawl_job_items WHERE job_id = %s AND mode = %s",
            [job_id, mode],
        )

        base_sql = sql.SQL(
            """
            INSERT INTO public.clinvar_crawl_job_items
              (job_id, schema_name, mode, "Chr","Start","End","Ref","Alt",
               occurrence_count, case_count, analysis_case_total, case_ratio,
               payload, created_at, updated_at)
            SELECT %s, %s, %s,
                   u."Chr", u."Start", u."End", u."Ref", u."Alt",
                   u.occurrence_count, u.case_count, u.analysis_case_total, u.case_ratio,
                   u.payload, u.created_at, u.updated_at
            FROM {}.{} u
            WHERE u."Chr"   IS NOT NULL
              AND u."Ref"   IS NOT NULL
              AND u."Alt"   IS NOT NULL
              AND u."Start" IS NOT NULL
              AND u."End"   IS NOT NULL
              AND COALESCE(NULLIF(u."Chr", ''), '-') <> '-'
              AND COALESCE(NULLIF(u."Ref", ''), '-') <> '-'
              AND COALESCE(NULLIF(u."Alt", ''), '-') <> '-'
              AND u.payload IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM jsonb_each_text(u.payload) kv
                WHERE kv.value IS NOT NULL AND kv.value <> '' AND kv.value <> '-'
              )
              AND (
                   COALESCE(NULLIF(u.payload->>'HGVSc', ''),   '-') <> '-'
                OR COALESCE(NULLIF(u.payload->>'AAChange.refGene',''), '-') <> '-'
                OR COALESCE(NULLIF(u.payload->>'HGVSp',''),   '-') <> '-'
                OR COALESCE(NULLIF(u.payload->>'avsnp150',''),'-') <> '-'
              )
            """
        ).format(sql.Identifier(schema), sql.Identifier(src_table))

        params = [job_id, schema, mode]
        if limit and int(limit) > 0:
            q = sql.Composed([base_sql, sql.SQL(" LIMIT "), sql.Literal(int(limit))])
        else:
            q = base_sql

        cur.execute(q, params)
        inserted = cur.rowcount or 0
        logger.info(
            "snapshot | schema=%s mode=%s src=%s inserted=%s",
            schema,
            mode,
            src_table,
            inserted,
        )
        return inserted


def _count_snapshot(job_id: str) -> int:
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM public.clinvar_crawl_job_items WHERE job_id = %s",
            [job_id],
        )
        return int(cur.fetchone()[0])


# ============================================================================


@csrf_exempt
@require_POST
def clinvar_start(request):
    """
    建立 job → 對 inter/diff 拍快照 → 背景執行
    POST body(JSON): { user_id, mode='both', resolve_mode='entrez', scrape=true, limit=null }
    """
    body = _parse_json_body(request)
    if not body:
        logger.exception("clinvar_start parse body fail")
        return HttpResponseBadRequest("invalid json body")

    try:
        user_id = int(body.get("user_id"))
    except Exception:
        logger.error("clinvar_start missing/invalid user_id | body=%s", body)
        return HttpResponseBadRequest("missing/invalid user_id")

    mode = (body.get("mode") or "both").lower()
    resolve_mode = (body.get("resolve_mode") or "entrez").lower()
    scrape = bool(body.get("scrape", True))
    limit = body.get("limit", None)
    if limit is not None:
        try:
            limit = int(limit)
        except Exception:
            limit = None

    logger.info(
        "clinvar_start | user_id=%s mode=%s resolve_mode=%s scrape=%s limit=%s",
        user_id,
        mode,
        resolve_mode,
        scrape,
        limit,
    )
    job_id = _insert_job(user_id, mode, resolve_mode, scrape)

    def _worker():
        try:
            _ensure_job_items_table()
            _update_job(job_id, status="running", started_at=datetime.utcnow())

            schema = _schema_for_user(user_id)
            modes = (
                ["intersect", "diff"]
                if mode == "both"
                else [("intersect" if mode == "intersect" else "diff")]
            )

            # 1) 快照
            snap_total = 0
            for m in modes:
                added = _snapshot_items(schema, m, job_id, limit)
                snap_total += added

            _update_job(job_id, total=snap_total)
            logger.info(
                "crawl start (from snapshot) | job_id=%s total=%s schema=%s modes=%s",
                job_id,
                snap_total,
                schema,
                modes,
            )

            # 2) 目標表
            _ensure_output_tables(schema)

            # 3) consume snapshot
            processed = 0
            select_sql = """
              SELECT mode,"Chr","Start","End","Ref","Alt",
                     occurrence_count, case_count, analysis_case_total, case_ratio,
                     payload AS detail, created_at, updated_at
              FROM public.clinvar_crawl_job_items
              WHERE job_id = %s
              ORDER BY "Chr","Start","Ref","Alt"
            """
            with PgConn(autocommit=True) as conn, conn.cursor(
                cursor_factory=RealDictCursor
            ) as cur:
                cur.execute(select_sql, [job_id])
                for row in cur:
                    # ← 每筆之前先檢查 job 狀態，有人按「取消」就停
                    try:
                        job_now = _get_job(job_id)
                        if job_now and job_now.get("status") == "canceled":
                            logger.info(
                                "job canceled detected in worker | job_id=%s processed=%s",
                                job_id,
                                processed,
                            )
                            break

                        q = build_query_from_rowlike(row)
                        if not q:
                            continue

                        # 解析 URL
                        if resolve_mode == "term":
                            url = build_term_url(q)
                        else:
                            url = get_clinvar_url_by_entrez(q)
                            if url == "not_found" or (
                                isinstance(url, str) and url.startswith("error:")
                            ):
                                url = build_term_url(q)

                        rec = {
                            "Chr": row["Chr"],
                            "Start": row["Start"],
                            "End": row["End"],
                            "Ref": row["Ref"],
                            "Alt": row["Alt"],
                            "query": q,
                            "resolve_mode": resolve_mode,
                            "clinvar_url": url,
                            "status": "ok"
                            if url and not str(url).startswith("error:")
                            else (url or "not_found"),
                        }
                        _upsert_lookup(conn, schema, rec)

                        if scrape:
                            latest = fetch_clinvar_latest_one(url)
                            if latest:
                                _upsert_latest(conn, schema, row, latest, q)

                    except Exception:
                        logger.exception(
                            f"row fail | job_id={job_id} "
                            f"row_head={{Chr:{row.get('Chr')},Start:{row.get('Start')},"
                            f"Ref:{row.get('Ref')},Alt:{row.get('Alt')}}}"
                        )
                    finally:
                        processed += 1
                        if processed % 10 == 0 or processed == snap_total:
                            _update_job(job_id, processed=processed)

            # 重新讀一次 job 狀態，看是正常完成還是使用者取消
            job_final = _get_job(job_id)
            if job_final and job_final.get("status") == "canceled":
                _update_job(
                    job_id,
                    processed=processed,
                    finished_at=datetime.utcnow(),
                )
                logger.info(
                    "crawl canceled | job_id=%s processed=%s total=%s",
                    job_id,
                    processed,
                    snap_total,
                )
            else:
                _update_job(
                    job_id,
                    processed=processed,
                    status="done",
                    finished_at=datetime.utcnow(),
                )
                logger.info(
                    "crawl done | job_id=%s processed=%s total=%s",
                    job_id,
                    processed,
                    snap_total,
                )

        except Exception:
            logger.exception("crawl fatal | job_id=%s", job_id)
            _update_job(
                job_id,
                status="error",
                last_error="see server logs",
                finished_at=datetime.utcnow(),
            )

    import threading

    threading.Thread(target=_worker, daemon=True).start()
    return JsonResponse({"job_id": job_id})


# ============================================================================


@csrf_exempt
@require_POST
def clinvar_cancel(request):
    """
    取消 job
    POST body(JSON): { "job_id": "..." }
    """
    body = _parse_json_body(request)
    if not body:
        return HttpResponseBadRequest("invalid json body")

    job_id = body.get("job_id")
    if not job_id:
        return HttpResponseBadRequest("missing job_id")

    try:
        job = _get_job(job_id)
        if not job:
            return JsonResponse({"error": "job not found"}, status=404)

        # 將狀態改為 canceled，worker 會偵測到後自行停掉
        _update_job(job_id, status="canceled", last_error="canceled by user")
        logger.info(f"job canceled by user | job_id={job_id}")
        return JsonResponse({"ok": True, "job_id": job_id, "status": "canceled"})
    except Exception:
        logger.exception(f"clinvar_cancel error | job_id={job_id}")
        return JsonResponse({"error": "internal error"}, status=500)


@csrf_exempt
@require_POST
def clinvar_status(request):
    """
    查詢 job 狀態
    POST body(JSON): { "job_id": "..." }
    """
    body = _parse_json_body(request)
    if not body:
        return HttpResponseBadRequest("invalid json body")

    job_id = body.get("job_id")
    if not job_id:
        return HttpResponseBadRequest("missing job_id")
    try:
        job = _get_job(job_id)
    except Exception:
        return JsonResponse({"error": "internal error"}, status=500)

    if not job:
        return JsonResponse({"error": "job not found"}, status=404)

    total = job.get("total") or 0
    processed = job.get("processed") or 0
    pct = (processed / total * 100.0) if total > 0 else 0.0
    if pct > 100.0:
        pct = 100.0
    return JsonResponse(
        {
            "job_id": job_id,
            "status": job.get("status"),
            "total": total,
            "processed": processed,
            "percent": round(pct, 1),
            "last_error": job.get("last_error"),
            "started_at": job.get("started_at"),
            "finished_at": job.get("finished_at"),
        }
    )


@csrf_exempt
@require_POST
def clinvar_items(request):
    """
    列出 job 拍到的 snapshot item（可依 mode 分類）
    POST body(JSON):
      {
        "job_id": "...",
        "mode": "intersect" | "diff" | null,
        "page": 1,
        "page_size": 25
      }
    """
    body = _parse_json_body(request)
    if not body:
        return HttpResponseBadRequest("invalid json body")

    job_id = body.get("job_id")
    if not job_id:
        return HttpResponseBadRequest("missing job_id")

    mode = (body.get("mode") or "").strip().lower()

    try:
        page = int(body.get("page") or 1)
    except Exception:
        page = 1
    try:
        page_size = int(body.get("page_size") or 25)
    except Exception:
        page_size = 25

    page = max(1, page)
    page_size = max(1, min(1000, page_size))
    offset = (page - 1) * page_size

    try:
        where = "WHERE job_id = %s"
        params = [job_id]
        if mode in ("intersect", "diff"):
            where += " AND mode = %s"
            params.append(mode)

        count_sql = f"SELECT COUNT(*) FROM public.clinvar_crawl_job_items {where}"
        data_sql = f"""
            SELECT mode,"Chr","Start","End","Ref","Alt",payload,created_at,updated_at
            FROM public.clinvar_crawl_job_items
            {where}
            ORDER BY "Chr","Start","Ref","Alt"
            LIMIT %s OFFSET %s
        """

        with PgConn(autocommit=True) as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(count_sql, params)
            total = int(cur.fetchone()["count"])
            cur.execute(data_sql, [*params, page_size, offset])
            rows = cur.fetchall()

        return JsonResponse(
            {"rows": rows, "total": total, "page": page, "page_size": page_size},
            json_dumps_params={"ensure_ascii": False},
        )
    except Exception:
        logger.exception("clinvar_items error | job_id=%s", job_id)
        return JsonResponse({"error": "internal error"}, status=500)


@csrf_exempt
@require_POST
def clinvar_written(request):
    """
    回報自某個 job 開始以來，實際寫入 lookup / latest 的筆數與 sample
    POST body(JSON): { "job_id": "..." }
    """
    body = _parse_json_body(request)
    if not body:
        return HttpResponseBadRequest("invalid json body")

    job_id = body.get("job_id")
    if not job_id:
        return HttpResponseBadRequest("missing job_id")

    try:
        job = _get_job(job_id)
        if not job:
            return JsonResponse({"error": "job not found"}, status=404)

        user_id = int(job["user_id"])
        started_at = job.get("started_at")
        schema = _schema_for_user(user_id)

        with PgConn(autocommit=True) as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                sql.SQL(
                    """
                    SELECT COUNT(*) AS c FROM {}.clinvar_lookup
                    WHERE created_at_db >= %s
                    """
                ).format(sql.Identifier(schema)),
                [started_at],
            )
            lookup_count = int(cur.fetchone()["c"])

            cur.execute(
                sql.SQL(
                    """
                    SELECT COUNT(*) AS c FROM {}.clinvar_latest
                    WHERE created_at_db >= %s
                    """
                ).format(sql.Identifier(schema)),
                [started_at],
            )
            latest_count = int(cur.fetchone()["c"])

            cur.execute(
                sql.SQL(
                    """
                    SELECT "Chr","Start","End","Ref","Alt", query, clinvar_url, status, created_at_db
                    FROM {}.clinvar_lookup
                    WHERE created_at_db >= %s
                    ORDER BY created_at_db DESC
                    LIMIT 20
                    """
                ).format(sql.Identifier(schema)),
                [started_at],
            )
            lookup_samples = cur.fetchall()

            cur.execute(
                sql.SQL(
                    """
                    SELECT "Chr","Start","End","Ref","Alt", query, clinvar_url,
                           classification, review_stars, condition, submitter,
                           created_at_db
                    FROM {}.clinvar_latest
                    WHERE created_at_db >= %s
                    ORDER BY created_at_db DESC
                    LIMIT 20
                    """
                ).format(sql.Identifier(schema)),
                [started_at],
            )
            latest_samples = cur.fetchall()

        return JsonResponse(
            {
                "schema": schema,
                "started_at": started_at,
                "lookup_count": lookup_count,
                "latest_count": latest_count,
                "lookup_samples": lookup_samples,
                "latest_samples": latest_samples,
            },
            json_dumps_params={"ensure_ascii": False},
        )
    except Exception:
        logger.exception("clinvar_written error | job_id=%s", job_id)
        return JsonResponse({"error": "internal error"}, status=500)

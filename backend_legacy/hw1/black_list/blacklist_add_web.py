# yourapp/black_list/blacklist_add_web.py
import json, traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from psycopg2.extras import RealDictCursor

from ..postgressql_setting.dbpool import PgConn  # <<< 使用共用連線池（避免 put unkeyed connection）

def _err(stage, e, status=500, debug=False, stage_hist=None, extra=None):
    payload = {"error": f"{stage}: {type(e).__name__}: {str(e)}", "stage": stage}
    if stage_hist: payload["stage_hist"] = stage_hist
    if debug: payload["traceback"] = traceback.format_exc()
    if extra: payload.update(extra)
    return JsonResponse(payload, status=status, json_dumps_params={"ensure_ascii": False})

@csrf_exempt
@require_POST
def blacklist_user_summary(request):
    stage = "init"
    stage_hist = []
    try:
        # 1) 解析 body
        stage = "parse_body"; stage_hist.append(stage)
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except Exception as e:
            return _err(stage, e, status=400, debug=True, stage_hist=stage_hist)

        debug = bool(body.get("debug", False))

        # 2) 檢查 user_id
        stage = "validate_user_id"; stage_hist.append(stage)
        try:
            user_id = int(body.get("user_id"))
        except Exception as e:
            return _err(stage, e, status=400, debug=debug, stage_hist=stage_hist, extra={"hint":"user_id 必填且為整數"})

        schema     = f"user_{user_id}"
        table      = (body.get("table") or "").strip()
        page       = max(1, int(body.get("page", 1)))
        page_size  = max(1, min(int(body.get("pageSize", 25)), 200))
        offset     = (page - 1) * page_size

        # 3) schema 存在？
        stage = "check_schema"; stage_hist.append(stage)
        with PgConn(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 1
                    FROM pg_catalog.pg_namespace
                    WHERE nspname = %s
                """, (schema,))
                has_schema = cur.fetchone() is not None
        if not has_schema:
            return JsonResponse({"error": f"{stage}: schema 不存在: {schema}", "schema": schema, "stage_hist": stage_hist},
                                status=404, json_dumps_params={"ensure_ascii": False})

        # 4) 列出 vep_annovar_merge_*（用 pg_catalog + 參數化 LIKE）
        stage = "list_tables"; stage_hist.append(stage)
        with PgConn(autocommit=True) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                like_pattern = r"vep\_annovar\_merge\_%"
                cur.execute("""
                    SELECT tablename AS table_name
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = %s
                      AND tablename LIKE %s ESCAPE '\\'
                    ORDER BY tablename
                """, (schema, like_pattern))
                rows_dict = [dict(r) for r in cur.fetchall()]
                tables = [str(r.get("table_name")) for r in rows_dict if r.get("table_name")]

        if not table:
            return JsonResponse({"schema": schema, "tables": tables, "info": "提供 table 可讀取單表資料", "stage_hist": stage_hist},
                                status=200, json_dumps_params={"ensure_ascii": False})

        if table not in tables:
            return JsonResponse({"schema": schema, "tables": tables, "error": f"指定的 table 不存在: {table}", "stage_hist": stage_hist},
                                status=404, json_dumps_params={"ensure_ascii": False})

        # 5) 單表總數
        stage = "read_table_total"; stage_hist.append(stage)
        with PgConn(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                total_row = cur.fetchone()
                total = int(total_row[0]) if total_row else 0

        # 6) 分頁資料
        stage = "read_table_rows"; stage_hist.append(stage)
        with PgConn(autocommit=True) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f'SELECT * FROM "{schema}"."{table}" LIMIT %s OFFSET %s',
                    (page_size, offset)
                )
                rows_raw = cur.fetchall()
                rows = [dict(r) for r in rows_raw]

        stage = "respond"; stage_hist.append(stage)
        return JsonResponse(
            {"schema": schema, "table": table, "total": total, "page": page, "pageSize": page_size, "rows": rows, "stage_hist": stage_hist},
            status=200, json_dumps_params={"ensure_ascii": False}
        )

    except Exception as e:
        return _err(stage, e, status=500, debug=True, stage_hist=stage_hist)

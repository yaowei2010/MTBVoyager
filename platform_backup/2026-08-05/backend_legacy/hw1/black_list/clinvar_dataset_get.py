# hw1/black_list/clinvar_result_api.py
from __future__ import annotations

import json
import re
from typing import List

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from ..postgressql_setting.dbpool import PgConn
from .blacklist_clinvar_web import _schema_for_user

# 允許排序的欄位白名單（避免 SQL 注入）
_SORTABLE = {
    "Chr": '"Chr"',
    "Start": '"Start"',
    "End": '"End"',
    "Ref": '"Ref"',
    "Alt": '"Alt"',
    "query": "query",
    "clinvar_url": "clinvar_url",
    # Legacy columns no longer displayed/searched by default
    "classification": "classification",
    "review_stars": "review_stars",
    "created_at_db": "created_at_db",   # 建議用這個排序（真正的時間）
    "created_at": "created_at_db",      # 前端若傳 created_at，就映射到 created_at_db

    # 來源時間欄位（排序仍用原始欄位）
    "src_created_at": "src_created_at",
    "src_updated_at": "src_updated_at",

    # 新增 ClinVar germline / somatic summary 欄位
    "germline_classification": "germline_classification",
    "germline_review_stars": "germline_review_stars",
    "germline_submission_count": "germline_submission_count",
    "somatic_clinical_impact": "somatic_clinical_impact",
    "somatic_clinical_impact_review_stars": "somatic_clinical_impact_review_stars",
    "somatic_clinical_impact_submission_count": "somatic_clinical_impact_submission_count",
    "somatic_oncogenicity": "somatic_oncogenicity",
    "somatic_oncogenicity_review_stars": "somatic_oncogenicity_review_stars",
    "somatic_oncogenicity_submission_count": "somatic_oncogenicity_submission_count",
}

# ISO-like datetime pattern: 2025-11-10T19:47:36Z, 2025-11-10 19:47:36+00:00, etc.
_TIME_PATTERN = re.compile(
    r'^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})'
    r'(?:\.\d+)?'            # optional .fraction
    r'(?:Z|[+-]\d{2}:?\d{2})?$'  # optional timezone
)


def _normalize_payload_datetime(value):
    """
    將 payload 中看起來像時間的字串，統一轉成 'YYYY-MM-DD HH:MM:SS'。
    遞迴處理 dict / list，其它型別保持原樣。
    """
    if isinstance(value, dict):
        return {k: _normalize_payload_datetime(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize_payload_datetime(v) for v in value]
    if isinstance(value, str):
        m = _TIME_PATTERN.match(value)
        if m:
            # 只取 date + time，不處理時區偏移
            return f"{m.group(1)} {m.group(2)}"
    return value


# ---------- 這三個 helper 跟 blacklist_compare_view 裡的邏輯一致 ----------

def _list_merge_tables(schema: str) -> list[str]:
    """列出 user_xxx schema 下所有 vep_annovar_merge_* 表（給 payload 欄位排序用）"""
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = %s
              AND tablename LIKE %s ESCAPE '\\'
            ORDER BY tablename
            """,
            [schema, r"vep_annovar_merge\_%"],
        )
        return [r[0] for r in cur.fetchall()]


def _get_table_columns_order(schema: str, table: str) -> list[str]:
    """
    取得單一表的欄位「順序」：
      使用 pg_attribute.attnum，只取實體欄位（排除 dropped/system）
    """
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname
            FROM pg_catalog.pg_attribute a
            JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s
              AND c.relname = %s
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
            """,
            [schema, table],
        )
        return [row[0] for row in cur.fetchall()]


def _merge_column_orders(list_of_lists: list[list[str]]) -> list[str]:
    """多表欄位順序做「去重且保序」合併。"""
    seen = set()
    merged: list[str] = []
    for cols in list_of_lists:
        for c in cols:
            if c not in seen:
                seen.add(c)
                merged.append(c)
    return merged

# -----------------------------------------------------------------


@csrf_exempt
@require_POST
def clinvar_result(request):
    """
    以 POST 方式查 {schema}.clinvar_latest（伺服端分頁/排序/搜尋）

    body(JSON):
      user_id        (int, 必填)
      page           (int, 1-based, 預設 1)
      pageSize       (int, 預設 25, 上限 1000)
      sortBy         (str, 預設 created_at_db)
      sortDir        ('asc'|'desc', 預設 desc)
      q              (str, 關鍵字，會在 query/classification/condition/submitter 模糊搜尋)

    回傳：
      {
        rows: [
          {
            "Chr","Start","End","Ref","Alt",
            "query","clinvar_url","classification","review_stars","condition","submitter",
            "created_at_db",        # 原始 timestamp（給排序用）
            "created_at",           # 已格式化字串：YYYY-MM-DD HH24:MI:SS（Asia/Taipei）
            "src_created_at",       # 已格式化字串：YYYY-MM-DD HH24:MI:SS（Asia/Taipei）
            "src_updated_at",       # 已格式化字串：YYYY-MM-DD HH24:MI:SS（Asia/Taipei）
            "detail",               # src_payload JSONB（裡面的時間字串也已正規化）
          }, ...
        ],
        total: int,
        page: int,
        page_size: int,
        columns: [ "欄位1","欄位2", ... ]   # detail 內 JSON 的欄位順序（多表合併，保序去重）
      }
    """
    # 解析 body
    try:
        body = request.json if hasattr(request, "json") else None
    except Exception:
        body = None
    if not body:
        try:
            body = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return HttpResponseBadRequest("invalid json body")

    # 驗證與預設
    user_id = body.get("user_id")
    if user_id is None:
        return HttpResponseBadRequest("missing user_id")
    try:
        user_id = int(user_id)
    except Exception:
        return HttpResponseBadRequest("invalid user_id")

    page = body.get("page", 1)
    page_size = body.get("pageSize", 25)
    sort_by = (body.get("sortBy") or "created_at_db").strip()
    sort_dir = (body.get("sortDir") or "desc").strip().lower()
    keyword = (body.get("q") or "").strip()

    try:
        page = max(1, int(page))
    except Exception:
        page = 1
    try:
        page_size = max(1, min(1000, int(page_size)))
    except Exception:
        page_size = 25
    sort_dir = "desc" if sort_dir not in ("asc", "desc") else sort_dir

    schema = _schema_for_user(user_id)
    offset = (page - 1) * page_size

    try:
        with PgConn(autocommit=True) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            table_ident = sql.Identifier(schema, "clinvar_latest")

            # WHERE：keyword 模糊搜尋
            where_parts = []
            params: List[object] = []
            if keyword:
                like = f"%{keyword}%"
                where_parts.append(
                    sql.SQL(
                        """
                        (query ILIKE %s
                         OR germline_classification ILIKE %s
                         OR somatic_clinical_impact ILIKE %s
                         OR somatic_oncogenicity ILIKE %s)
                        """
                    )
                )
                params += [like, like, like, like]

            where_sql = sql.SQL("")
            if where_parts:
                where_sql = sql.SQL(" WHERE ") + sql.SQL(" AND ").join(where_parts)

            # COUNT
            count_sql = sql.SQL("SELECT COUNT(*) AS c FROM {}").format(table_ident) + where_sql
            cur.execute(count_sql, params)
            total = int(cur.fetchone()["c"])

            # SELECT 主體
            select_base = (
                sql.SQL(
                    """
                SELECT
                  "Chr","Start","End","Ref","Alt",
                  src_payload->>'AF' AS "AF",
                  src_payload->>'TaiwanBioBank' AS "TaiwanBioBank",
                  occurrence_count,
                  case_count,
                  analysis_case_total,
                  case_ratio,
                  query,
                  clinvar_url,

                  -- ClinVar 頁面上方 germline/somatic summary
                  germline_classification,
                  germline_review_stars,
                  germline_submission_count,
                  somatic_clinical_impact,
                  somatic_clinical_impact_review_stars,
                  somatic_clinical_impact_submission_count,
                  somatic_oncogenicity,
                  somatic_oncogenicity_review_stars,
                  somatic_oncogenicity_submission_count,
                  clinvar_summary,

                  created_at_db,
                  to_char(
                    COALESCE(created_at_db, NOW()) AT TIME ZONE 'Asia/Taipei',
                    'YYYY-MM-DD HH24:MI:SS'
                  ) AS created_at,
                  CASE
                    WHEN src_created_at IS NOT NULL THEN
                      to_char(
                        src_created_at AT TIME ZONE 'Asia/Taipei',
                        'YYYY-MM-DD HH24:MI:SS'
                      )
                    ELSE NULL
                  END AS src_created_at,
                  CASE
                    WHEN src_updated_at IS NOT NULL THEN
                      to_char(
                        src_updated_at AT TIME ZONE 'Asia/Taipei',
                        'YYYY-MM-DD HH24:MI:SS'
                      )
                    ELSE NULL
                  END AS src_updated_at,
                  src_payload AS detail
                FROM {}
            """
                ).format(table_ident)
                + where_sql
            )
            # ORDER + LIMIT/OFFSET（白名單）
            order_col = sql.SQL(_SORTABLE.get(sort_by, "created_at_db"))
            select_sql = (
                select_base
                + sql.SQL(" ORDER BY ")
                + order_col
                + sql.SQL(f" {sort_dir.upper()} NULLS LAST ")
                + sql.SQL(" LIMIT %s OFFSET %s ")
            )
            cur.execute(select_sql, [*params, page_size, offset])
            rows = cur.fetchall()

        # payload 內的時間字串正規化
        for r in rows:
            if "detail" in r and r["detail"] is not None:
                r["detail"] = _normalize_payload_datetime(r["detail"])

        # 整理 detail(JSONB) 欄位順序：跟 blacklist_compare_view 一樣看 vep_annovar_merge_* 的實際欄位
        tables = _list_merge_tables(schema)
        if tables:
            col_lists = [_get_table_columns_order(schema, t) for t in tables]
            payload_columns = _merge_column_orders(col_lists)
        else:
            payload_columns = []

        # 確保每列有 id
        for r in rows:
            r.setdefault(
                "id",
                f'{r.get("Chr","")}|{r.get("Start","")}|{r.get("End","")}|{r.get("Ref","")}|{r.get("Alt","")}',
            )

        return JsonResponse(
            {
                "rows": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "columns": payload_columns,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500, json_dumps_params={"ensure_ascii": False})

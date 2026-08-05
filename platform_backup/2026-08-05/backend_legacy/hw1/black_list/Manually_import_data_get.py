# hw1/black_list/clinvar_blacklist_list_api.py
from __future__ import annotations

import json
from typing import List

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from ..postgressql_setting.dbpool import PgConn
from .blacklist_clinvar_web import _schema_for_user
from .blacklist_manual_import import (   # 如果檔名不同就改成你的匯入檔名
    _list_merge_tables,
    _get_table_columns_order,
    _merge_column_orders,
    _BASE_HEAD,
    _BASE_TAIL,
)

# 可以排序的欄位
_SORTABLE = {
    "Chr": '"Chr"',
    "Start": '"Start"',
    "End": '"End"',
    "Ref": '"Ref"',
    "Alt": '"Alt"',
    "created_at_db": "created_at_db",
    "src_created_at": "src_created_at",
    "src_updated_at": "src_updated_at",
}

# 🟥 這些欄位「只存在於資料庫」，但永遠不出現在畫面上的 columns
_HIDDEN_COLS = {"id", "classification", "review_stars", "condition", "submitter","created_at"}


@csrf_exempt
@require_POST
def clinvar_blacklist_list(request):
    """
    列出 user_xxx.clinvar_blacklist（伺服端分頁/排序），
    欄位順序：HEAD(Chr..Alt) → payload(依 vep_annovar_merge_* 順序) → TAIL(time欄位) → 其他。
    _HIDDEN_COLS 內的欄位不會出現在 columns 中。
    """
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return HttpResponseBadRequest("invalid json body")

    user_id = body.get("user_id")
    if user_id is None:
        return HttpResponseBadRequest("missing user_id")
    try:
        user_id = int(user_id)
    except Exception:
        return HttpResponseBadRequest("invalid user_id")

    page = body.get("page", 1)
    page_size = body.get("pageSize", 25)
    sort_by = (body.get("sortBy") or "created_at").strip()
    sort_dir = (body.get("sortDir") or "desc").strip().lower()

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
            table_ident = sql.Identifier(schema, "clinvar_blacklist")

            # 表是否存在
            cur.execute(
                "SELECT to_regclass(%s) IS NOT NULL AS exists",
                [f"{schema}.clinvar_blacklist"],
            )
            if not cur.fetchone()["exists"]:
                return JsonResponse(
                    {
                        "rows": [],
                        "total": 0,
                        "page": page,
                        "page_size": page_size,
                        "columns": [],
                    },
                    json_dumps_params={"ensure_ascii": False},
                )

            # COUNT
            count_sql = sql.SQL("SELECT COUNT(*) AS c FROM {}").format(table_ident)
            cur.execute(count_sql)
            total = int(cur.fetchone()["c"])

            # SELECT * + 排序
            order_col = sql.SQL(_SORTABLE.get(sort_by, "created_at"))
            select_sql = (
                sql.SQL("SELECT * FROM {}").format(table_ident)
                + sql.SQL(" ORDER BY ")
                + order_col
                + sql.SQL(f" {sort_dir.upper()} NULLS LAST ")
                + sql.SQL(" LIMIT %s OFFSET %s ")
            )
            cur.execute(select_sql, [page_size, offset])
            rows = cur.fetchall()

            actual_cols = [d.name for d in cur.description]

        # 取得 vep_annovar_merge_* 欄位順序
        tables = _list_merge_tables(schema)
        if tables:
            col_lists = [_get_table_columns_order(schema, t) for t in tables]
            payload_columns_all = _merge_column_orders(col_lists)
        else:
            payload_columns_all = []

        # payload 欄位 = 同時出現在 blacklist 表 + vep 表 的那些（排除隱藏欄位）
        payload_cols = [
            c
            for c in payload_columns_all
            if c in actual_cols
            and c not in _BASE_HEAD
            and c not in _BASE_TAIL
            and c not in _HIDDEN_COLS
        ]

        ordered_cols: List[str] = []
        seen = set()

        # 1) HEAD
        for c in _BASE_HEAD:
            if c in actual_cols and c not in _HIDDEN_COLS and c not in seen:
                ordered_cols.append(c)
                seen.add(c)

        # 2) payload（依 vep 欄位順序）
        for c in payload_cols:
            if c in actual_cols and c not in _HIDDEN_COLS and c not in seen:
                ordered_cols.append(c)
                seen.add(c)

        # 3) TAIL + created_at
        for c in [* _BASE_TAIL, "created_at"]:
            if c in actual_cols and c not in _HIDDEN_COLS and c not in seen:
                ordered_cols.append(c)
                seen.add(c)

        # 4) 其他剩餘欄位（排除隱藏欄位）
        for c in sorted(actual_cols):
            if c not in seen and c not in _HIDDEN_COLS:
                ordered_cols.append(c)
                seen.add(c)

        return JsonResponse(
            {
                "rows": rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "columns": ordered_cols,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )

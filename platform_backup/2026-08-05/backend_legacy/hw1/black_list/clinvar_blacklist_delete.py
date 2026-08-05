# hw1/black_list/clinvar_blacklist_delete_api.py
from __future__ import annotations

import json
from typing import List

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from psycopg2 import sql

from ..postgressql_setting.dbpool import PgConn
from .blacklist_clinvar_web import _schema_for_user


@csrf_exempt
@require_POST
def clinvar_blacklist_delete(request):
    """
    刪除使用者 schema 下 clinvar_blacklist 的資料列

    Request JSON:
      {
        "user_id": 5,
        "ids": [1,2,3]
      }

    Response JSON:
      {
        "ok": true,
        "deleted": 3
      }
    """
    # 解析 body
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return HttpResponseBadRequest("invalid json body")

    user_id = body.get("user_id")
    ids = body.get("ids")

    if user_id is None:
        return HttpResponseBadRequest("missing user_id")
    try:
        user_id = int(user_id)
    except Exception:
        return HttpResponseBadRequest("invalid user_id")

    if not isinstance(ids, list) or not ids:
        return HttpResponseBadRequest("ids must be a non-empty array")

    # 全部轉成 int，過濾掉不合法的
    id_list: List[int] = []
    for x in ids:
        try:
            id_list.append(int(x))
        except Exception:
            continue

    if not id_list:
        return HttpResponseBadRequest("no valid ids to delete")

    schema = _schema_for_user(user_id)

    try:
        with PgConn(autocommit=False) as conn, conn.cursor() as cur:
            table_ident = sql.Identifier(schema, "clinvar_blacklist")

            # 確認表是否存在
            cur.execute(
                """
                SELECT to_regclass(%s) IS NOT NULL AS exists
                """,
                [f'{schema}.clinvar_blacklist'],
            )
            row = cur.fetchone()
            # row 會是 tuple，例如 (True,) 或 (False,)
            exists = bool(row[0]) if row is not None else False

            if not exists:
                return JsonResponse(
                    {"ok": False, "error": "table not found", "deleted": 0},
                    status=400,
                    json_dumps_params={"ensure_ascii": False},
                )

            # 刪除指定 id
            delete_sql = sql.SQL(
                "DELETE FROM {} WHERE id = ANY(%s)"
            ).format(table_ident)
            cur.execute(delete_sql, (id_list,))
            deleted = cur.rowcount or 0

        return JsonResponse(
            {"ok": True, "deleted": deleted},
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception as e:
        return JsonResponse(
            {"ok": False, "error": str(e)},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )

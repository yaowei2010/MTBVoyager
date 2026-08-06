# hw1/black_list/blacklist_import_api.py
from __future__ import annotations

import json
from typing import List, Dict, Any

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from psycopg2.extras import execute_values

from ..postgressql_setting.dbpool import PgConn
from .blacklist_clinvar_web import _schema_for_user

TARGET_TABLE_NAME = "clinvar_blacklist"

# HEAD / TAIL 欄位，會固定排在最前 / 最後
_BASE_HEAD: List[str] = ["Chr", "Start", "End", "Ref", "Alt"]
_BASE_TAIL: List[str] = ["created_at_db", "src_created_at", "src_updated_at"]


# ---------- 跟 clinvar_result_api 裡一樣的 helper：抓 vep_annovar_merge_* 欄位順序 ----------

def _list_merge_tables(schema: str) -> list[str]:
    """列出 user_xxx schema 下所有 vep_annovar_merge_* 表（給欄位排序用）"""
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
    """取得單一表的欄位實際順序（依 pg_attribute.attnum）"""
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


# ---------- 小工具：把 123191727.0 / "123191727.0" / 123191727 轉成 int ----------

def _parse_pos(val) -> int | None:
    """
    嘗試把 Start/End 轉成 int：
      - 123        -> 123
      - "123"      -> 123
      - "123.0"    -> 123
      - 123.0      -> 123
      - 其他失敗   -> None
    """
    if val in (None, ""):
        return None
    s = str(val).strip()
    try:
        return int(s)
    except Exception:
        try:
            return int(float(s))
        except Exception:
            return None


@csrf_exempt
@require_POST
def blacklist_import_from_clinvar(request):
    """
    從前端「已勾選 ClinVar Payload 彙整」匯入到使用者 schema 下表：
      {schema}.clinvar_blacklist

    會匯入的欄位：
      - 固定 head：Chr, Start, End, Ref, Alt
      - 中間：依 vep_annovar_merge_* 的欄位順序，把 payload 裡有的欄位塞進來
      - 固定 tail：created_at_db, src_created_at, src_updated_at

    ★ 已加入「不重複匯入」：
      - 同一個 request 內，先以 (Chr,Start,End,Ref,Alt) 去重
      - DB 端對 (Chr,Start,End,Ref,Alt) 建 UNIQUE INDEX
        並使用 ON CONFLICT DO NOTHING，避免多次呼叫 API 時重複插入
    """
    # 解析 body
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return HttpResponseBadRequest("invalid json body")

    user_id = body.get("user_id")
    rows = body.get("rows")

    if user_id is None:
        return HttpResponseBadRequest("missing user_id")
    try:
        user_id = int(user_id)
    except Exception:
        return HttpResponseBadRequest("invalid user_id")

    if not isinstance(rows, list) or not rows:
        return HttpResponseBadRequest("rows must be a non-empty array")

    schema = _schema_for_user(user_id)

    prepared_rows: List[Dict[str, Any]] = []
    skipped = 0

    # 先把每一列做基本清洗 & 型別處理
    for r in rows:
        if not isinstance(r, dict):
            skipped += 1
            continue

        chr_val = r.get("Chr")
        start_raw = r.get("Start")
        end_raw = r.get("End")
        ref_val = r.get("Ref")
        alt_val = r.get("Alt")

        # —— 關鍵欄位：Chr / Ref / Alt 一定要有，Start/End 允許缺 —— #
        if chr_val is None or ref_val is None or alt_val is None:
            skipped += 1
            continue

        # ✅ 用 _parse_pos，把 "123191727.0" 也轉成 123191727
        start_val = _parse_pos(start_raw)
        end_val = _parse_pos(end_raw)

        row_clean: Dict[str, Any] = dict(r)  # 先複製一份
        # 強制覆蓋關鍵欄位（避免 weird type）
        row_clean["Chr"] = str(chr_val)
        row_clean["Start"] = start_val
        row_clean["End"] = end_val
        row_clean["Ref"] = str(ref_val)
        row_clean["Alt"] = str(alt_val)

        prepared_rows.append(row_clean)

    if not prepared_rows:
        sample_row = rows[0] if rows else None
        return JsonResponse(
            {
                "ok": False,
                "error": "no valid rows to import",
                "skipped": skipped,
                "total_received": len(rows),
                "sample_first_row": sample_row,
            },
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    # ===== 在「同一批 request」內，以 (Chr,Start,End,Ref,Alt) 去重 =====
    dedup_seen = set()
    dedup_rows: List[Dict[str, Any]] = []
    duplicates_skipped = 0

    for r in prepared_rows:
        key = (r.get("Chr"), r.get("Start"), r.get("End"), r.get("Ref"), r.get("Alt"))
        if key in dedup_seen:
            duplicates_skipped += 1
            continue
        dedup_seen.add(key)
        dedup_rows.append(r)

    prepared_rows = dedup_rows

    if not prepared_rows:
        return JsonResponse(
            {
                "ok": False,
                "error": "no rows left after dedup",
                "skipped": skipped,
                "duplicates_skipped": duplicates_skipped,
                "total_received": len(rows),
            },
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    # ===== 收集所有 key（DataFrame 的所有欄位） =====
    all_keys = set()
    for r in prepared_rows:
        all_keys.update(r.keys())

    # ---- 取得 vep_annovar_merge_* 欄位順序，當作 payload 欄位排序依據 ----
    tables = _list_merge_tables(schema)
    if tables:
        col_lists = [_get_table_columns_order(schema, t) for t in tables]
        payload_columns_all = _merge_column_orders(col_lists)
    else:
        payload_columns_all = []

    # payload 真正要用的欄位 = 出現在 all_keys 裡的那些
    payload_cols = [
        c
        for c in payload_columns_all
        if c in all_keys and c not in _BASE_HEAD and c not in _BASE_TAIL and c != "id"
    ]

    # 1. 固定 HEAD 欄位
    insert_cols: List[str] = []
    for c in _BASE_HEAD:
        if c in all_keys:
            insert_cols.append(c)

    # 2. payload 欄位（依 vep_annovar_merge_* 順序）
    for c in payload_cols:
        if c not in insert_cols:
            insert_cols.append(c)

    # 3. 固定 TAIL 欄位
    for c in _BASE_TAIL:
        if c in all_keys and c not in insert_cols:
            insert_cols.append(c)

    # 4. 其他零星欄位（保險起見）
    for c in sorted(all_keys):
        if c not in insert_cols and c != "id":
            insert_cols.append(c)

    try:
        with PgConn(autocommit=False) as conn, conn.cursor() as cur:
            # 1) 確保 schema 存在
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

            # 2) 建立基礎表（只放 head + tail，其他欄位動態建立）
            cur.execute(
                f'''
                CREATE TABLE IF NOT EXISTS "{schema}"."{TARGET_TABLE_NAME}" (
                    id BIGSERIAL PRIMARY KEY,
                    "Chr" TEXT NOT NULL,
                    "Start" BIGINT,
                    "End" BIGINT,
                    "Ref" TEXT,
                    "Alt" TEXT,
                    created_at_db TEXT,
                    src_created_at TEXT,
                    src_updated_at TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
                '''
            )

            # 2-1) 為避免跨多次匯入重複，建立 UNIQUE INDEX（Chr,Start,End,Ref,Alt）
            cur.execute(
                f'''
                CREATE UNIQUE INDEX IF NOT EXISTS "{schema}_{TARGET_TABLE_NAME}_uniq"
                ON "{schema}"."{TARGET_TABLE_NAME}" ("Chr","Start","End","Ref","Alt")
                '''
            )

            # 3) 動態欄位（payload 其他欄位，全部 TEXT）
            base_and_system = {
                "id",
                "Chr",
                "Start",
                "End",
                "Ref",
                "Alt",
                "created_at_db",
                "src_created_at",
                "src_updated_at",
                "created_at",
            }
            dynamic_cols = [c for c in insert_cols if c not in base_and_system]

            for col in dynamic_cols:
                cur.execute(
                    f'ALTER TABLE "{schema}"."{TARGET_TABLE_NAME}" '
                    f'ADD COLUMN IF NOT EXISTS "{col}" TEXT'
                )

            # 4) 準備 INSERT values（依 insert_cols 的順序）
            cols_sql = ", ".join(f'"{c}"' for c in insert_cols)
            values: List[List[Any]] = []

            for r in prepared_rows:
                row_vals: List[Any] = []
                for c in insert_cols:
                    v = r.get(c)
                    if c in ("Start", "End"):
                        v = _parse_pos(v)
                    row_vals.append(v)
                values.append(row_vals)

            # 使用 ON CONFLICT DO NOTHING 避免已存在的變異再被插入
            insert_sql = (
                f'INSERT INTO "{schema}"."{TARGET_TABLE_NAME}" ({cols_sql}) '
                f'VALUES %s '
                f'ON CONFLICT ("Chr","Start","End","Ref","Alt") DO NOTHING'
            )

            execute_values(cur, insert_sql, values)
            inserted = cur.rowcount or 0  # 實際成功插入的 row 數

        return JsonResponse(
            {
                "ok": True,
                "inserted": inserted,
                "skipped": skipped,
                "duplicates_skipped": duplicates_skipped,
                "total_received": len(rows),
                "schema": schema,
                "table": TARGET_TABLE_NAME,
                "columns": insert_cols,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception as e:
        return JsonResponse(
            {"ok": False, "error": str(e), "schema": schema},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )

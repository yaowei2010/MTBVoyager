# views.py
from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from psycopg2 import sql
from ..postgressql_setting.dbpool import PgConn


# ──────────────────────────────────────────────────────────────────────────────
# Logging（寫到 /miRTI/logs/blacklist_compare.log，10MB x 5 個輪替）
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger("blacklist.compare")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    try:
        fh = RotatingFileHandler(
            "/miRTI/logs/blacklist_compare.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
        )
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except Exception as _e:
        # 若容器內沒有該目錄，不讓程式崩；仍可從 console 看訊息
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s",
        )
        logger.warning("log file handler init failed: %s", _e)


# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────

# 比對鍵：只用這五欄來判定是否為相同變異（JOIN/USING 與排序皆以此為準）
ALLOWED_COLUMNS: list[str] = ["Chr", "Start", "End", "Ref", "Alt"]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _dictfetchall(cur):
    """cursor => list[dict]（欄位名源自 cursor.description）"""
    cols = [c.name for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _schema_for_user(user_id: int) -> str:
    return f"user_{int(user_id)}"


def _list_merge_tables(schema: str) -> list[str]:
    """列出 user_xxx schema 下所有 vep_annovar_merge_* 表"""
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
      使用 pg_attribute.attnum（或 information_schema.columns.ordinal_position）
      只取實體欄位（排除 dropped/system）
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


def _to_bigint_clean(idt: sql.Identifier) -> sql.Composed:
    """
    只取欄位「開頭那一段連續的數字」轉成 BIGINT：
      例如：
        '123.45'     -> 123
        '123-456'    -> 123
        '123,456.7'  -> 123
        'chr1:12345' -> NULL  （因為不是以數字開頭）
    """
    return sql.SQL(
        "CAST(NULLIF(substring({}::text from '^[0-9]+'), '') AS BIGINT)"
    ).format(idt)



def _build_union_all_sql(schema: str, tables: list[str]) -> sql.Composed:
    """
    將多張 vep_annovar_merge_* 投影為：
      - 五鍵：Chr(TEXT), Start(BIGINT), End(BIGINT), Ref(TEXT), Alt(TEXT)
      - payload JSONB：整列 to_jsonb(t) 保存原始所有欄位/型別（取來源整列）
      - created_at / updated_at：來源表的時間欄位（若欄位名稱不同可擴充候選）
    再以 UNION ALL 串接。
    假設呼叫端已保證 tables 非空。
    """
    KEY_CANDIDATES: dict[str, list[str]] = {
        "Chr":   ["Chr"],
        "Start": ["Start"],
        "End":   ["End"],
        "Ref":   ["Ref"],
        "Alt":   ["Alt"],
    }

    selects: list[sql.Composed] = []
    for t in tables:
        # 這裡只需要「欄位集合」，用 order 函式 + set 即可，避免多寫一個幾乎一樣的查詢
        colset = set(_get_table_columns_order(schema, t))

        # 五鍵欄位（型別正規化）
        key_items: list[sql.Composed] = []
        for target_col, candidates in KEY_CANDIDATES.items():
            picked = next((c for c in candidates if c in colset), None)
            if target_col in ("Start", "End"):
                expr = (
                    _to_bigint_clean(sql.Identifier(picked))
                    if picked
                    else sql.SQL("CAST(NULL AS BIGINT)")
                )
            else:
                expr = (
                    sql.SQL("{}::text").format(sql.Identifier(picked))
                    if picked
                    else sql.SQL("CAST(NULL AS TEXT)")
                )
            key_items.append(
                sql.SQL("{} AS {}").format(expr, sql.Identifier(target_col))
            )

        # created_at / updated_at（轉 timestamptz；若沒有則為 NULL）
        c_picked = "created_at" if "created_at" in colset else None
        u_picked = "updated_at" if "updated_at" in colset else None

        created_expr = (
            sql.SQL("{}::timestamptz").format(sql.Identifier(c_picked))
            if c_picked
            else sql.SQL("CAST(NULL AS timestamptz)")
        )
        updated_expr = (
            sql.SQL("{}::timestamptz").format(sql.Identifier(u_picked))
            if u_picked
            else sql.SQL("CAST(NULL AS timestamptz)")
        )

        selects.append(
            sql.SQL(
                "SELECT {}, {}::text AS source_table, "
                "to_jsonb(t) AS payload, {} AS created_at, {} AS updated_at "
                "FROM {}.{} t"
            ).format(
                sql.SQL(", ").join(key_items),
                sql.Literal(t),
                created_expr,
                updated_expr,
                sql.Identifier(schema),
                sql.Identifier(t),
            )
        )

    return sql.SQL(" UNION ALL ").join(selects)


def _build_ori_distinct_select() -> sql.Composed:
    """public.blacklist_ori 投影為相同型別（Start/End→BIGINT，其餘TEXT）"""
    parts = [
        sql.SQL("{} AS {}").format(
            sql.SQL("{}::text").format(sql.Identifier("Chr")), sql.Identifier("Chr")
        ),
        sql.SQL("{} AS {}").format(
            _to_bigint_clean(sql.Identifier("Start")), sql.Identifier("Start")
        ),
        sql.SQL("{} AS {}").format(
            _to_bigint_clean(sql.Identifier("End")), sql.Identifier("End")
        ),
        sql.SQL("{} AS {}").format(
            sql.SQL("{}::text").format(sql.Identifier("Ref")), sql.Identifier("Ref")
        ),
        sql.SQL("{} AS {}").format(
            sql.SQL("{}::text").format(sql.Identifier("Alt")), sql.Identifier("Alt")
        ),
    ]
    return sql.Composed(
        [
            sql.SQL("SELECT DISTINCT "),
            sql.SQL(", ").join(parts),
            sql.SQL(" FROM public.blacklist_ori"),
        ]
    )



def _clinvar_blacklist_exists(schema: str) -> bool:
    """確認 user_xxx.clinvar_blacklist 是否存在。"""
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL", [f"{schema}.clinvar_blacklist"])
        row = cur.fetchone()
        return bool(row[0]) if row else False


def _build_effective_blacklist_select(schema: str) -> sql.Composed:
    """
    比對用黑名單：
      public.blacklist_ori + user_xxx.clinvar_blacklist

    只投影五鍵 Chr/Start/End/Ref/Alt。
    這裡使用 UNION 去重；對比對功能而言，只要位點存在於任一黑名單來源，就算黑名單。
    """
    original = _build_ori_distinct_select()

    user_added = sql.SQL(
        """
        SELECT DISTINCT
               "Chr"::text AS "Chr",
               CAST(NULLIF(substring("Start"::text from '^[0-9]+'), '') AS BIGINT) AS "Start",
               CAST(NULLIF(substring("End"::text from '^[0-9]+'), '') AS BIGINT) AS "End",
               "Ref"::text AS "Ref",
               "Alt"::text AS "Alt"
        FROM {}.{}
        WHERE "Chr" IS NOT NULL
          AND "Start" IS NOT NULL
          AND "End" IS NOT NULL
          AND "Ref" IS NOT NULL
          AND "Alt" IS NOT NULL
        """
    ).format(
        sql.Identifier(schema),
        sql.Identifier("clinvar_blacklist"),
    )

    return sql.Composed([
        sql.SQL("SELECT DISTINCT * FROM ("),
        original,
        sql.SQL(" UNION "),
        user_added,
        sql.SQL(") effective_blacklist"),
    ])

def _ensure_result_tables(schema: str) -> None:
    """
    建立/修補 user_xxx.blacklist_compare_{intersect,diff}
    欄位：
      Chr TEXT, Start BIGINT, End BIGINT, Ref TEXT, Alt TEXT,
      payload JSONB,
      created_at TIMESTAMPTZ,   -- 同組最早
      updated_at TIMESTAMPTZ,   -- 同組最晚
      created_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- 本表寫入時間（保留）
    再進行一次性去重（保留最新的一筆），最後建立唯一索引。
    """
    col_defs = [
        sql.SQL("{} TEXT").format(sql.Identifier("Chr")),
        sql.SQL("{} BIGINT").format(sql.Identifier("Start")),
        sql.SQL("{} BIGINT").format(sql.Identifier("End")),
        sql.SQL("{} TEXT").format(sql.Identifier("Ref")),
        sql.SQL("{} TEXT").format(sql.Identifier("Alt")),
        sql.SQL("occurrence_count BIGINT"),
        sql.SQL("case_count BIGINT"),
        sql.SQL("analysis_case_total BIGINT"),
        sql.SQL("case_ratio NUMERIC"),
        sql.SQL("payload JSONB"),
        sql.SQL("created_at TIMESTAMPTZ"),
        sql.SQL("updated_at TIMESTAMPTZ"),
        sql.SQL("created_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
    ]
    cols_sql = sql.SQL(", ").join(col_defs)

    def _dedupe_then_create_unique(conn, table_name: str):
        with conn.cursor() as cur:


            # 2) 先統計目前筆數
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(schema), sql.Identifier(table_name)
                )
            )
            before_cnt = int(cur.fetchone()[0])

            # 3) 以 row_number() 分組去重（保留最新的一筆）
            #    排序規則：updated_at DESC NULLS LAST, created_at DESC NULLS LAST, created_at_db DESC
            #    rn > 1 的列刪掉
            cur.execute(
                sql.SQL(
                    """
                    WITH ranked AS (
                      SELECT ctid,
                             ROW_NUMBER() OVER (
                               PARTITION BY "Chr","Start","End","Ref","Alt"
                               ORDER BY updated_at DESC NULLS LAST,
                                        created_at DESC NULLS LAST,
                                        created_at_db DESC
                             ) AS rn
                      FROM {}.{}
                    )
                    DELETE FROM {}.{} t
                    USING ranked r
                    WHERE t.ctid = r.ctid AND r.rn > 1
                """
                ).format(
                    sql.Identifier(schema),
                    sql.Identifier(table_name),
                    sql.Identifier(schema),
                    sql.Identifier(table_name),
                )
            )

            # 4) 再統計去重後筆數
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                    sql.Identifier(schema), sql.Identifier(table_name)
                )
            )
            after_cnt = int(cur.fetchone()[0])

            removed = before_cnt - after_cnt
            if removed > 0:
                logger.info(
                    "dedupe | %s.%s | before=%d after=%d removed=%d",
                    schema,
                    table_name,
                    before_cnt,
                    after_cnt,
                    removed,
                )
            else:
                logger.info("dedupe | %s.%s | no-dup", schema, table_name)

            # 5) 建唯一索引（IF NOT EXISTS）
            cur.execute(
                sql.SQL(
                    """
                    CREATE UNIQUE INDEX IF NOT EXISTS {} 
                    ON {}.{} ("Chr","Start","End","Ref","Alt")
                """
                ).format(
                    sql.Identifier(f"uniq_{table_name}_chr_start_end_ref_alt"),
                    sql.Identifier(schema),
                    sql.Identifier(table_name),
                )
            )

            # 6) 查詢輔助索引（非唯一）
            cur.execute(
                sql.SQL(
                    """
                    CREATE INDEX IF NOT EXISTS {} 
                    ON {}.{} ("Chr","Start","Ref","Alt", created_at_db)
                """
                ).format(
                    sql.Identifier(f"idx_{table_name}_chr_start_ref_alt_createddb"),
                    sql.Identifier(schema),
                    sql.Identifier(table_name),
                )
            )

    # 一個連線處理：建表 + 去重 + 建索引
    with PgConn(autocommit=True) as conn, conn.cursor() as cur:
        # 先確保兩張表存在
        for name in ("blacklist_compare_intersect", "blacklist_compare_diff"):
            cur.execute(
                sql.SQL("CREATE TABLE IF NOT EXISTS {}.{} ({})").format(
                    sql.Identifier(schema),
                    sql.Identifier(name),
                    cols_sql,
                )
            )
            # 舊表補欄位：若已存在舊版 blacklist_compare_*，補上統計欄位
            for addcol in (
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS occurrence_count BIGINT").format(
                    sql.Identifier(schema), sql.Identifier(name)
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS case_count BIGINT").format(
                    sql.Identifier(schema), sql.Identifier(name)
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS analysis_case_total BIGINT").format(
                    sql.Identifier(schema), sql.Identifier(name)
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS case_ratio NUMERIC").format(
                    sql.Identifier(schema), sql.Identifier(name)
                ),
            ):
                cur.execute(addcol)

        # 逐表去重 → 建唯一索引
        _dedupe_then_create_unique(conn, "blacklist_compare_intersect")
        _dedupe_then_create_unique(conn, "blacklist_compare_diff")


# ──────────────────────────────────────────────────────────────────────────────
# View
# ──────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def blacklist_compare_view(request):
    """
    比對 user_{user_id}.vep_annovar_merge_* 與有效黑名單
    有效黑名單 = public.blacklist_ori + user_xxx.clinvar_blacklist
    只以 (Chr, Start, End, Ref, Alt) 為判定欄位；
    去重後：
      - created_at = 該組最早建立時間 (MIN)
      - updated_at = 該組最晚更新時間 (MAX)
      - payload    = 取該組「最新 updated_at」那筆的整列 JSON
    並將結果「重建」寫入 user_<id>.blacklist_compare_{intersect,diff}，
    每次呼叫（save=True）都會先 TRUNCATE，確保結果表內容與當下計算一致。
    """
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")

        user_id = int(body.get("user_id") or 0)
        if not user_id:
            return HttpResponseBadRequest("missing user_id")

        mode = (body.get("mode") or "intersect").lower()
        if mode not in ("intersect", "diff"):
            mode = "intersect"

        page = max(1, int(body.get("page", 1)))
        page_size = max(1, min(1000, int(body.get("pageSize", 25))))
        save = bool(body.get("save", True))

        schema = _schema_for_user(user_id)
        tables = _list_merge_tables(schema)
        if not tables:
            logger.info(
                "user=%s | no vep_annovar_merge_* tables under %s", user_id, schema
            )
            return JsonResponse(
                {
                    "rows": [],
                    "total": 0,
                    "page": page,
                    "saved": {"intersect": 0, "diff": 0},
                    "columns": [],
                    "stats": {},
                }
            )

        # 整理原始資料表欄位順序（多表合併去重且保序）
        payload_columns = _merge_column_orders(
            [_get_table_columns_order(schema, t) for t in tables]
        )

        union_all = _build_union_all_sql(schema, tables)

        cols = [sql.Identifier(c) for c in ALLOWED_COLUMNS]
        cols_csv = sql.SQL(", ").join(cols)
        using_cols = sql.SQL(", ").join(cols)

        ori_select = _build_effective_blacklist_select(schema) if _clinvar_blacklist_exists(schema) else _build_ori_distinct_select()

        # 基底 CTE：user_all / user_dedup / ori / inter_cte / diff_cte
        # occurrence_count：該位點在所有 vep_annovar_merge_* 的總出現次數
        # case_count：該位點出現在幾個分析案例（以來源表 source_table 計算）
        # case_ratio：case_count / analysis_case_total
        analysis_case_total = len(tables)
        base_cte = sql.SQL(
            "WITH user_all AS ({}), "
            "user_dedup AS ("
            "  SELECT {}, "
            "         COUNT(*)::bigint AS occurrence_count, "
            "         COUNT(DISTINCT source_table)::bigint AS case_count, "
            "         {}::bigint AS analysis_case_total, "
            "         ROUND((COUNT(DISTINCT source_table)::numeric / NULLIF({}::numeric, 0)), 4) AS case_ratio, "
            "         MIN(created_at) AS created_at, "
            "         MAX(updated_at) AS updated_at, "
            "         (ARRAY_AGG(payload "
            "            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST"
            "          ))[1] AS payload "
            "  FROM user_all "
            "  GROUP BY {}"
            "), "
            "ori AS ({}), "
            "inter_cte AS ("
            "  SELECT u.{}, "
            "         u.occurrence_count, u.case_count, u.analysis_case_total, u.case_ratio, "
            "         u.payload, u.created_at, u.updated_at "
            "  FROM user_dedup u JOIN ori o USING ({})"
            "), "
            "diff_cte AS ("
            "  SELECT u.{}, "
            "         u.occurrence_count, u.case_count, u.analysis_case_total, u.case_ratio, "
            "         u.payload, u.created_at, u.updated_at "
            "  FROM user_dedup u LEFT JOIN ori o USING ({}) "
            "  WHERE o.\"Chr\" IS NULL"
            ")"
        ).format(
            union_all,
            cols_csv,
            sql.Literal(analysis_case_total),
            sql.Literal(analysis_case_total),
            cols_csv,
            ori_select,
            cols_csv,
            using_cols,
            cols_csv,
            using_cols,
        )

        which_cte = sql.SQL("inter_cte") if mode == "intersect" else sql.SQL("diff_cte")

        # 過濾無意義資料列
        where_not_all_dash = sql.SQL(
            """
        WHERE
          u.payload IS NOT NULL
          AND EXISTS (
              SELECT 1
              FROM jsonb_each_text(u.payload) kv
              WHERE kv.value IS NOT NULL
                    AND kv.value <> ''
                    AND kv.value <> '-'
          )
          -- 五鍵必須有意義的值
          AND COALESCE(NULLIF(u."Chr",  ''), '-') <> '-'
          AND u."Start" IS NOT NULL
          AND u."End"   IS NOT NULL
          AND COALESCE(NULLIF(u."Ref",  ''), '-') <> '-'
          AND COALESCE(NULLIF(u."Alt",  ''), '-') <> '-'
        """
        )

        # === 計數統計：user_all / user_dedup / inter_cte / diff_cte ===
        with PgConn(autocommit=True) as conn, conn.cursor() as cur:
            # user_all count
            cur.execute(
                sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" SELECT COUNT(*) FROM user_all"),
                    ]
                )
            )
            cnt_user_all = int(cur.fetchone()[0])

            # user_dedup count
            cur.execute(
                sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" SELECT COUNT(*) FROM user_dedup"),
                    ]
                )
            )
            cnt_user_dedup = int(cur.fetchone()[0])

            # inter_cte count（已去重）
            cur.execute(
                sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" SELECT COUNT(*) FROM inter_cte"),
                    ]
                )
            )
            cnt_inter = int(cur.fetchone()[0])

            # diff_cte count（已去重）
            cur.execute(
                sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" SELECT COUNT(*) FROM diff_cte"),
                    ]
                )
            )
            cnt_diff = int(cur.fetchone()[0])

        stats = {
            "tables": tables,
            "counts": {
                "user_all": cnt_user_all,
                "user_dedup": cnt_user_dedup,
                "intersect": cnt_inter,
                "diff": cnt_diff,
            },
        }
        logger.info(
            "user=%s schema=%s | tables=%d | user_all=%d user_dedup=%d inter=%d diff=%d",
            user_id,
            schema,
            len(tables),
            cnt_user_all,
            cnt_user_dedup,
            cnt_inter,
            cnt_diff,
        )

        # === 寫庫：採「重建」策略（TRUNCATE + INSERT），不再使用 UPSERT ===
        saved_counts = {"intersect": 0, "diff": 0}
        if save:
            _ensure_result_tables(schema)
            with PgConn() as conn, conn.cursor() as cur:
                # 先清空兩張結果表，確保內容與這次計算完全一致
                cur.execute(
                    sql.SQL("TRUNCATE {}.{}").format(
                        sql.Identifier(schema),
                        sql.Identifier("blacklist_compare_intersect"),
                    )
                )
                cur.execute(
                    sql.SQL("TRUNCATE {}.{}").format(
                        sql.Identifier(schema),
                        sql.Identifier("blacklist_compare_diff"),
                    )
                )

                insert_cols = sql.SQL(", ").join(
                    [
                        *cols,
                        sql.Identifier("occurrence_count"),
                        sql.Identifier("case_count"),
                        sql.Identifier("analysis_case_total"),
                        sql.Identifier("case_ratio"),
                        sql.Identifier("payload"),
                        sql.Identifier("created_at"),
                        sql.Identifier("updated_at"),
                    ]
                )

                # === intersect 重建 ===
                inter_sql = sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" INSERT INTO "),
                        sql.Identifier(schema),
                        sql.SQL("."),
                        sql.Identifier("blacklist_compare_intersect"),
                        sql.SQL(" ("),
                        insert_cols,
                        sql.SQL(") "),
                        sql.SQL(" SELECT "),
                        cols_csv,
                        sql.SQL(", occurrence_count, case_count, analysis_case_total, case_ratio, payload, created_at, updated_at FROM inter_cte "),
                    ]
                )
                cur.execute(inter_sql)
                saved_counts["intersect"] = cur.rowcount or 0

                # === diff 重建 ===
                diff_sql = sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" INSERT INTO "),
                        sql.Identifier(schema),
                        sql.SQL("."),
                        sql.Identifier("blacklist_compare_diff"),
                        sql.SQL(" ("),
                        insert_cols,
                        sql.SQL(") "),
                        sql.SQL(" SELECT "),
                        cols_csv,
                        sql.SQL(", occurrence_count, case_count, analysis_case_total, case_ratio, payload, created_at, updated_at FROM diff_cte "),
                    ]
                )
                cur.execute(diff_sql)
                saved_counts["diff"] = cur.rowcount or 0

            logger.info(
                "rewrite result tables | user=%s schema=%s | inter rows=%d diff rows=%d",
                user_id,
                schema,
                saved_counts["intersect"],
                saved_counts["diff"],
            )

        # === 回傳分頁資料 ===
        count_sql = sql.Composed(
            [
                base_cte,
                sql.SQL(" SELECT COUNT(*) FROM "),
                which_cte,
                sql.SQL(" u "),
                where_not_all_dash,
            ]
        )

        offset = (page - 1) * page_size
        data_sql = sql.Composed(
            [
                base_cte,
                sql.SQL(" SELECT "),
                cols_csv,
                sql.SQL(", u.occurrence_count, u.case_count, u.analysis_case_total, u.case_ratio, u.payload AS detail, u.created_at, u.updated_at"),
                sql.SQL(" FROM "),
                which_cte,
                sql.SQL(" u "),
                where_not_all_dash,
                sql.SQL(' ORDER BY "Chr","Start","Ref","Alt" '),
                sql.SQL(" LIMIT "),
                sql.Literal(page_size),
                sql.SQL(" OFFSET "),
                sql.Literal(offset),
            ]
        )

        with PgConn(autocommit=True) as conn, conn.cursor() as cur:
            cur.execute(count_sql)
            total = int(cur.fetchone()[0])

            cur.execute(data_sql)
            rows = _dictfetchall(cur)

        # 前端 row id
        def _make_key(r: dict) -> str:
            return "|".join(str(r.get(k, "")) for k in ALLOWED_COLUMNS)

        for r in rows:
            r.setdefault("id", _make_key(r))
            if "payload" in r:
                r["detail"] = r.pop("payload")

        logger.info(
            "respond | user=%s mode=%s page=%d size=%d total=%d",
            user_id,
            mode,
            page,
            page_size,
            total,
        )

        return JsonResponse(
            {
                "rows": rows,
                "total": total,
                "page": page,
                "saved": saved_counts if save else {"intersect": 0, "diff": 0},
                # 前端 detail 表格可用的原始欄位順序（多表合併）
                "columns": payload_columns,
                # 這次運算的統計（也已寫入 log）
                "stats": stats,
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception as e:
        logger.exception("blacklist_compare_view error")
        return JsonResponse(
            {"error": str(e)}, status=500, json_dumps_params={"ensure_ascii": False}
        )

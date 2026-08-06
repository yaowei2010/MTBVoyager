# yourapp/black_list/blacklist_main_web.py
from __future__ import annotations

import json
from urllib.parse import unquote

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from ..postgressql_setting.dbpool import PgConn


# 第一個黑名單主表要顯示的欄位
DISPLAY_COLUMNS = [
    "Gene",
    "Chr",
    "Start",
    "End",
    "Ref",
    "Alt",
    "Func.refGeneWithVer",
    "Gene.refGene",
    "ExonicFunc.refGeneWithVer",
    "AAChange.refGeneWithVer",
    "AF",
    "created_at_db",
    "src_created_at",
    "src_updated_at",
]

# 後端允許排序的欄位
SORTABLE_COLUMNS = set(DISPLAY_COLUMNS + ["source_type"])

SEARCH_COLUMNS = DISPLAY_COLUMNS + ["source_type"]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _schema_for_user(user_id: int) -> str:
    return f"user_{int(user_id)}"


def _safe_sort(sort_by: str, sort_dir: str):
    sort_by = sort_by if sort_by in SORTABLE_COLUMNS else "Chr"
    sort_dir = (sort_dir or "").lower()
    sort_dir = "desc" if sort_dir == "desc" else "asc"
    return sort_by, sort_dir


def _table_exists(cur, schema: str, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists", [f"{schema}.{table}"])
    row = cur.fetchone()
    return bool(row["exists"] if isinstance(row, dict) else row[0])


def _get_columns(cur, schema: str, table: str) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        """,
        [schema, table],
    )
    return {r["column_name"] if isinstance(r, dict) else r[0] for r in cur.fetchall()}


def _text_col_expr(colset: set[str], candidates: list[str], alias: str) -> sql.Composed:
    """從候選欄位找第一個存在的欄位，統一轉 text 並 alias 成固定欄名。"""
    for c in candidates:
        if c in colset:
            return sql.SQL("{}::text AS {}").format(
                sql.Identifier(c),
                sql.Identifier(alias),
            )
    return sql.SQL("NULL::text AS {}").format(sql.Identifier(alias))


def _bigint_col_expr(colset: set[str], candidates: list[str], alias: str) -> sql.Composed:
    """Start/End 用，只取開頭連續數字，避免 123.0 顯示/轉型問題。"""
    for c in candidates:
        if c in colset:
            return sql.SQL(
                "CAST(NULLIF(substring({}::text from '^[0-9]+'), '') AS BIGINT) AS {}"
            ).format(
                sql.Identifier(c),
                sql.Identifier(alias),
            )
    return sql.SQL("NULL::bigint AS {}").format(sql.Identifier(alias))


def _numeric_col_expr(colset: set[str], candidates: list[str], alias: str) -> sql.Composed:
    """AF 用。若來源是 '-' 或非數字，轉成 NULL，避免 numeric cast 失敗。"""
    for c in candidates:
        if c in colset:
            return sql.SQL(
                "CASE "
                "WHEN NULLIF({}::text, '') IS NULL THEN NULL::numeric "
                "WHEN {}::text ~ '^-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?$' THEN {}::numeric "
                "ELSE NULL::numeric END AS {}"
            ).format(
                sql.Identifier(c),
                sql.Identifier(c),
                sql.Identifier(c),
                sql.Identifier(alias),
            )
    return sql.SQL("NULL::numeric AS {}").format(sql.Identifier(alias))


def _time_col_expr(
    colset: set[str],
    candidates: list[str],
    alias: str,
    default_text: str | None = None,
) -> sql.Composed:
    """
    時間欄位統一回傳成 text。
    不強制 cast timestamptz，避免來源欄位是文字或格式不一致時爆掉。
    """
    for c in candidates:
        if c in colset:
            return sql.SQL("{}::text AS {}").format(
                sql.Identifier(c),
                sql.Identifier(alias),
            )

    if default_text is not None:
        return sql.SQL("{}::text AS {}").format(
            sql.Literal(default_text),
            sql.Identifier(alias),
        )

    return sql.SQL("NULL::text AS {}").format(sql.Identifier(alias))


def _build_original_select(cur) -> sql.Composed:
    """
    public.blacklist_ori 投影成前端固定欄位。
    新版原始黑名單中的 gene_symbol 會被回傳為 Gene 與 Gene.refGene。
    原始黑名單三個時間欄位固定為 2025-05-06 00:00:00。
    """
    cols = _get_columns(cur, "public", "blacklist_ori")

    gene_candidates = [
        "Gene.refGene",
        "Gene_refGene",
        "Gene.refGeneWithVer",
        "Gene_refGeneWithVer",
        "gene_symbol",
    ]

    parts = [
        sql.SQL("'original_blacklist'::text AS source_type"),
        sql.SQL("2::int AS source_priority"),

        _text_col_expr(cols, gene_candidates, "Gene"),
        _text_col_expr(cols, ["Chr"], "Chr"),
        _bigint_col_expr(cols, ["Start"], "Start"),
        _bigint_col_expr(cols, ["End"], "End"),
        _text_col_expr(cols, ["Ref"], "Ref"),
        _text_col_expr(cols, ["Alt"], "Alt"),

        _text_col_expr(
            cols,
            ["Func.refGeneWithVer", "Func_refGeneWithVer", "Func.refGene"],
            "Func.refGeneWithVer",
        ),
        _text_col_expr(cols, gene_candidates, "Gene.refGene"),
        _text_col_expr(
            cols,
            [
                "ExonicFunc.refGeneWithVer",
                "ExonicFunc_refGeneWithVer",
                "ExonicFunc.refGene",
            ],
            "ExonicFunc.refGeneWithVer",
        ),
        _text_col_expr(
            cols,
            [
                "AAChange.refGeneWithVer",
                "AAChange_refGeneWithVer",
                "AAChange.refGene",
            ],
            "AAChange.refGeneWithVer",
        ),
        _numeric_col_expr(cols, ["AF"], "AF"),

        sql.SQL("'2025-05-06 00:00:00'::text AS created_at_db"),
        sql.SQL("'2025-05-06 00:00:00'::text AS src_created_at"),
        sql.SQL("'2025-05-06 00:00:00'::text AS src_updated_at"),
    ]

    return sql.SQL("SELECT {} FROM public.blacklist_ori").format(
        sql.SQL(", ").join(parts)
    )


def _build_user_added_select(cur, schema: str) -> sql.Composed | None:
    """
    user_xxx.clinvar_blacklist 投影成前端固定欄位。
    使用者新增黑名單 source_priority = 1，所以若五鍵和原始黑名單重複，
    使用者新增資料會優先顯示。
    """
    if not _table_exists(cur, schema, "clinvar_blacklist"):
        return None

    cols = _get_columns(cur, schema, "clinvar_blacklist")

    gene_candidates = [
        "Gene.refGene",
        "Gene_refGene",
        "Gene.refGeneWithVer",
        "Gene_refGeneWithVer",
        "gene_symbol",
    ]

    parts = [
        sql.SQL("'user_added'::text AS source_type"),
        sql.SQL("1::int AS source_priority"),

        _text_col_expr(cols, gene_candidates, "Gene"),
        _text_col_expr(cols, ["Chr"], "Chr"),
        _bigint_col_expr(cols, ["Start"], "Start"),
        _bigint_col_expr(cols, ["End"], "End"),
        _text_col_expr(cols, ["Ref"], "Ref"),
        _text_col_expr(cols, ["Alt"], "Alt"),

        _text_col_expr(
            cols,
            ["Func.refGeneWithVer", "Func_refGeneWithVer", "Func.refGene"],
            "Func.refGeneWithVer",
        ),
        _text_col_expr(cols, gene_candidates, "Gene.refGene"),
        _text_col_expr(
            cols,
            [
                "ExonicFunc.refGeneWithVer",
                "ExonicFunc_refGeneWithVer",
                "ExonicFunc.refGene",
            ],
            "ExonicFunc.refGeneWithVer",
        ),
        _text_col_expr(
            cols,
            [
                "AAChange.refGeneWithVer",
                "AAChange_refGeneWithVer",
                "AAChange.refGene",
            ],
            "AAChange.refGeneWithVer",
        ),
        _numeric_col_expr(cols, ["AF"], "AF"),

        _time_col_expr(
            cols,
            ["created_at_db", "created_at", "updated_at_db", "updated_at"],
            "created_at_db",
        ),
        _time_col_expr(
            cols,
            ["src_created_at", "created_at_db", "created_at", "updated_at_db", "updated_at"],
            "src_created_at",
        ),
        _time_col_expr(
            cols,
            ["src_updated_at", "src_created_at", "updated_at_db", "updated_at", "created_at_db", "created_at"],
            "src_updated_at",
        ),
    ]

    return sql.SQL("SELECT {} FROM {}.{}").format(
        sql.SQL(", ").join(parts),
        sql.Identifier(schema),
        sql.Identifier("clinvar_blacklist"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def blacklist_api(request):
    """
    POST /blacklist_main

    Body:
      {
        "user_id": 5,
        "page": 1,
        "pageSize": 25,
        "sortBy": "Chr",
        "sortDir": "asc",
        "q": "TP53"
      }

    功能：
      第一個黑名單主表顯示：
        public.blacklist_ori + user_xxx.clinvar_blacklist

      若五鍵 Chr/Start/End/Ref/Alt 重複：
        優先顯示 user_xxx.clinvar_blacklist。
    """
    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    user_id = body.get("user_id")
    try:
        user_id = int(user_id) if user_id not in (None, "", 0, "0") else None
    except Exception:
        user_id = None

    try:
        page = max(1, int(body.get("page", 1)))
    except Exception:
        page = 1

    try:
        page_size = max(1, min(int(body.get("pageSize", 25)), 200))
    except Exception:
        page_size = 25

    offset = (page - 1) * page_size

    sort_by_req = str(body.get("sortBy", "Chr")).strip()
    sort_dir_req = str(body.get("sortDir", "asc")).strip()
    sort_by, sort_dir = _safe_sort(sort_by_req, sort_dir_req)

    q = str(body.get("q", "")).strip()
    q = unquote(q) if q else ""

    try:
        with PgConn(autocommit=True) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if not _table_exists(cur, "public", "blacklist_ori"):
                    return JsonResponse(
                        {
                            "rows": [],
                            "total": 0,
                            "columns": DISPLAY_COLUMNS + ["source_type"],
                        },
                        json_dumps_params={"ensure_ascii": False},
                    )

                selects: list[sql.Composed] = []

                if user_id:
                    user_select = _build_user_added_select(cur, _schema_for_user(user_id))
                    if user_select is not None:
                        selects.append(user_select)

                selects.append(_build_original_select(cur))

                union_sql = sql.SQL(" UNION ALL ").join(selects)

                where_sql = sql.SQL("")
                params: list[str] = []
                if q:
                    like_parts = [
                        sql.SQL("{}::text ILIKE %s").format(sql.Identifier(c))
                        for c in SEARCH_COLUMNS
                    ]
                    where_sql = sql.SQL("WHERE ") + sql.SQL(" OR ").join(like_parts)
                    params.extend([f"%{q}%"] * len(SEARCH_COLUMNS))

                base_cte = sql.SQL(
                    """
                    WITH all_blacklist AS (
                        {}
                    ),
                    ranked AS (
                        SELECT *,
                               ROW_NUMBER() OVER (
                                   PARTITION BY "Chr", "Start", "End", "Ref", "Alt"
                                   ORDER BY source_priority ASC
                               ) AS rn
                        FROM all_blacklist
                        WHERE "Chr" IS NOT NULL
                          AND "Start" IS NOT NULL
                          AND "End" IS NOT NULL
                          AND "Ref" IS NOT NULL
                          AND "Alt" IS NOT NULL
                    ),
                    final_blacklist AS (
                        SELECT *
                        FROM ranked
                        WHERE rn = 1
                    )
                    """
                ).format(union_sql)

                count_sql = sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" SELECT COUNT(*) AS cnt FROM final_blacklist "),
                        where_sql,
                    ]
                )

                select_cols = [sql.Identifier(c) for c in DISPLAY_COLUMNS]

                data_sql = sql.Composed(
                    [
                        base_cte,
                        sql.SQL(" SELECT "),
                        sql.SQL(", ").join(select_cols),
                        sql.SQL(", source_type FROM final_blacklist "),
                        where_sql,
                        sql.SQL(" ORDER BY "),
                        sql.Identifier(sort_by),
                        sql.SQL(f" {sort_dir.upper()} NULLS LAST "),
                        sql.SQL(" LIMIT %s OFFSET %s"),
                    ]
                )

                cur.execute(count_sql, params)
                total = int(cur.fetchone()["cnt"])

                cur.execute(data_sql, params + [page_size, offset])
                rows = [dict(r) for r in cur.fetchall()]

        for r in rows:
            r["id"] = "|".join(
                str(r.get(k, ""))
                for k in ["Chr", "Start", "End", "Ref", "Alt"]
            )

        return JsonResponse(
            {
                "rows": rows,
                "total": total,
                "columns": DISPLAY_COLUMNS + ["source_type"],
            },
            json_dumps_params={"ensure_ascii": False},
        )

    except Exception as e:
        return JsonResponse(
            {"error": f"{type(e).__name__}: {str(e)}"},
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )
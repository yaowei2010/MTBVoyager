import io
import zipfile
from typing import Iterable, Optional, List

import pandas as pd
import psycopg2
from psycopg2 import pool, sql
from contextlib import contextmanager
# ===== 你原本就有的：DB_CONFIG、POOL、pooled_conn() =====
# ...（略）...
DB_CONFIG = dict(
    dbname="somatic",
    user="uuuwei0504",
    password="REDACTED_SET_VIA_ENV",
    host="172.17.0.1",
    port="5432",
)

# ── 建立連線池 (1~6 條連線) ──────────────────
POOL = pool.SimpleConnectionPool(minconn=1, maxconn=6, **DB_CONFIG)

@contextmanager
def pooled_conn():
    """自訂 context manager，用完自動歸還連線。"""
    conn = POOL.getconn()
    try:
        yield conn
    finally:
        POOL.putconn(conn)
# ========== 小工具：確認表是否存在 ==========
def table_exists(table_name: str) -> bool:
    q = """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
          AND table_name = %s
        LIMIT 1
    """
    with pooled_conn() as conn, conn.cursor() as cur:
        cur.execute(q, (table_name,))
        return cur.fetchone() is not None

# ========== 小工具：分批讀取 ==========
def read_table_in_chunks(conn, table_name: str, chunksize: int = 100_000) -> Iterable[pd.DataFrame]:
    """
    使用 pandas.read_sql_query + chunksize 分批讀整張表，依序 yield DataFrame。
    """
    query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name))
    # 用 pandas 的 chunksize 分批
    for chunk in pd.read_sql_query(query.as_string(conn), conn, chunksize=chunksize):
        # 補上來源表名（方便後續合併追蹤）
        chunk["source_table"] = table_name
        yield chunk

# ========== 1) 讀單一 job 的 vep_annovar_merge_<jobID> ==========
def fetch_merge_by_job(job_id: str, chunksize: int = 100_000) -> pd.DataFrame:
    """
    將 vep_annovar_merge_<jobID> 整張表讀出來。
    """
    table_name = f"vep_annovar_merge_{job_id}"
    if not table_exists(table_name):
        return pd.DataFrame()

    frames = []
    with pooled_conn() as conn:
        for chunk in read_table_in_chunks(conn, table_name, chunksize=chunksize):
            frames.append(chunk)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# ========== 2) 讀所有 vep_annovar_merge_% 並合併 ==========
def fetch_all_merges(target_tables: Optional[List[str]] = None, chunksize: int = 100_000) -> pd.DataFrame:
    """
    將所有（或指定子集合） vep_annovar_merge_% 表完整讀出並合併。
    - target_tables=None 時，會自動呼叫 get_all_target_tables()
    """
    tables = target_tables or get_all_target_tables()
    frames = []
    with pooled_conn() as conn:
        for tbl in tables:
            # 保險檢查
            if not table_exists(tbl):
                continue
            for chunk in read_table_in_chunks(conn, tbl, chunksize=chunksize):
                frames.append(chunk)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

# ========== 3) 匯出：單表/多表 → CSV 或 ZIP ==========
def to_single_csv_bytes(df: pd.DataFrame) -> bytes:
    """
    將 DataFrame 轉為 UTF-8 CSV 的 bytes（可直接回傳 Django HttpResponse）。
    """
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def to_zip_bytes_from_tables(tables: List[str], chunksize: int = 200_000) -> bytes:
    """
    將多個 vep_annovar_merge_* 表逐張輸出成 CSV，打包成 ZIP（bytes）。
    適合非常大時：逐張表邊讀邊寫，不需把所有表合併進一個大 DF。
    """
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        with pooled_conn() as conn:
            for tbl in tables:
                if not table_exists(tbl):
                    # 空檔作為佔位，也可選擇略過
                    zf.writestr(f"{tbl}.csv", "")
                    continue
                # 每張表分批讀，直接寫入 ZIP 內的 CSV
                csv_buf = io.StringIO()
                first = True
                for chunk in read_table_in_chunks(conn, tbl, chunksize=chunksize):
                    if first:
                        chunk.to_csv(csv_buf, index=False)
                        first = False
                    else:
                        # 後續塊只寫資料行
                        chunk.to_csv(csv_buf, index=False, header=False)
                zf.writestr(f"{tbl}.csv", csv_buf.getvalue())
    mem.seek(0)
    return mem.getvalue()
def list_all_tables() -> list[str]:
    q = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
    """
    with pooled_conn() as conn, conn.cursor() as cur:
        cur.execute(q)
        return [r[0] for r in cur.fetchall()]
def get_all_target_tables() -> list[str]:
    """
    從 DB 直接撈出所有 vep_annovar_merge_% 的表
    """
    q = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
          AND table_name LIKE 'vep_annovar_merge_%'
        ORDER BY table_name
    """
    with pooled_conn() as conn, conn.cursor() as cur:
        cur.execute(q)
        return [r[0] for r in cur.fetchall()]

if __name__ == "__main__":
    print(list_all_tables()) 
    # 1) 單一 job
    # df_one = fetch_merge_by_job("rNuMzfSCBJ", chunksize=200_000)
    # df_one.to_csv('/miRTI/hw1/VUS/a.csv')
    # print("單一表 rows:", len(df_one), "cols:", len(df_one.columns))

    # # 2) 全部合併（可能很大）
    # all_df = fetch_all_merges(chunksize=200_000)
    # print("全部合併 rows:", len(all_df))

    # 3) 直接打包 ZIP（每張表各一個 CSV）
    tables = get_all_target_tables()
    zip_bytes = to_zip_bytes_from_tables(tables)
    with open("vep_annovar_merges.zip", "wb") as f:
        f.write(zip_bytes)

    # POOL.closeall()

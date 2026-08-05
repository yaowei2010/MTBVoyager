"""
高速查詢 VEP + ANNOVAR Merge
---------------------------
‧ Gene 只要「包含」就符合 (LIKE %gene%)
‧ 若輸入 gene.p.Variant → 精準比對 gene + variant
‧ 在 SQL 端先過濾，再回傳 * 以保留所有欄位
‧ 使用 dbpool.py 的 psycopg2 ThreadedConnectionPool + 向量化 HGVSp 轉換
"""

import re
from typing import List, Optional
from urllib.parse import unquote

import pandas as pd
from psycopg2 import sql

from ..postgressql_setting.dbpool import PgConn


# ── 胺基酸三碼 → 單碼 ──────────────────────
AA_DICT = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*", "Stop": "*", "*": "*"
}


def aa3_to_1(aa: str) -> str:
    if aa is None:
        return ""
    return AA_DICT.get(str(aa).capitalize(), str(aa))


def normalize_hgvsp_input(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None

    s = str(s).strip()
    if not s or s in {"-", "NA", "N/A", "None", "nan"}:
        return None

    s = unquote(s)
    s = re.split(r"[,;]\s*", s, maxsplit=1)[0].strip()
    return s


def extract_hgvsp_tail(s: Optional[str]) -> Optional[str]:
    s = normalize_hgvsp_input(s)
    if not s:
        return None

    if ":p." in s:
        tail = s.split(":p.", 1)[1]
    elif s.startswith("p."):
        tail = s[2:]
    else:
        m = re.search(r"p\.(.+)$", s)
        tail = m.group(1) if m else s

    return tail.strip()


def hgvsp_get_protein_id(s: Optional[str]) -> Optional[str]:
    s = normalize_hgvsp_input(s)
    if not s:
        return None

    if ":p." in s:
        pid = s.split(":p.", 1)[0].strip()
        return pid if pid else None

    m = re.search(r"\b((?:NP|XP|YP)_[0-9]+(?:\.[0-9]+)?|ENSP[0-9]+(?:\.[0-9]+)?)\b", s)
    return m.group(1) if m else None


def convert_aa_seq_3_to_1(seq: str) -> str:
    if not seq:
        return ""

    tokens = re.findall(r"[A-Z][a-z]{2}|Ter|Stop|\*", seq)
    if not tokens:
        return seq
    return "".join(aa3_to_1(x) for x in tokens)


def hgvsp_to_short(s: Optional[str]) -> Optional[str]:
    tail = extract_hgvsp_tail(s)
    if not tail:
        return None

    # 1) substitution / stop / synonymous
    m = re.match(r"^([A-Za-z]{3})(\d+)([A-Za-z]{3}|Ter|Stop|\*|=)$", tail)
    if m:
        ref3, pos, alt3 = m.groups()
        ref1 = aa3_to_1(ref3)

        if alt3 == "=":
            return f"{ref1}{pos}{ref1}"

        if alt3 in {"Ter", "Stop", "*"}:
            return f"{ref1}{pos}*"

        alt1 = aa3_to_1(alt3)
        return f"{ref1}{pos}{alt1}"

    # 2) frameshift: Lys382AsnfsTer40 -> K382Nfs*40
    m = re.match(r"^([A-Za-z]{3})(\d+)([A-Za-z]{3})fs(?:Ter|Stop|\*)(\d+)$", tail)
    if m:
        ref3, pos, alt3, stop_num = m.groups()
        return f"{aa3_to_1(ref3)}{pos}{aa3_to_1(alt3)}fs*{stop_num}"

    # 3) frameshift: Lys382fs -> K382fs
    m = re.match(r"^([A-Za-z]{3})(\d+)fs$", tail, flags=re.IGNORECASE)
    if m:
        ref3, pos = m.groups()
        return f"{aa3_to_1(ref3)}{pos}fs"

    # 4) 單點 del / ins / dup
    m = re.match(r"^([A-Za-z]{3})(\d+)(del|ins|dup)$", tail, flags=re.IGNORECASE)
    if m:
        ref3, pos, op = m.groups()
        return f"{aa3_to_1(ref3)}{pos}{op.lower()}"

    # 5) 單點 delins
    m = re.match(r"^([A-Za-z]{3})(\d+)delins([A-Za-z\*]+)$", tail, flags=re.IGNORECASE)
    if m:
        ref3, pos, ins_seq = m.groups()
        return f"{aa3_to_1(ref3)}{pos}delins{convert_aa_seq_3_to_1(ins_seq)}"

    # 6) 區間 del / ins / dup
    m = re.match(
        r"^([A-Za-z]{3})(\d+)_([A-Za-z]{3})(\d+)(del|ins|dup)$",
        tail,
        flags=re.IGNORECASE
    )
    if m:
        aa1, pos1, aa2, pos2, op = m.groups()
        return f"{aa3_to_1(aa1)}{pos1}_{aa3_to_1(aa2)}{pos2}{op.lower()}"

    # 7) 區間 delins / ins + inserted aa
    m = re.match(
        r"^([A-Za-z]{3})(\d+)_([A-Za-z]{3})(\d+)(delins|ins)([A-Za-z\*]+)$",
        tail,
        flags=re.IGNORECASE
    )
    if m:
        aa1, pos1, aa2, pos2, op, ins_seq = m.groups()
        ins_short = convert_aa_seq_3_to_1(ins_seq)
        return f"{aa3_to_1(aa1)}{pos1}_{aa3_to_1(aa2)}{pos2}{op.lower()}{ins_short}"

    return tail


def hgvsp_to_standard(s: Optional[str]) -> Optional[str]:
    s = normalize_hgvsp_input(s)
    if not s:
        return None

    protein_id = hgvsp_get_protein_id(s)
    short_change = hgvsp_to_short(s)

    if not short_change:
        return None

    if protein_id:
        return f"{protein_id}:p.{short_change}"

    return f"p.{short_change}"


def parse_user_query(user_input: str):
    """
    支援：
    TP53
    TP53.p.R175H
    TP53:p.R175H
    TP53 p.R175H
    TP53.p.K382Nfs*40
    EGFR.p.E746_A750del
    """
    s = str(user_input or "").strip()
    m = re.match(r"^([A-Za-z0-9_-]+)\s*(?:[.:]|\s)\s*p\.\s*(.+)$", s, re.I)
    if not m:
        return None, None

    gene = m.group(1).upper()
    variant = m.group(2).replace(" ", "")
    return gene, variant


# ── 公用函式 ────────────────────────────────
def get_all_target_tables(schema_name: str) -> list[str]:
    """
    回傳該 schema 下所有 vep_annovar_merge_% 表名（不含 schema 前綴）。
    """
    sql_q = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type   = 'BASE TABLE'
          AND table_name LIKE %s;
    """
    with PgConn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_q, (schema_name, "vep_annovar_merge_%"))
            rows = cur.fetchall()
    return [r[0] for r in rows]


def convert_hgvsp_series(col: pd.Series) -> pd.Series:
    return col.map(hgvsp_to_short)


def convert_hgvsp_standard_series(col: pd.Series) -> pd.Series:
    return col.map(hgvsp_to_standard)


# ── 主要查詢 ────────────────────────────────
def search_inhouse(user_input: str, schema_name: str) -> pd.DataFrame:
    """
    只在指定 schema 中查詢。
    1) 若輸入 'GENE.p.Variant' → 精確比對 gene + variant
    2) 否則僅模糊比對 gene (LIKE %gene%)
    """
    exact_gene, exact_var = parse_user_query(user_input.strip())

    if exact_gene and exact_var:
        is_variant = True
        gene_like = f"%{exact_gene}%"
        fuzzy_gene = exact_gene
    else:
        fuzzy_gene = user_input.strip().upper()
        is_variant = False
        gene_like = f"%{fuzzy_gene}%"

    frames = []
    tables = get_all_target_tables(schema_name)

    for tbl in tables:
        with PgConn() as conn:
            sql_q = sql.SQL("""
                SELECT *, %s AS source_table
                FROM {}.{}
                WHERE upper("Gene.refGene") LIKE %s
            """).format(sql.Identifier(schema_name), sql.Identifier(tbl))

            df = pd.read_sql_query(
                sql_q.as_string(conn),
                conn,
                params=(tbl, gene_like),
            )

        if df.empty:
            continue

        if "HGVSp" in df.columns:
            df["Protein_Change"] = convert_hgvsp_series(df["HGVSp"].astype(str))
            df["standard_HGVSp"] = convert_hgvsp_standard_series(df["HGVSp"].astype(str))
        else:
            df["Protein_Change"] = pd.NA
            df["standard_HGVSp"] = pd.NA

        if is_variant:
            df = df.loc[
                (df["Gene.refGene"].astype(str).str.upper() == exact_gene) &
                (df["Protein_Change"].astype(str).str.upper() == exact_var.upper())
            ]
        else:
            df = df.loc[df["Gene.refGene"].astype(str).str.upper() == fuzzy_gene]

        if not df.empty:
            frames.append(df)

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def get_full_records(schema_name: str, tables: List[str], gene: str, variant_short: str) -> pd.DataFrame:
    """在指定 schema 的 tables 內撈出 gene+variant 的所有欄位記錄。"""
    all_frames = []

    for tbl in tables:
        with PgConn() as conn:
            sql_q = sql.SQL("""
                SELECT *, %s AS source_table
                FROM {}.{}
                WHERE upper("Gene.refGene") LIKE %s
            """).format(sql.Identifier(schema_name), sql.Identifier(tbl))

            df = pd.read_sql_query(
                sql_q.as_string(conn),
                conn,
                params=(tbl, f"%{gene.upper()}%"),
            )

        if df.empty:
            continue

        if "HGVSp" in df.columns:
            df["Protein_Change"] = convert_hgvsp_series(df["HGVSp"].astype(str))
            df["standard_HGVSp"] = convert_hgvsp_standard_series(df["HGVSp"].astype(str))
        else:
            df["Protein_Change"] = pd.NA
            df["standard_HGVSp"] = pd.NA

        df = df.loc[
            (df["Gene.refGene"].astype(str).str.upper() == gene.upper()) &
            (df["Protein_Change"].astype(str).str.upper() == variant_short.upper())
        ]

        if not df.empty:
            all_frames.append(df)

    return pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()


# ── 主程式 ────────────────────────────────
if __name__ == "__main__":
    schema = input("📌 請輸入 schema（例如 user_5）：\n> ").strip()
    q = input("🔍 請輸入查詢（例如 TP53 或 KRAS.p.A146T）：\n> ").strip()

    result_df = search_inhouse(q, schema_name=schema)

    if not result_df.empty:
        gene = result_df.iloc[0]["Gene.refGene"]
        variant_short = result_df.iloc[0]["Protein_Change"]
        tables = result_df["source_table"].unique().tolist()

        full_df = get_full_records(schema, tables, gene, variant_short)
        if not full_df.empty:
            pd.set_option("display.max_columns", None)
            print("\n🟢 完整結果：")
            print(full_df)
        else:
            print("❌ 沒找到任何完整資料")
    else:
        print("❌ 沒有符合條件的資料")
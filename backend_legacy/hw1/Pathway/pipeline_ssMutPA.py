import os
import sys
import re
import math
import subprocess
import pandas as pd
import numpy as np
from psycopg2 import sql

from ..postgressql_setting.dbpool import PgConn

# ========== 路徑設定 ==========
R_SCRIPT_DIR = "/miRTI/hw1/Pathway/R"
RUN_SSMUTPA_R = os.path.join(R_SCRIPT_DIR, "run_ssMutPA.R")
RUN_FASTSEA_R = os.path.join(R_SCRIPT_DIR, "run_FastSEAscore_pvql.R")

# ========== DB helper ==========
def _table_exists(conn, schema: str, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname = %s
              AND c.relname = %s
            LIMIT 1;
            """,
            (schema, table),
        )
        return cur.fetchone() is not None


def _fetch_patient_variants(patient_id: str, *, schema: str) -> pd.DataFrame:
    candidates = [
        f"vep_annovar_merge_{patient_id}",
        f"somatic_result_{patient_id}",
    ]

    with PgConn() as conn:
        chosen = None
        for t in candidates:
            if _table_exists(conn, schema, t):
                chosen = t
                break

        if not chosen:
            raise RuntimeError(
                f"在 schema '{schema}' 中找不到病人資料表，嘗試過：{', '.join(candidates)}"
            )

        query = sql.SQL("SELECT * FROM {}.{}").format(
            sql.Identifier(schema),
            sql.Identifier(chosen),
        )
        df = pd.read_sql_query(query.as_string(conn), conn)
        return df


# ========== CSV helper ==========
def _read_population_csv(pop_csv_path: str) -> pd.DataFrame:
    """
    讀取 df_population.csv
    - 自動推斷分隔符（csv/tsv 都可）
    - 對常見的空值做處理
    """
    if not os.path.isfile(pop_csv_path):
        raise FileNotFoundError(pop_csv_path)

    df = pd.read_csv(pop_csv_path, sep=None, engine="python")
    df = df.replace(
        {"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "none": pd.NA, "None": pd.NA}
    )
    return df


def _load_variants_source(
    patient_id: str,
    *,
    schema: str,
    source: str = "db",
    pop_csv_path: str | None = None,
) -> pd.DataFrame:
    """
    統一入口：從 db 或 csv 載入 variants table
    source:
      - "db": 走原本資料庫流程
      - "csv": 讀 pop_csv_path
    """
    source = (source or "").lower().strip()
    if source == "db":
        return _fetch_patient_variants(patient_id, schema=schema)

    if source == "csv":
        if not pop_csv_path:
            raise RuntimeError("source='csv' 時必須提供 pop_csv_path")
        return _read_population_csv(pop_csv_path)

    raise ValueError(f"未知的 source: {source}（可用：'db'/'csv'）")


# ========== functional filter (nonsilent) ==========
def _filter_nonsilent(df: pd.DataFrame) -> pd.DataFrame:
    """
    盡量自動從常見欄位判斷 nonsilent：
    - ANNOVAR: ExonicFunc.refGene（你目前只用這個）
    """
    annovar_col = next((c for c in ["ExonicFunc.refGene"] if c in df.columns), None)
    if annovar_col:
        ef = df[annovar_col].astype(str).str.strip().str.lower()
        mask = (~ef.isin({"synonymous snv", "synonymous", ".", "unknown", "nan", "none", ""})) & ef.notna()
        return df[mask].copy()

    raise RuntimeError(
        "找不到用來判斷 nonsilent 的欄位。"
        "請確認 df 是否包含 MAF 的 Variant_Classification 或 ANNOVAR 的 ExonicFunc.refGene。"
    )


# ========== GenePy burden helpers ==========
def _pick_first_existing_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((c for c in candidates if c in df.columns), None)


# ---------------------------
# ClinVar → Di  (CADD DISABLED)
# ---------------------------
def _clinvar_to_Di(x, *, default_for_unknown: float = 0.0) -> float:
    """
    ClinVar clinical significance → Di (CADD disabled)

    Mapping:
      Pathogenic = 1.0
      Likely pathogenic = 0.9
      Likely benign = 0.1
      Benign = 0.0
      VUS/uncertain/conflicting/unknown/missing = default_for_unknown
    """
    s = None
    if x is not None and not (isinstance(x, float) and math.isnan(x)):
        s = str(x).strip().lower()
        # normalize: Likely_benign -> likely benign
        s = s.replace("_", " ")
        s = re.sub(r"\s+", " ", s)

    if not s or s in {"nan", "none", "."}:
        return default_for_unknown

    # split multi-labels like "pathogenic/likely pathogenic"
    tokens = [t.strip() for t in re.split(r"[;|,/]+", s) if t.strip()]

    def has(substr: str) -> bool:
        return any(substr in t for t in tokens)

    # if contradictory labels appear together, treat as conflicting
    if has("pathogenic") and has("benign"):
        return default_for_unknown

    # order matters: likely pathogenic should override pathogenic if both exist
    if has("likely pathogenic"):
        return 0.9
    if has("pathogenic"):
        return 1.0
    if has("likely benign"):
        return 0.1
    if has("benign"):
        return 0.0

    # VUS / uncertain / conflicting / others
    return default_for_unknown


def _parse_af(v) -> float | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip()
    if s == "" or s.lower() in {"nan", "none", "."}:
        return None

    # could be "0.001,0.0008"
    parts = re.split(r"[;,|]", s)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        try:
            x = float(p)
            if 0.0 <= x <= 1.0:
                return x
        except Exception:
            pass
    return None


def _infer_zygosity(gt) -> str:
    """
    Return: 'HET' / 'HOM' / 'UNK'
    Supports: 0/1, 1/1, 0|1, 1|0, het, hom, HOMVAR...
    """
    if gt is None or (isinstance(gt, float) and np.isnan(gt)):
        return "UNK"
    s = str(gt).strip().lower()
    if s in {"", ".", "nan", "none"}:
        return "UNK"
    if re.search(r"(0[\/|]1|1[\/|]0)", s) or "het" in s:
        return "HET"
    if re.search(r"(1[\/|]1)", s) or "hom" in s:
        return "HOM"
    return "UNK"


def _f1f2_from_af_zygosity(af: float, zyg: str) -> float:
    af = min(max(af, 1e-12), 1 - 1e-12)
    if zyg == "HOM":
        return af * af
    # treat HET/UNK as heterozygous: alt * ref
    return af * (1.0 - af)


def _parse_vaf(v) -> float | None:
    """
    Parse VAF:
      - accept 0~1
      - accept 0~100 (%) and convert to 0~1
      - accept strings like "0.23", "23%", "0.23,0.25"
    """
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    s = str(v).strip()
    if s == "" or s.lower() in {"nan", "none", "."}:
        return None

    # could be "0.12,0.15" or "23%"
    parts = re.split(r"[;,|]", s)
    for p in parts:
        p = p.strip().replace("%", "")
        if not p:
            continue
        try:
            x = float(p)
            if x < 0:
                continue
            # if looks like percent (e.g. 23), convert
            if x > 1.0 and x <= 100.0:
                x = x / 100.0
            if 0.0 <= x <= 1.0:
                return x
        except Exception:
            pass
    return None


def _compute_genepy_gene_burden(df_ns: pd.DataFrame) -> pd.DataFrame:
    """
    NEW scoring (your formula):

      Wi = VAF_i * (-log10(f_i))
      Score_gene = sum_i Di * Wi
      S_gene = Score_gene / k

    Output (keep compatibility with R):
      gene, Sgh, Sgh_raw, k
        - Sgh_raw = Score_gene
        - Sgh     = S_gene (mean per-variant score)
    """
    gene_col = "Gene.refGene"
    # ClinVar significance (Di)
    clinvar_col = "CLNSIG"

    # population frequency f_i (gnomAD/ExAC/1KG...)
    f_col = "AF"



    # VAF
    vaf_col = "VAF"


    rows = []
    for _, r in df_ns.iterrows():
        gene = str(r.get(gene_col, "")).strip().upper()
        if not gene or gene.lower() in {"nan", "none"}:
            continue

        f = _parse_af(r.get(f_col))
        if f is None:
            continue

        vaf = _parse_vaf(r.get(vaf_col))
        if vaf is None:
            continue

        Di = _clinvar_to_Di(r.get(clinvar_col) if clinvar_col else None, default_for_unknown=0.0)

        # Wi = VAF * (-log10(f))
        Wi = vaf * (-math.log10(max(f, 1e-300)))

        # per-variant contribution: Di * Wi
        contrib = Di * Wi
        rows.append((gene, contrib))

    if not rows:
        return pd.DataFrame(columns=["gene", "Sgh", "Sgh_raw", "k"])

    tmp = pd.DataFrame(rows, columns=["gene", "contrib"])
    agg = tmp.groupby("gene", as_index=False).agg(
        Sgh_raw=("contrib", "sum"),
        k=("contrib", "size"),
    )
    agg["Sgh"] = agg["Sgh_raw"] / agg["k"]
    agg = agg.sort_values("Sgh_raw", ascending=False).reset_index(drop=True)

    return agg[["gene", "Sgh", "Sgh_raw", "k"]]

def _write_gene_burden_csv(burden_df: pd.DataFrame, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "gene_burden.csv")
    burden_df.to_csv(out_path, index=False)
    return out_path


def _write_df_csv(df: pd.DataFrame, output_dir: str, filename: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    return out_path


# ========== seed genes + gene burden ==========
def _make_seed_genes_and_burden(df: pd.DataFrame, output_dir: str) -> tuple[str, str]:
    df_ns = _filter_nonsilent(df)
    _write_df_csv(df_ns, output_dir, "df_nonsilent.csv")

    # seed genes
    candidate_cols = [
        "Gene.refGene",
    ]
    gene_col = next((c for c in candidate_cols if c in df_ns.columns), None)
    if not gene_col:
        raise RuntimeError(f"找不到基因欄位（候選：{', '.join(candidate_cols)}）")

    genes = (
        df_ns[gene_col]
        .astype(str)
        .str.strip()
        .str.upper()
        .replace({"": pd.NA, "nan": pd.NA, "none": pd.NA})
        .dropna()
        .unique()
        .tolist()
    )
    if not genes:
        raise RuntimeError("此病人沒有 nonsilent mutation 的基因，無法建立 seed_genes.csv")

    os.makedirs(output_dir, exist_ok=True)
    seed_file = os.path.join(output_dir, "seed_genes.csv")
    pd.DataFrame({"Gene": genes}).to_csv(seed_file, index=False)

    # gene burden
    burden_df = _compute_genepy_gene_burden(df_ns)
    burden_file = _write_gene_burden_csv(burden_df, output_dir)

    return seed_file, burden_file


# ========== Rscript ==========
def _run_rscript(r_script: str, args: list[str], *, log_path: str | None = None):
    cmd = ["mamba", "run", "-n", "arriba", "Rscript", "--vanilla", r_script] + args
    print("[CMD]", " ".join(cmd))

    ret = subprocess.run(cmd, capture_output=True, text=True)

    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("CMD:\n" + " ".join(cmd) + "\n\n")
            f.write("STDOUT:\n" + (ret.stdout or "") + "\n\n")
            f.write("STDERR:\n" + (ret.stderr or "") + "\n")

    if ret.returncode != 0:
        print("========== R STDOUT ==========")
        print(ret.stdout)
        print("========== R STDERR ==========")
        print(ret.stderr)
        raise RuntimeError(
            f"{os.path.basename(r_script)} failed (exit {ret.returncode}). "
            f"See log: {log_path or '(no log)'}"
        )


# ========== Pipeline ==========
def pipeline(
    patient_id: str,
    output_dir: str,
    gmt_rdata: str,
    *,
    min_g: int = 1,
    max_g: int = 500,
    nperm: int = 1000,
    schema: str = "public",
    source: str = "db",
    pop_csv_path: str | None = None,
    gamma: float = 0.0,
):
    if not os.path.isfile(RUN_SSMUTPA_R):
        raise FileNotFoundError(RUN_SSMUTPA_R)
    if not os.path.isfile(RUN_FASTSEA_R):
        raise FileNotFoundError(RUN_FASTSEA_R)
    if not os.path.isfile(gmt_rdata):
        raise FileNotFoundError(gmt_rdata)

    print(f"[INFO] Loading variants for {patient_id} (source={source}, schema={schema})")
    df = _load_variants_source(patient_id, schema=schema, source=source, pop_csv_path=pop_csv_path)

    print("[INFO] Generating seed_genes.csv + gene_burden.csv (ClinVar-only; CADD disabled)")
    seed_file, burden_file = _make_seed_genes_and_burden(df, output_dir)
    print(f"[INFO] seed_genes: {seed_file}")
    print(f"[INFO] gene_burden: {burden_file}")

    print(f"[INFO] Running ssMutPA / RWR with gene burden (gamma={gamma})")
    ssmutpa_log = os.path.join(output_dir, "run_ssMutPA.log")
    _run_rscript(RUN_SSMUTPA_R, [seed_file, output_dir, burden_file, str(gamma)], log_path=ssmutpa_log)

    mrwr_file = os.path.join(output_dir, "MRWR_result.csv")
    if not os.path.isfile(mrwr_file):
        raise FileNotFoundError(mrwr_file)

    print("[INFO] Running FastSEAscore")
    out_csv = os.path.join(output_dir, "PathES_results.csv")
    plot_pathway = "ACC/ACC-2016-TP53-RB-pathway"
    plot_prefix = os.path.join(output_dir, "perm_plot")
    _run_rscript(
        RUN_FASTSEA_R,
        [
            mrwr_file,
            gmt_rdata,
            out_csv,
            str(min_g),
            str(max_g),
            str(nperm),
            plot_pathway,
            plot_prefix,
        ],
    )

    if not os.path.isfile(out_csv):
        raise FileNotFoundError(out_csv)

    print("[INFO] Pipeline finished")
    return {"mrwr": mrwr_file, "pathes": out_csv, "seed": seed_file, "burden": burden_file}


# ========== CLI ==========
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python pipeline_ssMutPA.py "
            "<patient_id> <output_dir> <all_pathways_gmt.Rdata> "
            "[min_g=10] [max_g=500] [nperm=1000] "
            "[source=db|csv] [pop_csv_path=/path/to/df_population.csv] "
            "[gamma=0.0]"
        )
        sys.exit(1)

    patient_id = sys.argv[1]
    output_dir = sys.argv[2]
    gmt_rdata = sys.argv[3]
    min_g = int(sys.argv[4]) if len(sys.argv) >= 5 else 10
    max_g = int(sys.argv[5]) if len(sys.argv) >= 6 else 500
    nperm = int(sys.argv[6]) if len(sys.argv) >= 7 else 1000

    source = sys.argv[7] if len(sys.argv) >= 8 else "db"
    pop_csv_path = sys.argv[8] if len(sys.argv) >= 9 else None
    gamma = float(sys.argv[9]) if len(sys.argv) >= 10 else 0.0

    result = pipeline(
        patient_id,
        output_dir,
        gmt_rdata,
        min_g=min_g,
        max_g=max_g,
        nperm=nperm,
        source=source,
        pop_csv_path=pop_csv_path,
        gamma=gamma,
    )
    print(result)
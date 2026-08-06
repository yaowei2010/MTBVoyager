import os, json, traceback, pandas as pd
def read_table_csv(csv_path, top_n=100, normalize=None):
    """
    讀 CSV 成 (columns, rows, total_rows) 結構。
    normalize: 可傳入函式做欄位標準化 / 衍生欄位（例如加 rank）
    """
    if not os.path.exists(csv_path):
        return {"columns": [], "rows": [], "total_rows": 0, "path": csv_path, "exists": False}

    df = pd.read_csv(csv_path)
    if callable(normalize):
        df = normalize(df)

    total = int(len(df))
    if top_n is not None:
        df = df.head(int(top_n))

    return {
        "columns": df.columns.tolist(),
        "rows": df.to_dict(orient="records"),
        "total_rows": total,
        "path": csv_path,
        "exists": True,
    }

def normalize_mrwr(df: pd.DataFrame) -> pd.DataFrame:
    # 對齊欄名：NodeNames/Score -> gene/score，並加 rank
    cols = {c.lower(): c for c in df.columns}
    if "nodenames" in cols and "gene" not in df.columns:
        df = df.rename(columns={cols["nodenames"]: "gene"})
    if "score" not in df.columns:
        # 找第一個數值欄當 score
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if num_cols:
            df = df.rename(columns={num_cols[0]: "score"})
    # 排序（大到小）並加 rank
    if "score" in df.columns:
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
        df.insert(0, "rank", df.index + 1)
    return df

def normalize_pathes(df: pd.DataFrame) -> pd.DataFrame:
    # 確保欄位名稱 Pathway/ES/Overlap/Size 存在並排序
    rename_map = {c: c for c in df.columns}
    lower = {c.lower(): c for c in df.columns}
    if "pathway" not in df.columns and "pathway" in lower:
        rename_map[lower["pathway"]] = "Pathway"
    if "es" not in df.columns and "es" in lower:
        rename_map[lower["es"]] = "ES"
    if "overlap" not in df.columns and "overlap" in lower:
        rename_map[lower["overlap"]] = "Overlap"
    if "size" not in df.columns and "size" in lower:
        rename_map[lower["size"]] = "Size"
    df = df.rename(columns=rename_map)

    if "ES" in df.columns:
        df = df.sort_values("ES", ascending=False).reset_index(drop=True)
        df.insert(0, "rank", df.index + 1)
    return df
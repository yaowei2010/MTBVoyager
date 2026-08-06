# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# import os
# import sys
# import csv
# import pandas as pd

# FILE = "/miRTI/media/patient/tPCpbsamGz/NSR24066-3---22756831-49_ann.txt"
# TARGET_COL = "promoterAI_tss500"

# OUT_ALL = "promoterAI_tss500.all.txt"
# OUT_NONEMPTY = "promoterAI_tss500.nonempty.txt"
# OUT_WITH_KEY = "promoterAI_tss500.with_key.tsv"

# KEY_COLS = ["Chr", "Start", "End", "Ref", "Alt"]  # 若你的檔案欄位名不同可自行改

# def sniff_sep(path: str) -> str:
#     # 先讀一小段判斷分隔符（tab / comma）
#     with open(path, "r", encoding="utf-8", errors="replace") as f:
#         sample = f.read(8192)
#     try:
#         dialect = csv.Sniffer().sniff(sample, delimiters=["\t", ",", ";"])
#         return dialect.delimiter
#     except Exception:
#         # fallback：有 tab 就用 tab，否則用逗號
#         return "\t" if "\t" in sample else ","

# def main():
#     if not os.path.exists(FILE):
#         print(f"[ERROR] File not found: {FILE}")
#         sys.exit(1)

#     sep = sniff_sep(FILE)
#     print(f"[INFO] Detected delimiter: {repr(sep)}")

#     df = pd.read_csv(FILE, sep=sep, dtype=str, low_memory=False)
#     print(f"[INFO] rows={len(df)} cols={len(df.columns)}")

#     if TARGET_COL not in df.columns:
#         print(f"[ERROR] Column not found: {TARGET_COL}")
#         print("[INFO] Similar columns:")
#         for c in df.columns:
#             cl = str(c).lower()
#             if "promoter" in cl or "tss500" in cl:
#                 print("  ", c)
#         sys.exit(2)

#     s = df[TARGET_COL].fillna("").astype(str)

#     # 1) 全部輸出（含空/點）
#     pd.Series([TARGET_COL]).append(s, ignore_index=True).to_csv(
#         OUT_ALL, index=False, header=False
#     )
#     print(f"[OK] Wrote all values -> {OUT_ALL}")

#     # 2) 非空非 '.' 的值
#     nonempty = s[(s != "") & (s != ".")]
#     pd.Series([TARGET_COL]).append(nonempty, ignore_index=True).to_csv(
#         OUT_NONEMPTY, index=False, header=False
#     )
#     print(f"[OK] Wrote non-empty values -> {OUT_NONEMPTY}")

#     # 3) 統計
#     missing = ((s == "") | (s == ".")).sum()
#     print("\n[STATS]")
#     print("  total rows:", len(df))
#     print("  missing ('' or '.'):", int(missing))
#     print("  non-missing:", int(len(df) - missing))
#     print("  unique (non-missing):", int(nonempty.nunique()))

#     print("\n[TOP 20 non-missing]")
#     vc = nonempty.value_counts().head(20)
#     if len(vc) == 0:
#         print("  (none)")
#     else:
#         for val, cnt in vc.items():
#             print(f"  {val}\t{cnt}")

#     # 4) 連同 key 欄位一起輸出（如果 key 欄位存在）
#     have_keys = [c for c in KEY_COLS if c in df.columns]
#     if len(have_keys) == len(KEY_COLS):
#         out_df = df[KEY_COLS + [TARGET_COL]].copy()
#         out_df.to_csv(OUT_WITH_KEY, sep="\t", index=False)
#         print(f"\n[OK] Wrote with key columns -> {OUT_WITH_KEY}")
#     else:
#         print("\n[WARN] Key columns not complete; skip with_key output.")
#         print("       Found keys:", have_keys)
#         print("       Expected keys:", KEY_COLS)

# if __name__ == "__main__":
#     main()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import re
import pandas as pd

FILE = "/miRTI/media/patient/tPCpbsamGz/NSR24066-3---22756831-49_ann.txt"

# ---- settings ----
PROM_COL = "promoterAI_tss500"
PROM_THR = 0.5

SPLICE_THR = 0.2  # 0.2 / 0.5 / 0.8 你可改
KEY_COLS = ["Chr", "Start", "End", "Ref", "Alt"]

# VEP SpliceAI plugin 常見欄位名候選
SPLICE_DS_COLS = [
    "DS_AG","DS_AL","DS_DG","DS_DL",
    "SpliceAI_DS_AG","SpliceAI_DS_AL","SpliceAI_DS_DG","SpliceAI_DS_DL",
    "SpliceAI_pred_DS_AG","SpliceAI_pred_DS_AL","SpliceAI_pred_DS_DG","SpliceAI_pred_DS_DL",
]

# ---- outputs ----
OUT_PROM_PASS = f"{PROM_COL}.abs_ge_{PROM_THR}.with_key.tsv"
OUT_SPLICE_PASS = f"SpliceAI.maxDS_ge_{SPLICE_THR}.with_key.tsv"
OUT_BOTH_PASS = f"PromoterAI_or_SpliceAI.pass.with_key.tsv"

OUT_STATS = "promoter_splice_filter.stats.txt"

def sniff_sep(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(8192)
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=["\t", ",", ";"])
        return dialect.delimiter
    except Exception:
        return "\t" if "\t" in sample else ","

def to_num_series(s: pd.Series) -> pd.Series:
    s = s.replace({".": None, "": None, "nan": None, "NaN": None})
    return pd.to_numeric(s, errors="coerce")

def pick_splice_cols(df: pd.DataFrame):
    cols = [c for c in SPLICE_DS_COLS if c in df.columns]
    if cols:
        return cols
    # fuzzy: 找含 DS_AG/DS_AL/DS_DG/DS_DL 的欄位
    fuzzy = [c for c in df.columns if re.search(r"(DS[_\.]?(AG|AL|DG|DL))", str(c), re.IGNORECASE)]
    return fuzzy

def main():
    if not os.path.exists(FILE):
        print(f"[ERROR] File not found: {FILE}")
        sys.exit(1)

    sep = sniff_sep(FILE)
    print(f"[INFO] Detected delimiter: {repr(sep)}")

    df = pd.read_csv(FILE, sep=sep, dtype=str, low_memory=False)
    print(f"[INFO] rows={len(df)} cols={len(df.columns)}")

    have_keys = all(c in df.columns for c in KEY_COLS)

    # -------------------------
    # PromoterAI filter
    # -------------------------
    if PROM_COL not in df.columns:
        print(f"[WARN] PromoterAI column not found: {PROM_COL}")
        prom_score = pd.Series([pd.NA] * len(df), index=df.index, dtype="float")
        prom_pass = pd.Series([False] * len(df), index=df.index)
    else:
        prom_score = to_num_series(df[PROM_COL].copy())
        prom_pass = prom_score.abs() >= PROM_THR

    prom_pass_df = df.loc[prom_pass].copy()
    prom_pass_df[f"{PROM_COL}_num"] = prom_score.loc[prom_pass]
    prom_pass_df[f"{PROM_COL}_sign"] = prom_pass_df[f"{PROM_COL}_num"].apply(lambda x: "pos" if x >= 0 else "neg")

    if have_keys:
        prom_out = prom_pass_df[KEY_COLS + [PROM_COL, f"{PROM_COL}_num", f"{PROM_COL}_sign"]]
    else:
        prom_out = prom_pass_df

    prom_out.to_csv(OUT_PROM_PASS, sep="\t", index=False)
    print(f"[OK] PromoterAI abs>= {PROM_THR} -> {OUT_PROM_PASS} (rows={int(prom_pass.sum())})")

    # -------------------------
    # SpliceAI filter (max DS)
    # -------------------------
    ds_cols = pick_splice_cols(df)
    if not ds_cols:
        print("[WARN] SpliceAI DS_* columns not found. Similar columns:")
        for c in df.columns:
            if "spliceai" in str(c).lower() or re.search(r"ds[_\.]?(ag|al|dg|dl)", str(c), re.IGNORECASE):
                print("  ", c)
        splice_maxds = pd.Series([pd.NA] * len(df), index=df.index, dtype="float")
        splice_pass = pd.Series([False] * len(df), index=df.index)
    else:
        mat = pd.DataFrame({c: to_num_series(df[c].copy()) for c in ds_cols}, index=df.index)
        splice_maxds = mat.max(axis=1, skipna=True)
        splice_pass = splice_maxds >= SPLICE_THR

    splice_pass_df = df.loc[splice_pass].copy()
    splice_pass_df["SpliceAI_maxDS"] = splice_maxds.loc[splice_pass]

    # 同時把四個 DS 欄位（若存在）一起輸出，方便你看是哪個造成 max
    for c in ds_cols:
        if c in df.columns:
            splice_pass_df[c] = to_num_series(df.loc[splice_pass, c])

    if have_keys:
        cols_out = KEY_COLS + ["SpliceAI_maxDS"] + ds_cols
        cols_out = [c for c in cols_out if c in splice_pass_df.columns]
        splice_out = splice_pass_df[cols_out]
    else:
        splice_out = splice_pass_df

    splice_out.to_csv(OUT_SPLICE_PASS, sep="\t", index=False)
    print(f"[OK] SpliceAI maxDS >= {SPLICE_THR} -> {OUT_SPLICE_PASS} (rows={int(splice_pass.sum())})")

    # -------------------------
    # Combined (PromoterAI OR SpliceAI)
    # -------------------------
    both_pass = prom_pass | splice_pass
    both_df = df.loc[both_pass].copy()
    if PROM_COL in df.columns:
        both_df[f"{PROM_COL}_num"] = prom_score.loc[both_pass]
    both_df["SpliceAI_maxDS"] = splice_maxds.loc[both_pass]

    if have_keys:
        cols_out = KEY_COLS + []
        if PROM_COL in df.columns:
            cols_out += [PROM_COL, f"{PROM_COL}_num"]
        cols_out += ["SpliceAI_maxDS"]
        # 若你想也把 DS_* 一起帶出來
        cols_out += ds_cols
        cols_out = [c for c in cols_out if c in both_df.columns]
        both_out = both_df[cols_out]
    else:
        both_out = both_df

    both_out.to_csv(OUT_BOTH_PASS, sep="\t", index=False)
    print(f"[OK] PromoterAI OR SpliceAI pass -> {OUT_BOTH_PASS} (rows={int(both_pass.sum())})")

    # -------------------------
    # Stats summary
    # -------------------------
    with open(OUT_STATS, "w", encoding="utf-8") as f:
        f.write(f"file\t{FILE}\n")
        f.write(f"rows_total\t{len(df)}\n")

        # promoter stats
        f.write(f"\n[promoterAI]\n")
        f.write(f"col\t{PROM_COL}\n")
        f.write(f"thr_abs\t{PROM_THR}\n")
        f.write(f"prom_missing_or_non_numeric\t{int(prom_score.isna().sum())}\n")
        f.write(f"prom_abs_ge_thr\t{int(prom_pass.sum())}\n")
        if prom_pass.any():
            f.write(f"prom_min_pass\t{float(prom_score.loc[prom_pass].min())}\n")
            f.write(f"prom_max_pass\t{float(prom_score.loc[prom_pass].max())}\n")

        # splice stats
        f.write(f"\n[spliceAI]\n")
        f.write(f"thr_maxDS\t{SPLICE_THR}\n")
        f.write(f"ds_cols\t{','.join(ds_cols) if ds_cols else ''}\n")
        f.write(f"splice_missing_or_non_numeric\t{int(splice_maxds.isna().sum())}\n")
        f.write(f"splice_maxDS_ge_thr\t{int(splice_pass.sum())}\n")
        if splice_pass.any():
            f.write(f"splice_min_pass\t{float(splice_maxds.loc[splice_pass].min())}\n")
            f.write(f"splice_max_pass\t{float(splice_maxds.loc[splice_pass].max())}\n")

        # combined
        f.write(f"\n[combined]\n")
        f.write(f"prom_or_splice_pass\t{int(both_pass.sum())}\n")
        f.write(f"prom_only\t{int((prom_pass & ~splice_pass).sum())}\n")
        f.write(f"splice_only\t{int((~prom_pass & splice_pass).sum())}\n")
        f.write(f"both\t{int((prom_pass & splice_pass).sum())}\n")

    print(f"[OK] stats -> {OUT_STATS}")

if __name__ == "__main__":
    main()


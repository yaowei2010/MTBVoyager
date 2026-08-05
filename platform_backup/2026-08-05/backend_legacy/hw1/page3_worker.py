#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shlex
import time
import traceback
import subprocess
from datetime import datetime
from pathlib import Path

import pandas as pd

# ====== Django setup (讓 worker 可以操作 DB model) ======
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "uploadfunction.settings")  # <-- 改成你的 settings module
import django
django.setup()
from .models import existJobs  # <-- 改成你的 app 路徑

# ====== import 你原本 view 裡用到的功能 ======
# 這些你原本就有：請把路徑改成你實際放的位置
from .views import (  # <-- 你可以把原本那堆函式放到 utils.py 再 import
    genePanelListProcessing,
    extractHpoIds,
    requestAmelieAPI,   # 如果它硬要 request，我下面有 fallback
    saveConfig,
    getConfig,
    check_pickle_exist,
    preprocessor,
    WES_layering,
    WES_layering_hg38,
    get_summary_excel,
    normalize_gnomad_population,
    apply_gnomad_population_af,
)

import pickle


# =========================
# helpers
# =========================
def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def _log(log_path: str, msg: str):
    line = f"[{_now()}] {msg}\n"
    _ensure_dir(os.path.dirname(log_path))
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()
    print(line, end="")

def _log_file_head(log_path: str, file_path: str, n_lines: int = 30, max_chars_per_line: int = 500):
    """把檔案前 n 行寫到 log（避免太長，每行截斷）"""
    try:
        if not os.path.exists(file_path):
            _log(log_path, f"[HEAD] file not found: {file_path}")
            return
        _log(log_path, f"[HEAD] {file_path} (first {n_lines} lines)")
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for i in range(n_lines):
                line = f.readline()
                if not line:
                    break
                line = line.rstrip("\n")
                if len(line) > max_chars_per_line:
                    line = line[:max_chars_per_line] + "...(truncated)"
                _log(log_path, f"  {i+1:02d}: {line}")
    except Exception as e:
        _log(log_path, f"[HEAD] failed to read head: {e}")


def _log_tsv_preview(log_path: str, tsv_path: str, n_rows: int = 5, n_cols: int = 12):
    """用 pandas 讀 TSV 的前幾列，寫到 log（同樣避免太長）"""
    try:
        if not os.path.exists(tsv_path):
            _log(log_path, f"[PREVIEW] file not found: {tsv_path}")
            return
        df = pd.read_csv(tsv_path, sep="\t", nrows=n_rows)
        # 欄位太多就只留前 n_cols 欄
        if df.shape[1] > n_cols:
            df2 = df.iloc[:, :n_cols].copy()
            _log(log_path, f"[PREVIEW] columns truncated: showing first {n_cols}/{df.shape[1]} columns")
        else:
            df2 = df

        _log(log_path, f"[PREVIEW] {tsv_path} shape(head)={df.shape} showing {df2.shape[0]}x{df2.shape[1]}")
        _log(log_path, f"[PREVIEW] columns: {list(df2.columns)}")
        _log(log_path, "[PREVIEW] head:\n" + df2.to_string(index=False))
    except Exception as e:
        _log(log_path, f"[PREVIEW] failed: {e}")
def _log_tsv_columns(log_path: str, tsv_path: str, sep: str = "\t", wrap: int = 20):
    """
    只讀 TSV header，將「完整欄位清單」寫到 log。
    wrap: 每行印幾個欄位（避免單行太長）
    """
    try:
        if not os.path.exists(tsv_path):
            _log(log_path, f"[COLUMNS] file not found: {tsv_path}")
            return

        # 只讀 header，不讀資料
        df0 = pd.read_csv(tsv_path, sep=sep, nrows=0)
        cols = list(df0.columns)

        _log(log_path, f"[COLUMNS] {tsv_path} total_cols={len(cols)}")

        # 完整列出（分行）
        if wrap and wrap > 0:
            for i in range(0, len(cols), wrap):
                chunk = cols[i:i+wrap]
                _log(log_path, "  " + " | ".join(chunk))
        else:
            # 不分行（不建議）
            _log(log_path, "  " + " | ".join(cols))

    except Exception as e:
        _log(log_path, f"[COLUMNS] failed: {e}")

def _status_marker_path(jobid: str) -> str:
    return os.path.join("media", "patient", jobid, "pipeline_status.json")


def _write_status_marker(jobid: str, status: str, extra: dict | None = None):
    p = _status_marker_path(jobid)
    _ensure_dir(os.path.dirname(p))
    payload = {"jobid": jobid, "status": status, "time": _now()}
    if extra:
        payload.update(extra)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _run(cmd: str, log_path: str):
    _log(log_path, f"[CMD] {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def _load_summary(jobid: str) -> dict:
    p = os.path.join("media", "patient", jobid, "summary.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _safe_request_amelie(log_path: str, hpoTermIds, gene_panel):
    """
    你原本 requestAmelieAPI(request, ...) 在 worker 沒有 request。
    我先用 try/except：如果你的函式允許 request=None 就照跑；
    不行就 fallback 成空結果（但流程不中斷）。
    """
    try:
        return requestAmelieAPI(None, hpoTermIds, gene_panel)
    except Exception as e:
        _log(log_path, f"[WARN] requestAmelieAPI failed in worker (no request). skip amelie. err={e}")
        return {}  # 空 dict -> 後面會填 -1


def _build_pipeline_cmd(build: str, upload: str, out_tmp: str, jobid: str) -> str:
    upload_q = shlex.quote(upload)
    out_q = shlex.quote(out_tmp)
    jobid_q = shlex.quote(jobid)

    if build == "hg38":
        # 由外部環境提供 AG_API_KEY，這裡只負責啟用 AlphaGenome
        # 注意：每個 token 後面都要空白
        prefix = " ".join([
            "RUN_ALPHAGENOME=1",
            "ALPHAGENOME_AG_PYTHON=/root/miniconda3/envs/ag/bin/python",
            "ALPHAGENOME_SEQ=100KB",
            "ALPHAGENOME_MAX=200",
        ]) + " "

        return (
            prefix
            + f"python3 /miRTI/test_hg38/hg38_pipeline_backup.py "
              f"-input {upload_q} -output {out_q} --jobid {jobid_q}"
        )

    else:
        return f"python3 /miRTI/annovar_pipeline0_3.py -input {upload_q} -output {out_q} --jobid {jobid_q}"



def _job_dir(jobid: str) -> str:
    return os.path.join("media", "patient", jobid)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobid", required=True)
    args = ap.parse_args()

    jobid = args.jobid
    base_dir = _job_dir(jobid)
    page3_log = os.path.join(base_dir, "page3_backend.log")

    _log(page3_log, "==== page3_worker START ====")
    _write_status_marker(jobid, "running")

    try:
        summary = _load_summary(jobid)
        build = summary.get("build", "hg19")
        uploadFile_url = summary["uploadFile_url"]
        resultFile_url = summary["resultFile_url"]

        maf = summary.get("maf_cutoff", "")
        min_dp = summary.get("min_dp_cutoff", "")
        min_aaf = summary.get("min_aaf", "")
        config_name = summary.get("configName", "default")
        frontendJson = summary.get("genePanelList", {})
        gnomad_population = normalize_gnomad_population(summary.get("gnomad_population", "eas"))

        # DB job
        job = existJobs.jobs.get(jobID=jobid)
        sampleID = job.subject_id

        # ✅ 重要：resultFile_url 不能提早生成，否則 show_job_list 會提早判 finished
        # 所以 pipeline 先輸出 tmp，全部跑完最後再 os.replace 到 resultFile_url
        out_tmp = resultFile_url + ".tmp"

        # cleanup 舊 tmp
        try:
            if os.path.exists(out_tmp):
                os.remove(out_tmp)
        except Exception:
            pass

        # -------- Step 1: pipeline (annovar/hg38) --------
        _log(page3_log, f"Step 1: run pipeline build={build} gnomad_population={gnomad_population}")
        cmd = _build_pipeline_cmd(build, uploadFile_url, out_tmp, jobid)
        _run(cmd, page3_log)

        if not os.path.isfile(out_tmp):
            raise RuntimeError(f"Pipeline output tmp not found: {out_tmp}")

        _log(page3_log, f"Pipeline tmp OK: {out_tmp}")
        # ---- DEBUG: dump a small part of annovar output into log ----
        _log_file_head(page3_log, out_tmp, n_lines=2)
        _log_tsv_preview(page3_log, out_tmp, n_rows=3, n_cols=12)
        _log_tsv_columns(page3_log, out_tmp, wrap=15)  # wrap 你可以改 10/20/30
        # -------- Step 2: interpretation/layering (你的原本功能) --------
        _log(page3_log, "Step 2: interpretation/layering START")

        # strategy 固定 A（照你原本）
        strategy = "A"
        review_status = "0"
        filtering = "False"

        # gene panel / HPO / Amelie
        gene_panel = []
        genePanelDataFrame = None
        aggregateDict = {}

        if strategy != "Cancer":
            frontendJsonContent = frontendJson if isinstance(frontendJson, dict) else {}
            aggregateDict = genePanelListProcessing(frontendJsonContent.get("GenePanelList", []))
            gene_panel = aggregateDict.get("genes", [])
            panelNames = aggregateDict.get("panelNames", [])
            genePanelDataFrame = aggregateDict.get("result", None)
            hpoTermIds = extractHpoIds(panelNames)

            _log(page3_log, f"gene_panel={len(gene_panel)} panelNames={len(panelNames)} hpo={len(hpoTermIds)}")

            if genePanelDataFrame is not None:
                if len(hpoTermIds) != 0:
                    amelieResultDict = _safe_request_amelie(page3_log, hpoTermIds, gene_panel)

                    if amelieResultDict:
                        amelieResultTable = pd.DataFrame({"Genes": amelieResultDict.keys()})
                        amelieResultTable["Max_Score"] = amelieResultTable["Genes"].apply(
                            lambda x: round(max(dict(amelieResultDict[x]).values()), 2)
                        )
                        amelieResultTable["Mean_Score"] = amelieResultTable["Genes"].apply(
                            lambda x: round(sum(dict(amelieResultDict[x]).values()) / len(dict(amelieResultDict[x]).values()), 2)
                        )
                        amelieResultTable["Number_of_References"] = amelieResultTable["Genes"].apply(
                            lambda x: len(dict(amelieResultDict[x]).values())
                        )
                        amelieResultTable["References_List"] = amelieResultTable["Genes"].apply(
                            lambda x: list(dict(amelieResultDict[x]).keys())
                        )
                        amelieResultTable["Scores_List"] = amelieResultTable["Genes"].apply(
                            lambda x: list(dict(amelieResultDict[x]).values())
                        )

                        genePanelDataFrame = genePanelDataFrame.merge(amelieResultTable, on="Genes", how="outer").fillna(-1)
                        genePanelDataFrame["Number_of_References"] = genePanelDataFrame["Number_of_References"].to_numpy(int)
                    else:
                        # amelie skip -> fill -1
                        genePanelDataFrame["Max_Score"] = -1
                        genePanelDataFrame["Mean_Score"] = -1
                        genePanelDataFrame["Number_of_References"] = -1
                        genePanelDataFrame["References_List"] = -1
                        genePanelDataFrame["Scores_List"] = -1
                else:
                    genePanelDataFrame["Max_Score"] = -1
                    genePanelDataFrame["Mean_Score"] = -1
                    genePanelDataFrame["Number_of_References"] = -1
                    genePanelDataFrame["References_List"] = -1
                    genePanelDataFrame["Scores_List"] = -1

                out_gp = os.path.join(base_dir, "GenePanelDataFrame.tsv")
                genePanelDataFrame.to_csv(out_gp, sep="\t", index=None)
                _log(page3_log, f"Wrote {out_gp}")

        # saveConfig（照你原本）
        config_values = [strategy, review_status, maf, min_dp, min_aaf, filtering]
        config_keys = ["strategy", "review_status", "MAF_cutoff", "Min_DP_cutoff", "Min_AAF", "filtering"]
        config = dict(zip(config_keys, config_values))
        if isinstance(frontendJson, dict):
            config.update(frontendJson)

        saveConfig(config, jobid, config_name)
        _log(page3_log, "saveConfig DONE")

        # load annotated + genotype
        annotated_file = out_tmp  # 先用 tmp 讀，最後才 move 到 resultFile_url
        input_file = uploadFile_url

        annot_table = pd.read_csv(annotated_file, sep="\t")
        _log(page3_log, f"annot_table loaded shape={annot_table.shape}")

        # cutoff 轉型
        try:
            min_aaf_value = float(min_aaf)
        except Exception:
            min_aaf_value = None

        try:
            min_dp_value = int(min_dp)
        except Exception:
            min_dp_value = None

        import re
        regex = re.compile(r"\.vcf$")

        if regex.search(input_file):
            gt_input_file = regex.sub("_tmp.avinput", input_file)
            gt_input = pd.read_csv(gt_input_file, sep="\t", header=None, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 9, 14, 16, 17])

            av_processor = preprocessor(gt_input, min_aaf_value, min_dp_value)
            gt_input = av_processor.start_processing()
            _log(page3_log, f"gt_input processed shape={gt_input.shape}")
        else:
            gt_input = pd.read_csv(input_file, sep="\t", header=None)
            gt_input = gt_input.rename(columns={0: "Chr", 1: "Start", 2: "End", 3: "Ref", 4: "Alt", 5: "GT", 6: "QUAL", 7: "DP"})
            gt_input["VAF"] = 0.5
            gt_input["AD"] = "250,250"

        # layering（依 build 選 hg38 或 hg19 class）
        if strategy != "Cancer":
            if build == "hg38":
                WES_layer = WES_layering_hg38(
                    annotation_table=annot_table,
                    genotype_table=gt_input,
                    gene_panel=gene_panel,
                    MAF_cutoff=maf,
                    review_status=review_status,
                    phenotypeDrivenRanking=genePanelDataFrame,
                    log_file=os.path.join(base_dir, "layering.log"),
                    debug_dir=os.path.join(base_dir, "layering_debug"),
                    write_step_tsv=False,
                    gnomad_population=gnomad_population,
                )
            else:
                WES_layer = WES_layering(
                    annotation_table=annot_table,
                    genotype_table=gt_input,
                    gene_panel=gene_panel,
                    MAF_cutoff=maf,
                    review_status=review_status,
                    phenotypeDrivenRanking=genePanelDataFrame,
                )

            parameters = WES_layer.layering()
            _log(page3_log, "WES_layer.layering DONE")
        else:
            Somatic_layer = Somatic_layering(
                annotation_table=annot_table,
                genotype_table=gt_input,
                MAF_cutoff=maf,
            )
            parameters = Somatic_layer.layering()
            _log(page3_log, "Somatic_layer.layering DONE")

        # save pickle + excel
        result_prefix = os.path.join(base_dir, sampleID)
        with open(result_prefix + ".pickle", "wb") as wf:
            pickle.dump(parameters, wf)
        _log(page3_log, f"Pickle saved: {result_prefix}.pickle")

        # get_summary_excel(parameters, jobid, sampleID)
        # _log(page3_log, "get_summary_excel DONE")

        # -------- Step 3: 最後才把 tmp -> resultFile_url（show_job_list 才會判 finished）--------
        _ensure_dir(os.path.dirname(resultFile_url))
        os.replace(out_tmp, resultFile_url)
        _log(page3_log, f"FINAL output created: {resultFile_url}")

        # finished
        existJobs.jobs.filter(jobID=jobid).update(status="finished")
        _write_status_marker(jobid, "finished")
        _log(page3_log, "==== page3_worker FINISHED ====")

    except Exception as e:
        _log(page3_log, "FATAL ERROR in page3_worker:")
        _log(page3_log, str(e))
        _log(page3_log, traceback.format_exc())

        existJobs.jobs.filter(jobID=jobid).update(status="failed")
        _write_status_marker(jobid, "failed", {"error": str(e)})

        # tmp 檔避免誤判 finished（確保不存在）
        try:
            summary = _load_summary(jobid)
            out_tmp = summary.get("resultFile_url", "") + ".tmp"
            if out_tmp and os.path.exists(out_tmp):
                os.remove(out_tmp)
        except Exception:
            pass

        raise


if __name__ == "__main__":
    main()

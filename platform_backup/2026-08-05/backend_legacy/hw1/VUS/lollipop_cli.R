#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(maftools)
  library(data.table)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  stop("USAGE: Rscript lollipop_cli.R <in_maf.tsv> <gene> <out_prefix>")
}
in_maf   <- args[1]
gene     <- args[2]
out_pref <- args[3]

# ---------- 抓腳本目錄並載入函式 ----------
get_script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  if (length(file_arg) == 1) {
    return(dirname(normalizePath(sub("^--file=", "", file_arg))))
  }
  if (!is.null(sys.frames()[[1]]) && !is.null(sys.frames()[[1]]$ofile)) {
    return(dirname(normalizePath(sys.frames()[[1]]$ofile)))
  }
  getwd()
}
script_dir <- get_script_dir()
source(file.path(script_dir, "lollipop_data.R"))

# ---------- 讀 MAF ----------
maf_obj <- read.maf(maf = fread(in_maf, data.table = FALSE))

# ---------- 依 isoform 分群跑（回傳 list，每個元素是 lollipopPlotData 的輸出） ----------
res_list <- lollipopPlotDataByIsoform(maf = maf_obj, gene = gene)

# 若只有一組（沒有 isoform 欄位或全部 UNKNOWN），也統一走 bundle 輸出
if (length(res_list) < 1) {
  stop("No result returned from lollipopPlotDataByIsoform().")
}

# ---------- 決定 defaultIsoform：選 nMutations 最大的（若無則取第一個） ----------
n_mut <- sapply(res_list, function(x) {
  if (!is.null(x$nMutations) && !is.na(x$nMutations)) return(as.numeric(x$nMutations))
  if (!is.null(x$mutSummary) && nrow(x$mutSummary)) return(sum(x$mutSummary$count))
  0
})
default_iso <- names(res_list)[which.max(n_mut)]
if (is.null(default_iso) || length(default_iso) == 0) default_iso <- names(res_list)[1]

# ---------- 輸出每個 isoform 的 TSV + meta ----------
safe_id <- function(x) {
  # 檔名安全：非英數都轉底線
  gsub("[^A-Za-z0-9]+", "_", x)
}

bundle_items <- list()

for (iso_id in names(res_list)) {
  one <- res_list[[iso_id]]

  sid <- safe_id(iso_id)
  pref_i <- paste0(out_pref, "__", sid)

  # TSV
  fwrite(one$mutSummary, file = paste0(pref_i, "_mutSummary.tsv"), sep = "\t")
  fwrite(one$domainDF,   file = paste0(pref_i, "_domainDF.tsv"),   sep = "\t")

  # meta.json（沿用你原本 meta 結構，加上 isoform 資訊）
  titleInfo <- one$titleInfo
  titleInfo$subTitle <- paste(deparse(titleInfo$subTitle), collapse = "")

  meta <- list(
    isoformID = one$isoformID,
    isoformCol = one$isoformCol,
    nMutations = one$nMutations,
    axisInfo  = one$axisInfo,
    colors    = list(
      variantColors = as.list(one$colors$variantColors),
      domainColors  = as.list(one$colors$domainColors)
    ),
    titleInfo = titleInfo,
    labDat    = one$labDat,
    protLen   = one$protLen
  )

  write_json(meta,
             path = paste0(pref_i, "_meta.json"),
             auto_unbox = TRUE, pretty = TRUE)

  bundle_items[[length(bundle_items) + 1]] <- list(
    isoformID = iso_id,
    safeID = sid,
    prefix = pref_i
  )
}

# ---------- bundle.json（給 Python 讀回所有 isoform） ----------
bundle <- list(
  gene = gene,
  defaultIsoform = default_iso,
  isoforms = bundle_items
)

write_json(bundle,
           path = paste0(out_pref, "_bundle.json"),
           auto_unbox = TRUE, pretty = TRUE)

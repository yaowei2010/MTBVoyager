#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ssMutPA)  # 提供 FastSEAscore
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  cat("Usage:\n",
      "  Rscript run_FastSEAscore.R <MRWR_result.(csv|rds)> <all_pathways_gmt.Rdata> <out_csv> [min_g=10] [max_g=500]\n\n",
      "Notes:\n",
      "  - MRWR CSV 欄位可為 (gene,score) 或 (NodeNames,Score)\n",
      "  - RDS 支援 list(RWRM_Results=data.frame(NodeNames,Score), ...)\n",
      "  - all_pathways_gmt.Rdata 需有二欄 data.frame：Pathway, Gene（物件名不限）\n",
      sep = "")
  quit(status = 1)
}
mrwr_path <- args[[1]]
gmt_rdata <- args[[2]]
out_csv   <- args[[3]]
min_g     <- ifelse(length(args) >= 4, as.integer(args[[4]]), 10L)
max_g     <- ifelse(length(args) >= 5, as.integer(args[[5]]), 500L)

# ---------- 1) 讀取 MRWR 結果 → gene_list (named numeric, 排序遞減) ----------
read_mrwr_to_gene_list <- function(path) {
  stopifnot(file.exists(path))
  ext <- tolower(sub(".*\\.(\\w+)$", "\\1", path))
  if (ext == "csv") {
    df <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
    cn <- tolower(colnames(df))
    # 嘗試對應欄位名
    gene_col <- if ("gene" %in% cn) colnames(df)[match("gene", cn)] else
                if ("nodenames" %in% cn) colnames(df)[match("nodenames", cn)] else
                stop("MRWR CSV needs a 'gene' or 'NodeNames' column.")
    score_col <- if ("score" %in% cn) colnames(df)[match("score", cn)] else
                 if ("rwr_score" %in% cn) colnames(df)[match("rwr_score", cn)] else
                 if ("rankscore" %in% cn) colnames(df)[match("rankscore", cn)] else
                 if ("score" %in% cn) "score" else
                 if ("Score" %in% colnames(df)) "Score" else
                 stop("MRWR CSV needs a numeric score column (e.g., 'score' or 'Score').")
    vec <- as.numeric(df[[score_col]])
    names(vec) <- toupper(trimws(as.character(df[[gene_col]])))
    vec <- vec[!is.na(vec) & nchar(names(vec)) > 0]
    vec <- vec[!duplicated(names(vec))]  # 去重
    vec[order(-vec)]
  } else if (ext == "rds") {
    res <- readRDS(path)
    # 常見結構：list(RWRM_Results=data.frame(NodeNames,Score), Seed_Nodes=...)
    if (is.list(res) && !is.null(res$RWRM_Results) && is.data.frame(res$RWRM_Results)) {
      df <- res$RWRM_Results
      gene_col <- if ("NodeNames" %in% colnames(df)) "NodeNames" else
                  if ("gene" %in% colnames(df)) "gene" else
                  colnames(df)[1]
      score_col <- if ("Score" %in% colnames(df)) "Score" else
                   if ("score" %in% colnames(df)) "score" else
                   colnames(df)[sapply(df, is.numeric)][1]
      vec <- as.numeric(df[[score_col]])
      names(vec) <- toupper(trimws(as.character(df[[gene_col]])))
      vec <- vec[!is.na(vec) & nchar(names(vec)) > 0]
      vec <- vec[!duplicated(names(vec))]
      vec[order(-vec)]
    } else {
      stop("Unrecognized RDS structure. Expect list with $RWRM_Results data.frame.")
    }
  } else {
    stop("Unsupported MRWR file extension: ", ext)
  }
}

cat("[INFO] Reading MRWR results ...\n")
gene_list <- read_mrwr_to_gene_list(mrwr_path)
if (length(gene_list) == 0) stop("Empty gene_list derived from MRWR results.")

# ---------- 2) 讀取 all_pathways_gmt.Rdata → 二欄 data.frame Pathway,Gene ----------
cat("[INFO] Loading pathway Rdata ...\n")
load(gmt_rdata)
# 找出第一個二欄 data.frame 作為 gmt（容錯：欄名包含 Pathway/Gene 即可）
objs <- ls()
pick <- NULL
for (o in objs) {
  x <- get(o)
  if (is.data.frame(x) && ncol(x) >= 2) {
    cols <- tolower(colnames(x))
    if (any(grepl("pathway", cols)) && any(grepl("^gene$", cols))) {
      pick <- o; break
    }
  }
}
if (is.null(pick)) {
  # 退而求其次：第一個 data.frame
  for (o in objs) {
    if (is.data.frame(get(o)) && ncol(get(o)) >= 2) { pick <- o; break }
  }
}
if (is.null(pick)) stop("No 2-column data.frame (Pathway, Gene) found in Rdata.")

gmt <- get(pick)
# 標準化欄名
colnames(gmt)[1:2] <- c("Pathway", "Gene")
gmt$Pathway <- as.character(gmt$Pathway)
gmt$Gene    <- toupper(trimws(as.character(gmt$Gene)))
gmt <- gmt[nchar(gmt$Gene) > 0, , drop = FALSE]
gmt <- unique(gmt)

# 可選：以基因數篩選 pathway 規模
sizes <- table(gmt$Pathway)
keep_pw <- names(sizes)[sizes >= min_g & sizes <= max_g]
gmt <- gmt[gmt$Pathway %in% keep_pw, , drop = FALSE]

cat(sprintf("[INFO] Pathways kept after size filter (%d–%d genes): %d (rows: %d)\n",
            min_g, max_g, length(unique(gmt$Pathway)), nrow(gmt)))

# ---------- 3) 準備 pathway list 與名稱對齊 ----------
pathway_list <- split(gmt$Gene, gmt$Pathway)
# gene_list 名稱（基因符號）一律大寫（已處理），確保與 pathway 一致
gl_names <- names(gene_list)

# ---------- 4) 對每個 pathway 計算 FastSEAscore ----------
cat("[INFO] Computing FastSEAscore for each pathway ...\n")
compute_es <- function(geneset) {
  gs <- unique(geneset)
  tag.ind <- sign(match(gl_names, gs, nomatch = 0))
  # 若沒有任何重疊就回 NA，避免毫無意義的 ES
  if (sum(tag.ind != 0) == 0) return(NA_real_)
  FastSEAscore(labels.list = tag.ind, correl_vector = gene_list)
}

pw_names <- names(pathway_list)
es_vals <- vapply(pathway_list, compute_es, numeric(1))
overlap <- vapply(pathway_list, function(gs) sum(gl_names %in% unique(gs)), integer(1))

out <- data.frame(
  Pathway = pw_names,
  ES      = es_vals,
  Overlap = overlap,
  Size    = as.integer(sapply(pathway_list, function(gs) length(unique(gs)))),
  stringsAsFactors = FALSE
)
# 排序：先 ES（大→小），再 Overlap（大→小）
out <- out[order(-out$ES, -out$Overlap), ]

# ---------- 5) 輸出 ----------
write.csv(out, out_csv, row.names = FALSE)
cat("[INFO] Wrote Pathway ES to:", normalizePath(out_csv), "\n")

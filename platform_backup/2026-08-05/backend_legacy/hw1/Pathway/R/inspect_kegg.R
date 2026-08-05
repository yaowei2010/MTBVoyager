#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(ssMutPA)
})

# 1) 載入 kegg_323_gmt
path <- system.file("extdata", "kegg_323_gmt.Rdata", package = "ssMutPA")
if (path == "") {
  stop("找不到 kegg_323_gmt.Rdata，請確認 ssMutPA 是否安裝。")
}
load(path)  # 載入物件 kegg_323_gmt
cat("[INFO] 已載入 kegg_323_gmt\n")

# 2) 基本資訊
cat("總 pathway 數量:", length(unique(kegg_323_gmt[,1])), "\n")
cat("總 row 數 (Pathway-基因對):", nrow(kegg_323_gmt), "\n\n")

# 每個 pathway 的基因數（前 10 名）
sizes <- sort(table(kegg_323_gmt[,1]), decreasing = TRUE)
cat("[Top 10 Pathway by size]\n")
print(head(sizes, 10))

# 3) 隨機預覽
set.seed(123)
pw <- sample(names(sizes), 1)
cat("\n隨機抽一個 pathway:", pw, "\n")
genes <- kegg_323_gmt[kegg_323_gmt[,1] == pw, 2]
print(head(genes, 20))

# 4) 匯出 CSV
out_csv <- "kegg_323_gmt_export.csv"
write.csv(kegg_323_gmt, out_csv, row.names = FALSE)
cat("\n已匯出完整二欄表至:", normalizePath(out_csv), "\n")

# 5) 若要轉成 list（跟範例程式一致）
pathway_list <- split(kegg_323_gmt[,2], kegg_323_gmt[,1])
cat("pathway_list 已建立，可在互動環境中使用。\n")

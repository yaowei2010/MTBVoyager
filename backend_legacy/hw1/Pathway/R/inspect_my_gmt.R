#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript inspect_my_gmt.R <your_Rdata_file>", call. = FALSE)
}

rdata_file <- args[1]
if (!file.exists(rdata_file)) {
  stop("File not found: ", rdata_file)
}

# 載入
load(rdata_file)

# 假設你的物件叫 tcga_like_gmt
obj_name <- ls()[sapply(ls(), function(x) is.data.frame(get(x)))]
if (length(obj_name) == 0) {
  stop("No data.frame object found in ", rdata_file)
}
gmt <- get(obj_name[1])

cat("[INFO] Loaded object:", obj_name[1], "\n")
cat("Rows (Pathway-Gene pairs):", nrow(gmt), "\n")
cat("Unique pathways:", length(unique(gmt$Pathway)), "\n\n")

# pathway 大小
sizes <- sort(table(gmt$Pathway), decreasing = TRUE)
cat("[Top 10 largest pathways]\n")
print(head(sizes, 10))

cat("\n[Top 10 smallest pathways]\n")
print(tail(sizes, 10))

# 隨機抽一個 pathway
set.seed(123)
pw <- sample(names(sizes), 1)
cat("\n[Preview pathway]", pw, "\n")
print(head(gmt$Gene[gmt$Pathway == pw], 20))

# 匯出 CSV
out_csv <- sub("\\.Rdata$", "_export.csv", rdata_file)
write.csv(gmt, out_csv, row.names = FALSE)
cat("\n[INFO] Exported 2-column CSV to:", normalizePath(out_csv), "\n")

# 建立 list 格式
pathway_list <- split(gmt$Gene, gmt$Pathway)
cat("[INFO] pathway_list object built (list: Pathway -> Gene vector)\n")

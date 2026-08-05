#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(igraph)
  library(Matrix)
  library(ssMutPA)
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 2) {
  stop("Usage: Rscript run_ssMutPA.R seed_genes.csv output_dir [gene_burden.csv] [gamma]", call. = FALSE)
}
seed_csv <- args[1]
out_dir  <- args[2]
burden_csv <- if (length(args) >= 3) args[3] else NA
gamma <- if (length(args) >= 4) as.numeric(args[4]) else 0

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
log_msg <- function(...) cat(sprintf("[%s] ", format(Sys.time(), "%H:%M:%S")), sprintf(...), "\n")

# -------------------------
# helper: run MRWR (RWR) given restart vector p0
# -------------------------
run_mrwr <- function(W, p0, r = 0.7, tol = 1e-10, max_iter = 2000) {
  p <- p0
  for (it in 1:max_iter) {
    p_new <- (1 - r) * as.numeric(W %*% p) + r * p0
    if (sum(abs(p_new - p)) < tol) {
      p <- p_new
      return(list(p = p, it = it, converged = TRUE))
    }
    p <- p_new
  }
  list(p = p, it = max_iter, converged = FALSE)
}

# 1) load network
net_path <- system.file("extdata", "ppi_network.Rdata", package = "ssMutPA")
if (net_path == "") stop("Could not find ssMutPA extdata/ppi_network.Rdata. Is ssMutPA installed?")
load(net_path)  # ppi_network igraph
stopifnot(inherits(ppi_network, "igraph"))

# 2) adjacency -> column-stochastic transition matrix W
A   <- as_adjacency_matrix(ppi_network, sparse = TRUE)
deg <- Matrix::colSums(A)
deg[deg == 0] <- 1
W   <- t(t(A) / deg)

# 3) read seeds
seed_df <- read.csv(seed_csv, stringsAsFactors = FALSE)
sym_col <- if ("Hugo_Symbol" %in% colnames(seed_df)) "Hugo_Symbol" else colnames(seed_df)[1]
seed_raw <- unique(trimws(as.character(seed_df[[sym_col]])))
seed_raw <- seed_raw[!is.na(seed_raw) & seed_raw != ""]

nodes <- V(ppi_network)$name
Seeds <- intersect(seed_raw, nodes)

write.csv(data.frame(input_seed = seed_raw),
          file = file.path(out_dir, "debug_input_seeds.csv"), row.names = FALSE)
write.csv(data.frame(seeds_in_network = Seeds),
          file = file.path(out_dir, "debug_seeds_in_network.csv"), row.names = FALSE)

if (length(Seeds) == 0) {
  write.csv(data.frame(message = "No seeds overlap the PPI network"),
            file = file.path(out_dir, "MRWR_result.csv"), row.names = FALSE)
  quit(status = 0)
}
log_msg("Seeds: %d in CSV, %d overlapped network.", length(seed_raw), length(Seeds))

# 4) local weight Wi from ssMutPA
Seeds_Score <- get_seeds_score(
  net_data = ppi_network,
  seed     = Seeds,
  mut_gene = Seeds,
  BC_Num   = 12436,
  cut_point = 0
)
write.csv(Seeds_Score, file = file.path(out_dir, "local_weight_seeds_score.csv"), row.names = FALSE)

if (!all(c("Seeds_ID", "Score") %in% colnames(Seeds_Score))) {
  stop("Expected columns Seeds_ID and Score in Seeds_Score, but got: ",
       paste(colnames(Seeds_Score), collapse = ", "))
}

Wi_df <- data.frame(
  gene = trimws(as.character(Seeds_Score[["Seeds_ID"]])),
  Wi   = as.numeric(Seeds_Score[["Score"]]),
  stringsAsFactors = FALSE
)

# 只保留在 Seeds（network overlap 的 seed genes）
Wi_df <- Wi_df[Wi_df$gene %in% Seeds, , drop = FALSE]

# -------------------------
# NEW: 用「原始 Wi」跑 MRWR
# -------------------------
Wi_only <- Wi_df[, c("gene", "Wi"), drop = FALSE]
Wi_only$Wi[is.na(Wi_only$Wi) | Wi_only$Wi < 0] <- 0
write.csv(Wi_only, file = file.path(out_dir, "debug_Wi_only.csv"), row.names = FALSE)

p0_rawWi <- rep(0, length(nodes)); names(p0_rawWi) <- nodes
if (nrow(Wi_only) == 0) {
  log_msg("Wi_only empty; fallback to uniform over Seeds for rawWi MRWR.")
  p0_rawWi[Seeds] <- 1
} else {
  p0_rawWi[Wi_only$gene] <- Wi_only$Wi
  if (sum(p0_rawWi) == 0) p0_rawWi[Seeds] <- 1
}
p0_rawWi <- p0_rawWi / sum(p0_rawWi)

res_rawWi <- run_mrwr(W, p0_rawWi, r = 0.7, tol = 1e-10, max_iter = 2000)
log_msg("MRWR(rawWi) %s, it=%d.", if (res_rawWi$converged) "converged" else "reached max_iter", res_rawWi$it)

df_res_rawWi <- data.frame(gene = names(res_rawWi$p), score = as.numeric(res_rawWi$p), stringsAsFactors = FALSE)
df_res_rawWi <- df_res_rawWi[order(-df_res_rawWi$score), ]
write.csv(df_res_rawWi, file = file.path(out_dir, "MRWR_result_rawWi.csv"), row.names = FALSE)

k <- min(20, nrow(df_res_rawWi))
top <- df_res_rawWi[seq_len(k), , drop = FALSE]
png(file.path(out_dir, "MRWR_top20_rawWi.png"), width = 900, height = 600)
par(mar = c(10, 4, 2, 1))
barplot(top$score, names.arg = top$gene, las = 2,
        main = "MRWR using raw local weight (Wi) Top-20", ylab = "score")
dev.off()

# 5) read gene burden Sgh (optional)
Sgh_df <- data.frame(gene=character(0), Sgh=numeric(0))
if (!is.na(burden_csv) && file.exists(burden_csv)) {
  Sgh_df <- read.csv(burden_csv, stringsAsFactors = FALSE)
  if (!all(c("gene","Sgh") %in% colnames(Sgh_df))) {
    if ("Hugo_Symbol" %in% colnames(Sgh_df)) colnames(Sgh_df)[colnames(Sgh_df)=="Hugo_Symbol"] <- "gene"
    if (!("Sgh" %in% colnames(Sgh_df))) stop("gene_burden.csv must contain Sgh column")
  }
  Sgh_df$gene <- trimws(as.character(Sgh_df$gene))
  Sgh_df$Sgh  <- as.numeric(Sgh_df$Sgh)
}

# 6) Wprime = Wi * (1 + gamma*Sgh_scaled) * penalty
Wi_df <- merge(Wi_df, Sgh_df, by="gene", all.x=TRUE)
Wi_df$Sgh[is.na(Wi_df$Sgh)] <- 0

if (max(Wi_df$Sgh) > 0) {
  Wi_df$Sgh_scaled <- Wi_df$Sgh / max(Wi_df$Sgh)
} else {
  Wi_df$Sgh_scaled <- 0
}

penalty_zero <- 0.8
sgh_zero_eps <- 0.5
Wi_df$penalty <- 1
Wi_df$penalty[is.na(Wi_df$Sgh) | Wi_df$Sgh <= sgh_zero_eps] <- penalty_zero

Wi_df$Wi <- as.numeric(Wi_df$Wi)
Wi_df$Sgh_scaled <- as.numeric(Wi_df$Sgh_scaled)
Wi_df$Wprime <- Wi_df$Wi * (1 + gamma * Wi_df$Sgh_scaled) * Wi_df$penalty
Wi_df$Wprime[is.na(Wi_df$Wprime) | Wi_df$Wprime < 0] <- 0

# 6.5) Smooth penalty (power compression) - optional
ratio_thr <- 1.5
p_pow <- 0.6
eps <- 1e-12

wp <- Wi_df$Wprime
wp_pos <- wp[wp > eps]

if (length(wp_pos) >= 2) {
  s <- sort(wp_pos, decreasing = TRUE)
  ratio <- s[1] / s[2]
  if (ratio > ratio_thr) {
    log_msg("Smooth penalty triggered: top1/top2 ratio=%.2f > %.2f; apply power p=%.2f",
            ratio, ratio_thr, p_pow)
    m <- max(wp)
    if (m > 0) {
      Wi_df$Wprime <- (wp / m) ^ p_pow * m
    }
  }
}

write.csv(Wi_df, file = file.path(out_dir, "debug_Wi_Sgh_Wprime.csv"), row.names = FALSE)

# 7) build p0 over all nodes (restart distribution) using Wprime
p0 <- rep(0, length(nodes))
names(p0) <- nodes

if (nrow(Wi_df) == 0 || is.null(Wi_df$Wprime) || length(Wi_df$Wprime) != nrow(Wi_df)) {
  log_msg("Wi_df empty or Wprime invalid; fallback to uniform over Seeds.")
  p0[Seeds] <- 1
} else {
  p0[Wi_df$gene] <- Wi_df$Wprime
  if (sum(p0) == 0) p0[Seeds] <- 1
}
p0 <- p0 / sum(p0)

# 8) Run MRWR (Wprime)
res_wprime <- run_mrwr(W, p0, r = 0.7, tol = 1e-10, max_iter = 2000)
log_msg("MRWR(Wprime) %s, it=%d.", if (res_wprime$converged) "converged" else "reached max_iter", res_wprime$it)

# 9) output MRWR_result.csv compatible format
df_res <- data.frame(gene = names(res_wprime$p), score = as.numeric(res_wprime$p), stringsAsFactors = FALSE)
df_res <- df_res[order(-df_res$score), ]
write.csv(df_res, file = file.path(out_dir, "MRWR_result.csv"), row.names = FALSE)

# plot top20 (Wprime)
k <- min(20, nrow(df_res))
top <- df_res[seq_len(k), , drop = FALSE]
png(file.path(out_dir, "MRWR_top20.png"), width = 900, height = 600)
par(mar = c(10, 4, 2, 1))
barplot(top$score, names.arg = top$gene, las = 2,
        main = "MRWR using Wprime (Wi * (1+gamma*Sgh) * penalty) Top-20",
        ylab = "score")
dev.off()


# ============================================================
# EXTRA: (A) rawWi vs Wprime compare topK
#        (B) build COSMIC gene sets (CGC colon + actionability MSI/dMMR)
#        (C) evaluate Precision@K / Recall@K + dump hit lists
# ============================================================

# -------------------------
# (A) rawWi vs Wprime: topK overlap / diff / rank-score table
# -------------------------
compare_k <- 20  # 你想看 top 幾（用來列交集/差集），自己改

df_res_rawWi$rank_rawWi <- seq_len(nrow(df_res_rawWi))
df_res$rank_wprime <- seq_len(nrow(df_res))

top_rawWi <- head(df_res_rawWi, compare_k)
top_wprime <- head(df_res, compare_k)

raw_set <- top_rawWi$gene
wp_set  <- top_wprime$gene

intersect_genes <- intersect(raw_set, wp_set)
only_rawWi      <- setdiff(raw_set, wp_set)
only_wprime     <- setdiff(wp_set, raw_set)

write.csv(data.frame(gene = intersect_genes),
          file = file.path(out_dir, sprintf("compare_top%d_intersection.csv", compare_k)),
          row.names = FALSE)
write.csv(data.frame(gene = only_rawWi),
          file = file.path(out_dir, sprintf("compare_top%d_only_rawWi.csv", compare_k)),
          row.names = FALSE)
write.csv(data.frame(gene = only_wprime),
          file = file.path(out_dir, sprintf("compare_top%d_only_Wprime.csv", compare_k)),
          row.names = FALSE)

union_genes <- union(raw_set, wp_set)

sub_raw <- df_res_rawWi[df_res_rawWi$gene %in% union_genes, c("gene","rank_rawWi","score")]
colnames(sub_raw) <- c("gene","rank_rawWi","score_rawWi")

sub_wp  <- df_res[df_res$gene %in% union_genes, c("gene","rank_wprime","score")]
colnames(sub_wp) <- c("gene","rank_Wprime","score_Wprime")

cmp <- merge(sub_raw, sub_wp, by="gene", all=TRUE)
cmp$rank_delta_rawWi_minus_Wprime <- cmp$rank_rawWi - cmp$rank_Wprime
cmp <- cmp[order(-cmp$rank_delta_rawWi_minus_Wprime), ]

write.csv(cmp,
          file = file.path(out_dir, sprintf("compare_top%d_union_rank_score.csv", compare_k)),
          row.names = FALSE)

log_msg("Compare done: top%d rawWi vs Wprime. intersection=%d, only_rawWi=%d, only_Wprime=%d",
        compare_k, length(intersect_genes), length(only_rawWi), length(only_wprime))


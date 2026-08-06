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

# Robustly extract (gene, Wi)
# ssMutPA output columns may vary; try common possibilities
col_gene <- intersect(colnames(Seeds_Score), c("seed", "Seed", "Gene", "gene", "Node", "NodeNames"))
col_w    <- intersect(colnames(Seeds_Score), c("Weight", "weight", "Seeds_Score", "score", "W", "Wi"))
if (length(col_gene) == 0 || length(col_w) == 0) {
  stop("Cannot parse Seeds_Score columns. Please check local_weight_seeds_score.csv")
}
Wi_df <- data.frame(
  gene = as.character(Seeds_Score[[col_gene[1]]]),
  Wi   = as.numeric(Seeds_Score[[col_w[1]]]),
  stringsAsFactors = FALSE
)
Wi_df$gene <- trimws(Wi_df$gene)
Wi_df <- Wi_df[Wi_df$gene %in% Seeds, , drop = FALSE]

# 5) read gene burden Sgh (optional)
Sgh_df <- data.frame(gene=character(0), Sgh=numeric(0))
if (!is.na(burden_csv) && file.exists(burden_csv)) {
  Sgh_df <- read.csv(burden_csv, stringsAsFactors = FALSE)
  # expect columns: gene, Sgh
  if (!all(c("gene","Sgh") %in% colnames(Sgh_df))) {
    # try to normalize
    if ("Hugo_Symbol" %in% colnames(Sgh_df)) colnames(Sgh_df)[colnames(Sgh_df)=="Hugo_Symbol"] <- "gene"
    if (!("Sgh" %in% colnames(Sgh_df))) stop("gene_burden.csv must contain Sgh column")
  }
  Sgh_df$gene <- trimws(as.character(Sgh_df$gene))
  Sgh_df$Sgh  <- as.numeric(Sgh_df$Sgh)
}

# 6) multiplicative model: W'i = Wi * (1 + gamma * Sgh_i)
# Practical: scale Sgh to [0,1] within sample to avoid exploding weights
Wi_df <- merge(Wi_df, Sgh_df, by="gene", all.x=TRUE)
Wi_df$Sgh[is.na(Wi_df$Sgh)] <- 0

if (max(Wi_df$Sgh) > 0) {
  Wi_df$Sgh_scaled <- Wi_df$Sgh / max(Wi_df$Sgh)
} else {
  Wi_df$Sgh_scaled <- 0
}
Wi_df$Wprime <- Wi_df$Wi * (1 + gamma * Wi_df$Sgh_scaled)

# 7) build p0 over all nodes (restart distribution)
p0 <- rep(0, length(nodes))
names(p0) <- nodes
p0[Wi_df$gene] <- Wi_df$Wprime

if (sum(p0) == 0) {
  # fallback: uniform over seeds
  p0[Seeds] <- 1
}
p0 <- p0 / sum(p0)

write.csv(Wi_df, file = file.path(out_dir, "debug_Wi_Sgh_Wprime.csv"), row.names = FALSE)

# 8) Run RWR with restart vector p0
# standard update: p_{t+1} = (1-r) * W %*% p_t + r * p0
r <- 0.7
p <- p0
tol <- 1e-10
max_iter <- 2000

for (it in 1:max_iter) {
  p_new <- (1 - r) * as.numeric(W %*% p) + r * p0
  if (sum(abs(p_new - p)) < tol) {
    p <- p_new
    break
  }
  p <- p_new
}
log_msg("RWR converged (or reached max_iter=%d).", max_iter)

# 9) output MRWR_result.csv compatible format
df_res <- data.frame(gene = names(p), score = as.numeric(p), stringsAsFactors = FALSE)
df_res <- df_res[order(-df_res$score), ]
write.csv(df_res, file = file.path(out_dir, "MRWR_result.csv"), row.names = FALSE)

# plot top20
k <- min(20, nrow(df_res))
top <- df_res[seq_len(k), , drop = FALSE]
png(file.path(out_dir, "MRWR_top20.png"), width = 900, height = 600)
par(mar = c(10, 4, 2, 1))
barplot(top$score, names.arg = top$gene, las = 2, main = "RWR (Wi * (1+gamma*Sgh)) Top-20", ylab = "score")
dev.off()

log_msg("Done. Outputs written to: %s", normalizePath(out_dir))
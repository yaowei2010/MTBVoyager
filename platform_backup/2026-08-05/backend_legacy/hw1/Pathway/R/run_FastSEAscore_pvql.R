#===========================================================================================
suppressPackageStartupMessages({
  library(ssMutPA)  # FastSEAscore
})

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3) {
  cat(
    "Usage:\n",
    "  Rscript run_FastSEAscore_entropy_support.R <MRWR_result.(csv|rds)> <all_pathways_gmt.Rdata> <out_csv> [min_g=10] [max_g=500] [nperm=1000] [plot_pathway=''] [plot_prefix='']\n\n",
    "Args:\n",
    "  plot_pathway : (optional) exact Pathway name to export perm_ES distribution (CSV + PNG)\n",
    "  plot_prefix  : (optional) prefix for output files; default = out_csv without .csv\n\n",
    sep = ""
  )
  quit(status = 1)
}

mrwr_path <- args[[1]]
gmt_rdata <- args[[2]]
out_csv   <- args[[3]]

min_g     <- ifelse(length(args) >= 4, as.integer(args[[4]]), 10L)
max_g     <- ifelse(length(args) >= 5, as.integer(args[[5]]), 500L)
nperm     <- ifelse(length(args) >= 6, as.integer(args[[6]]), 1000L)
plot_pathway <- ifelse(length(args) >= 7, as.character(args[[7]]), "")
plot_prefix  <- ifelse(length(args) >= 8, as.character(args[[8]]), sub("\\.csv$", "", out_csv))

# ---------- 1) Read MRWR -> gene_list ----------
read_mrwr_to_gene_list <- function(path) {
  stopifnot(file.exists(path))
  ext <- tolower(sub(".*\\.(\\w+)$", "\\1", path))

  if (ext == "csv") {
    df <- read.csv(path, stringsAsFactors = FALSE, check.names = FALSE)
    cn <- tolower(colnames(df))

    gene_col <- if ("gene" %in% cn) colnames(df)[match("gene", cn)] else
      if ("nodenames" %in% cn) colnames(df)[match("nodenames", cn)] else
        stop("MRWR CSV needs a 'gene' or 'NodeNames' column.")

    score_col <- if ("score" %in% cn) colnames(df)[match("score", cn)] else
      if ("rwr_score" %in% cn) colnames(df)[match("rwr_score", cn)] else
        if ("rankscore" %in% cn) colnames(df)[match("rankscore", cn)] else
          if ("Score" %in% colnames(df)) "Score" else
            stop("MRWR CSV needs a numeric score column (e.g., 'score').")

    vec <- as.numeric(df[[score_col]])
    names(vec) <- toupper(trimws(as.character(df[[gene_col]])))
    vec <- vec[!is.na(vec) & nchar(names(vec)) > 0]
    vec <- vec[!duplicated(names(vec))]
    vec[order(-vec)]

  } else if (ext == "rds") {
    res <- readRDS(path)
    if (is.list(res) && !is.null(res$RWRM_Results) && is.data.frame(res$RWRM_Results)) {
      df <- res$RWRM_Results

      gene_col <- if ("NodeNames" %in% colnames(df)) "NodeNames" else
        if ("gene" %in% colnames(df)) "gene" else colnames(df)[1]

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

cat(sprintf("[CHK] gene_list N=%d | unique(abs(weights))=%d\n",
            length(gene_list), length(unique(abs(gene_list)))))
print(summary(abs(gene_list)))

# ---------- 2) Load pathway gmt ----------
cat("[INFO] Loading pathway Rdata ...\n")
load(gmt_rdata)

objs <- ls()
pick <- NULL
for (o in objs) {
  x <- get(o)
  if (is.data.frame(x) && ncol(x) >= 2) {
    cols <- tolower(colnames(x))
    if (any(grepl("pathway", cols)) && any(grepl("^gene$", cols))) {
      pick <- o
      break
    }
  }
}
if (is.null(pick)) {
  for (o in objs) {
    x <- get(o)
    if (is.data.frame(x) && ncol(x) >= 2) {
      pick <- o
      break
    }
  }
}
if (is.null(pick)) stop("No 2-column data.frame (Pathway,Gene) found in Rdata.")

gmt <- get(pick)
colnames(gmt)[1:2] <- c("Pathway", "Gene")
gmt$Pathway <- as.character(gmt$Pathway)
gmt$Gene    <- toupper(trimws(as.character(gmt$Gene)))
gmt <- gmt[nchar(gmt$Gene) > 0, , drop = FALSE]
gmt <- unique(gmt)

sizes <- table(gmt$Pathway)
keep_pw <- names(sizes)[sizes >= min_g & sizes <= max_g]
gmt <- gmt[gmt$Pathway %in% keep_pw, , drop = FALSE]

cat(sprintf("[INFO] Pathways kept after size filter (%d–%d genes): %d\n",
            min_g, max_g, length(unique(gmt$Pathway))))

pathway_list <- split(gmt$Gene, gmt$Pathway)

# ---------- 3) ES + permutation ----------
cat("[INFO] Computing ES and permutation p-values ...\n")
set.seed(12345)

gl_names <- names(gene_list)
N <- length(gl_names)

compute_es_pval <- function(gs, pw_name) {
  gs <- unique(toupper(trimws(gs)))
  tag.ind <- sign(match(gl_names, gs, nomatch = 0))
  hit_n <- sum(tag.ind != 0)

  if (hit_n == 0) return(c(NA_real_, NA_real_, NA_real_))

  ES_obs <- FastSEAscore(labels.list = tag.ind, correl_vector = gene_list)

  perm_ES <- numeric(nperm)
  for (i in seq_len(nperm)) {
    perm_tag <- integer(N)
    perm_tag[sample.int(N, hit_n)] <- 1L
    perm_ES[i] <- FastSEAscore(labels.list = perm_tag, correl_vector = gene_list)
  }

  if (ES_obs >= 0) {
    pval <- (1 + sum(perm_ES >= ES_obs)) / (nperm + 1)
    perm_same_sign <- perm_ES[perm_ES >= 0]
    denom <- mean(perm_same_sign, na.rm = TRUE)
  } else {
    pval <- (1 + sum(perm_ES <= ES_obs)) / (nperm + 1)
    perm_same_sign <- perm_ES[perm_ES < 0]
    denom <- abs(mean(perm_same_sign, na.rm = TRUE))
  }

  NES <- if (!is.na(denom) && is.finite(denom) && denom > 0) {
    ES_obs / denom
  } else {
    NA_real_
  }

  if (nzchar(plot_pathway) && identical(pw_name, plot_pathway)) {
    pw_safe <- gsub("[^A-Za-z0-9_\\-]", "_", pw_name)

    perm_csv <- paste0(plot_prefix, ".", pw_safe, ".perm_ES.csv")
    write.csv(data.frame(perm_ES = perm_ES), perm_csv, row.names = FALSE)

    png_file <- paste0(plot_prefix, ".", pw_safe, ".perm_ES.hist.png")
    png(png_file, width = 1000, height = 700)
    hist(perm_ES, breaks = 60,
         main = paste0("perm_ES distribution (random hits): ", pw_name),
         xlab = "perm_ES", ylab = "count")
    abline(v = ES_obs, lwd = 4)
    legend("topright",
           legend = c(
             paste0("ES_obs=", formatC(ES_obs, digits = 6, format = "f")),
             paste0("NES=", formatC(NES, digits = 6, format = "f")),
             paste0("Hit=", hit_n),
             paste0("p=", formatC(pval, digits = 6, format = "f"))
           ),
           lwd = c(4, NA, NA, NA), bty = "n")
    dev.off()

    cat("[INFO] Saved perm_ES CSV:", normalizePath(perm_csv), "\n")
    cat("[INFO] Saved perm_ES histogram PNG:", normalizePath(png_file), "\n")
  }

  c(ES_obs, NES, pval)
}

# ---------- 4) Size-aware entropy-based support metrics ----------
get_pathway_support_metrics <- function(gs, gene_list, size_scale = 10) {
  gs <- unique(toupper(trimws(gs)))
  pathway_genes <- unique(gs)

  scores <- gene_list[pathway_genes]
  scores[is.na(scores)] <- 0
  scores <- as.numeric(scores)

  m <- length(scores)

  if (m == 0) {
    return(c(
      PathwaySize   = 0,
      MeanHitScore  = NA_real_,
      RMSHitScore   = NA_real_,
      TotalHitScore = NA_real_,
      Top1Score     = NA_real_,
      Dominance     = NA_real_,
      Entropy       = NA_real_,
      EntropyNorm   = NA_real_,
      NonZeroCount  = 0,
      SizeFactor    = NA_real_,
      EntropyWeight = NA_real_,
      SupportScore  = NA_real_
    ))
  }

  mean_score  <- mean(scores)
  rms_score   <- sqrt(mean(scores^2))
  total_score <- sum(scores)
  top1_score  <- max(scores)

  dominance <- if (is.finite(total_score) && total_score > 0) {
    top1_score / total_score
  } else {
    NA_real_
  }

  nonzero_scores <- scores[scores > 0]
  nonzero_count  <- length(nonzero_scores)

  if (length(nonzero_scores) <= 1) {
    entropy <- 0
    entropy_norm <- 0
  } else {
    p <- nonzero_scores / sum(nonzero_scores)
    entropy <- -sum(p * log(p))
    entropy_norm <- entropy / log(length(nonzero_scores))
  }

  # 小 pathway 輕懲罰；大 pathway 完整使用 entropy
  size_factor <- min(m / size_scale, 1)
  entropy_weight <- (1 - size_factor) + size_factor * entropy_norm

  support_score <- rms_score * entropy_weight

  c(
    PathwaySize   = m,
    MeanHitScore  = mean_score,
    RMSHitScore   = rms_score,
    TotalHitScore = total_score,
    Top1Score     = top1_score,
    Dominance     = dominance,
    Entropy       = entropy,
    EntropyNorm   = entropy_norm,
    NonZeroCount  = nonzero_count,
    SizeFactor    = size_factor,
    EntropyWeight = entropy_weight,
    SupportScore  = support_score
  )
}

pw_names <- names(pathway_list)

mat <- t(vapply(pw_names, function(pw) {
  compute_es_pval(pathway_list[[pw]], pw)
}, numeric(3)))
rownames(mat) <- pw_names
colnames(mat) <- c("ES", "NES", "pval")

support_list <- lapply(pw_names, function(pw) {
  get_pathway_support_metrics(
    gs = pathway_list[[pw]],
    gene_list = gene_list,
    size_scale = 10
  )
})

support_mat <- do.call(rbind, support_list)
support_mat <- as.data.frame(support_mat, stringsAsFactors = FALSE)
rownames(support_mat) <- pw_names

overlap <- vapply(pathway_list, function(gs) sum(gl_names %in% unique(gs)), integer(1))
size    <- vapply(pathway_list, function(gs) length(unique(gs)), integer(1))

out <- data.frame(
  Pathway        = pw_names,
  ES             = mat[, "ES"],
  NES            = mat[, "NES"],
  Overlap        = overlap,
  Size           = size,
  pval           = mat[, "pval"],
  MeanHitScore   = support_mat$MeanHitScore,
  RMSHitScore    = support_mat$RMSHitScore,
  TotalHitScore  = support_mat$TotalHitScore,
  Top1Score      = support_mat$Top1Score,
  Dominance      = support_mat$Dominance,
  Entropy        = support_mat$Entropy,
  EntropyNorm    = support_mat$EntropyNorm,
  NonZeroCount   = support_mat$NonZeroCount,
  SizeFactor     = support_mat$SizeFactor,
  EntropyWeight  = support_mat$EntropyWeight,
  SupportScore   = support_mat$SupportScore,
  stringsAsFactors = FALSE
)

# ---------- 5) FDR ----------
ok <- !is.na(out$pval)
out$qval <- NA_real_
out$qval[ok] <- p.adjust(out$pval[ok], method = "BH")

# ---------- 6) Optional descriptive class ----------
out$SupportClass <- ifelse(
  is.na(out$EntropyNorm), "NA",
  ifelse(out$EntropyNorm < 0.3, "Single-gene-like",
         ifelse(out$EntropyNorm < 0.7, "Intermediate", "Distributed"))
)

# ---------- 7) Output ----------
out_by_p <- out[order(out$pval, -out$SupportScore), ]
write.csv(out_by_p, out_csv, row.names = FALSE)
cat("[INFO] Wrote Pathway ES+pval+qval+size-aware entropy support metrics to:", normalizePath(out_csv), "\n")

support_csv <- sub("\\.csv$", ".by_support.csv", out_csv)
if (identical(support_csv, out_csv)) {
  support_csv <- paste0(out_csv, ".by_support.csv")
}
out_by_support <- out[order(-out$SupportScore, out$pval), ]
write.csv(out_by_support, support_csv, row.names = FALSE)
cat("[INFO] Wrote size-aware entropy-support-prioritized pathway table to:", normalizePath(support_csv), "\n")

# ---------- 8) Helpful note if plot_pathway not found ----------
if (nzchar(plot_pathway) && !(plot_pathway %in% pw_names)) {
  cat("[WARN] plot_pathway not found in pathway_list after size filter.\n")
  cat("[WARN] Requested:", plot_pathway, "\n")
  cat("[WARN] Tip: ensure the pathway name matches exactly (case-sensitive).\n")
}

# ---------- 9) Console summary ----------
cat("\n[INFO] Parameters used:\n")
cat("  min_g =", min_g, "\n")
cat("  max_g =", max_g, "\n")
cat("  nperm =", nperm, "\n")

cat("\n[INFO] Top 10 by p-value:\n")
print(utils::head(out_by_p[, c(
  "Pathway", "ES", "NES", "pval", "qval",
  "SupportScore", "RMSHitScore", "EntropyNorm", "EntropyWeight",
  "Dominance", "Size", "SizeFactor", "SupportClass"
)], 10))

cat("\n[INFO] Top 10 by SupportScore:\n")
print(utils::head(out_by_support[, c(
  "Pathway", "ES", "NES", "pval", "qval",
  "SupportScore", "RMSHitScore", "EntropyNorm", "EntropyWeight",
  "Dominance", "Size", "SizeFactor", "SupportClass"
)], 10))
#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 1) {
  stop("Usage: Rscript inspect_res.R MRWR_result.rds [out_dir]", call. = FALSE)
}
rds_path <- args[1]
out_dir  <- ifelse(length(args) >= 2, args[2], dirname(rds_path))
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

outfile <- file.path(out_dir, "debug_res_structure.txt")

cat(sprintf("Reading RDS: %s\n", rds_path))
res <- readRDS(rds_path)

sink(outfile)
cat("===== class(res) =====\n")
print(class(res))

cat("\n===== names(res) =====\n")
print(names(res))

cat("\n===== slotNames(res) (if S4) =====\n")
if (methods::is(res, "S4")) {
  print(methods::slotNames(res))
} else {
  cat("Not an S4 object.\n")
}

cat("\n===== str(res, max.level=2) =====\n")
str(res, max.level = 2)

cat("\n===== head(res) =====\n")
suppressWarnings(print(utils::head(res)))
sink()

cat(sprintf("Done. Structure written to: %s\n", outfile))

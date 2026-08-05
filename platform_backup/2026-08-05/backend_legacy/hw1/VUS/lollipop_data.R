# ============================================================
# lollipop_data.R  ── 產出 lollipopPlot 所需資料 (無繪圖)
# 新增：依 isoform (Protein_ID) 分群輸出
# 相容舊版 maftools：自帶 get_vcColors / get_domain_cols fallback
# ============================================================

suppressPackageStartupMessages({
  library(maftools)
  library(data.table)
})

# ---------- 1. variant class 顏色 ------------------------------------------
.default_vc_colors <- function(alpha = 0.7) {
  raw <- c(
    "Frame_Shift_Del"   = "#e41a1c",
    "Frame_Shift_Ins"   = "#e41a1c",
    "Nonsense_Mutation" = "#377eb8",
    "Nonstop_Mutation"  = "#984ea3",
    "Splice_Site"       = "#ff7f00",
    "Missense_Mutation" = "#4daf4a",
    "In_Frame_Del"      = "#ffff33",
    "In_Frame_Ins"      = "#a65628",
    "Silent"            = "#999999"
  )
  grDevices::adjustcolor(raw, alpha.f = alpha)
}

get_vc_cols_safe <- function(alpha = 0.7, named = TRUE) {
  if (exists("get_vcColors", envir = asNamespace("maftools"), inherits = FALSE)) {
    colfun <- get("get_vcColors", envir = asNamespace("maftools"))
    return(colfun(alpha = alpha, named = named))
  }
  cols <- .default_vc_colors(alpha)
  if (!named) unname(cols) else cols
}

# ---------- 2. domain 顏色 -------------------------------------------------
.default_domain_cols <- function() {
  # 12 亮色 (Set3 調色盤)
  c("#8dd3c7", "#ffffb3", "#bebada", "#fb8072",
    "#80b1d3", "#fdb462", "#b3de69", "#fccde5",
    "#d9d9d9", "#bc80bd", "#ccebc5", "#ffed6f")
}

get_domain_cols_safe <- function() {
  if (exists("get_domain_cols", envir = asNamespace("maftools"), inherits = FALSE)) {
    return(get("get_domain_cols", envir = asNamespace("maftools"))())
  }
  .default_domain_cols()
}

# ============================================================
# 主函式：單一 isoform 的資料產生（你原本的核心）
# ============================================================
lollipopPlotData <- function(
  maf, gene,
  AACol = NULL, labelPos = NULL,
  showMutationRate = TRUE, cBioPortal = FALSE,
  refSeqID = NULL, proteinID = NULL,
  repel = FALSE, collapsePosLabel = TRUE,
  defaultYaxis = FALSE, labelOnlyUniqueDoamins = TRUE,
  colors = NULL, domainAlpha = 1, domainBorderCol = "black",
  clusterSize = 10
) {

  if (missing(gene) || is.null(gene))
    stop("請提供 gene 參數。")
  geneID <- gene

  # --------- 讀蛋白質結構 --------------------------------------------
  gff_path <- system.file("extdata", "protein_domains.RDs", package = "maftools")
  prot <- readRDS(gff_path)
  prot <- data.table::as.data.table(prot)

  # --------- 擷取變異 ---------------------------------------------------
  mut <- subsetMaf(maf, includeSyn = FALSE, genes = geneID,
                   query = "Variant_Type != 'CNV'", mafObj = FALSE)

  if (!nrow(mut))
    stop(sprintf("MAF 中找不到基因 %s 的突變紀錄。", geneID))

  # 確認 AA 欄位
  if (is.null(AACol)) {
    cand <- c("HGVSp_Short", "Protein_Change", "AAChange")
    hit  <- cand[cand %in% names(mut)][1]
    if (is.na(hit))
      stop("AAChange 欄位找不到，請用 AACol 指定。")
    setnames(mut, hit, "AAChange_")
  } else {
    if (!AACol %in% names(mut))
      stop(sprintf("Column %s 不存在於 MAF。", AACol))
    setnames(mut, AACol, "AAChange_")
  }

  # --------- domain 選擇 ----------------------------------------------
  prot <- prot[HGNC %in% geneID]
  if (!nrow(prot))
    stop(sprintf("找不到 %s 的蛋白質結構資訊。", geneID))

strip_version <- function(x) sub("\\.\\d+$", "", x)

if (!is.null(refSeqID)) {
  # 先精準比對（含版本）
  prot0 <- prot[refseq.ID == refSeqID]

  if (!nrow(prot0)) {
    # 再嘗試忽略版本比對
    want <- strip_version(refSeqID)
    prot0 <- prot[strip_version(refseq.ID) == want]
  }

  if (!nrow(prot0)) {
    # 最後 fallback：選最長 isoform（或你也可以選最常出現的那個）
    prot0 <- prot[aa.length == max(aa.length)]
  }

  prot <- prot0
} else if (!is.null(proteinID)) {
  prot0 <- prot[protein.ID == proteinID]
  if (!nrow(prot0)) prot0 <- prot[aa.length == max(aa.length)]
  prot <- prot0
} else {
  prot <- prot[aa.length == max(aa.length)]
}

  len <- max(prot$aa.length, na.rm = TRUE)

  # --------- variant colors -------------------------------------------
  if (cBioPortal) {
    vc_map <- c(
      "Nonstop_Mutation" = "Truncating", "Frame_Shift_Del" = "Truncating",
      "Missense_Mutation" = "Missense", "Nonsense_Mutation" = "Truncating",
      "Splice_Site"       = "Truncating", "Frame_Shift_Ins" = "Truncating",
      "In_Frame_Del"      = "In-frame", "In_Frame_Ins" = "In-frame"
    )
    col_map <- c("Truncating" = "black",
                 "Missense"   = "#33A02C",
                 `In-frame`   = "brown")
  } else {
    col_map <- if (is.null(colors)) get_vc_cols_safe(alpha = 0.7) else colors
  }

  # --------- 解析 AA 位置 ----------------------------------------------
  prot.dat <- mut[Hugo_Symbol %in% geneID,
                  .(Variant_Type, Variant_Classification, AAChange_)]
  conv <- sapply(strsplit(prot.dat$AAChange_, "\\."), tail, 1L)

  # 把第一段連續數字抽出來，不管前面有沒有字母
  pos  <- as.numeric(sub(".*?(\\d+).*", "\\1", conv, perl = TRUE))
  pos[!grepl("\\d+", conv)] <- NA

  prot.dat[, `:=`(conv = conv, pos = pos)]
  prot.dat <- prot.dat[!is.na(pos)]

  if (!nrow(prot.dat))
    stop("變異欄位解析不到任何胺基酸位置，請確認 AACol 格式。")

  # --------- 彙總點資料 -----------------------------------------------
  mutSummary <- prot.dat[, .N, .(Variant_Classification, conv, pos)]
  setnames(mutSummary, "N", "count")

  if (!nrow(mutSummary))
    stop("mutSummary 為空，無資料可繪。")

  if (max(mutSummary$count) <= 5) {
    mutSummary[, count2 := 1 + count]
    lim.pos <- 2:6; lim.lab <- 1:5
  } else {
    mutSummary[, count2 := 1 + (count * (5 / max(count)))]
    lim.pos <- unique(mutSummary$count2)
    lim.lab <- unique(mutSummary$count)
  }
  if (!defaultYaxis) {
    lim.pos <- range(lim.pos); lim.lab <- range(lim.lab)
  }

  if (repel) {
    mutSummary <- repelPoints(dat = mutSummary, protLen = len, clustSize = clusterSize)
  } else {
    mutSummary[, pos2 := pos]
  }
  mutSummary[, point_col := col_map[as.character(Variant_Classification)]]

  # --------- domain colors --------------------------------------------
  domain_cols <- get_domain_cols_safe()
  domains <- unique(prot$Label)
  if (length(domains) > length(domain_cols))
    domain_cols <- grDevices::rainbow(length(domains))
  domain_cols <- grDevices::adjustcolor(domain_cols[seq_along(domains)],
                                        alpha.f = domainAlpha)
  names(domain_cols) <- domains
  prot[, domainCol := domain_cols[Label]]

  # --------- labelPos 處理 --------------------------------------------
  labDat <- NULL
  if (!is.null(labelPos)) {
    labDat <- if (length(labelPos) == 1 && labelPos != "all") {
      mutSummary[pos %in% labelPos]
    } else {
      mutSummary[pos %in% labelPos]
    }
    if (!nrow(labDat))
      stop("labelPos 指定的位置沒有突變。")
    if (collapsePosLabel) {
      labDat <- labDat[, .(count2 = max(count2),
                           conv   = paste(conv, collapse = "/")),
                       keyby = pos2]
    }
  }

  # --------- meta ------------------------------------------------------
  sampleSize <- maf@summary[ID == "Samples", summary]
  mutRate    <- round(getGeneSummary(maf)[Hugo_Symbol == geneID, MutatedSamples] /
                        sampleSize * 100, 2)

  subTitle   <- if (showMutationRate)
    bquote(italic(.(geneID))~": [Somatic Mutation Rate:"~.(mutRate)~"%]")
  else geneID

  xlimPos <- { v <- pretty(c(0, len)); v[length(v)] <- len; v }

  # --------- 回傳 -----------------------------------------------------
  list(
    mutSummary = mutSummary[],
    domainDF   = prot[],
    axisInfo   = list(x = xlimPos, yPos = lim.pos, yLab = lim.lab),
    colors     = list(variantColors = col_map, domainColors = domain_cols),
    titleInfo  = list(
      subTitle = subTitle,
      refseqID  = unique(prot$refseq.ID),
      proteinID = unique(prot$protein.ID),
      mutationRate = mutRate
    ),
    labDat     = labDat,
    protLen    = len
  )
}

# ============================================================
# NEW：依 isoform (Protein_ID) 分群計算
# ============================================================

.pick_isoform_col <- function(maf_dt) {
  if ("Protein_ID" %in% colnames(maf_dt)) return("Protein_ID")
  if ("RefSeq_Protein" %in% colnames(maf_dt)) return("RefSeq_Protein")
  return(NULL)
}

.norm_isoform_id <- function(x) {
  x <- as.character(x)
  x[is.na(x) | x == "" | x %in% c("-", "NA", "N/A", "None")] <- NA
  x
}

lollipopPlotDataByIsoform <- function(
  maf, gene,
  AACol = NULL,
  isoform_col = NULL,
  min_mutations_per_isoform = 1,
  showMutationRate = TRUE,
  cBioPortal = FALSE,
  repel = FALSE,
  collapsePosLabel = TRUE,
  defaultYaxis = FALSE,
  labelOnlyUniqueDoamins = TRUE,
  colors = NULL,
  domainAlpha = 1,
  domainBorderCol = "black",
  clusterSize = 10
) {
  # 抓 gene 的突變（mafObj=FALSE，會回 data.frame）
  mut <- subsetMaf(maf, includeSyn = FALSE, genes = gene,
                   query = "Variant_Type != 'CNV'", mafObj = FALSE)
  if (!nrow(mut))
    stop(sprintf("MAF 中找不到基因 %s 的突變紀錄。", gene))

  if (is.null(isoform_col)) isoform_col <- .pick_isoform_col(mut)

  # 沒 isoform 欄位 → 退回單一策略
  if (is.null(isoform_col)) {
    one <- lollipopPlotData(
      maf = maf, gene = gene,
      AACol = AACol,
      showMutationRate = showMutationRate,
      cBioPortal = cBioPortal,
      repel = repel,
      collapsePosLabel = collapsePosLabel,
      defaultYaxis = defaultYaxis,
      labelOnlyUniqueDoamins = labelOnlyUniqueDoamins,
      colors = colors,
      domainAlpha = domainAlpha,
      domainBorderCol = domainBorderCol,
      clusterSize = clusterSize
    )
    one$isoformID  <- NA_character_
    one$isoformCol <- NA_character_
    one$nMutations <- nrow(mut)
    return(list(one))
  }

  mut[[isoform_col]] <- .norm_isoform_id(mut[[isoform_col]])
  mut$.__isoform_group__ <- ifelse(is.na(mut[[isoform_col]]), "UNKNOWN", mut[[isoform_col]])
  groups <- split(mut, mut$.__isoform_group__)

  out_list <- list()

  for (iso_id in names(groups)) {
    gdt <- groups[[iso_id]]
    if (nrow(gdt) < min_mutations_per_isoform) next

    # 用這個 isoform 的突變建 mafObj
    maf_sub <- maftools::read.maf(maf = gdt)

    # iso_id 判斷：NP/XP/YP → refSeqID，其餘 → proteinID
    refSeqID  <- NULL
    proteinID <- NULL
    if (iso_id != "UNKNOWN") {
      if (grepl("^(NP|XP|YP)_[0-9]+(\\.[0-9]+)?$", iso_id)) {
        refSeqID <- iso_id
      } else {
        proteinID <- iso_id
      }
    }

    # 跑核心（指定 isoform，避免選最長 aa.length）
    one <- lollipopPlotData(
      maf = maf_sub, gene = gene,
      AACol = AACol,
      showMutationRate = showMutationRate,
      cBioPortal = cBioPortal,
      refSeqID = refSeqID,
      proteinID = proteinID,
      repel = repel,
      collapsePosLabel = collapsePosLabel,
      defaultYaxis = defaultYaxis,
      labelOnlyUniqueDoamins = labelOnlyUniqueDoamins,
      colors = colors,
      domainAlpha = domainAlpha,
      domainBorderCol = domainBorderCol,
      clusterSize = clusterSize
    )

    one$isoformID  <- iso_id
    one$isoformCol <- isoform_col
    one$nMutations <- nrow(gdt)

    out_list[[iso_id]] <- one
  }

  # 全部失敗（isoform 都不在 domain DB）→ 退回單一策略
  if (length(out_list) == 0) {
    one <- lollipopPlotData(
      maf = maf, gene = gene,
      AACol = AACol,
      showMutationRate = showMutationRate,
      cBioPortal = cBioPortal,
      repel = repel,
      collapsePosLabel = collapsePosLabel,
      defaultYaxis = defaultYaxis,
      labelOnlyUniqueDoamins = labelOnlyUniqueDoamins,
      colors = colors,
      domainAlpha = domainAlpha,
      domainBorderCol = domainBorderCol,
      clusterSize = clusterSize
    )
    one$isoformID  <- NA_character_
    one$isoformCol <- isoform_col
    one$nMutations <- nrow(mut)
    return(list(one))
  }

  out_list
}
# --------------------------- END OF FILE -----------------------------------

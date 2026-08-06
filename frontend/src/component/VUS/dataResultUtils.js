import React from "react";
import { Box, Button } from "@mui/material";

export const DETAIL_FIELDS_PER_PAGE = 8;

export const DETAIL_FIELD_GROUPS = {
  "Basic Identifiers": [
    "End",
    "Location",
    "avsnp150",
    "Existing_variation",
    "#Uploaded_variation",
    "VARIANT_CLASS",
    "Allele",
    "mergeidx",
    "GIVEN_REF",
    "USED_REF",
  ],

  "Gene & Transcript Details": [
    "Gene",
    "SYMBOL",
    "HGNC_ID",
    "BIOTYPE",
    "SYMBOL_SOURCE",
    "GeneDetail.refGene",
    "Func.refGene",
    "ExonicFunc.refGene",
    "IMPACT",
    "CANONICAL",
    "REFSEQ_MATCH",
    "REFSEQ_OFFSET",
    "HGVSc",
    "short_HGVSp",
    "AAChange.refGene",
    "Amino_acids",
    "Codons",
    "EXON",
    "INTRON",
    "cDNA_position",
    "CDS_position",
    "Protein_position",
    "DISTANCE",
    "STRAND",
    "Feature",
    "Feature_type",
    "HGVS_OFFSET",
    "enasmbl_HGVSp",
    "Protein_Change",
    "HGVSp",
  ],

  "Population Frequency": [
    "AF",
    "AF_raw",
    "AF_male",
    "AF_female",
    "AF_eas",
    "AF_sas",
    "AF_afr",
    "AF_amr",
    "AF_nfe",
    "AF_fin",
    "AF_asj",
    "AF_oth",
    "1000g2015aug_all",
    "AF_popmax",
    "non_topmed_AF_popmax",
    "non_neuro_AF_popmax",
    "non_cancer_AF_popmax",
    "controls_AF_popmax",
    "TaiwanBioBank",
  ],

  "Clinical & Disease Databases": [
    "CLNDN",
    "CLNALLELEID",
    "CLNDISDB",
    "CLNREVSTAT",
    "ClinGen_annotation",
    "CIVIC_annotation",
    "cosmic90_coding",
    "LOVD_all_clinical",
    "diagnosis",
    "OCP_ver2",
  ],

  "In-silico Pathogenicity": [
    "CADD_phred",
    "SIFT_score",
    "SIFT_pred",
    "Polyphen2_HDIV_score",
    "Polyphen2_HDIV_pred",
    "Polyphen2_HVAR_score",
    "Polyphen2_HVAR_pred",
    "LRT_score",
    "LRT_pred",
    "MutationTaster_score",
    "MutationTaster_pred",
    "MutationAssessor_score",
    "MutationAssessor_pred",
    "FATHMM_score",
    "FATHMM_pred",
    "PROVEAN_score",
    "PROVEAN_pred",
    "VEST3_score",
    "MetaSVM_score",
    "MetaSVM_pred",
    "MetaLR_score",
    "MetaLR_pred",
    "M-CAP_score",
    "M-CAP_pred",
    "REVEL_score",
    "MutPred_score",
    "CADD_raw",
    "DANN_score",
    "fathmm-MKL_coding_score",
    "fathmm-MKL_coding_pred",
    "Eigen_coding_or_noncoding",
    "Eigen-raw",
    "Eigen-PC-raw",
    "GenoCanyon_score",
    "integrated_fitCons_score",
  ],

  "Conservation": [
    "GERP++_RS",
    "phyloP100way_vertebrate",
    "phyloP20way_mammalian",
    "phastCons100way_vertebrate",
    "phastCons20way_mammalian",
    "SiPhy_29way_logOdds",
  ],

  "Rankscores": [
    "SIFT_converted_rankscore",
    "Polyphen2_HDIV_rankscore",
    "Polyphen2_HVAR_rankscore",
    "LRT_converted_rankscore",
    "MutationTaster_converted_rankscore",
    "MutationAssessor_score_rankscore",
    "FATHMM_converted_rankscore",
    "PROVEAN_converted_rankscore",
    "VEST3_rankscore",
    "MetaSVM_rankscore",
    "MetaLR_rankscore",
    "M-CAP_rankscore",
    "REVEL_rankscore",
    "MutPred_rankscore",
    "CADD_raw_rankscore",
    "DANN_rankscore",
    "fathmm-MKL_coding_rankscore",
    "GenoCanyon_score_rankscore",
    "integrated_fitCons_score_rankscore",
    "GERP++_RS_rankscore",
    "phyloP100way_vertebrate_rankscore",
    "phyloP20way_mammalian_rankscore",
    "phastCons100way_vertebrate_rankscore",
    "phastCons20way_mammalian_rankscore",
    "SiPhy_29way_logOdds_rankscore",
  ],

  "Quality & Metadata": [
    "FAO",
    "DP",
    "BAM_EDIT",
    "GTEx_V6p_gene",
    "GTEx_V6p_tissue",
    "Interpro_domain",
    "integrated_confidence_value",
    "FLAGS",
    "Otherinfo1",
    "Otherinfo2",
    "Otherinfo3",
    "Otherinfo4",
    "Otherinfo5",
    "created_at",
    "updated_at",
    "source_table",
    "job_id",
  ],
};

export function getFieldGroupName(field) {
  for (const [groupName, fields] of Object.entries(DETAIL_FIELD_GROUPS)) {
    if (fields.includes(field)) return groupName;
  }
  return "Other";
}

export function groupFields(fields) {
  const grouped = {};
  fields.forEach((field) => {
    const groupName = getFieldGroupName(field);
    if (!grouped[groupName]) grouped[groupName] = [];
    grouped[groupName].push(field);
  });
  return grouped;
}

function extractAnalysisJobId(sourceTable) {
  if (sourceTable == null) return "";
  const text = String(sourceTable).trim();
  if (!text) return "";

  const parts = text.split("_").filter(Boolean);
  if (parts.length === 0) return "";

  return parts[parts.length - 1];
}

export function buildRows(currentData) {
  if (!currentData?.full_results) return [];

  return currentData.full_results.map((row, idx) => {
    const updatedRow = { ...row };

    if (!isNaN(updatedRow.Start)) updatedRow.Start = parseInt(updatedRow.Start, 10);
    if (!isNaN(updatedRow.End)) updatedRow.End = parseInt(updatedRow.End, 10);

    const analysisJobId = extractAnalysisJobId(updatedRow.source_table);

    return {
      id: idx,
      job_id: analysisJobId,
      ...updatedRow,
    };
  });
}

export function getAllFields(rows) {
  if (!rows.length) return [];
  return Object.keys(rows[0]).filter((k) => k !== "id");
}

export function getSummaryFields(allFields) {
  const preferred = [
    "diagnosis",
    "Gene.refGene",
    "Chr",
    "Start",
    "Ref",
    "Alt",
    "standard_HGVSp",
    "Consequence",
    "CLNSIG",
    "VAF",
  ];

  const fallbackMap = {
    SYMBOL: ["SYMBOL", "Gene.refGene", "Gene", "SYMBOL_SOURCE"],
    Chr: ["Chr", "CHROM", "#CHROM"],
    Start: ["Start", "POS"],
    Ref: ["Ref", "REF"],
    Alt: ["Alt", "ALT"],
    HGVSp: ["HGVSp", "short_HGVSp", "AAChange.refGene"],
    Consequence: ["Consequence", "ExonicFunc.refGene", "Func.refGene"],
    CLNSIG: ["CLNSIG", "ClinVar_CLNSIG", "LOVD_all_clinical"],
    AF_popmax: ["AF_popmax", "controls_AF_popmax", "non_topmed_AF_popmax"],
    CADD_phred: ["CADD_phred"],
    VAF: ["VAF", "AF_VAF", "TumorVAF"],
    DP: ["DP", "Depth", "ReadDepth"],
  };

  const resolved = preferred
    .map((label) => {
      const candidates = fallbackMap[label] || [label];
      return candidates.find((f) => allFields.includes(f));
    })
    .filter(Boolean);

  return resolved.length > 0 ? Array.from(new Set(resolved)) : allFields.slice(0, 11);
}

export function getDefaultDetailFields(allFields, summaryFields) {
  return allFields.filter((f) => !summaryFields.includes(f));
}

export function getSelectableDetailFields(allFields, summaryFields) {
  return allFields.filter((field) => !summaryFields.includes(field));
}

export function getFilteredSelectableDetailFields(selectableDetailFields, fieldSearch) {
  const keyword = fieldSearch.trim().toLowerCase();
  if (!keyword) return selectableDetailFields;
  return selectableDetailFields.filter((field) =>
    field.toLowerCase().includes(keyword)
  );
}

export function getSelectedFieldCountSummary(detailFields) {
  const grouped = groupFields(detailFields);
  const parts = Object.entries(grouped).map(
    ([groupName, fields]) => `${groupName} ${fields.length}`
  );
  return parts.join(" | ");
}

export function getDetailDialogPagedFields(detailFields, detailDialogPage) {
  const totalPages = Math.max(1, Math.ceil(detailFields.length / DETAIL_FIELDS_PER_PAGE));
  const currentPage = Math.min(detailDialogPage, totalPages);
  const start = (currentPage - 1) * DETAIL_FIELDS_PER_PAGE;
  const end = start + DETAIL_FIELDS_PER_PAGE;

  return {
    currentPage,
    totalPages,
    fields: detailFields.slice(start, end),
  };
}

export function getColumnConfig(field) {
  if (field === "diagnosis") {
    return { minWidth: 180, width: 220, flex: 1 };
  }
  if (field === "HGVSp") {
    return { minWidth: 180, width: 220, flex: 1 };
  }
  if (field === "Consequence") {
    return { minWidth: 160, width: 190, flex: 1 };
  }
  if (field === "CLNSIG") {
    return { minWidth: 120, width: 140 };
  }
  if (["Chr", "CHROM", "#CHROM", "Start", "POS", "VAF", "DP"].includes(field)) {
    return { minWidth: 100, width: 110 };
  }
  if (["Ref", "REF", "Alt", "ALT"].includes(field)) {
    return { minWidth: 160, width: 190 };
  }
  return { minWidth: 120, width: 150 };
}

export function createDataGridColumns(summaryFields, openRowDetailDialog) {
  const cols = summaryFields.map((field) => {
    const columnConfig = getColumnConfig(field);

    return {
      field,
      headerName: field,
      minWidth: columnConfig.minWidth,
      width: columnConfig.width,
      flex: columnConfig.flex,
      sortable: false,
      renderCell: (params) => {
        const value = params.row[field];
        const isLongSequenceField = ["Ref", "REF", "Alt", "ALT"].includes(field);

        return (
          <Box
            sx={{
              py: 1,
              width: "100%",
              lineHeight: 1.4,
              whiteSpace: "normal",
              wordBreak: isLongSequenceField ? "break-all" : "break-word",
              overflowWrap: "anywhere",
              display: "flex",
              alignItems: "flex-start",
            }}
          >
            {value == null || value === "" ? "-" : String(value)}
          </Box>
        );
      },
    };
  });

  cols.push({
    field: "__detail__",
    headerName: "Variant Details",
    width: 110,
    minWidth: 110,
    sortable: false,
    filterable: false,
    disableColumnMenu: true,
    renderCell: (params) => (
      <Box
        sx={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Button
          variant="outlined"
          size="small"
          onClick={() => openRowDetailDialog(params.row)}
        >
          View
        </Button>
      </Box>
    ),
  });

  cols.push({
    field: "__analysis__",
    headerName: "Analysis Result",
    width: 150,
    minWidth: 150,
    sortable: false,
    filterable: false,
    disableColumnMenu: true,
    renderCell: (params) => {
      const analysisJobId = params.row.job_id;
      const targetUrl = analysisJobId
        ? `/variant/Job_results/detail_somatic/${analysisJobId}`
        : null;

      return (
        <Box
          sx={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Button
            variant="outlined"
            size="small"
            disabled={!targetUrl}
            onClick={() => {
              if (!targetUrl) return;
              window.open(targetUrl, "_blank");
            }}
          >
            Detail
          </Button>
        </Box>
      );
    },
  });

  return cols;
}
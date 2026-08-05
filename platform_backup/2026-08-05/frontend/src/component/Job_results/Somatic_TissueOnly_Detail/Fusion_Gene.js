import React, { useState, useEffect, useRef, useMemo } from "react";
import axios from "axios";
import { DataGrid } from "@mui/x-data-grid";
import {
  Box,
  Typography,
  Chip,
  Paper,
  Stack,
  Divider,
  Alert,
  CircularProgress,
  Tooltip,
} from "@mui/material";
import { config } from "../../../constant";

import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
GlobalWorkerOptions.workerSrc = process.env.PUBLIC_URL + "/pdf.worker.mjs";

const PDFPage = ({ pdf, pageNumber, scale = 1.7 }) => {
  const canvasRef = useRef(null);

  useEffect(() => {
    const renderPage = async () => {
      try {
        const page = await pdf.getPage(pageNumber);
        const canvas = canvasRef.current;

        if (!canvas) return;

        const context = canvas.getContext("2d");
        const viewport = page.getViewport({ scale });

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        await page.render(renderContext).promise;
      } catch (err) {
        console.error(`Error rendering page ${pageNumber}:`, err);
      }
    };

    if (pdf && pageNumber) {
      renderPage();
    }
  }, [pdf, pageNumber, scale]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        border: "3px solid #ccc",
        marginBottom: "20px",
        maxWidth: "100%",
      }}
    />
  );
};

const CANCER_TYPE_LABELS = {
  ACC: "Adrenocortical carcinoma",
  BLCA: "Bladder cancer",
  BRCA: "Breast cancer",
  CESC: "Cervical cancer",
  CHOL: "Cholangiocarcinoma",
  COAD: "Colon adenocarcinoma",
  DLBC: "Diffuse large B-cell lymphoma",
  ESCA: "Esophageal carcinoma",
  GBM: "Glioblastoma",
  HNSC: "Head and neck squamous cell carcinoma",
  KICH: "Kidney chromophobe",
  KIRC: "Kidney renal clear cell carcinoma",
  KIRP: "Kidney renal papillary cell carcinoma",
  LAML: "Acute myeloid leukemia",
  LGG: "Lower-grade glioma",
  LIHC: "Liver hepatocellular carcinoma",
  LUAD: "Lung adenocarcinoma",
  LUSC: "Lung squamous cell carcinoma",
  MESO: "Mesothelioma",
  OV: "Ovarian cancer",
  PAAD: "Pancreatic adenocarcinoma",
  PCPG: "Pheochromocytoma and paraganglioma",
  PRAD: "Prostate adenocarcinoma",
  READ: "Rectum adenocarcinoma",
  SARC: "Sarcoma",
  SKCM: "Skin cutaneous melanoma",
  STAD: "Stomach adenocarcinoma",
  TGCT: "Testicular germ cell tumor",
  THCA: "Thyroid carcinoma",
  THYM: "Thymoma",
  UCEC: "Endometrial carcinoma",
  UCS: "Uterine carcinosarcoma",
  UVM: "Uveal melanoma",
};

const safeValue = (value) => {
  if (
    value === undefined ||
    value === null ||
    value === "" ||
    value === "." ||
    value === "nan" ||
    value === "None"
  ) {
    return "-";
  }

  return String(value);
};

const normalizeRowKeys = (row) => {
  const normalized = {};

  Object.entries(row || {}).forEach(([key, value]) => {
    const cleanKey = String(key).trim().replace(/\r/g, "");
    normalized[cleanKey] = value;
  });

  return normalized;
};

const getField = (row, fieldName) => {
  if (!row) return "-";

  if (row[fieldName] !== undefined) {
    return row[fieldName];
  }

  const matchedKey = Object.keys(row).find(
    (key) => key.trim().replace(/\r/g, "") === fieldName
  );

  if (matchedKey) {
    return row[matchedKey];
  }

  return "-";
};

const getDisplayFusionName = (row) => {
  if (!row) return "-";

  if (
    getField(row, "detected_fusion") &&
    getField(row, "detected_fusion") !== "-"
  ) {
    return getField(row, "detected_fusion");
  }

  if (
    getField(row, "fusion_gene_name") &&
    getField(row, "fusion_gene_name") !== "-"
  ) {
    return getField(row, "fusion_gene_name");
  }

  if (row["Fusion Name"] && row["Fusion Name"] !== "-") {
    return row["Fusion Name"];
  }

  const gene1 = row["#gene1"] || row.gene1 || "-";
  const gene2 = row.gene2 || "-";

  if (gene1 !== "-" || gene2 !== "-") {
    return `${gene1}--${gene2}`;
  }

  return "-";
};

const parseCancerTypes = (value) => {
  if (!value || value === "." || value === "-") {
    return [];
  }

  return String(value)
    .split(";")
    .map((item) => item.trim())
    .filter((item) => item && item !== "." && item !== "-")
    .map((item) => CANCER_TYPE_LABELS[item] || item)
    .filter((item, index, array) => array.indexOf(item) === index);
};

const formatCancerTypes = (value) => {
  const cancerTypes = parseCancerTypes(value);

  if (cancerTypes.length === 0) {
    return "-";
  }

  return cancerTypes.join(", ");
};

const getOrfColor = (value) => {
  if (value === "In-frame" || value === "Matched") return "success";
  if (value === "Frame-shift") return "warning";

  if (
    value === "5CDS-intron" ||
    value === "5CDS-5UTR" ||
    value === "5UTR-5UTR"
  ) {
    return "info";
  }

  return "default";
};

const InfoItem = ({ label, value, multiline = false }) => (
  <Box>
    <Typography
      variant="caption"
      sx={{
        color: "text.secondary",
        fontWeight: 600,
        letterSpacing: 0.2,
      }}
    >
      {label}
    </Typography>

    <Typography
      variant="body2"
      sx={{
        mt: 0.3,
        wordBreak: "break-word",
        color: "text.primary",
        whiteSpace: multiline ? "pre-line" : "normal",
      }}
    >
      {safeValue(value)}
    </Typography>
  </Box>
);

const SummaryCard = ({ title, value, subtitle }) => (
  <Paper
    elevation={0}
    sx={{
      p: 2,
      borderRadius: 3,
      border: "1px solid #e5e7eb",
      background:
        "linear-gradient(180deg, rgba(248,250,252,1) 0%, rgba(255,255,255,1) 100%)",
      minHeight: 110,
    }}
  >
    <Typography variant="body2" sx={{ color: "text.secondary", mb: 0.7 }}>
      {title}
    </Typography>

    <Typography variant="h4" sx={{ fontWeight: 800, lineHeight: 1.1 }}>
      {value}
    </Typography>

    {subtitle && (
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        {subtitle}
      </Typography>
    )}
  </Paper>
);

const Fusion_gene = () => {
  const [pdfBase64, setPdfBase64] = useState("");
  const [pdfDoc, setPdfDoc] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [tsvData, setTsvData] = useState([]);
  const [columns, setColumns] = useState([]);
  const [selectedFusion, setSelectedFusion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const rowHeight = 58;
  const headerHeight = 54;
  const visibleRowCount = Math.min(tsvData.length || 0, 10);

  const gridHeight = Math.min(
    Math.max(visibleRowCount * rowHeight + headerHeight + 72, 330),
    720
  );

  const summary = useMemo(() => {
    const total = tsvData.length;

    const orfResultCount = tsvData.filter((row) => {
      return safeValue(getField(row, "orf_analysis_result")) !== "-";
    }).length;

    return {
      total,
      orfResultCount,
    };
  }, [tsvData]);

  const selectedPdfPageNumber =
    selectedFusion && Number.isInteger(Number(selectedFusion.id))
      ? Number(selectedFusion.id) + 1
      : null;

  const hasSelectedPdfPage =
    pdfDoc &&
    selectedPdfPageNumber !== null &&
    selectedPdfPageNumber >= 1 &&
    selectedPdfPageNumber <= numPages;

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);

      try {
        const response = await axios.post(`${config.rootApiIP}/fusion_gene`, {
          newjobid: window.location.pathname.split("/").pop(),
        });

        const rawData = response.data.tsv_data || [];

        const dataWithId = rawData.map((originalRow, idx) => {
          const row = normalizeRowKeys(originalRow);
          const detectedFusion = getDisplayFusionName(row);

          return {
            id: idx,
            ...row,
            detected_fusion: detectedFusion,
            breakpoint_summary: `${safeValue(
              getField(row, "breakpoint1")
            )} / ${safeValue(getField(row, "breakpoint2"))}`,
            read_support_summary: `SR ${safeValue(
              getField(row, "split_reads1")
            )}/${safeValue(getField(row, "split_reads2"))} · DM ${safeValue(
              getField(row, "discordant_mates")
            )}`,
          };
        });

        const professionalColumns = [
          {
            field: "detected_fusion",
            headerName: "Fusion Event",
            flex: 1.15,
            minWidth: 230,
            renderCell: (params) => {
              const svType = safeValue(getField(params.row, "type"));

              return (
                <Stack
                  justifyContent="center"
                  sx={{
                    height: "100%",
                    minWidth: 0,
                    overflow: "hidden",
                  }}
                >
                  <Tooltip title={safeValue(params.value)}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 800,
                        color: "#111827",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        lineHeight: 1.35,
                      }}
                    >
                      {safeValue(params.value)}
                    </Typography>
                  </Tooltip>

                  {svType !== "-" && (
                    <Typography
                      variant="caption"
                      sx={{
                        color: "#6b7280",
                        lineHeight: 1.35,
                        textTransform: "capitalize",
                      }}
                    >
                      {svType}
                    </Typography>
                  )}
                </Stack>
              );
            },
          },
          {
            field: "breakpoint_summary",
            headerName: "Breakpoints",
            flex: 1.55,
            minWidth: 360,
            renderCell: (params) => {
              const breakpoint1 = safeValue(getField(params.row, "breakpoint1"));
              const breakpoint2 = safeValue(getField(params.row, "breakpoint2"));

              return (
                <Tooltip title={`${breakpoint1} / ${breakpoint2}`}>
                  <Stack
                    direction="row"
                    spacing={1}
                    alignItems="center"
                    sx={{
                      height: "100%",
                      width: "100%",
                      minWidth: 0,
                      overflow: "hidden",
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: "monospace",
                        fontWeight: 600,
                        color: "#374151",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {breakpoint1}
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{ color: "#94a3b8", fontWeight: 800 }}
                    >
                      /
                    </Typography>

                    <Typography
                      variant="body2"
                      sx={{
                        fontFamily: "monospace",
                        fontWeight: 600,
                        color: "#374151",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {breakpoint2}
                    </Typography>
                  </Stack>
                </Tooltip>
              );
            },
          },
          {
            field: "read_support_summary",
            headerName: "Read Support",
            flex: 0.95,
            minWidth: 220,
            align: "center",
            headerAlign: "center",
            sortable: false,
            renderCell: (params) => {
              const splitReads1 = safeValue(getField(params.row, "split_reads1"));
              const splitReads2 = safeValue(getField(params.row, "split_reads2"));
              const discordantMates = safeValue(
                getField(params.row, "discordant_mates")
              );

              return (
                <Stack
                  direction="row"
                  spacing={0.75}
                  justifyContent="center"
                  alignItems="center"
                  sx={{ height: "100%", width: "100%" }}
                >
                  <Chip
                    label={`SR ${splitReads1}/${splitReads2}`}
                    size="small"
                    variant="outlined"
                    sx={{
                      height: 26,
                      fontWeight: 700,
                      backgroundColor: "#ffffff",
                      borderColor: "#cbd5e1",
                    }}
                  />

                  <Chip
                    label={`DM ${discordantMates}`}
                    size="small"
                    variant="outlined"
                    sx={{
                      height: 26,
                      fontWeight: 700,
                      backgroundColor: "#ffffff",
                      borderColor: "#cbd5e1",
                    }}
                  />
                </Stack>
              );
            },
          },
          {
            field: "orf_analysis_result",
            headerName: "ORF Result",
            flex: 0.9,
            minWidth: 210,
            align: "center",
            headerAlign: "center",
            renderCell: (params) => {
              const value = safeValue(params.value);
              const displayValue = value === "-" ? "Not available" : value;

              return (
                <Chip
                  label={displayValue}
                  size="small"
                  color={getOrfColor(value)}
                  variant={value === "-" ? "outlined" : "filled"}
                  sx={{
                    height: 28,
                    minWidth: 112,
                    fontWeight: 700,
                    justifyContent: "center",
                    "& .MuiChip-label": {
                      px: 1.4,
                    },
                  }}
                />
              );
            },
          },
        ];

        setColumns(professionalColumns);
        setTsvData(dataWithId);
        setSelectedFusion(dataWithId[0] || null);
        setPdfBase64(response.data.pdf_base64 || "");
        setError(null);
      } catch (err) {
        console.error(err);
        setError("Failed to fetch fusion gene data.");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const loadPdf = async () => {
      if (pdfBase64) {
        try {
          const pdfData = atob(pdfBase64);
          const pdf = await getDocument({ data: pdfData }).promise;

          setPdfDoc(pdf);
          setNumPages(pdf.numPages);
        } catch (err) {
          console.error("Error loading PDF:", err);
          setError("Error loading fusion gene PDF.");
        }
      }
    };

    loadPdf();
  }, [pdfBase64]);

  return (
    <Box
      sx={{
        p: 3,
        backgroundColor: "#f8fafc",
        minHeight: "100vh",
      }}
    >
      <Paper
        elevation={0}
        sx={{
          p: 3,
          borderRadius: 4,
          border: "1px solid #e5e7eb",
          backgroundColor: "#ffffff",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", md: "center" }}
          spacing={2}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, mb: 0.5 }}>
              Fusion Gene Prediction
            </Typography>

            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              Detected fusion events from FACTERA with read-support evidence and
              ORF annotation.
            </Typography>

            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              ORF: Open Reading Frame. This page focuses on ORF-related
              annotation and fusion structure visualization.
            </Typography>
          </Box>

          <Chip
            label="FACTERA + ORF"
            color="primary"
            variant="outlined"
            sx={{ fontWeight: 700 }}
          />
        </Stack>

        <Divider sx={{ my: 2 }} />

        {loading && (
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ my: 3 }}>
            <CircularProgress size={22} />
            <Typography variant="body2">Loading fusion gene results...</Typography>
          </Stack>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {!loading && !error && tsvData.length === 0 && (
          <Alert severity="info" sx={{ mb: 2 }}>
            No fusion gene result was detected for this sample.
          </Alert>
        )}

        {tsvData.length > 0 && (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "1fr 1fr",
                  md: "repeat(2, 1fr)",
                },
                gap: 2,
                mb: 3,
              }}
            >
              <SummaryCard
                title="Detected Fusions"
                value={summary.total}
                subtitle="After low-confidence filtering"
              />
              <SummaryCard
                title="With ORF Result"
                value={summary.orfResultCount}
                subtitle="Fusion events with ORF annotation"
              />
            </Box>

            <Typography variant="h6" sx={{ fontWeight: 800, mb: 1 }}>
              Prioritized Fusion Events
            </Typography>

            <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
              Select a row to inspect supporting reads, ORF annotation, and
              structure visualization.
            </Typography>

            <Box sx={{ height: gridHeight, width: "100%", mb: 3 }}>
              <DataGrid
                rows={tsvData}
                columns={columns}
                pageSize={10}
                rowsPerPageOptions={[10, 20, 50]}
                pageSizeOptions={[10, 20, 50]}
                initialState={{
                  pagination: {
                    paginationModel: { pageSize: 10 },
                  },
                }}
                rowHeight={rowHeight}
                columnHeaderHeight={headerHeight}
                disableSelectionOnClick
                disableRowSelectionOnClick
                rowSelection={false}
                hideFooterSelectedRowCount
                onRowClick={(params) => {
                  setSelectedFusion(params.row);
                }}
                sx={{
                  borderRadius: 3,
                  border: "1px solid #e5e7eb",
                  backgroundColor: "#fff",
                  "& .MuiDataGrid-columnHeaders": {
                    backgroundColor: "#f8fafc",
                    color: "#0f172a",
                    fontWeight: 800,
                    borderBottom: "1px solid #e2e8f0",
                  },
                  "& .MuiDataGrid-columnHeader": {
                    outline: "none !important",
                  },
                  "& .MuiDataGrid-columnHeaderTitle": {
                    fontWeight: 800,
                    letterSpacing: 0.1,
                  },
                  "& .MuiDataGrid-row": {
                    cursor: "pointer",
                  },
                  "& .MuiDataGrid-row:nth-of-type(even)": {
                    backgroundColor: "#fbfdff",
                  },
                  "& .MuiDataGrid-row:hover": {
                    backgroundColor: "#eff6ff",
                  },
                  "& .MuiDataGrid-row.Mui-selected": {
                    backgroundColor: "transparent",
                  },
                  "& .MuiDataGrid-row.Mui-selected:hover": {
                    backgroundColor: "#eff6ff",
                  },
                  "& .MuiDataGrid-cell": {
                    display: "flex",
                    alignItems: "center",
                    borderBottom: "1px solid #eef2f7",
                    outline: "none !important",
                  },
                  "& .MuiDataGrid-footerContainer": {
                    minHeight: 48,
                    borderTop: "1px solid #e5e7eb",
                  },
                }}
              />
            </Box>

            {selectedFusion && (
              <Paper
                elevation={0}
                sx={{
                  p: 2.5,
                  borderRadius: 3,
                  border: "1px solid #e5e7eb",
                  backgroundColor: "#fcfcfd",
                  mb: 3,
                }}
              >
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  justifyContent="space-between"
                  alignItems={{ xs: "flex-start", md: "center" }}
                  spacing={1.5}
                  sx={{ mb: 2 }}
                >
                  <Box>
                    <Typography variant="h6" sx={{ fontWeight: 800 }}>
                      {getDisplayFusionName(selectedFusion)}
                    </Typography>

                    <Typography variant="body2" sx={{ color: "text.secondary" }}>
                      Detailed fusion evidence and ORF annotation
                    </Typography>
                  </Box>

                  <Chip
                    label={`ORF Result: ${safeValue(
                      getField(selectedFusion, "orf_analysis_result")
                    )}`}
                    color={getOrfColor(
                      safeValue(getField(selectedFusion, "orf_analysis_result"))
                    )}
                    size="small"
                    variant={
                      safeValue(getField(selectedFusion, "orf_analysis_result")) ===
                      "-"
                        ? "outlined"
                        : "filled"
                    }
                    sx={{ fontWeight: 700 }}
                  />
                </Stack>

                <Divider sx={{ mb: 2 }} />

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      sm: "1fr 1fr",
                      md: "repeat(4, 1fr)",
                    },
                    gap: 2,
                  }}
                >
                  <InfoItem label="SV Type" value={getField(selectedFusion, "type")} />
                  <InfoItem
                    label="Breakpoint 1"
                    value={getField(selectedFusion, "breakpoint1")}
                  />
                  <InfoItem
                    label="Breakpoint 2"
                    value={getField(selectedFusion, "breakpoint2")}
                  />
                  <InfoItem
                    label="Read Support"
                    value={`Split reads ${safeValue(
                      getField(selectedFusion, "split_reads1")
                    )}/${safeValue(
                      getField(selectedFusion, "split_reads2")
                    )}, discordant mates ${safeValue(
                      getField(selectedFusion, "discordant_mates")
                    )}`}
                  />

                  <InfoItem
                    label="ORF Result"
                    value={getField(selectedFusion, "orf_analysis_result")}
                  />
                  <InfoItem
                    label="ORF Cancer Type"
                    value={formatCancerTypes(
                      getField(selectedFusion, "orf_cancer_type")
                    )}
                    multiline
                  />
                  <InfoItem
                    label="ORF Sample ID"
                    value={getField(selectedFusion, "orf_sample_id")}
                  />
                  <InfoItem
                    label="ORF Gene 5'"
                    value={getField(selectedFusion, "orf_gene5p")}
                  />

                  <InfoItem
                    label="ORF Gene 3'"
                    value={getField(selectedFusion, "orf_gene3p")}
                  />
                  <InfoItem
                    label="ORF Breakpoint 5'"
                    value={getField(selectedFusion, "orf_breakpoint5p")}
                  />
                  <InfoItem
                    label="ORF Breakpoint 3'"
                    value={getField(selectedFusion, "orf_breakpoint3p")}
                  />
                </Box>
              </Paper>
            )}
          </>
        )}
      </Paper>

      {pdfDoc && (
        <Paper
          elevation={0}
          sx={{
            mt: 5,
            p: 2.5,
            borderRadius: 3,
            border: "1px solid #e5e7eb",
            backgroundColor: "#ffffff",
          }}
        >
          <Stack
            direction={{ xs: "column", md: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", md: "center" }}
            spacing={1.5}
            sx={{ mb: 2 }}
          >
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 800 }}>
                Fusion Structure Visualization
              </Typography>

              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Visualization of the currently selected fusion event.
              </Typography>
            </Box>

            {selectedFusion && (
              <Chip
                label={`Selected: ${getDisplayFusionName(selectedFusion)}`}
                color="primary"
                variant="outlined"
                sx={{ fontWeight: 700 }}
              />
            )}
          </Stack>

          <Divider sx={{ mb: 2 }} />

          {!selectedFusion && (
            <Alert severity="info">
              Select a fusion event from the table to view its structure
              visualization.
            </Alert>
          )}

          {selectedFusion && !hasSelectedPdfPage && (
            <Alert severity="warning">
              No corresponding visualization page was found for this selected
              fusion.
            </Alert>
          )}

          {hasSelectedPdfPage && (
            <Box>
              <Box sx={{ mb: 1.5 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {getDisplayFusionName(selectedFusion)}
                </Typography>

                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  Page {selectedPdfPageNumber} of {numPages} ·{" "}
                  {safeValue(getField(selectedFusion, "breakpoint1"))} /{" "}
                  {safeValue(getField(selectedFusion, "breakpoint2"))}
                </Typography>
              </Box>

              <PDFPage pdf={pdfDoc} pageNumber={selectedPdfPageNumber} />
            </Box>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default Fusion_gene;

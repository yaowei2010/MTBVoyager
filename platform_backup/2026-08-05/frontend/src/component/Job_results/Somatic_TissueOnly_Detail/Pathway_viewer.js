// src/pages/.../Pathway.jsx
import React, {
  useMemo,
  useState,
  useCallback,
  useEffect,
  useContext,
  useRef,
} from "react";
import axios from "axios";
import { config } from "../../../constant";

import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import CircularProgress from "@mui/material/CircularProgress";
import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";

import { DataGrid } from "@mui/x-data-grid";

import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import TextField from "@mui/material/TextField";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import IconButton from "@mui/material/IconButton";
import ClearIcon from "@mui/icons-material/Clear";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";

import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";

import PathwayViewer from "../../VUS/PathwayContain";
import { AuthContext } from "../../Auth/AuthContext";

const DEFAULT_CANCER_TYPE = "PanCanAtlas";
const FIXED_SOURCE = "csv";

const CANCER_TYPE_DISPLAY_MAP = {
  BCLA: "BLCA",
};

function getCancerTypeDisplayName(cancerType = "") {
  const key = String(cancerType || "");
  return CANCER_TYPE_DISPLAY_MAP[key] || key;
}

function getPathwayDisplayName(pathwayName = "") {
  const s = String(pathwayName || "");
  return s
    .replace(/^BCLA(?=\/)/, "BLCA")
    .replace(/\s*[·\-]?\s*\(?Wprime\)?\s*$/i, "")
    .trim();
}

function splitFolderAndFileBase(raw = "") {
  const s = String(raw || "").trim();
  const parts = s.split(/[/\\]+/).filter(Boolean);
  const folder = parts.length >= 2 ? parts[0] : DEFAULT_CANCER_TYPE;
  const last = parts.length ? parts[parts.length - 1] : s;
  const fileBase = last.replace(/\.json$/i, "");
  return { folder, fileBase };
}

function getCancerTypeFromPathway(nameLike = "", urlLike = "") {
  const candidates = [urlLike, nameLike].map((v) => String(v || ""));

  for (const candidate of candidates) {
    const match = candidate.match(/tcga_pathways_json[/\\]+([^/\\]+)/i);
    if (match?.[1]) return decodeURIComponent(match[1]);
  }

  return splitFolderAndFileBase(nameLike).folder;
}

function buildPublicJsonUrl(nameLike) {
  const { folder, fileBase } = splitFolderAndFileBase(nameLike);
  return `/tcga_pathways_json/${folder}/${fileBase}.json`;
}

function formatP(val) {
  const n = Number(val);

  if (!Number.isFinite(n)) return String(val ?? "");
  if (n === 0) return "0";
  if (n < 1e-3) return n.toExponential(2);

  return n.toFixed(4);
}

function toGridRows(rows = []) {
  return rows.map((r, i) => ({
    id: i + 1,
    ...r,
  }));
}

function toGridColumns(cols = []) {
  return cols.map((c) => ({
    field: c,
    headerName: c,
    flex: 1,
    minWidth: 120,
    sortable: true,
  }));
}

function normalizeGeneList(raw) {
  if (!Array.isArray(raw)) return [];

  return raw
    .flatMap((g) => String(g ?? "").split(/[;,]/))
    .map((g) => g.trim())
    .filter(Boolean);
}


function normalizeVariantGeneMap(raw) {
  if (!raw) return {};

  const source = raw.by_gene || raw;
  const out = {};

  if (Array.isArray(source)) {
    source.forEach((item) => {
      const gene = String(
        item?.gene || item?.Gene || item?.["Gene.refGene"] || ""
      )
        .trim()
        .toUpperCase();

      if (!gene) return;
      out[gene] = out[gene] || [];
      out[gene].push(item);
    });

    return out;
  }

  Object.entries(source || {}).forEach(([geneRaw, records]) => {
    const gene = String(geneRaw || "").trim().toUpperCase();
    if (!gene) return;

    if (Array.isArray(records)) {
      out[gene] = records;
    } else if (records && typeof records === "object") {
      out[gene] = [records];
    }
  });

  return out;
}

function flattenVariantRows(variantGeneMap) {
  return Object.entries(variantGeneMap || {}).flatMap(([gene, records]) =>
    (records || []).map((record, idx) => ({
      id: `${gene}_${idx + 1}`,
      gene,
      protein_change: record?.protein_change || "",
      mutation_type: record?.mutation_type || "",
      pathogenicity: record?.pathogenicity || "",
      clinvar: record?.clinvar || "",
      lovd: record?.lovd || "",
    }))
  );
}

function SummaryCard({ label, value, helper }) {
  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        minHeight: 96,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: 0.6,
        }}
      >
        {label}
      </Typography>

      <Typography
        variant="h6"
        sx={{
          mt: 0.5,
          fontWeight: 800,
          color: "#111827",
          wordBreak: "break-word",
        }}
      >
        {value}
      </Typography>

      {helper && (
        <Typography variant="body2" sx={{ mt: 0.5, color: "text.secondary" }}>
          {helper}
        </Typography>
      )}
    </Paper>
  );
}

function SectionCard({ title, subtitle, action, children, sx }) {
  return (
    <Card
      elevation={0}
      sx={{
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        overflow: "hidden",
        bgcolor: "background.paper",
        ...sx,
      }}
    >
      <Box
        sx={{
          px: 2.5,
          py: 2,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "#fbfcfe",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 2,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant="subtitle1"
            sx={{
              fontWeight: 800,
              color: "#111827",
            }}
          >
            {title}
          </Typography>

          {subtitle && (
            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
                mt: 0.3,
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {subtitle}
            </Typography>
          )}
        </Box>

        {action}
      </Box>

      <CardContent sx={{ p: 2.5 }}>{children}</CardContent>
    </Card>
  );
}

const dataGridSx = {
  "& .MuiDataGrid-root": {
    border: "none",
  },
  "& .MuiDataGrid-columnHeaders": {
    bgcolor: "#f8fafc",
    color: "#334155",
    fontWeight: 800,
  },
  "& .MuiDataGrid-columnHeader": {
    display: "flex",
    alignItems: "center",
  },
  "& .MuiDataGrid-columnHeaderTitle": {
    fontWeight: 800,
  },
  "& .MuiDataGrid-row:hover": {
    bgcolor: "#f8fbff",
  },
  "& .MuiDataGrid-cell": {
    borderColor: "#eef2f7",
    display: "flex",
    alignItems: "center",
  },
  "& .MuiDataGrid-cellContent": {
    display: "flex",
    alignItems: "center",
  },
};

export default function Pathway() {
  const patientId = useMemo(() => {
    const parts = window.location.pathname.split("/").filter(Boolean);
    return parts[parts.length - 1] || "";
  }, []);

  const { userId } = useContext(AuthContext);

  const [loading, setLoading] = useState(false);
  const [resp, setResp] = useState(null);
  const [error, setError] = useState("");
  const [topN] = useState(100);

  const [selectedCancerType, setSelectedCancerType] =
    useState(DEFAULT_CANCER_TYPE);

  const [selectedPathway, setSelectedPathway] = useState(null);
  const [pathwayJSON, setPathwayJSON] = useState(null);
  const [pvLoading, setPvLoading] = useState(false);
  const [pvError, setPvError] = useState("");

  const [rowSelectionModel, setRowSelectionModel] = useState([]);
  const [autoSelectedOnce, setAutoSelectedOnce] = useState(false);

  const [esMin, setEsMin] = useState("");
  const [pMax, setPMax] = useState("");
  const [qMax, setQMax] = useState("");

  const hasAutoRunRef = useRef(false);
  const loadPathwaySeqRef = useRef(0);

  const clearPathwaySelection = useCallback(() => {
    loadPathwaySeqRef.current += 1;

    setSelectedPathway(null);
    setPathwayJSON(null);
    setPvError("");
    setPvLoading(false);
    setRowSelectionModel([]);
    setAutoSelectedOnce(false);
  }, []);

  const resetFilters = () => {
    setEsMin("");
    setPMax("");
    setQMax("");
    clearPathwaySelection();
  };

  const [geneDetailOpen, setGeneDetailOpen] = useState(false);
  const [geneDetailGene, setGeneDetailGene] = useState("");
  const [geneDetailLoading, setGeneDetailLoading] = useState(false);
  const [geneDetailError, setGeneDetailError] = useState("");
  const [geneDetailTable, setGeneDetailTable] = useState(null);

  const closeGeneDetail = () => {
    setGeneDetailOpen(false);
    setGeneDetailGene("");
    setGeneDetailLoading(false);
    setGeneDetailError("");
    setGeneDetailTable(null);
  };

  const fetchGeneVariants = useCallback(
    async (gene) => {
      const { data } = await axios.post(`${config.rootApiIP}/variants_by_gene`, {
        patient_id: patientId,
        userId,
        gene,
        source: FIXED_SOURCE,
      });

      if (data?.ok === false) {
        throw new Error(data?.error || "Backend returned ok=false");
      }

      return data?.table || data?.result?.table || data;
    },
    [patientId, userId]
  );

  const openGeneDetail = useCallback(
    async (geneRaw) => {
      const gene = String(geneRaw ?? "").trim().toUpperCase();
      if (!gene) return;

      setGeneDetailOpen(true);
      setGeneDetailGene(gene);
      setGeneDetailLoading(true);
      setGeneDetailError("");
      setGeneDetailTable(null);

      try {
        const t = await fetchGeneVariants(gene);

        const columns = t?.columns || t?.table?.columns || [];
        const rows = t?.rows || t?.table?.rows || [];

        if (Array.isArray(columns) && Array.isArray(rows)) {
          setGeneDetailTable({
            columns,
            rows: rows.map((r, i) => ({
              id: i + 1,
              ...r,
            })),
          });
        } else {
          setGeneDetailTable({ raw: t });
        }
      } catch (e) {
        setGeneDetailError(
          e?.response?.data?.detail ||
            e?.response?.data?.error ||
            e?.message ||
            "Load gene variants failed"
        );
      } finally {
        setGeneDetailLoading(false);
      }
    },
    [fetchGeneVariants]
  );

  const runAnalysis = useCallback(async () => {
    setLoading(true);
    setError("");
    setResp(null);

    clearPathwaySelection();

    try {
      const { data } = await axios.post(`${config.rootApiIP}/pathway`, {
        patient_id: patientId,
        userId,
        top_n: topN,
        source: FIXED_SOURCE,
      });

      setResp(data);
    } catch (e) {
      const serverDetail =
        e?.response?.data?.detail ||
        e?.response?.data?.error ||
        e?.message ||
        "Unknown error";

      setError(serverDetail);
    } finally {
      setLoading(false);
    }
  }, [patientId, userId, topN, clearPathwaySelection]);

  useEffect(() => {
    if (!patientId || !userId) return;
    if (hasAutoRunRef.current) return;

    hasAutoRunRef.current = true;
    runAnalysis();
  }, [patientId, userId, runAnalysis]);

  const ok =
    (resp && resp.ok === true) ||
    (resp && resp.status && String(resp.status).toLowerCase() === "success");

  const outputs = resp?.outputs || {};
  const tables = resp?.tables || {};

  const seedGenes = useMemo(() => {
    return normalizeGeneList(
      resp?.seed_genes || resp?.tables?.seed_genes?.genes || []
    );
  }, [resp]);

  const variantGeneMap = useMemo(() => {
    return normalizeVariantGeneMap(
      resp?.variant_gene_map ||
        resp?.functional_variants?.by_gene ||
        resp?.tables?.functional_variants?.by_gene ||
        {}
    );
  }, [resp]);

  const variantGenes = useMemo(() => {
    return Object.keys(variantGeneMap).sort((a, b) => a.localeCompare(b));
  }, [variantGeneMap]);

  const variantRows = useMemo(() => {
    return flattenVariantRows(variantGeneMap);
  }, [variantGeneMap]);

  const seedGeneRows = useMemo(() => {
    return seedGenes.map((gene, i) => ({
      id: i + 1,
      gene,
    }));
  }, [seedGenes]);

  const seedGeneCols = useMemo(
    () => [
      {
        field: "gene",
        headerName: "Input seed gene",
        flex: 1,
        minWidth: 180,
      },
    ],
    []
  );

  const variantCols = useMemo(
    () => [
      { field: "gene", headerName: "Gene", width: 110 },
      {
        field: "protein_change",
        headerName: "Protein change",
        flex: 1,
        minWidth: 170,
      },
      {
        field: "mutation_type",
        headerName: "Mutation",
        flex: 1,
        minWidth: 130,
      },
      {
        field: "pathogenicity",
        headerName: "ClinVar / LOVD result",
        flex: 1.2,
        minWidth: 190,
      },
      { field: "clinvar", headerName: "ClinVar", flex: 1, minWidth: 160 },
      { field: "lovd", headerName: "LOVD", flex: 1, minWidth: 160 },
    ],
    []
  );

  useEffect(() => {
    if (!resp) return;

    console.log("[Pathway] backend resp:", resp);
    console.log("[Pathway] seed_genes:", seedGenes);
    console.log("[Pathway] seed_gene_count:", resp?.seed_gene_count);
    console.log("[Pathway] variant_gene_map:", variantGeneMap);
    console.log("[Pathway] variant_genes:", variantGenes);
    console.log("[Pathway] tables.seed_genes:", resp?.tables?.seed_genes);
  }, [resp, seedGenes, variantGeneMap, variantGenes]);

  const mrwrRows = toGridRows(tables?.mrwr?.rows || []);
  const mrwrTotal = tables?.mrwr?.total_rows || 0;

  const pathesRowsRaw = toGridRows(tables?.pathes?.rows || []);
  const pathesTotal = tables?.pathes?.total_rows || 0;

  const detectMrwrCols = () => {
    const cols = tables?.mrwr?.columns || [];

    return {
      gene: cols.find((c) => /^(gene|symbol|hgnc(_symbol)?|name)$/i.test(c)),
      score:
        cols.find((c) => /^(mrwr(_score)?|score|weight|rank_score)$/i.test(c)) ||
        cols[1],
    };
  };

  const mrwrDetected = detectMrwrCols();

  const mrwrScoreMap = useMemo(() => {
    const map = {};

    if (!mrwrRows?.length || !mrwrDetected.gene || !mrwrDetected.score) {
      return map;
    }

    mrwrRows.forEach((r) => {
      const gene = String(r[mrwrDetected.gene] ?? "").toUpperCase().trim();
      const raw = r[mrwrDetected.score];
      const val = typeof raw === "number" ? raw : Number(raw);

      if (gene && Number.isFinite(val)) {
        map[gene] = val;
      }
    });

    return map;
  }, [mrwrRows, mrwrDetected.gene, mrwrDetected.score]);

  const mrwrCols = useMemo(() => {
    const baseCols = toGridColumns(tables?.mrwr?.columns || []);
    const geneField = mrwrDetected?.gene;

    return [
      ...baseCols,
      {
        field: "__detail",
        headerName: "Detail",
        width: 110,
        sortable: false,
        filterable: false,
        disableColumnMenu: true,
        renderCell: (params) => {
          const gene = geneField ? params.row?.[geneField] : "";

          return (
            <Button
              size="small"
              variant="outlined"
              onClick={(e) => {
                e.stopPropagation();
                openGeneDetail(gene);
              }}
              disabled={!gene}
              sx={{
                textTransform: "none",
                borderRadius: 2,
                fontWeight: 700,
              }}
            >
              Detail
            </Button>
          );
        },
      },
    ];
  }, [tables?.mrwr?.columns, mrwrDetected?.gene, openGeneDetail]);

  const detectPathCols = () => {
    const cols = tables?.pathes?.columns || [];

    const findExactOrRegex = (exactNames = [], regex) => {
      for (const name of exactNames) {
        const found = cols.find((c) => c === name);
        if (found) return found;
      }

      return cols.find((c) => regex.test(c));
    };

    const qvalGlobal = findExactOrRegex(
      ["qval_global", "global_qval", "qval_all_pathways", "qval"],
      /^(qval_global|global_qval|qval_all_pathways|global_fdr|qval(ue)?|q_value|qvalue|fdr|padj|adjp)$/i
    );

    return {
      name: findExactOrRegex(["Pathway"], /^(pathway|name|path_name)$/i),
      cancerType: findExactOrRegex(
        ["CancerType", "cancer_type", "cancerType"],
        /^(cancertype|cancer_type|cancer|group|reference_group)$/i
      ),
      es: findExactOrRegex(["ES"], /^(es|score|ss?mutpes)$/i),
      supportscore: findExactOrRegex(
        ["SupportScore", "supportscore", "support_score"],
        /^(supportscore|support_score|support)$/i
      ),
      pval: findExactOrRegex(
        ["pval"],
        /^(pval(ue)?|p_value|pvalue|p|p\-value)$/i
      ),
      qval: qvalGlobal,
      qvalGlobal,
      url: cols.find((c) => /^(url|json_url|pathway_json)$/i.test(c)),
    };
  };

  const colsDetected = detectPathCols();

  const getPathCellValue = (row, field, fallbackKeys = []) => {
    if (field && row[field] != null) return row[field];

    for (const key of fallbackKeys) {
      if (row[key] != null) return row[key];
    }

    return undefined;
  };

  const pathesCols = useMemo(() => {
    const desiredFields = [
      colsDetected.name,
      colsDetected.es,
      "Overlap",
      "Size",
      colsDetected.pval,
      colsDetected.qval,
    ].filter(Boolean);

    const uniqueFields = Array.from(new Set(desiredFields));

    return uniqueFields.map((field) => {
      const isPathwayCol = field === colsDetected.name;

      if (isPathwayCol) {
        return {
          field,
          headerName: "Pathway",
          flex: 2.2,
          minWidth: 260,
          sortable: true,
          renderCell: (params) => {
            const displayName = getPathwayDisplayName(params.value);

            return (
              <Box
                sx={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  overflow: "hidden",
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    width: "100%",
                    lineHeight: 1.4,
                  }}
                  title={displayName}
                >
                  {displayName}
                </Typography>
              </Box>
            );
          },
        };
      }

      const headerMap = {
        [colsDetected.es]: "ES",
        Overlap: "Overlap",
        Size: "Size",
        [colsDetected.pval]: "p val",
        [colsDetected.qval]: "q val",
      };

      return {
        field,
        headerName: headerMap[field] || field,
        flex: 1,
        minWidth: field === "Overlap" ? 110 : 100,
        sortable: true,
        align: field === "Overlap" || field === "Size" ? "center" : "right",
        headerAlign:
          field === "Overlap" || field === "Size" ? "center" : "right",
        renderCell: (params) => {
          const value = params.value;

          if (
            field === colsDetected.pval ||
            field === colsDetected.qval
          ) {
            return formatP(value);
          }

          return value ?? "";
        },
      };
    });
  }, [
    colsDetected.name,
    colsDetected.es,
    colsDetected.pval,
    colsDetected.qval,
  ]);

  const pathesRowsSorted = useMemo(() => {
    const rows = [...pathesRowsRaw];
    const p = colsDetected.pval;

    if (!p) return rows;

    rows.sort((a, b) => {
      const av = Number(a[p]);
      const bv = Number(b[p]);

      if (!Number.isFinite(av) && !Number.isFinite(bv)) return 0;
      if (!Number.isFinite(av)) return 1;
      if (!Number.isFinite(bv)) return -1;

      return av - bv;
    });

    return rows;
  }, [pathesRowsRaw, colsDetected.pval]);

  const listRows = useMemo(() => {
    return pathesRowsSorted.map((r) => {
      const nameVal = getPathCellValue(r, colsDetected.name, [
        "Pathway",
        "pathway",
        "name",
      ]);

      const esVal = getPathCellValue(r, colsDetected.es, ["ES", "es"]);
      const supportVal = getPathCellValue(r, colsDetected.supportscore, [
        "SupportScore",
        "supportscore",
        "support_score",
      ]);
      const pVal = getPathCellValue(r, colsDetected.pval, ["pval", "p"]);
      const qVal = getPathCellValue(r, colsDetected.qval, [
        "qval_global",
        "global_qval",
        "qval_all_pathways",
        "qval",
        "q",
      ]);

      const esNum = Number(esVal);
      const supportNum = Number(supportVal);
      const pNum = Number(pVal);
      const qNum = Number(qVal);

      return {
        ...r,
        __name: String(nameVal ?? ""),
        __cancerType: getCancerTypeFromPathway(
          nameVal,
          colsDetected.url ? r[colsDetected.url] : ""
        ),
        __esNum: Number.isFinite(esNum) ? esNum : null,
        __supportNum: Number.isFinite(supportNum) ? supportNum : null,
        __pNum: Number.isFinite(pNum) ? pNum : null,
        __qNum: Number.isFinite(qNum) ? qNum : null,
        __es: Number.isFinite(esNum) ? esNum.toFixed(4) : "",
        __support: Number.isFinite(supportNum) ? supportNum.toFixed(4) : "",
        __p: Number.isFinite(pNum) ? formatP(pNum) : "",
        __q: Number.isFinite(qNum) ? formatP(qNum) : "",
      };
    });
  }, [
    pathesRowsSorted,
    colsDetected.name,
    colsDetected.es,
    colsDetected.supportscore,
    colsDetected.pval,
    colsDetected.qval,
    colsDetected.url,
  ]);

  const cancerTypeOptions = useMemo(() => {
    const seen = new Set();

    listRows.forEach((r) => {
      if (r.__cancerType) seen.add(r.__cancerType);
    });

    return Array.from(seen).sort((a, b) => {
      if (a === DEFAULT_CANCER_TYPE) return -1;
      if (b === DEFAULT_CANCER_TYPE) return 1;
      return a.localeCompare(b);
    });
  }, [listRows]);

  const cancerTypeRows = useMemo(() => {
    return listRows.filter((r) => r.__cancerType === selectedCancerType);
  }, [listRows, selectedCancerType]);

  useEffect(() => {
    if (!cancerTypeOptions.length) return;
    if (cancerTypeOptions.includes(selectedCancerType)) return;

    setSelectedCancerType(
      cancerTypeOptions.includes(DEFAULT_CANCER_TYPE)
        ? DEFAULT_CANCER_TYPE
        : cancerTypeOptions[0]
    );
  }, [cancerTypeOptions, selectedCancerType]);

  const filterThresholds = useMemo(
    () => ({
      eMin: esMin === "" ? null : Number(esMin),
      pUpper: pMax === "" ? null : Number(pMax),
      qUpper: qMax === "" ? null : Number(qMax),
    }),
    [esMin, pMax, qMax]
  );

  const doesRowMatchCurrentFilters = useCallback(
    (r) => {
      const { eMin, pUpper, qUpper } = filterThresholds;

      if (eMin != null) {
        if (!Number.isFinite(eMin)) return false;
        if (!(r.__esNum != null && r.__esNum >= eMin)) return false;
      }

      if (pUpper != null) {
        if (!Number.isFinite(pUpper)) return false;
        if (!(r.__pNum != null && r.__pNum <= pUpper)) return false;
      }

      if (qUpper != null) {
        if (!Number.isFinite(qUpper)) return false;
        if (!(r.__qNum != null && r.__qNum <= qUpper)) return false;
      }

      return true;
    },
    [filterThresholds]
  );

  const filteredListRows = useMemo(() => {
    return cancerTypeRows.filter(doesRowMatchCurrentFilters);
  }, [cancerTypeRows, doesRowMatchCurrentFilters]);

  const cancerTypeMatchCounts = useMemo(() => {
    const counts = {};

    cancerTypeOptions.forEach((cancerType) => {
      counts[cancerType] = 0;
    });

    listRows.forEach((r) => {
      const cancerType = r.__cancerType;
      if (!cancerType) return;

      if (doesRowMatchCurrentFilters(r)) {
        counts[cancerType] = (counts[cancerType] || 0) + 1;
      }
    });

    return counts;
  }, [cancerTypeOptions, listRows, doesRowMatchCurrentFilters]);

  const selectedFilteredCount =
    cancerTypeMatchCounts[selectedCancerType] ?? filteredListRows.length;

  const selectedTotalCount = cancerTypeRows.length;

  const selectableCols = useMemo(() => {
    const cols = [
      {
        field: "__name",
        headerName: "Pathway",
        flex: 2,
        minWidth: 240,
        renderCell: (params) => {
          const displayName = getPathwayDisplayName(params.value);

          return (
            <Typography
              variant="body2"
              sx={{
                fontWeight: 500,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                width: "100%",
              }}
              title={displayName}
            >
              {displayName}
            </Typography>
          );
        },
      },
      {
        field: "__es",
        headerName: "ES",
        flex: 1,
        minWidth: 100,
        align: "right",
        headerAlign: "right",
        sortComparator: (a, b) => (Number(a) || 0) - (Number(b) || 0),
      },
    ];

    // SupportScore is temporarily hidden from the pathway selection table.
    // if (filteredListRows.some((r) => r.__support !== "" && r.__support != null)) {
    //   cols.push({
    //     field: "__support",
    //     headerName: "SupportScore",
    //     flex: 1,
    //     minWidth: 130,
    //     align: "right",
    //     headerAlign: "right",
    //     sortComparator: (a, b) => (Number(a) || 0) - (Number(b) || 0),
    //   });
    // }

    if (filteredListRows.some((r) => r.__p !== "" && r.__p != null)) {
      cols.push({
        field: "__p",
        headerName: "p value",
        flex: 1,
        minWidth: 110,
        align: "right",
        headerAlign: "right",
        sortComparator: (a, b) => (Number(a) || 0) - (Number(b) || 0),
      });
    }

    if (filteredListRows.some((r) => r.__q !== "" && r.__q != null)) {
      cols.push({
        field: "__q",
        headerName: "q value",
        flex: 1,
        minWidth: 110,
        align: "right",
        headerAlign: "right",
        sortComparator: (a, b) => (Number(a) || 0) - (Number(b) || 0),
      });
    }

    return cols;
  }, [filteredListRows]);

  const getPathwayUrl = useCallback(
    (pathwayName) => {
      const map =
        resp?.pathway_files ||
        resp?.pathways ||
        outputs?.pathway_files ||
        outputs?.pathways;

      if (map && map[pathwayName]) return map[pathwayName];

      if (colsDetected?.url && colsDetected?.name) {
        const found = pathesRowsSorted.find(
          (r) => String(r[colsDetected.name]) === String(pathwayName)
        );

        if (found?.[colsDetected.url]) return found[colsDetected.url];
      }

      return buildPublicJsonUrl(pathwayName);
    },
    [
      resp,
      outputs,
      colsDetected.url,
      colsDetected.name,
      pathesRowsSorted,
    ]
  );

  const loadPathway = async (opt) => {
    const requestSeq = loadPathwaySeqRef.current + 1;
    loadPathwaySeqRef.current = requestSeq;

    setSelectedPathway(opt);
    setPathwayJSON(null);
    setPvError("");

    if (!opt?.value) return;

    setPvLoading(true);

    try {
      const { folder, fileBase } = splitFolderAndFileBase(opt.value);
      const directUrl = opt.url || getPathwayUrl(opt.value);

      const nameVariants = Array.from(
        new Set([
          `${fileBase}.json`,
          `${fileBase.replace(/\(/g, "%28").replace(/\)/g, "%29")}.json`,
          `${fileBase.replace(/[()]/g, "")}.json`,
        ])
      );

      const publicCandidates = nameVariants.map(
        (n) => `/tcga_pathways_json/${folder}/${n}`
      );

      const apiBase = `${config.rootApiIP}/pathway/json?patient_id=${encodeURIComponent(
        patientId
      )}&name=`;

      const apiCandidates = Array.from(
        new Set([
          apiBase + encodeURIComponent(fileBase),
          apiBase + encodeURIComponent(fileBase + ".json"),
          apiBase + fileBase.replace(/\(/g, "%28").replace(/\)/g, "%29"),
          apiBase +
            (fileBase + ".json").replace(/\(/g, "%28").replace(/\)/g, "%29"),
          apiBase + encodeURIComponent(fileBase.replace(/[()]/g, "")),
          apiBase + encodeURIComponent(fileBase.replace(/[()]/g, "") + ".json"),
        ])
      );

      const candidates = [directUrl, ...publicCandidates, ...apiCandidates].filter(
        Boolean
      );

      let data = null;
      let lastErr = null;

      for (const u of candidates) {
        try {
          console.debug("[Pathway] try:", u);
          const r = await axios.get(u);

          if (r?.data && (r.data.nodes || r.data.edges)) {
            data = r.data;
            break;
          }

          lastErr = new Error("Invalid pathway JSON format.");
        } catch (e) {
          lastErr = e;
        }
      }

      if (!data) {
        throw new Error(
          `Load pathway failed. Tried:\n${candidates.join(
            "\n"
          )}\nLast error: ${lastErr?.response?.status || ""} ${
            lastErr?.message || ""
          }`
        );
      }

      if (loadPathwaySeqRef.current !== requestSeq) return;

      setPathwayJSON(data);
    } catch (e) {
      if (loadPathwaySeqRef.current !== requestSeq) return;

      setPvError(
        e?.response?.data?.detail || String(e?.message || "Load pathway failed")
      );
    } finally {
      if (loadPathwaySeqRef.current === requestSeq) {
        setPvLoading(false);
      }
    }
  };

  useEffect(() => {
    if (!pathwayJSON) return;

    const pathwayGenes = (pathwayJSON.nodes || [])
      .filter((n) => String(n.type || "").toUpperCase() === "GENE")
      .map((n) => String(n.name || "").trim().toUpperCase())
      .filter(Boolean);

    const seedSet = new Set(seedGenes.map((g) => String(g).toUpperCase()));
    const variantSet = new Set(variantGenes.map((g) => String(g).toUpperCase()));
    const matched = pathwayGenes.filter((g) => seedSet.has(g));
    const matchedVariants = pathwayGenes.filter((g) => variantSet.has(g));

    console.log("[Pathway] pathway genes:", pathwayGenes);
    console.log("[Pathway] seed genes:", Array.from(seedSet));
    console.log("[Pathway] variant genes:", Array.from(variantSet));
    console.log("[Pathway] matched seed genes on current pathway:", matched);
    console.log("[Pathway] matched variant genes on current pathway:", matchedVariants);
  }, [pathwayJSON, seedGenes, variantGenes]);

  useEffect(() => {
    if (!ok || !colsDetected.name) return;
    if (filteredListRows.length > 0) return;

    clearPathwaySelection();
  }, [ok, colsDetected.name, filteredListRows.length, clearPathwaySelection]);

  useEffect(() => {
    if (!ok || autoSelectedOnce) return;
    if (!filteredListRows?.length || !colsDetected.name) return;

    const nameField = colsDetected.name;
    const esField = colsDetected.es;
    const pField = colsDetected.pval;

    let best = filteredListRows[0] || null;

    if (pField) {
      best =
        filteredListRows.find((r) => Number.isFinite(Number(r[pField]))) ||
        best;
    } else if (esField) {
      let maxVal = -Infinity;

      filteredListRows.forEach((r) => {
        const v = Number(r[esField]);

        if (Number.isFinite(v) && v > maxVal) {
          maxVal = v;
          best = r;
        }
      });
    }

    if (!best) return;

    const id = best.id;
    setRowSelectionModel([id]);

    const opt = {
      label: String(best[nameField] ?? ""),
      value: String(best[nameField] ?? ""),
      es: esField ? best[esField] : undefined,
      url: colsDetected.url ? best[colsDetected.url] : undefined,
    };

    loadPathway(opt);
    setAutoSelectedOnce(true);

    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    ok,
    filteredListRows,
    colsDetected.name,
    colsDetected.es,
    colsDetected.pval,
    colsDetected.url,
    autoSelectedOnce,
    selectedCancerType,
  ]);

  const handleCancerTypeChange = (e) => {
    setSelectedCancerType(e.target.value);
    clearPathwaySelection();
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        bgcolor: "#f5f7fb",
        px: { xs: 2, md: 3 },
        py: 3,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          p: 3,
          mb: 3,
          borderRadius: 4,
          border: "1px solid",
          borderColor: "divider",
          background:
            "linear-gradient(135deg, #ffffff 0%, #f7fbff 55%, #eef6ff 100%)",
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", md: "center" }}
          spacing={2}
        >
          <Box>
            <Stack direction="row" spacing={1.2} alignItems="center" flexWrap="wrap">
              <Typography variant="h5" sx={{ fontWeight: 900, color: "#111827" }}>
                Network Pathway Analysis
              </Typography>

              {loading && <CircularProgress size={22} />}

              {ok && (
                <Chip
                  size="small"
                  label="Completed"
                  color="success"
                  variant="outlined"
                  sx={{ fontWeight: 700 }}
                />
              )}
            </Stack>

            <Typography variant="body2" sx={{ mt: 1, color: "text.secondary" }}>
              Patient ID: <b>{patientId}</b>
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 3, whiteSpace: "pre-wrap" }}>
          {error}
        </Alert>
      )}

      {!ok && !error && (
        <Alert severity="info" sx={{ mb: 3 }}>
          {loading ? "Running pathway analysis..." : "Preparing results..."}
        </Alert>
      )}

      {ok && (
        <>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, 1fr)",
                lg: "repeat(3, 1fr)",
              },
              gap: 2,
              mb: 3,
            }}
          >
            <SummaryCard
              label="Cancer type"
              value={getCancerTypeDisplayName(selectedCancerType)}
              helper="Current pathway reference group; q value is adjusted across all analyzed pathways"
            />

            <SummaryCard
              label="Somatic variant genes"
              value={variantGenes.length || seedGenes.length}
              helper="Genes marked by green dots in the pathway"
            />


            <SummaryCard
              label="Pathways"
              value={`${selectedFilteredCount} / ${selectedTotalCount}`}
              helper="Pathways matching current filters"
            />
          </Box>

          <Paper
            elevation={0}
            sx={{
              p: 2,
              mb: 3,
              borderRadius: 3,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Stack
              direction={{ xs: "column", lg: "row" }}
              spacing={2}
              alignItems={{ xs: "stretch", lg: "center" }}
              justifyContent="space-between"
            >
              <Stack
                direction={{ xs: "column", sm: "row" }}
                spacing={1}
                alignItems={{ xs: "stretch", sm: "center" }}
              >
                <FormControl size="small" sx={{ minWidth: 180 }}>
                  <InputLabel id="pathway-cancer-type-label">Cancer type</InputLabel>

                  <Select
                    labelId="pathway-cancer-type-label"
                    value={selectedCancerType}
                    label="Cancer type"
                    onChange={handleCancerTypeChange}
                    renderValue={(value) => getCancerTypeDisplayName(value)}
                  >
                    {cancerTypeOptions.map((cancerType) => {
                      const matchCount = cancerTypeMatchCounts[cancerType] || 0;

                      return (
                        <MenuItem key={cancerType} value={cancerType}>
                          <Box
                            sx={{
                              width: "100%",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              gap: 2,
                            }}
                          >
                            <Typography variant="body2">
                              {getCancerTypeDisplayName(cancerType)}
                            </Typography>

                            <Chip
                              size="small"
                              label={`${matchCount} pathway${
                                matchCount === 1 ? "" : "s"
                              }`}
                              color={matchCount > 0 ? "primary" : "default"}
                              variant={matchCount > 0 ? "outlined" : "filled"}
                              sx={{ fontWeight: 700 }}
                            />
                          </Box>
                        </MenuItem>
                      );
                    })}
                  </Select>
                </FormControl>

                <Chip
                  label={`${selectedFilteredCount} pathway${
                    selectedFilteredCount === 1 ? "" : "s"
                  } match current filters`}
                  color={selectedFilteredCount > 0 ? "primary" : "default"}
                  variant={selectedFilteredCount > 0 ? "outlined" : "filled"}
                  sx={{
                    height: 40,
                    borderRadius: 2,
                    fontWeight: 800,
                    justifyContent: "center",
                  }}
                />
              </Stack>

              <Stack
                direction={{ xs: "column", md: "row" }}
                spacing={1}
                alignItems={{ xs: "stretch", md: "center" }}
              >
                <TextField
                  label="ES ≥"
                  size="small"
                  value={esMin}
                  onChange={(e) => {
                    setEsMin(e.target.value);
                    clearPathwaySelection();
                  }}
                  placeholder="0.10"
                  sx={{ width: { xs: "100%", md: 110 } }}
                  inputProps={{ inputMode: "decimal" }}
                />

                <TextField
                  label="p ≤"
                  size="small"
                  value={pMax}
                  onChange={(e) => {
                    setPMax(e.target.value);
                    clearPathwaySelection();
                  }}
                  placeholder="0.05"
                  sx={{ width: { xs: "100%", md: 110 } }}
                  inputProps={{ inputMode: "decimal" }}
                />

                <TextField
                  label="q ≤"
                  size="small"
                  value={qMax}
                  onChange={(e) => {
                    setQMax(e.target.value);
                    clearPathwaySelection();
                  }}
                  placeholder="0.05"
                  sx={{ width: { xs: "100%", md: 110 } }}
                  inputProps={{ inputMode: "decimal" }}
                />

                <IconButton
                  aria-label="reset filters"
                  onClick={resetFilters}
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                  }}
                >
                  <ClearIcon />
                </IconButton>
              </Stack>
            </Stack>
          </Paper>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                xl: "minmax(0, 1fr) 460px",
              },
              gap: 3,
              alignItems: "start",
            }}
          >
            <SectionCard
              title="Pathway Visualization"
              subtitle={
                selectedFilteredCount === 0
                  ? `No ${getCancerTypeDisplayName(
                      selectedCancerType
                    )} pathway matches current filters.`
                  : selectedPathway?.label
                  ? getPathwayDisplayName(selectedPathway.label)
                  : "Select a pathway from the right panel to display the network."
              }
              sx={{ minWidth: 0 }}
            >
              {pvLoading && (
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
                  <CircularProgress size={20} />

                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    Loading pathway JSON...
                  </Typography>
                </Stack>
              )}

              {pvError && (
                <Alert severity="error" sx={{ mb: 2, whiteSpace: "pre-wrap" }}>
                  {pvError}
                </Alert>
              )}

              {selectedFilteredCount === 0 ? (
                <Alert severity="info">
                  No pathway visualization is shown because no pathway matches the
                  current cancer type and filter settings.
                </Alert>
              ) : pathwayJSON ? (
                <Box
                  sx={{
                    borderRadius: 3,
                    overflow: "hidden",
                    border: "1px solid",
                    borderColor: "divider",
                    bgcolor: "#fff",
                  }}
                >
                  <PathwayViewer
                    pathwayData={pathwayJSON}
                    title={getPathwayDisplayName(selectedPathway?.label || "")}
                    height="720px"
                    mrwrScores={mrwrScoreMap}
                    seedGenes={seedGenes}
                    variantGeneMap={variantGeneMap}
                    analysisScope="q value adjusted across all analyzed pathways"
                    onGeneClick={(gene) => openGeneDetail(gene)}
                  />
                </Box>
              ) : (
                <Alert severity="info">
                  Pick a pathway on the right to visualize its pathway network.
                </Alert>
              )}
            </SectionCard>

            <SectionCard
              title="Pathway Selection"
              subtitle={`${selectedFilteredCount} pathway(s) match current filters; q value is adjusted across all analyzed pathways`}
              sx={{ minWidth: 0 }}
            >
              {!filteredListRows ||
              filteredListRows.length === 0 ||
              !colsDetected.name ? (
                <Alert severity="info">
                  {listRows.length === 0 ? (
                    <>
                      No pathway ES rows in response. Make sure backend returns{" "}
                      <code>tables.pathes</code>.
                    </>
                  ) : (
                    `No ${getCancerTypeDisplayName(
                      selectedCancerType
                    )} rows match current filters.`
                  )}
                </Alert>
              ) : (
                <Box
                  sx={{
                    height: 620,
                    width: "100%",
                    ...dataGridSx,
                  }}
                >
                  <DataGrid
                    rows={filteredListRows}
                    columns={selectableCols}
                    checkboxSelection
                    rowHeight={58}
                    columnHeaderHeight={56}
                    disableRowSelectionOnClick={false}
                    disableMultipleRowSelection
                    rowSelectionModel={rowSelectionModel}
                    onRowSelectionModelChange={(newModel) => {
                      const modelArray = Array.isArray(newModel)
                        ? newModel
                        : Array.from(newModel?.ids || []);

                      const lastId = modelArray[modelArray.length - 1] ?? null;
                      const single = lastId ? [lastId] : [];

                      setRowSelectionModel(single);

                      if (!lastId) {
                        setSelectedPathway(null);
                        setPathwayJSON(null);
                        return;
                      }

                      const row = filteredListRows.find(
                        (r) => String(r.id) === String(lastId)
                      );

                      if (!row) return;

                      const label = String(row.__name ?? "");

                      loadPathway({
                        label,
                        value: label,
                        url: undefined,
                      });
                    }}
                    pageSizeOptions={[10, 25, 50]}
                    initialState={{
                      pagination: {
                        paginationModel: {
                          pageSize: 10,
                          page: 0,
                        },
                      },
                      sorting: filteredListRows.some((r) => r.__pNum != null)
                        ? {
                            sortModel: [
                              {
                                field: "__p",
                                sort: "asc",
                              },
                            ],
                          }
                        : undefined,
                    }}
                    hideFooterSelectedRowCount
                  />
                </Box>
              )}
            </SectionCard>
          </Box>

          <Stack spacing={2.5} sx={{ mt: 3 }}>
            <Accordion
              disableGutters
              elevation={0}
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: "16px !important",
                overflow: "hidden",
                bgcolor: "background.paper",
                "&:before": {
                  display: "none",
                },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    Gene Global Weight
                  </Typography>

                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    {mrwrTotal || mrwrRows.length} gene(s) from MRWR global weight ranking
                  </Typography>
                </Box>
              </AccordionSummary>

              <AccordionDetails sx={{ pt: 0 }}>
                {!tables?.mrwr ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Server did not include gene global weight table. Need{" "}
                    <code>tables.mrwr</code>.
                  </Alert>
                ) : mrwrRows.length === 0 ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    No gene global weight records returned from backend.
                  </Alert>
                ) : (
                  <Box
                    sx={{
                      height: 480,
                      width: "100%",
                      ...dataGridSx,
                    }}
                  >
                    <DataGrid
                      rows={mrwrRows}
                      columns={mrwrCols}
                      pageSizeOptions={[10, 25, 50, 100]}
                      initialState={{
                        pagination: {
                          paginationModel: {
                            pageSize: 25,
                            page: 0,
                          },
                        },
                      }}
                      disableRowSelectionOnClick
                    />
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>

            {/* Temporarily hidden: functional somatic variant table and input seed gene table. */}
            {false && (
              <>
            <Accordion
              disableGutters
              elevation={0}
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: "16px !important",
                overflow: "hidden",
                bgcolor: "background.paper",
                "&:before": {
                  display: "none",
                },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    Functional Somatic Variants
                  </Typography>

                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    {variantRows.length} variant record(s) from df_functional.csv. Green dots mark genes with functional somatic variants; hover the dot to review all variant annotations.
                  </Typography>
                </Box>
              </AccordionSummary>

              <AccordionDetails sx={{ pt: 0 }}>
                {variantRows.length === 0 ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    No functional somatic variant records returned from backend.
                  </Alert>
                ) : (
                  <Box
                    sx={{
                      height: 360,
                      width: "100%",
                      ...dataGridSx,
                    }}
                  >
                    <DataGrid
                      rows={variantRows}
                      columns={variantCols}
                      pageSizeOptions={[10, 25, 50, 100]}
                      initialState={{
                        pagination: {
                          paginationModel: {
                            pageSize: 10,
                            page: 0,
                          },
                        },
                      }}
                      disableRowSelectionOnClick
                    />
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>

            <Accordion
              disableGutters
              elevation={0}
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: "16px !important",
                overflow: "hidden",
                bgcolor: "background.paper",
                "&:before": {
                  display: "none",
                },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    Input Seed Genes
                  </Typography>

                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    {seedGenes.length} gene(s) from original input variants
                  </Typography>
                </Box>
              </AccordionSummary>

              <AccordionDetails sx={{ pt: 0 }}>
                {seedGenes.length === 0 ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    No seed genes returned from backend.
                  </Alert>
                ) : (
                  <Box
                    sx={{
                      height: 360,
                      width: "100%",
                      ...dataGridSx,
                    }}
                  >
                    <DataGrid
                      rows={seedGeneRows}
                      columns={seedGeneCols}
                      pageSizeOptions={[10, 25, 50, 100]}
                      initialState={{
                        pagination: {
                          paginationModel: {
                            pageSize: 10,
                            page: 0,
                          },
                        },
                      }}
                      disableRowSelectionOnClick
                    />
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>

              </>
            )}

            <Accordion
              disableGutters
              elevation={0}
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderRadius: "16px !important",
                overflow: "hidden",
                bgcolor: "background.paper",
                "&:before": {
                  display: "none",
                },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                    Pathway Result
                  </Typography>

                  <Typography variant="body2" sx={{ color: "text.secondary" }}>
                    {selectedTotalCount
                      ? `${selectedFilteredCount} / ${selectedTotalCount} pathways match current filters`
                      : "Pathway enrichment score table"}
                  </Typography>
                </Box>
              </AccordionSummary>

              <AccordionDetails sx={{ pt: 0 }}>
                {!tables?.pathes ? (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Server did not include Pathway ES table. Need{" "}
                    <code>tables.pathes</code>.
                  </Alert>
                ) : (
                  <Box
                    sx={{
                      height: 480,
                      width: "100%",
                      ...dataGridSx,
                    }}
                  >
                    <DataGrid
                      rows={filteredListRows}
                      columns={pathesCols}
                      pageSizeOptions={[10, 25, 50, 100]}
                      initialState={{
                        pagination: {
                          paginationModel: {
                            pageSize: 10,
                            page: 0,
                          },
                        },
                      }}
                      disableRowSelectionOnClick
                    />
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          </Stack>
        </>
      )}

      <Dialog
        open={geneDetailOpen}
        onClose={closeGeneDetail}
        fullWidth
        maxWidth="lg"
        PaperProps={{
          sx: {
            borderRadius: 3,
          },
        }}
      >
        <DialogTitle sx={{ fontWeight: 900 }}>
          Gene variants: <b>{geneDetailGene}</b>
        </DialogTitle>

        <DialogContent dividers>
          {geneDetailLoading && (
            <Stack direction="row" spacing={1} alignItems="center">
              <CircularProgress size={20} />

              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Loading gene variant records...
              </Typography>
            </Stack>
          )}

          {geneDetailError && (
            <Alert severity="error" sx={{ whiteSpace: "pre-wrap", mb: 2 }}>
              {geneDetailError}
            </Alert>
          )}

          {!geneDetailLoading && !geneDetailError && geneDetailTable?.columns && (
            <Box
              sx={{
                height: 520,
                width: "100%",
                ...dataGridSx,
              }}
            >
              <DataGrid
                rows={geneDetailTable.rows || []}
                columns={toGridColumns(geneDetailTable.columns || [])}
                pageSizeOptions={[10, 25, 50, 100]}
                initialState={{
                  pagination: {
                    paginationModel: {
                      pageSize: 25,
                      page: 0,
                    },
                  },
                }}
                disableRowSelectionOnClick
              />
            </Box>
          )}

          {!geneDetailLoading && !geneDetailError && geneDetailTable?.raw && (
            <Alert severity="info" sx={{ whiteSpace: "pre-wrap" }}>
              Backend did not return a tabular format. Raw payload:
              {"\n"}
              {JSON.stringify(geneDetailTable.raw, null, 2)}
            </Alert>
          )}
        </DialogContent>

        <DialogActions sx={{ px: 3, py: 2 }}>
          <Button
            onClick={closeGeneDetail}
            variant="contained"
            sx={{
              textTransform: "none",
              borderRadius: 2,
              fontWeight: 700,
              boxShadow: "none",
            }}
          >
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
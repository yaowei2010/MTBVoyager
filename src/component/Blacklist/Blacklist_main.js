// src/component/Blacklist/Blacklist_main.js
import React, { useEffect, useState, useMemo, useContext } from "react";
import axios from "axios";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import {
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  Divider,
  IconButton,
  Typography,
  TextField,
  MenuItem,
  Stack,
  Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate, useSearchParams } from "react-router-dom";
import { config } from "../../constant";
import { AuthContext } from "../Auth/AuthContext";

const norm = (s) => (s || "").replace(/\/+$/g, "");

const API_BLACKLIST = `${norm(config.rootApiIP)}/blacklist_main`;
const API_CLINVAR = `${norm(config.rootApiIP)}/clinvar_result`;
const API_IMPORT_BLACKLIST = `${norm(config.rootApiIP)}/blacklist_import_from_clinvar`;
const API_IMPORTED_LIST = `${norm(config.rootApiIP)}/clinvar_blacklist_list`;
const API_IMPORTED_DELETE = `${norm(config.rootApiIP)}/clinvar_blacklist_delete`;
const API_ORIGINAL_EXCLUDE = `${norm(config.rootApiIP)}/blacklist_original_exclude`;

function stringifyCell(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function formatIntegerCell(v) {
  if (v === null || v === undefined || v === "") return "";
  const n = Number(v);
  return Number.isFinite(n) ? String(Math.trunc(n)) : String(v);
}

function formatDateTimeCell(v) {
  if (v === null || v === undefined || v === "") return "";

  const raw = String(v).trim();
  if (!raw) return "";

  // Already normalized by backend, or ISO-like datetime from Django/PostgreSQL.
  // Keep display stable as YYYY-MM-DD HH:mm:ss and remove milliseconds / timezone suffix.
  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;

  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function normalizePositionFields(row) {
  if (!row || typeof row !== "object") return row;
  const out = { ...row };
  if ("Start" in out) out.Start = formatIntegerCell(out.Start);
  if ("End" in out) out.End = formatIntegerCell(out.End);
  return out;
}

function parseMaybeJson(value) {
  if (typeof value !== "string") return value;
  const text = value.trim();
  if (!text || (!text.startsWith("{") && !text.startsWith("["))) return value;
  try {
    return JSON.parse(text);
  } catch {
    return value;
  }
}

function getPayloadValue(row, key) {
  const payload = parseMaybeJson(row?.detail ?? row?.src_payload ?? row?.payload ?? null);
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    return payload[key];
  }
  return undefined;
}

function firstNonEmpty(...vals) {
  for (const v of vals) {
    if (v !== null && v !== undefined && String(v).trim() !== "") return v;
  }
  return "";
}

function normalizeClinvarRow(row) {
  const r = normalizePositionFields(row || {});
  const symbol = firstNonEmpty(
    r.SYMBOL,
    r.symbol,
    getPayloadValue(r, "SYMBOL"),
    getPayloadValue(r, "symbol"),
    r["Gene.refGene"],
    r["Gene.refGeneWithVer"],
    r.Gene,
    r.gene_symbol,
    getPayloadValue(r, "Gene.refGene"),
    getPayloadValue(r, "Gene.refGeneWithVer")
  );

  return {
    ...r,
    SYMBOL: symbol,
    Gene: symbol,
    "Gene.refGene": symbol,
    "Func.refGene": firstNonEmpty(r["Func.refGene"], r["Func.refGeneWithVer"], getPayloadValue(r, "Func.refGene"), getPayloadValue(r, "Func.refGeneWithVer")),
    "ExonicFunc.refGene": firstNonEmpty(r["ExonicFunc.refGene"], r["ExonicFunc.refGeneWithVer"], getPayloadValue(r, "ExonicFunc.refGene"), getPayloadValue(r, "ExonicFunc.refGeneWithVer")),
    "AAChange.refGene": firstNonEmpty(r["AAChange.refGene"], r["AAChange.refGeneWithVer"], getPayloadValue(r, "AAChange.refGene"), getPayloadValue(r, "AAChange.refGeneWithVer")),
    HGVSc: firstNonEmpty(r.HGVSc, getPayloadValue(r, "HGVSc")),
    HGVSp: firstNonEmpty(r.HGVSp, getPayloadValue(r, "HGVSp")),
    avsnp150: firstNonEmpty(r.avsnp150, getPayloadValue(r, "avsnp150")),
  };
}

function getFormatterValue(paramsOrValue) {
  if (paramsOrValue && typeof paramsOrValue === "object" && "value" in paramsOrValue) {
    return paramsOrValue.value;
  }
  return paramsOrValue;
}

const positionColumnProps = {
  valueFormatter: (paramsOrValue) => formatIntegerCell(getFormatterValue(paramsOrValue)),
};

const dateTimeColumnProps = {
  width: 190,
  minWidth: 170,
  valueFormatter: (paramsOrValue) => formatDateTimeCell(getFormatterValue(paramsOrValue)),
};

const gridSx = {
  border: "1px solid #e5edf7",
  borderRadius: 3,
  backgroundColor: "#fff",
  boxShadow: "0 10px 28px rgba(15, 23, 42, 0.08)",
  "& .MuiDataGrid-columnHeaders": {
    backgroundColor: "#f1f5fb",
    fontWeight: 800,
  },
  "& .MuiDataGrid-row:hover": {
    backgroundColor: "#f8fbff",
  },
  "& .MuiDataGrid-footerContainer": {
    position: "sticky",
    bottom: 0,
    background: "#fff",
    zIndex: 2,
  },
};

const HIDDEN_PAYLOAD_FIELDS = new Set([
  "id",
  "rn",
  "Gene",
  "gene_symbol",
  "Gene.refGene",
  "Gene.refGeneWithVer",
  "Gene_refGene",
  "Gene_refGeneWithVer",
]);

function HeaderWithHelp({ label, help }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
      <span>{label}</span>
      <Tooltip title={help} arrow placement="top">
        <span
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 16,
            height: 16,
            borderRadius: "50%",
            border: "1px solid #94a3b8",
            color: "#475569",
            fontSize: 11,
            fontWeight: 800,
            cursor: "help",
            lineHeight: 1,
          }}
        >
          ?
        </span>
      </Tooltip>
    </span>
  );
}

const TIME_HELP = {
  lastEvaluated: "The latest time this variant was queried in ClinVar and the crawled result was updated.",
  importTime: "The time this variant was actually imported into blacklist management. Original blacklist records use the system default import time; user-added records use the user import time.",
  firstSubmission: "The earliest submission time of this variant in the source analysis tables.",
  lastSubmission: "The latest submission/update time of this variant in the source analysis tables.",
};

const TIME_FIELD_CONFIG = {
  import_time: { label: "Import Time", help: TIME_HELP.importTime },
  last_evaluated_at: { label: "Last Evaluated", help: TIME_HELP.lastEvaluated },
  src_created_at: { label: "First Submission", help: TIME_HELP.firstSubmission },
  src_updated_at: { label: "Last Submission", help: TIME_HELP.lastSubmission },
};

const DISPLAY_HEADER_MAP = {
  SYMBOL: "SYMBOL",
};

function getDisplayHeader(field) {
  return TIME_FIELD_CONFIG[field]?.label || DISPLAY_HEADER_MAP[field] || field;
}

function getTimeHelp(field) {
  return TIME_FIELD_CONFIG[field]?.help || "";
}

function isTimeField(field) {
  return Boolean(TIME_FIELD_CONFIG[field]);
}

function formatDisplayCell(field, value) {
  if (field === "Start" || field === "End") return formatIntegerCell(value);
  if (isTimeField(field)) return formatDateTimeCell(value);
  return stringifyCell(value);
}

function timeHeader(field) {
  const cfg = TIME_FIELD_CONFIG[field];
  if (!cfg) return undefined;
  return () => <HeaderWithHelp label={cfg.label} help={cfg.help} />;
}

function buildPayloadTable(data, preferredOrder = []) {
  const order = Array.isArray(preferredOrder) ? preferredOrder : [];

  if (Array.isArray(data) && data.length > 0 && typeof data[0] === "object" && !Array.isArray(data[0])) {
    const pageKeys = Array.from(new Set(data.flatMap((obj) => Object.keys(obj || {})))).filter((k) => !HIDDEN_PAYLOAD_FIELDS.has(k));
    const seen = new Set();
    const colsOrder = [];

    for (const k of order) {
      if (pageKeys.includes(k) && !seen.has(k)) {
        seen.add(k);
        colsOrder.push(k);
      }
    }
    for (const k of pageKeys) {
      if (!seen.has(k)) {
        seen.add(k);
        colsOrder.push(k);
      }
    }

    const cols = colsOrder.map((k) => ({
      field: k,
      headerName: getDisplayHeader(k),
      width: isTimeField(k) ? 190 : Math.max(120, Math.min(420, String(getDisplayHeader(k)).length * 12)),
      ...(k === "Start" || k === "End" ? positionColumnProps : {}),
      ...(isTimeField(k) ? dateTimeColumnProps : {}),
      ...(isTimeField(k) ? { renderHeader: timeHeader(k) } : {}),
    }));

    const rows = data.map((obj, i) => {
      const row = { id: obj?.id ?? i + 1 };
      colsOrder.forEach((k) => {
        row[k] = formatDisplayCell(k, obj?.[k]);
      });
      return row;
    });
    return { cols, rows };
  }

  if (data && typeof data === "object" && !Array.isArray(data)) {
    const keysAll = Object.keys(data).filter((k) => !HIDDEN_PAYLOAD_FIELDS.has(k));
    const seen = new Set();
    const keysInOrder = [];

    for (const k of order) {
      if (k in data && !seen.has(k)) {
        seen.add(k);
        keysInOrder.push(k);
      }
    }
    for (const k of keysAll) {
      if (!seen.has(k)) {
        seen.add(k);
        keysInOrder.push(k);
      }
    }

    return {
      cols: [
        { field: "key", headerName: "Field", width: 240 },
        { field: "value", headerName: "Value", flex: 1, minWidth: 320 },
      ],
      rows: keysInOrder.map((k, i) => ({
        id: i + 1,
        key: k,
        value: formatDisplayCell(k, data[k]),
      })),
    };
  }

  return {
    cols: [
      { field: "key", headerName: "Field", width: 120 },
      { field: "value", headerName: "Value", flex: 1, minWidth: 300 },
    ],
    rows: [{ id: 1, key: "detail", value: stringifyCell(data) }],
  };
}

const mainColumns = [
  // { field: "source_type", headerName: "Source", width: 160 },

  { field: "Chr", headerName: "Chr", width: 90 },
  { field: "Start", headerName: "Start", width: 120, ...positionColumnProps },
  { field: "End", headerName: "End", width: 120, ...positionColumnProps },
  { field: "Ref", headerName: "Ref", width: 80 },
  { field: "Alt", headerName: "Alt", width: 80 },
  { field: "SYMBOL", headerName: "Gene.refGene", width: 170 },
  { field: "Func.refGeneWithVer", headerName: "Func.refGene", width: 210 },
  { field: "ExonicFunc.refGeneWithVer", headerName: "ExonicFunc.refGene", width: 240 },
  { field: "AAChange.refGeneWithVer", headerName: "AAChange.refGene", width: 320 },
  { field: "AF", headerName: "AF", width: 120 },
  { field: "import_time", headerName: "Import Time", width: 190, ...dateTimeColumnProps, renderHeader: timeHeader("import_time") },
];

const importedColumns = [
 
  { field: "Chr", headerName: "Chr", width: 90 },
  { field: "Start", headerName: "Start", width: 120, ...positionColumnProps },
  { field: "End", headerName: "End", width: 120, ...positionColumnProps },
  { field: "Ref", headerName: "Ref", width: 80 },
  { field: "Alt", headerName: "Alt", width: 80 },
  { field: "SYMBOL", headerName: "Gene.refGene", width: 170 },
  { field: "Func.refGene", headerName: "Func.refGene", width: 210 },
  { field: "ExonicFunc.refGene", headerName: "ExonicFunc.refGene", width: 240 },
  { field: "AAChange.refGene", headerName: "AAChange.refGene", width: 320 },
  { field: "AF", headerName: "AF", width: 120 },
  { field: "import_time", headerName: "Import Time", width: 190, ...dateTimeColumnProps, renderHeader: timeHeader("import_time") },
];

export default function BlacklistPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const initialUid = searchParams.get("user_id") || "";
  const { userId } = useContext(AuthContext) || {};

  const currentUid = Number(userId || initialUid);

  const [rowsA, setRowsA] = useState([]);
  const [totalA, setTotalA] = useState(0);
  const [loadingA, setLoadingA] = useState(false);
  const [errA, setErrA] = useState("");
  const [paginationModelA, setPaginationModelA] = useState({ page: 0, pageSize: 25 });
  const [sortModelA, setSortModelA] = useState([]);
  const [searchA, setSearchA] = useState("");

  const [rowsC, setRowsC] = useState([]);
  const [totalC, setTotalC] = useState(0);
  const [loadingC, setLoadingC] = useState(false);
  const [errC, setErrC] = useState("");
  const [paginationModelC, setPaginationModelC] = useState({ page: 0, pageSize: 25 });
  const [sortModelC, setSortModelC] = useState([]);
  const [selectionModelC, setSelectionModelC] = useState([]);
  const [deleteMsgC, setDeleteMsgC] = useState("");
  const [deleteErrC, setDeleteErrC] = useState("");

  const [rowsExisting, setRowsExisting] = useState([]);
  const [totalExisting, setTotalExisting] = useState(0);
  const [loadingExisting, setLoadingExisting] = useState(false);
  const [errExisting, setErrExisting] = useState("");
  const [paginationExisting, setPaginationExisting] = useState({ page: 0, pageSize: 25 });
  const [sortExisting, setSortExisting] = useState([]);
  const [selectionExisting, setSelectionExisting] = useState([]);
  const [excludeMsg, setExcludeMsg] = useState("");
  const [excludeErr, setExcludeErr] = useState("");

  const [rowsNew, setRowsNew] = useState([]);
  const [totalNew, setTotalNew] = useState(0);
  const [loadingNew, setLoadingNew] = useState(false);
  const [errNew, setErrNew] = useState("");
  const [paginationNew, setPaginationNew] = useState({ page: 0, pageSize: 25 });
  const [sortNew, setSortNew] = useState([]);
  const [selectionNew, setSelectionNew] = useState([]);

  const [searchClinvar, setSearchClinvar] = useState("");
  const [clinvarUpdateFilter, setClinvarUpdateFilter] = useState("updated");
  const [payloadOrder, setPayloadOrder] = useState([]);
  const [payloadOpen, setPayloadOpen] = useState(false);
  const [payloadData, setPayloadData] = useState(null);
  const [paginationModelPayload, setPaginationModelPayload] = useState({ page: 0, pageSize: 25 });
  const [importing, setImporting] = useState(false);
  const [importMsg, setImportMsg] = useState("");
  const [importErr, setImportErr] = useState("");

  const payloadTable = useMemo(() => buildPayloadTable(payloadData, payloadOrder), [payloadData, payloadOrder]);

  const openDetail = (row) => {
    setPayloadData(row?.detail ?? row?.src_payload ?? null);
    setPayloadOpen(true);
  };

  const closePayload = () => {
    setPayloadOpen(false);
    setPayloadData(null);
  };

  const clinvarColumns = useMemo(() => [
    // { field: "has_update", headerName: "Updated", width: 110, sortable: true, valueFormatter: (v) => (getFormatterValue(v) ? "Yes" : "No") },
    // { field: "update_type", headerName: "Update Type", width: 140, sortable: true },
    // { field: "update_fields", headerName: "Changed Fields", width: 220, sortable: false },
  
    { field: "Chr", headerName: "Chr", width: 90, sortable: true },
    { field: "Start", headerName: "Start", width: 130, sortable: true, ...positionColumnProps },
    { field: "End", headerName: "End", width: 130, sortable: true, ...positionColumnProps },
    { field: "Ref", headerName: "Ref", width: 80, sortable: true },
    { field: "Alt", headerName: "Alt", width: 80, sortable: true },
    { field: "SYMBOL", headerName: "Gene.refGene", width: 160, sortable: true },
    { field: "AF", headerName: "AF", width: 110, sortable: true },
    { field: "TaiwanBioBank", headerName: "TaiwanBioBank", width: 170, sortable: true },
    { field: "case_count", headerName: "Cases", width: 110, sortable: true },
    { field: "analysis_case_total", headerName: "Total Cases", width: 120, sortable: true },
    { field: "case_ratio", headerName: "Case Ratio", width: 120, sortable: true },
    { field: "germline_classification", headerName: "Germline Classification", width: 230, sortable: true },
    { field: "germline_review_stars", headerName: "Germline Stars", width: 140, sortable: true },
    { field: "germline_submission_count", headerName: "Germline Submissions", width: 190, sortable: true },
    { field: "somatic_clinical_impact", headerName: "Somatic Clinical Impact", width: 300, sortable: true },
    { field: "somatic_oncogenicity", headerName: "Somatic Oncogenicity", width: 260, sortable: true },
    {
      field: "clinvar_url",
      headerName: "ClinVar URL",
      width: 120,
      renderCell: (p) => p.value ? <a href={p.value} target="_blank" rel="noreferrer">Open</a> : "",
      sortable: false,
    },
    { field: "last_evaluated_at", headerName: "Last Evaluated", width: 190, sortable: true, ...dateTimeColumnProps, renderHeader: timeHeader("last_evaluated_at") },
    { field: "src_created_at", headerName: "First Submission", width: 190, sortable: true, ...dateTimeColumnProps, renderHeader: timeHeader("src_created_at") },
    { field: "src_updated_at", headerName: "Last Submission", width: 190, sortable: true, ...dateTimeColumnProps, renderHeader: timeHeader("src_updated_at") },
    {
      field: "detail",
      headerName: "Detail",
      width: 150,
      sortable: false,
      filterable: false,
      renderCell: (params) => (
        <Button size="small" variant="outlined" onClick={() => openDetail(params.row)}>
          View Detail
        </Button>
      ),
    },
  ], []);

  const fetchBlacklist = async ({ page = paginationModelA.page, pageSize = paginationModelA.pageSize, sort = sortModelA, keyword = searchA } = {}) => {
    setLoadingA(true);
    setErrA("");
    const sortBy = sort[0]?.field || "Chr";
    const sortDir = sort[0]?.sort || "asc";

    try {
      if (!currentUid) throw new Error("Please sign in or provide a user_id");
      const { data } = await axios.post(API_BLACKLIST, {
        user_id: currentUid,
        page: page + 1,
        pageSize,
        sortBy,
        sortDir,
        q: (keyword || "").trim(),
      }, { headers: { "Content-Type": "application/json" }, timeout: 60000 });

      const outRows = Array.isArray(data?.rows) ? data.rows.map((r, i) => {
        const row = normalizePositionFields(r);
        const symbol = firstNonEmpty(row.SYMBOL, row.symbol, row["Gene.refGene"], row["Gene.refGeneWithVer"], row.Gene, row.gene_symbol);
        return {
          id: row.id ?? `${page}-${i}-${row.Chr || ""}-${row.Start || ""}-${row.Ref || ""}-${row.Alt || ""}`,
          ...row,
          SYMBOL: symbol,
          import_time: formatDateTimeCell(row.import_time),
          src_created_at: formatDateTimeCell(row.src_created_at),
          src_updated_at: formatDateTimeCell(row.src_updated_at),
        };
      }) : [];
      setRowsA(outRows);
      setTotalA(Number(data?.total ?? outRows.length));
    } catch (e) {
      setErrA(e?.response?.data?.error || e.message || "Failed to load");
      setRowsA([]);
      setTotalA(0);
    } finally {
      setLoadingA(false);
    }
  };

  const fetchImportedBlacklist = async ({ page = paginationModelC.page, pageSize = paginationModelC.pageSize, sort = sortModelC } = {}) => {
    setLoadingC(true);
    setErrC("");
    setDeleteMsgC("");
    setDeleteErrC("");
    const sortBy = sort[0]?.field || "import_time";
    const sortDir = sort[0]?.sort || "desc";

    try {
      if (!currentUid) throw new Error("Please sign in or provide a user_id");
      const { data } = await axios.post(API_IMPORTED_LIST, {
        user_id: currentUid,
        page: page + 1,
        pageSize,
        sortBy,
        sortDir,
      }, { headers: { "Content-Type": "application/json" }, timeout: 60000 });

      const outRows = Array.isArray(data?.rows) ? data.rows.map((r) => {
        const row = normalizePositionFields(r);
        return {
          id: row.id ?? `${row.Chr || ""}-${row.Start || ""}-${row.End || ""}-${row.Ref || ""}-${row.Alt || ""}`,
          ...row,
          SYMBOL: firstNonEmpty(row.SYMBOL, row.symbol, row["Gene.refGene"], row["Gene.refGeneWithVer"], row.Gene, row.gene_symbol),
          Gene: firstNonEmpty(row.SYMBOL, row.symbol, row["Gene.refGene"], row["Gene.refGeneWithVer"], row.Gene, row.gene_symbol),
          "Gene.refGene": firstNonEmpty(row.SYMBOL, row.symbol, row["Gene.refGene"], row["Gene.refGeneWithVer"], row.Gene, row.gene_symbol),
          import_time: formatDateTimeCell(row.import_time || row.created_at_db || row.created_at || ""),
          created_at_db: formatDateTimeCell(row.created_at_db || row.import_time || row.created_at || ""),
          src_created_at: formatDateTimeCell(row.src_created_at || ""),
          src_updated_at: formatDateTimeCell(row.src_updated_at || row.src_created_at || ""),
        };
      }) : [];
      setRowsC(outRows);
      setTotalC(Number(data?.total ?? outRows.length));
      setSelectionModelC([]);
    } catch (e) {
      setErrC(e?.response?.data?.error || e.message || "Failed to load");
      setRowsC([]);
      setTotalC(0);
      setSelectionModelC([]);
    } finally {
      setLoadingC(false);
    }
  };

  const fetchClinvarGroup = async (mode, { page, pageSize, sort, keyword = searchClinvar, updateFilter = clinvarUpdateFilter } = {}) => {
    const isExisting = mode === "intersect";
    const setLoading = isExisting ? setLoadingExisting : setLoadingNew;
    const setErr = isExisting ? setErrExisting : setErrNew;
    const setRows = isExisting ? setRowsExisting : setRowsNew;
    const setTotal = isExisting ? setTotalExisting : setTotalNew;
    const clearSelection = isExisting ? setSelectionExisting : setSelectionNew;

    setLoading(true);
    setErr("");

    const sortBy = sort?.[0]?.field || "last_evaluated_at";
    const sortDir = sort?.[0]?.sort || "desc";

    try {
      if (!currentUid) throw new Error("Please sign in or provide a user_id");
      const { data } = await axios.post(API_CLINVAR, {
        user_id: currentUid,
        mode,
        update_filter: updateFilter,
        page: page + 1,
        pageSize,
        sortBy,
        sortDir,
        q: (keyword || "").trim(),
        search: (keyword || "").trim(),
      }, { headers: { "Content-Type": "application/json" }, timeout: 60000 });

      const outRows = Array.isArray(data?.rows) ? data.rows.map((r, i) => {
        const row = normalizeClinvarRow(r);
        return {
          id: row.id ?? `${mode}-${page}-${i}-${row.Chr || ""}-${row.Start || ""}-${row.Ref || ""}-${row.Alt || ""}-${row.clinvar_url || ""}`,
          ...row,
          last_evaluated_at: formatDateTimeCell(row.last_evaluated_at || row.created_at || row.updated_at_db || ""),
          src_created_at: formatDateTimeCell(row.src_created_at || ""),
          src_updated_at: formatDateTimeCell(row.src_updated_at || ""),
        };
      }) : [];

      setRows(outRows);
      setTotal(Number(data?.total ?? outRows.length));
      if (Array.isArray(data?.columns)) setPayloadOrder(data.columns);
      clearSelection([]);
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || "Failed to load ClinVar results");
      setRows([]);
      setTotal(0);
      clearSelection([]);
    } finally {
      setLoading(false);
    }
  };

  const refreshClinvarAll = ({ resetPage = false } = {}) => {
    const pageExisting = resetPage ? { page: 0, pageSize: paginationExisting.pageSize } : paginationExisting;
    const pageNew = resetPage ? { page: 0, pageSize: paginationNew.pageSize } : paginationNew;
    if (resetPage) {
      setPaginationExisting(pageExisting);
      setPaginationNew(pageNew);
    }
    fetchClinvarGroup("intersect", { ...pageExisting, sort: sortExisting });
    fetchClinvarGroup("diff", { ...pageNew, sort: sortNew });
  };

  useEffect(() => {
    if (!currentUid) return;
    fetchBlacklist({ page: 0, pageSize: paginationModelA.pageSize });
    fetchImportedBlacklist({ page: 0, pageSize: paginationModelC.pageSize });
    refreshClinvarAll({ resetPage: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUid]);

  useEffect(() => {
    if (!currentUid) return;
    const t = setTimeout(() => {
      const first = { page: 0, pageSize: paginationModelA.pageSize };
      setPaginationModelA(first);
      fetchBlacklist({ ...first, sort: sortModelA, keyword: searchA });
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchA]);

  useEffect(() => {
    if (!currentUid) return;
    const t = setTimeout(() => {
      refreshClinvarAll({ resetPage: true });
    }, 350);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchClinvar, clinvarUpdateFilter]);

  const handleDeleteImportedSelected = async () => {
    setDeleteMsgC("");
    setDeleteErrC("");

    if (!selectionModelC?.length) {
      alert("Select at least one imported row to delete.");
      return;
    }
    if (!window.confirm(`Delete ${selectionModelC.length} selected user-imported blacklist records?`)) return;

    try {
      if (!currentUid) throw new Error("Please sign in or provide a user_id");
      const { data } = await axios.post(API_IMPORTED_DELETE, {
        user_id: currentUid,
        ids: selectionModelC,
      }, { headers: { "Content-Type": "application/json" }, timeout: 60000 });

      if (data?.ok) {
        setDeleteMsgC(`Deleted: ${data.deleted || 0} rows`);
        setSelectionModelC([]);
        fetchImportedBlacklist();
        fetchBlacklist();
      } else {
        setDeleteErrC(data?.error || "Delete failed");
      }
    } catch (e) {
      setDeleteErrC(e?.response?.data?.error || e.message || "Delete failed");
    }
  };

  const handleExcludeExistingSelected = async () => {
    setExcludeMsg("");
    setExcludeErr("");

    if (!selectionExisting?.length) {
      alert("Select at least one existing blacklist row to exclude.");
      return;
    }
    if (!window.confirm(`Exclude ${selectionExisting.length} selected records from the displayed blacklist?`)) return;

    try {
      if (!currentUid) throw new Error("Please sign in or provide a user_id");
      const selectedSet = new Set(selectionExisting);
      const rowsForExclude = rowsExisting.filter((row) => selectedSet.has(row.id));

      const { data } = await axios.post(API_ORIGINAL_EXCLUDE, {
        user_id: currentUid,
        rows: rowsForExclude,
        reason: "excluded from ClinVar existing blacklist review",
      }, { headers: { "Content-Type": "application/json" }, timeout: 60000 });

      if (data?.ok) {
        setExcludeMsg(`Excluded / updated: ${data.inserted_or_updated || rowsForExclude.length} records`);
        setSelectionExisting([]);
        fetchBlacklist();
        refreshClinvarAll({ resetPage: true });
      } else {
        setExcludeErr(data?.error || "Exclude failed");
      }
    } catch (e) {
      setExcludeErr(e?.response?.data?.error || e.message || "Exclude failed");
    }
  };

  const combinedPayloadTable = useMemo(() => {
    if (!rowsNew?.length || !selectionNew?.length) return { cols: [], rows: [] };

    const selectedSet = new Set(selectionNew);
    const merged = [];

    rowsNew.forEach((row) => {
      if (!selectedSet.has(row.id)) return;
      const payload = parseMaybeJson(row.detail ?? row.src_payload);

      const baseInfo = {
        SYMBOL: row.SYMBOL || row.Gene || row["Gene.refGene"] || "",
        Gene: row.SYMBOL || row.Gene || row["Gene.refGene"] || "",
        "Gene.refGene": row.SYMBOL || row["Gene.refGene"] || row.Gene || "",
        Chr: row.Chr,
        Start: row.Start,
        End: row.End,
        Ref: row.Ref,
        Alt: row.Alt,
        AF: row.AF,
        TaiwanBioBank: row.TaiwanBioBank,
        occurrence_count: row.occurrence_count,
        case_count: row.case_count,
        analysis_case_total: row.analysis_case_total,
        case_ratio: row.case_ratio,
        germline_classification: row.germline_classification,
        germline_review_stars: row.germline_review_stars,
        germline_submission_count: row.germline_submission_count,
        somatic_clinical_impact: row.somatic_clinical_impact,
        somatic_clinical_impact_review_stars: row.somatic_clinical_impact_review_stars,
        somatic_clinical_impact_submission_count: row.somatic_clinical_impact_submission_count,
        somatic_oncogenicity: row.somatic_oncogenicity,
        somatic_oncogenicity_review_stars: row.somatic_oncogenicity_review_stars,
        somatic_oncogenicity_submission_count: row.somatic_oncogenicity_submission_count,
        src_created_at: row.src_created_at,
        src_updated_at: row.src_updated_at,
        last_evaluated_at: row.last_evaluated_at || row.created_at,
      };

      if (Array.isArray(payload)) {
        payload.forEach((p) => {
          if (p && typeof p === "object") merged.push({ ...baseInfo, ...p });
          else merged.push({ ...baseInfo, payload: stringifyCell(p) });
        });
      } else if (payload && typeof payload === "object") {
        merged.push({ ...baseInfo, ...payload });
      } else {
        merged.push({ ...baseInfo, payload: stringifyCell(payload) });
      }
    });

    if (!merged.length) return { cols: [], rows: [] };

    const preferredOrder = [
      "SYMBOL", "Chr", "Start", "End", "Ref", "Alt", "AF", "TaiwanBioBank",
      "case_count", "analysis_case_total", "case_ratio",
      "germline_classification", "germline_review_stars", "germline_submission_count",
      "somatic_clinical_impact", "somatic_clinical_impact_review_stars", "somatic_clinical_impact_submission_count",
      "somatic_oncogenicity", "somatic_oncogenicity_review_stars", "somatic_oncogenicity_submission_count",
      ...(payloadOrder || []),
      "last_evaluated_at", "src_created_at", "src_updated_at",
    ];

    return buildPayloadTable(merged, preferredOrder);
  }, [rowsNew, selectionNew, payloadOrder]);

  const handleImportSelected = async () => {
    setImportMsg("");
    setImportErr("");

    if (!combinedPayloadTable.rows?.length) {
      alert("Select at least one new candidate row before importing.");
      return;
    }

    try {
      setImporting(true);
      if (!currentUid) throw new Error("Please sign in or provide a user_id");
      const rowsForImport = combinedPayloadTable.rows.map(({ id, ...rest }) => rest);
      const { data } = await axios.post(API_IMPORT_BLACKLIST, {
        user_id: currentUid,
        rows: rowsForImport,
      }, { headers: { "Content-Type": "application/json" }, timeout: 120000 });

      if (data?.error) {
        setImportErr(data.error || "Import failed");
      } else {
        setImportMsg(data?.message || "Import completed");
        setSelectionNew([]);
        fetchImportedBlacklist();
        fetchBlacklist();
        refreshClinvarAll({ resetPage: true });
      }
    } catch (e) {
      setImportErr(e?.response?.data?.error || e.message || "Import failed");
    } finally {
      setImporting(false);
    }
  };

  const resetClinvarFilters = () => {
    setSearchClinvar("");
    setClinvarUpdateFilter("updated");
    refreshClinvarAll({ resetPage: true });
  };

  return (
    <div style={{ minHeight: "100vh", padding: "28px 24px 48px", maxWidth: 1720, margin: "0 auto", background: "linear-gradient(180deg, #f6f9ff 0%, #ffffff 42%)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, marginBottom: 20, padding: "22px 24px", borderRadius: 20, background: "linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%)", color: "#fff", boxShadow: "0 18px 45px rgba(15, 23, 42, 0.20)" }}>
        <Typography variant="h4" sx={{ fontWeight: 800, color: "#fff", letterSpacing: 0.2 }}>
          Blacklist Management
        </Typography>

        <Button variant="contained" color="primary" size="large" sx={{ padding: "10px 20px", fontSize: "18px", fontWeight: "bold", borderRadius: "10px", boxShadow: "0 8px 22px rgba(59,130,246,0.35)", textTransform: "none" }} onClick={() => navigate("/variant/blacklist/add")}>
          Update ClinVar Crawl
        </Button>
      </div>

      <div style={{ marginBottom: 8 }}>
        <input value={searchA} onChange={(e) => setSearchA(e.target.value)} placeholder="Search by SYMBOL, Chr, Start, Ref, Alt, AF..." style={{ width: 420, padding: "12px 14px", borderRadius: 12, border: "1px solid #d6e0f0", outline: "none", background: "#fff", boxShadow: "0 2px 10px rgba(15,23,42,0.06)" }} />
        {errA && <div style={{ color: "red", fontSize: 12, marginTop: 6 }}>Load error: {errA}</div>}
      </div>

      <div style={{ height: 560, width: "100%", paddingBottom: 16, position: "relative" }}>
        <DataGrid
          rows={rowsA}
          columns={mainColumns}
          rowCount={totalA}
          loading={loadingA}
          slots={{ toolbar: GridToolbar }}
          disableRowSelectionOnClick
          pagination
          paginationMode="server"
          sortingMode="server"
          paginationModel={paginationModelA}
          onPaginationModelChange={(model) => {
            setPaginationModelA(model);
            fetchBlacklist({ page: model.page, pageSize: model.pageSize, sort: sortModelA, keyword: searchA });
          }}
          sortModel={sortModelA}
          onSortModelChange={(model) => {
            setSortModelA(model);
            const first = { page: 0, pageSize: paginationModelA.pageSize };
            setPaginationModelA(first);
            fetchBlacklist({ ...first, sort: model, keyword: searchA });
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          sx={gridSx}
        />
      </div>

      <div style={{ marginTop: 16, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography variant="h5" sx={{ fontWeight: 800, color: "#102a43" }}>
          Imported Blacklist Records / Update Log
        </Typography>

        <Button variant="outlined" color="error" size="small" onClick={handleDeleteImportedSelected} disabled={selectionModelC.length === 0 || loadingC}>
          Delete Selected ({selectionModelC.length})
        </Button>
      </div>

      {errC && <div style={{ color: "red", fontSize: 12, marginBottom: 4 }}>Load error: {errC}</div>}
      {deleteErrC && <div style={{ color: "red", fontSize: 12, marginBottom: 4 }}>Delete error: {deleteErrC}</div>}
      {deleteMsgC && <div style={{ color: "green", fontSize: 12, marginBottom: 4 }}>{deleteMsgC}</div>}

      <div style={{ height: 400, width: "100%", paddingBottom: 16, position: "relative" }}>
        <DataGrid
          rows={rowsC}
          columns={importedColumns}
          rowCount={totalC}
          loading={loadingC}
          disableRowSelectionOnClick
          checkboxSelection
          rowSelectionModel={selectionModelC}
          onRowSelectionModelChange={(newSelection) => setSelectionModelC(newSelection)}
          pagination
          paginationMode="server"
          sortingMode="server"
          paginationModel={paginationModelC}
          onPaginationModelChange={(model) => {
            setPaginationModelC(model);
            fetchImportedBlacklist({ page: model.page, pageSize: model.pageSize, sort: sortModelC });
          }}
          sortModel={sortModelC}
          onSortModelChange={(model) => {
            setSortModelC(model);
            const first = { page: 0, pageSize: paginationModelC.pageSize };
            setPaginationModelC(first);
            fetchImportedBlacklist({ ...first, sort: model });
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          slots={{ toolbar: GridToolbar }}
          sx={gridSx}
        />
      </div>

      <Divider style={{ margin: "16px 0" }} />

      <Typography variant="h5" sx={{ fontWeight: 800, color: "#102a43", mt: 2, mb: 1.5 }}>
        ClinVar Crawling Results
      </Typography>

      <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5, flexWrap: "wrap", rowGap: 1.5, p: 1.5, borderRadius: 3, border: "1px solid #dbe7f5", background: "#fff", boxShadow: "0 6px 18px rgba(15,23,42,0.06)" }}>
        <TextField
          size="small"
          label="Search ClinVar Results"
          placeholder="SYMBOL / Chr / HGVSc / rsID / classification..."
          value={searchClinvar}
          onChange={(e) => setSearchClinvar(e.target.value)}
          sx={{ minWidth: 360 }}
        />

        <TextField
          select
          size="small"
          label="Display"
          value={clinvarUpdateFilter}
          onChange={(e) => setClinvarUpdateFilter(e.target.value)}
          sx={{ minWidth: 190 }}
        >
          <MenuItem value="updated">Updated only</MenuItem>
          <MenuItem value="all">All crawled results</MenuItem>
          {/* <MenuItem value="unchanged">Unchanged only</MenuItem>
          <MenuItem value="new_result">First-time result only</MenuItem> */}
        </TextField>

        <Button variant="outlined" size="small" onClick={resetClinvarFilters}>
          Reset
        </Button>
      </Stack>

      <div style={{ marginTop: 10, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Typography variant="h6" sx={{ fontWeight: 800, color: "#102a43" }}>
            Matched Records
          </Typography>
          <Typography variant="body2" sx={{ color: "#64748b" }}>
            These input variants were found in the original blacklist. Excluding them writes to a user exclusion table and does not delete public.blacklist_ori.
          </Typography>
        </div>

        <Button variant="outlined" color="error" size="small" onClick={handleExcludeExistingSelected} disabled={selectionExisting.length === 0 || loadingExisting}>
          Exclude Selected ({selectionExisting.length})
        </Button>
      </div>

      {excludeErr && <div style={{ color: "red", fontSize: 12, marginBottom: 4 }}>Exclude error: {excludeErr}</div>}
      {excludeMsg && <div style={{ color: "green", fontSize: 12, marginBottom: 4 }}>{excludeMsg}</div>}
      {errExisting && <div style={{ color: "red", fontSize: 12, marginBottom: 4 }}>Load error: {errExisting}</div>}

      <div style={{ height: 480, width: "100%", paddingBottom: 16, position: "relative" }}>
        <DataGrid
          rows={rowsExisting}
          columns={clinvarColumns}
          rowCount={totalExisting}
          loading={loadingExisting}
          slots={{ toolbar: GridToolbar }}
          disableRowSelectionOnClick
          checkboxSelection
          rowSelectionModel={selectionExisting}
          onRowSelectionModelChange={(newSelection) => setSelectionExisting(newSelection)}
          pagination
          paginationMode="server"
          sortingMode="server"
          paginationModel={paginationExisting}
          onPaginationModelChange={(model) => {
            setPaginationExisting(model);
            fetchClinvarGroup("intersect", { page: model.page, pageSize: model.pageSize, sort: sortExisting });
          }}
          sortModel={sortExisting}
          onSortModelChange={(model) => {
            setSortExisting(model);
            const first = { page: 0, pageSize: paginationExisting.pageSize };
            setPaginationExisting(first);
            fetchClinvarGroup("intersect", { ...first, sort: model });
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          sx={gridSx}
          getRowHeight={() => "auto"}
        />
      </div>

      <div style={{ marginTop: 18, marginBottom: 8, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <Typography variant="h6" sx={{ fontWeight: 800, color: "#102a43" }}>
            New Candidate Records
          </Typography>
          <Typography variant="body2" sx={{ color: "#64748b" }}>
            These input variants were not found in the original blacklist. Selected rows can be imported into the user blacklist table.
          </Typography>
        </div>
      </div>

      {errNew && <div style={{ color: "red", fontSize: 12, marginBottom: 4 }}>Load error: {errNew}</div>}

      {combinedPayloadTable.rows.length > 0 && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "4px 0 8px" }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 800, color: "#102a43" }}>
              Selected New Candidate Payload Preview
            </Typography>

            <Button variant="contained" color="secondary" size="small" onClick={handleImportSelected} disabled={importing || combinedPayloadTable.rows.length === 0}>
              {importing ? "Importing..." : "Import to Blacklist Database"}
            </Button>
          </div>

          {importErr && <div style={{ color: "red", fontSize: 12, marginBottom: 4 }}>Import error: {importErr}</div>}
          {importMsg && <div style={{ color: "green", fontSize: 12, marginBottom: 4 }}>{importMsg}</div>}

          <div style={{ height: 360, width: "100%", marginBottom: 16 }}>
            <DataGrid
              rows={combinedPayloadTable.rows}
              columns={combinedPayloadTable.cols.map((col) => {
                if (isTimeField(col.field)) {
                  return {
                    ...col,
                    headerName: getDisplayHeader(col.field),
                    ...dateTimeColumnProps,
                    renderHeader: timeHeader(col.field),
                  };
                }
                return col;
              })}
              disableRowSelectionOnClick
              sortingMode="client"
              pagination
              paginationModel={paginationModelPayload}
              onPaginationModelChange={setPaginationModelPayload}
              pageSizeOptions={[10, 25, 50, 100]}
              getRowHeight={() => "auto"}
              slots={{ toolbar: GridToolbar }}
              sx={gridSx}
            />
          </div>
        </>
      )}

      <div style={{ height: 520, width: "100%", paddingBottom: 16, position: "relative" }}>
        <DataGrid
          rows={rowsNew}
          columns={clinvarColumns}
          rowCount={totalNew}
          loading={loadingNew}
          slots={{ toolbar: GridToolbar }}
          disableRowSelectionOnClick
          checkboxSelection
          rowSelectionModel={selectionNew}
          onRowSelectionModelChange={(newSelection) => {
            setSelectionNew(newSelection);
            setPaginationModelPayload((prev) => ({ ...prev, page: 0 }));
          }}
          pagination
          paginationMode="server"
          sortingMode="server"
          paginationModel={paginationNew}
          onPaginationModelChange={(model) => {
            setPaginationNew(model);
            fetchClinvarGroup("diff", { page: model.page, pageSize: model.pageSize, sort: sortNew });
          }}
          sortModel={sortNew}
          onSortModelChange={(model) => {
            setSortNew(model);
            const first = { page: 0, pageSize: paginationNew.pageSize };
            setPaginationNew(first);
            fetchClinvarGroup("diff", { ...first, sort: model });
          }}
          pageSizeOptions={[10, 25, 50, 100]}
          sx={gridSx}
          getRowHeight={() => "auto"}
        />
      </div>

      <Dialog open={payloadOpen} onClose={closePayload} maxWidth="lg" fullWidth>
        <DialogTitle sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          ClinVar Source Payload
          <IconButton onClick={closePayload} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>

        <DialogContent dividers>
          <div style={{ height: 520, width: "100%" }}>
            <DataGrid
              rows={payloadTable.rows}
              columns={payloadTable.cols}
              disableRowSelectionOnClick
              sortingMode="client"
              slots={{ toolbar: GridToolbar }}
              sx={gridSx}
              getRowHeight={() => "auto"}
            />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

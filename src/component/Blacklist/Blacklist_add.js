// src/pages/Blacklist_add.js
import React, { useEffect, useState, useMemo, useContext, useRef } from "react";
import axios from "axios";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
  Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useSearchParams } from "react-router-dom";
import { config } from "../../constant";
import { AuthContext } from "../Auth/AuthContext";

const norm = (s) => (s || "").replace(/\/+$/g, "");
const API_LIST          = `${norm(config.rootApiIP)}/blacklist_user_summary`; // 列表/讀表（抓 schema 與 vep_annovar_merge_*）
const API_COMPARE       = `${norm(config.rootApiIP)}/blacklist_compare`;      // 與 public.blacklist_ori 比較（交集/差集）
const API_CRAWL_START   = `${norm(config.rootApiIP)}/clinvar_start`;          // 批次爬蟲啟動
const API_CRAWL_STATUS  = `${norm(config.rootApiIP)}/clinvar_status`;         // 批次爬蟲進度查詢
const API_CRAWL_CANCEL  = `${norm(config.rootApiIP)}/clinvar_cancel`;         // 批次爬蟲取消

// localStorage key：加入 user_id 避免不同使用者覆蓋
const jobKey = (uid) => `clinvar_job_id:${uid}`;

const RUNNING_CRAWL_STATUSES = new Set(["pending", "running"]);
const isRunningCrawlStatus = (status) =>
  RUNNING_CRAWL_STATUSES.has(String(status || "").toLowerCase());

// 供組唯一 id（實際去重仍以後端為準）
const TARGET_COLS = [
  "Chr","Start","End","Ref","Alt",
  "SYMBOL","Func.refGene","avsnp150",
  "Feature","HGVSc","HGVSp","AAChange.refGene",
  "#Uploaded_variation"
];
const makeKey = (row) => TARGET_COLS.map(k => String(row?.[k] ?? "")).join("|");


const EXTRA_VISIBLE_FIELDS = [
  "SYMBOL",
  "Func.refGene",
  "ExonicFunc.refGene",
  "AAChange.refGene",
];

const PRIMARY_FIELD_ORDER = [
  "Chr",
  "Start",
  "End",
  "Ref",
  "Alt",
  "SYMBOL",
  "Func.refGene",
  "ExonicFunc.refGene",
  "AAChange.refGene",
  "case_count",
  "analysis_case_total",
  "case_ratio",
  "created_at",
  "updated_at",
];

const COLUMN_WIDTH_MAP = {
  SYMBOL: 170,
  "Func.refGene": 150,
  "ExonicFunc.refGene": 180,
  "AAChange.refGene": 280,
  case_count: 120,
  analysis_case_total: 140,
  case_ratio: 140,
  created_at: 180,
  updated_at: 180,
};

/* ---------------- detail 轉表格工具 ---------------- */
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

const DISPLAY_HEADER_MAP = {
  SYMBOL: "Gene.refGene",
  case_count: "Cases",
  analysis_case_total: "Total Cases",
  case_ratio: "Case Ratio",
  created_at: "First Submission",
  updated_at: "Last Submission",
  src_created_at: "First Submission",
  src_updated_at: "Last Submission",
  last_evaluated_at: "Last Evaluated",
  import_time: "Import Time",
};

// Keep only one of Occurrences / Cases in the visible table.
// Current setting: show Cases, hide Occurrences.
const HIDDEN_TABLE_FIELDS = new Set([
  "id",
  "occurrence_count",
  "Gene",
  "gene_symbol",
  "Gene.refGene",
  "Gene.refGeneWithVer",
  "Gene_refGene",
  "Gene_refGeneWithVer",
]);

function isHiddenTableField(field) {
  return HIDDEN_TABLE_FIELDS.has(String(field || ""));
}

function getDisplayHeader(field) {
  return DISPLAY_HEADER_MAP[field] || field;
}


function parseMaybeJson(value) {
  if (typeof value !== "string") return value;

  const text = value.trim();
  if (!text) return value;
  if (!text.startsWith("{") && !text.startsWith("[")) return value;

  try {
    return JSON.parse(text);
  } catch {
    return value;
  }
}

function getFieldFromPayload(payload, field) {
  const parsed = parseMaybeJson(payload);

  if (Array.isArray(parsed)) {
    const values = parsed
      .map((item) => getFieldFromPayload(item, field))
      .filter((v) => v !== null && v !== undefined && String(v).trim() !== "");

    return Array.from(new Set(values.map((v) => stringifyCell(v)))).join("; ");
  }

  if (parsed && typeof parsed === "object") {
    if (Object.prototype.hasOwnProperty.call(parsed, field)) {
      return parsed[field];
    }

    // Some APIs return detail as { key: value } rows. This keeps the extraction robust.
    if (Object.prototype.hasOwnProperty.call(parsed, "key") && parsed.key === field) {
      return parsed.value;
    }

    if (Object.prototype.hasOwnProperty.call(parsed, "Field") && parsed.Field === field) {
      return parsed.Value;
    }
  }

  return "";
}

function firstNonEmpty(...vals) {
  for (const v of vals) {
    if (v !== null && v !== undefined && String(v).trim() !== "") return v;
  }
  return "";
}

function getSymbolFromRowLike(row, payload) {
  return firstNonEmpty(
    row?.SYMBOL,
    row?.symbol,
    getFieldFromPayload(payload, "SYMBOL"),
    getFieldFromPayload(payload, "symbol"),
    row?.["Gene.refGene"],
    row?.["Gene.refGeneWithVer"],
    row?.Gene,
    row?.gene_symbol,
    getFieldFromPayload(payload, "Gene.refGene"),
    getFieldFromPayload(payload, "Gene.refGeneWithVer")
  );
}

function ensureAnnotationFields(row) {
  if (!row || typeof row !== "object") return row;

  const out = { ...row };
  const payload = out.detail ?? out.payload ?? null;

  out.SYMBOL = getSymbolFromRowLike(out, payload);

  EXTRA_VISIBLE_FIELDS.forEach((field) => {
    if (out[field] === null || out[field] === undefined || String(out[field]).trim() === "") {
      out[field] = field === "SYMBOL" ? getSymbolFromRowLike(out, payload) : getFieldFromPayload(payload, field);
    }
  });

  return out;
}

function orderTableKeys(keys) {
  const seen = new Set();
  const ordered = [];

  PRIMARY_FIELD_ORDER.forEach((field) => {
    if (keys.includes(field) && !seen.has(field)) {
      seen.add(field);
      ordered.push(field);
    }
  });

  keys.forEach((field) => {
    if (!seen.has(field)) {
      seen.add(field);
      ordered.push(field);
    }
  });

  return ordered;
}

function getFormatterValue(paramsOrValue) {
  if (paramsOrValue && typeof paramsOrValue === "object" && "value" in paramsOrValue) {
    return paramsOrValue.value;
  }
  return paramsOrValue;
}

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
  created_at: { label: "First Submission", help: TIME_HELP.firstSubmission },
  updated_at: { label: "Last Submission", help: TIME_HELP.lastSubmission },
  src_created_at: { label: "First Submission", help: TIME_HELP.firstSubmission },
  src_updated_at: { label: "Last Submission", help: TIME_HELP.lastSubmission },
  last_evaluated_at: { label: "Last Evaluated", help: TIME_HELP.lastEvaluated },
  import_time: { label: "Import Time", help: TIME_HELP.importTime },
};

function isDateTimeField(field) {
  return Boolean(TIME_FIELD_CONFIG[String(field || "")]);
}

function timeHeader(field) {
  const cfg = TIME_FIELD_CONFIG[String(field || "")];
  if (!cfg) return undefined;
  return () => <HeaderWithHelp label={cfg.label} help={cfg.help} />;
}

function formatDateTimeCell(v) {
  if (v === null || v === undefined || v === "") return "";

  const raw = String(v).trim();
  if (!raw) return "";

  const m = raw.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/);
  if (m) return `${m[1]} ${m[2]}`;

  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;

  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatDisplayCell(field, value) {
  if (field === "Start" || field === "End") return formatIntegerCell(value);
  if (isDateTimeField(field)) return formatDateTimeCell(value);
  return stringifyCell(value);
}

function normalizeDisplayFields(row) {
  if (!row || typeof row !== "object") return row;
  const out = { ...row };
  Object.keys(out).forEach((field) => {
    out[field] = formatDisplayCell(field, out[field]);
  });
  return out;
}

const positionColumnProps = {
  valueFormatter: (paramsOrValue) => formatIntegerCell(getFormatterValue(paramsOrValue)),
};

const dateTimeColumnProps = {
  minWidth: 170,
  width: 180,
  valueFormatter: (paramsOrValue) => formatDateTimeCell(getFormatterValue(paramsOrValue)),
};

function buildGridColumns(keys, { minWidth = 120, maxWidth = 420, widthMultiplier = 12 } = {}) {
  return orderTableKeys(keys)
    .filter((k) => !isHiddenTableField(k))
    .map((k) => ({
      field: k,
      headerName: getDisplayHeader(k),
      width: COLUMN_WIDTH_MAP[k] || Math.max(minWidth, Math.min(maxWidth, String(getDisplayHeader(k)).length * widthMultiplier)),
      ...(k === "Start" || k === "End" ? positionColumnProps : {}),
      ...(isDateTimeField(k) ? dateTimeColumnProps : {}),
      ...(timeHeader(k) ? { renderHeader: timeHeader(k) } : {}),
    }));
}

const gridSx = {
  border: "1px solid #e5edf7",
  borderRadius: 3,
  backgroundColor: "#fff",
  boxShadow: "0 10px 28px rgba(15, 23, 42, 0.08)",
  "& .MuiDataGrid-columnHeaders": { backgroundColor: "#f1f5fb", fontWeight: 800 },
  "& .MuiDataGrid-row:hover": { backgroundColor: "#f8fbff" },
};
/** 將 detail/payload 建成可給 DataGrid 的 { cols, rows }（preferredOrder 來自後端 columns） */
function buildPayloadTable(data, preferredOrder = []) {
  const order = Array.isArray(preferredOrder) ? preferredOrder : [];

  // 情況 1：物件陣列 -> 每一鍵成欄
  if (Array.isArray(data) && data.length > 0 && typeof data[0] === "object" && !Array.isArray(data[0])) {
    const pageKeys = Array.from(new Set(data.flatMap(obj => Object.keys(obj || {}))));
    const seen = new Set();
    const colsOrder = [];
    for (const k of order) if (pageKeys.includes(k) && !seen.has(k)) { seen.add(k); colsOrder.push(k); }
    for (const k of pageKeys) if (!seen.has(k)) { seen.add(k); colsOrder.push(k); }

    const visibleColsOrder = colsOrder.filter((k) => !isHiddenTableField(k));
    const cols = buildGridColumns(visibleColsOrder, { minWidth: 120, maxWidth: 360, widthMultiplier: 12 });
    const rows = data.map((obj, i) => {
      const row = { id: obj?.id ?? i + 1 };
      visibleColsOrder.forEach(k => {
        row[k] = formatDisplayCell(k, obj?.[k]);
      });
      return row;
    });
    return { cols, rows };
  }

  // 情況 2：一般物件 -> 兩欄 Key / Value
  if (data && typeof data === "object" && !Array.isArray(data)) {
    const cols = [
      { field: "key", headerName: "Field", width: 220 },
      { field: "value", headerName: "Value", flex: 1, minWidth: 300 }
    ];
    const keysAll = Object.keys(data).filter((k) => !isHiddenTableField(k));
    const seen = new Set();
    const keysInOrder = [];
    for (const k of order) if (k in data && !seen.has(k) && !isHiddenTableField(k)) { seen.add(k); keysInOrder.push(k); }
    for (const k of keysAll) if (!seen.has(k)) { seen.add(k); keysInOrder.push(k); }

    const rows = keysInOrder.map((k, i) => ({
      id: i + 1,
      key: getDisplayHeader(k),
      value: formatDisplayCell(k, data[k])
    }));
    return { cols, rows };
  }

  // 情況 3：其他型別
  const cols = [
    { field: "key", headerName: "Field", width: 120 },
    { field: "value", headerName: "Value", flex: 1, minWidth: 300 }
  ];
  const rows = [{ id: 1, key: "detail", value: stringifyCell(data) }];
  return { cols, rows };
}
/* --------------------------------------------------- */

export default function BlacklistAdd() {
  const [searchParams] = useSearchParams();
  const initialUid = searchParams.get("user_id") || "";

  const { userId } = useContext(AuthContext);

  const [schema, setSchema] = useState("");
  const [tables, setTables] = useState([]);
  const [table, setTable] = useState("");

  const [rows, setRows] = useState([]);
  const [columns, setColumns] = useState([]);
  const [total, setTotal] = useState(0);

  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // 比較（交集 / 差集）
  const [sameRows, setSameRows] = useState([]);
  const [sameCols, setSameCols] = useState([]);
  const [sameTotal, setSameTotal] = useState(0);
  const [sameLoading, setSameLoading] = useState(false);

  const [diffRows, setDiffRows] = useState([]);
  const [diffCols, setDiffCols] = useState([]);
  const [diffTotal, setDiffTotal] = useState(0);
  const [diffLoading, setDiffLoading] = useState(false);

  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });

  // 比較表的分頁
  const [samePagination, setSamePagination] = useState({ page: 0, pageSize: 25 });
  const [diffPagination, setDiffPagination] = useState({ page: 0, pageSize: 25 });

  // ClinVar Query Scope：both=交集+差集；intersect=Existing blacklist only；diff=New candidates only
  const [crawlMode, setCrawlMode] = useState("diff");

  const hasTableSelected = useMemo(() => Boolean(table), [table]);

  // ===== detail 檢視對話框 =====
  const [payloadOpen, setPayloadOpen] = useState(false);
  const [payloadData, setPayloadData] = useState(null);
  // 從後端 /blacklist_compare 帶回來的原始Field順序
  const [payloadOrder, setPayloadOrder] = useState([]);

  const openDetail = (row) => {
    setPayloadData(row?.detail ?? row?.payload ?? null);
    setPayloadOpen(true);
  };
  const closePayload = () => {
    setPayloadOpen(false);
    setPayloadData(null);
  };

  const payloadTable = useMemo(
    () => buildPayloadTable(payloadData, payloadOrder),
    [payloadData, payloadOrder]
  );

  // ====== 批次爬蟲進度（含恢復機制） ======
  const [crawlJobId, setCrawlJobId] = useState("");
  const [crawlProgress, setCrawlProgress] = useState({
    status: "idle",
    total: 0,
    processed: 0,
    percent: 0,
    last_error: ""
  });
  const isCrawlRunning = isRunningCrawlStatus(crawlProgress.status);
  const pollRef = useRef(null);

  // 避免同一個 user_id 重複觸發頁面進入時的自動比較
  const autoCompareUidRef = useRef(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const handleCompareAll = () => {
    const initSame = { page: 0, pageSize: samePagination.pageSize };
    const initDiff = { page: 0, pageSize: diffPagination.pageSize };
    setSamePagination(initSame);
    setDiffPagination(initDiff);
    fetchCompare("intersect", initSame);
    fetchCompare("diff", initDiff);
  };

  const applyCrawlStatus = (data, fallbackJobId = "") => {
    const status = data?.status || "idle";
    const jobId = data?.job_id || fallbackJobId || "";

    setCrawlJobId(jobId);
    setCrawlProgress({
      status,
      total: Number(data?.total || 0),
      processed: Number(data?.processed || 0),
      percent: Number(data?.percent || 0),
      last_error: data?.last_error || ""
    });

    return { status, jobId };
  };

  const clearCrawlState = (uid) => {
    stopPolling();
    if (uid) localStorage.removeItem(jobKey(uid));
    setCrawlJobId("");
    setCrawlProgress({
      status: "idle",
      total: 0,
      processed: 0,
      percent: 0,
      last_error: ""
    });
  };

  const startPolling = (jobId) => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await axios.post(
          API_CRAWL_STATUS,
          { job_id: jobId },
          { headers: { "Content-Type": "application/json" } }
        );

        if (!data || data.error || data.active === false || data.status === "idle") {
          const uid = Number(userId || initialUid);
          clearCrawlState(uid);
          return;
        }

        const uid = Number(userId || initialUid);
        const { status, jobId: currentJobId } = applyCrawlStatus(data, jobId);
        if (uid && currentJobId) localStorage.setItem(jobKey(uid), currentJobId);

        // 任務完成/錯誤/取消：停止輪詢並清掉 localStorage，且自動刷新交/差集
        if (["done", "error", "canceled"].includes(status)) {
          stopPolling();
          if (uid) localStorage.removeItem(jobKey(uid));
          handleCompareAll();
        }
      } catch (e) {
        // 連線暫失敗不中斷輪詢
      }
    }, 1500);
  };

  const getCrawlModeText = (mode) => {
    if (mode === "intersect") return "Existing blacklist only";
    if (mode === "diff") return "New candidates only";
    return "Both matched and new candidates";
  };

  const handleStartCrawl = async () => {
    try {
      const uid = Number(userId || initialUid);
      if (!uid) throw new Error("Please sign in or provide a valid user_id");

      const body = { user_id: uid, mode: crawlMode, resolve_mode: "entrez", scrape: true };
      const { data } = await axios.post(API_CRAWL_START, body, {
        headers: { "Content-Type": "application/json" }
      });
      if (!data?.job_id) throw new Error("No job_id was returned");

      const status = data.status || "running";

      setCrawlJobId(data.job_id);
      localStorage.setItem(jobKey(uid), data.job_id); // 儲存 job_id 以便回頁面恢復
      setCrawlProgress({
        status,
        total: Number(data.total || 0),
        processed: Number(data.processed || 0),
        percent: Number(data.percent || 0),
        last_error: data.last_error || ""
      });
      startPolling(data.job_id);
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || "Failed to start ClinVar crawl");
    }
  };

  const handleCancelCrawl = async () => {
    try {
      const uid = Number(userId || initialUid);
      if (!crawlJobId && !uid) return;

      await axios.post(
        API_CRAWL_CANCEL,
        crawlJobId ? { job_id: crawlJobId } : { user_id: uid },
        { headers: { "Content-Type": "application/json" } }
      );

      // 後端會把 job.status 更新成 canceled；前端同步關閉輪詢與按鈕
      stopPolling();
      if (uid) localStorage.removeItem(jobKey(uid));
      setCrawlProgress((p) => ({ ...p, status: "canceled" }));
      setCrawlJobId("");
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || "Failed to cancel crawl");
    }
  };

  // 頁面掛載時：先用 localStorage 恢復；若 localStorage 遺失，再向後端查詢目前 active job
  useEffect(() => {
    const uid = Number(userId || initialUid);
    if (!uid) return;

    let cancelled = false;

    const tryRestore = async (body, fallbackJobId = "") => {
      try {
        const { data } = await axios.post(
          API_CRAWL_STATUS,
          body,
          { headers: { "Content-Type": "application/json" } }
        );

        if (cancelled) return false;

        if (
          !data ||
          data.error ||
          data.active === false ||
          ["done", "error", "canceled", "idle"].includes(data.status)
        ) {
          return false;
        }

        const { jobId } = applyCrawlStatus(data, fallbackJobId);
        const restoredJobId = jobId || fallbackJobId;

        if (!restoredJobId) return false;

        localStorage.setItem(jobKey(uid), restoredJobId);
        startPolling(restoredJobId);
        return true;
      } catch (e) {
        return false;
      }
    };

    (async () => {
      const savedJobId = localStorage.getItem(jobKey(uid));

      if (savedJobId) {
        const restored = await tryRestore({ job_id: savedJobId }, savedJobId);
        if (restored || cancelled) return;

        localStorage.removeItem(jobKey(uid));
      }

      // localStorage 沒有 job_id 或已失效時，仍可從後端找該 user 的 pending/running job
      await tryRestore({ user_id: uid, active: true });
    })();

    return () => {
      cancelled = true;
      stopPolling();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, initialUid]);

  useEffect(() => () => stopPolling(), []); // 卸載清理
  // ==========================

  // 取得 vep_annovar_merge_* 表清單
  const fetchTables = async ({ autoCompare = false } = {}) => {
    setErr("");
    setLoading(true);
    try {
      const uid = Number(userId || initialUid);
      if (!uid) throw new Error("Please sign in or provide a valid user_id");
      const { data } = await axios.post(
        API_LIST,
        { user_id: uid },
        { headers: { "Content-Type": "application/json" } }
      );
      if (!data || !Array.isArray(data.tables))
        throw new Error("Invalid API response. Expected {schema, tables}.");
      setSchema(data.schema || "");
      setTables(data.tables || []);
      setTable("");
      setRows([]);
      setColumns([]);
      setTotal(0);
      setPaginationModel((p) => ({ ...p, page: 0 }));
      // 清空比較區
      setSameRows([]);
      setSameCols([]);
      setSameTotal(0);
      setDiffRows([]);
      setDiffCols([]);
      setDiffTotal(0);
      setSamePagination({ page: 0, pageSize: samePagination.pageSize });
      setDiffPagination({ page: 0, pageSize: diffPagination.pageSize });

      // 進入頁面後自動計算交集與差集，不需要再按按鈕
      if (autoCompare) {
        handleCompareAll();
      }
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || "Failed to load table list");
      setSchema("");
      setTables([]);
      setTable("");
    } finally {
      setLoading(false);
    }
  };

  // 單表讀原始資料
  const fetchRows = async ({
    page = paginationModel.page,
    pageSize = paginationModel.pageSize
  } = {}) => {
    setErr("");
    setLoading(true);
    try {
      const uid = Number(userId || initialUid);
      if (!uid) throw new Error("Please sign in or provide a valid user_id");
      if (!table) throw new Error("Please select a table first");
      const body = { user_id: uid, table, page: page + 1, pageSize };
      const { data } = await axios.post(API_LIST, body, {
        headers: { "Content-Type": "application/json" }
      });
      if (!data || !Array.isArray(data.rows))
        throw new Error("Invalid API response. Expected {rows, total}.");
      const expandedRows = data.rows.map((r) => ensureAnnotationFields(r));
      const cols = expandedRows.length
        ? buildGridColumns(Object.keys(expandedRows[0]), { minWidth: 100, maxWidth: 400, widthMultiplier: 14 })
        : columns;
      const withId = expandedRows.map((r, i) => ({
        ...normalizeDisplayFields(r),
        id: r.id ?? `${data.page || (page + 1)}-${i}`
      }));
      setColumns(cols);
      setRows(withId);
      setTotal(Number(data.total ?? withId.length));
    } catch (e) {
      setErr(e?.response?.data?.error || e.message || "Failed to load data");
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  // 比較 API 呼叫（交集 / 差集）
  const fetchCompare = async (mode, { page, pageSize }) => {
    setErr("");
    const setLoadingFn = mode === "intersect" ? setSameLoading : setDiffLoading;
    const setColsFn = mode === "intersect" ? setSameCols : setDiffCols;
    const setRowsFn = mode === "intersect" ? setSameRows : setDiffRows;
    const setTotalFn = mode === "intersect" ? setSameTotal : setDiffTotal;

    setLoadingFn(true);
    try {
      const uid = Number(userId || initialUid);
      if (!uid) throw new Error("Please sign in or provide a valid user_id");
      const body = { user_id: uid, mode, page: page + 1, pageSize };
      const { data } = await axios.post(API_COMPARE, body, {
        headers: { "Content-Type": "application/json" }
      });
      if (!data || !Array.isArray(data.rows))
        throw new Error("Invalid API response. Expected {rows, total}.");

      const expandedRows = data.rows.map((r) => ensureAnnotationFields(r));
      const rawCols = expandedRows.length
        ? buildGridColumns(Object.keys(expandedRows[0]), { minWidth: 120, maxWidth: 420, widthMultiplier: 12 })
        : mode === "intersect"
        ? sameCols
        : diffCols;

      // 先拿掉 payload/detail Field，最後補 detail 按鈕欄
      const baseCols = rawCols.filter(
        (c) => c.field !== "payload" && c.field !== "detail" && !isHiddenTableField(c.field)
      );
      const cols = [
        ...baseCols,
        {
          field: "detail",
          headerName: "Detail",
          width: 140,
          sortable: false,
          filterable: false,
          renderCell: (params) => (
            <Button size="small" variant="outlined" onClick={() => openDetail(params.row)}>
              View Detail
            </Button>
          )
        }
      ];

      // 儲存後端提供的原始Field順序（作為 detail 顯示依據）
      if (Array.isArray(data.columns)) {
        setPayloadOrder(data.columns);
      }

      const withId = expandedRows.map((r, i) => ({
        ...normalizeDisplayFields(r),
        id: (r.id ?? makeKey(r)) || `${data.page || (page + 1)}-${i}`
      }));

      setColsFn(cols);
      setRowsFn(withId);
      setTotalFn(Number(data.total ?? withId.length));
    } catch (e) {
      setErr(
        e?.response?.data?.error ||
          e.message ||
          (mode === "intersect" ? "Failed to load matched records" : "Failed to load unmatched records")
      );
      setRowsFn([]);
      setTotalFn(0);
    } finally {
      setLoadingFn(false);
    }
  };

  // 初次進入頁面：當 userId 可用就載表清單，並自動計算交集與差集
  useEffect(() => {
    const uid = Number(userId || initialUid);
    if (!uid) return;

    const shouldAutoCompare = autoCompareUidRef.current !== uid;
    autoCompareUidRef.current = uid;

    fetchTables({ autoCompare: shouldAutoCompare });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, initialUid]);

  // 切表時刷新該表內容
  useEffect(() => {
    if (hasTableSelected) {
      setPaginationModel((p) => ({ ...p, page: 0 }));
      fetchRows({ page: 0 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table]);

  return (
    <div style={{ minHeight: "100vh", padding: "28px 24px 56px", maxWidth: 1720, margin: "0 auto", background: "linear-gradient(180deg, #f6f9ff 0%, #ffffff 42%)" }}>
      <Typography variant="h4" sx={{ fontWeight: 800, color: "#102a43", mb: 0.5 }}>Blacklist Candidate Review</Typography>
      <Typography variant="body2" sx={{ color: "#64748b", mb: 2 }}>Review VEP/ANNOVAR results, compare against the original blacklist, and launch ClinVar crawling jobs.</Typography>

      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{ mb: 2, flexWrap: "wrap", rowGap: 1.5, p: 2, borderRadius: 4, background: "#fff", boxShadow: "0 12px 30px rgba(15,23,42,0.08)", border: "1px solid #e5edf7" }}
      >


        <FormControl size="small" sx={{ minWidth: 320 }}>
          <InputLabel id="table-select-label">Select table (vep_annovar_merge_*)</InputLabel>
          <Select
            labelId="table-select-label"
            value={table}
            label="Select table"
            onChange={(e) => setTable(e.target.value)}
            disabled={!tables.length}
          >
            {tables.map((t) => (
              <MenuItem key={t} value={t}>
                {t}
              </MenuItem>
            ))}
          </Select>
        </FormControl>




        {/* 啟動批次爬蟲 + 顯示進度 */}
        <FormControl
          size="small"
          sx={{ minWidth: 260 }}
          disabled={isCrawlRunning}
        >
          <InputLabel id="crawl-mode-label">ClinVar Query Scope</InputLabel>
          <Select
            labelId="crawl-mode-label"
            value={crawlMode}
            label="ClinVar Query Scope"
            onChange={(e) => setCrawlMode(e.target.value)}
          >
            <MenuItem value="both">Both matched and new candidates</MenuItem>
            <MenuItem value="intersect">Existing blacklist only</MenuItem>
            <MenuItem value="diff">New candidates only</MenuItem>
          </Select>
        </FormControl>

        <Button
          variant="outlined"
          color="secondary"
          onClick={handleStartCrawl}
          disabled={isCrawlRunning}
        >
          Start ClinVar Query: {getCrawlModeText(crawlMode)}
        </Button>

        <Button
          variant="outlined"
          color="error"
          onClick={handleCancelCrawl}
          disabled={!isCrawlRunning || !crawlJobId}
          sx={{ ml: 1 }}
        >
          Cancel Crawl
        </Button>

        {crawlJobId && (
          <Typography variant="body2" sx={{ ml: 1 }}>
            Job: <b>{crawlJobId.slice(0, 8)}</b>
          </Typography>
        )}

        {schema && (
          <Typography variant="body2" sx={{ ml: 1 }}>
            Schema: <b>{schema}</b>
          </Typography>
        )}
        {err && (
          <Typography variant="body2" color="error" sx={{ ml: 1 }}>
            Error: {err}
          </Typography>
        )}
      </Stack>

      {/* 進度條區塊（可從 localStorage 恢復） */}
      {crawlProgress.status !== "idle" && (
        <Box sx={{ mt: 1, mb: 1 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <Box sx={{ minWidth: 220 }}>
              <Typography variant="caption" color="text.secondary">
                Crawl Status: {crawlProgress.status}
              </Typography>
              <Box sx={{ mt: 0.5 }}>
                <Typography variant="body2">
                  {crawlProgress.processed} / {crawlProgress.total || "?"} ({crawlProgress.percent}%)
                </Typography>
              </Box>
            </Box>
            <Box sx={{ flex: 1 }}>
              <div style={{ paddingTop: 6 }}>
                <div style={{ height: 8, background: "#eee", borderRadius: 6 }}>
                  <div
                    style={{
                      width: `${crawlProgress.percent}%`,
                      height: "100%",
                      borderRadius: 6,
                      background: "#1976d2",
                      transition: "width .4s ease"
                    }}
                  />
                </div>
              </div>
            </Box>
            {crawlProgress.last_error && (
              <Typography variant="body2" color="error">
                {crawlProgress.last_error}
              </Typography>
            )}
          </Stack>
        </Box>
      )}

      {/* 原始資料 */}
      <Typography variant="h6" sx={{ fontWeight: 800, color: "#102a43", mt: 2, mb: 1 }}>Source Table Records</Typography>
      <div style={{ height: 420, width: "100%", marginTop: 4 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          rowCount={total}
          loading={loading}
          pagination
          paginationMode="server"
          sortingMode="client"
          slots={{ toolbar: GridToolbar }}
          sx={gridSx}
          paginationModel={paginationModel}
          onPaginationModelChange={(m) => {
            setPaginationModel(m);
            if (hasTableSelected) fetchRows({ page: m.page, pageSize: m.pageSize });
          }}
          pageSizeOptions={[10, 25, 50, 100, 200]}
          disableRowSelectionOnClick
        />
      </div>

      {/* 交集 */}
      <Typography variant="h6" sx={{ fontWeight: 800, color: "#102a43", mt: 3, mb: 1 }}>Matched Records</Typography>
      <div style={{ height: 520, width: "100%", marginTop: 4 }}>
        <DataGrid
          rows={sameRows}
          columns={sameCols}
          rowCount={sameTotal}
          loading={sameLoading}
          pagination
          paginationMode="server"
          sortingMode="client"
          slots={{ toolbar: GridToolbar }}
          sx={gridSx}
          paginationModel={samePagination}
          onPaginationModelChange={(m) => {
            setSamePagination(m);
            fetchCompare("intersect", { page: m.page, pageSize: m.pageSize });
          }}
          pageSizeOptions={[10, 25, 50, 100, 200]}
          disableRowSelectionOnClick
          getRowId={(r) => r.id ?? makeKey(r)}
          getRowHeight={() => "auto"}
        />
      </div>

      {/* 差集 */}
      <Typography variant="h6" sx={{ fontWeight: 800, color: "#102a43", mt: 3, mb: 1 }}>New Candidate Records</Typography>
      <div style={{ height: 520, width: "100%", marginTop: 4 }}>
        <DataGrid
          rows={diffRows}
          columns={diffCols}
          rowCount={diffTotal}
          loading={diffLoading}
          pagination
          paginationMode="server"
          sortingMode="client"
          slots={{ toolbar: GridToolbar }}
          sx={gridSx}
          paginationModel={diffPagination}
          onPaginationModelChange={(m) => {
            setDiffPagination(m);
            fetchCompare("diff", { page: m.page, pageSize: m.pageSize });
          }}
          pageSizeOptions={[10, 25, 50, 100, 200]}
          disableRowSelectionOnClick
          getRowId={(r) => r.id ?? makeKey(r)}
          getRowHeight={() => "auto"}
        />
      </div>

      {/* detail 檢視對話框（表格） */}
      <Dialog open={payloadOpen} onClose={closePayload} maxWidth="lg" fullWidth>
        <DialogTitle
          sx={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
        >
          Raw Detail
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
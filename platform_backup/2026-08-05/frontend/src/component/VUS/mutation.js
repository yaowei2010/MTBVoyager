// MutationViewer.jsx
import React, { useState, useRef, useMemo, useEffect } from "react";
import {
  Box,
  Typography,
  Paper,
  Button,
  Stack,
  Divider,
  IconButton,
  Menu,
  MenuItem,
  FormControl,
  Select,
  InputLabel,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

const TABLE_HEIGHT = 420;

// Parse R-style title: italic("TP53") ~ ... 74.42 ...
function parseTitle(raw) {
  if (!raw) return null;
  const geneMatch = raw.match(/italic\("([^"]+)"\)/);
  const rateMatch = raw.match(/([0-9]+(?:\.[0-9]+)?)/);
  const gene = geneMatch ? geneMatch[1] : "";
  const rate = rateMatch ? rateMatch[1] : "";
  if (!gene && !rate) return null;
  return { gene, rate };
}

/* ---------------------- Classification: consistent with oncoprint / lollipop ---------------------- */
const CATEGORY_COLORS = {
  truncating: "#000000",
  missense: "#26A537",
  splice: "#FF8C00",
  inframe: "#7A4CC2",
  synonymous: "#8A8A8A",
  other: "#ECECEC",
};

const CATEGORY_LABELS = {
  truncating: "Truncating",
  missense: "Missense",
  splice: "Splice",
  inframe: "Inframe",
  synonymous: "Synonymous",
  other: "Other",
};

function toGroup(vcRaw) {
  const vc = String(vcRaw || "").trim().toLowerCase();

  if (
    [
      "nonsense_mutation",
      "frame_shift_del",
      "frame_shift_ins",
      "frame_shift",
      "stop_gained",
      "stopgain",
      "nonstop_mutation",
      "translation_start_site",
      "start_codon_del",
      "start_codon_ins",
      "start_codon_snp",
      "startloss",
      "stop_lost",
      "start_lost",
    ].includes(vc)
  ) {
    return "truncating";
  }

  if (
    [
      "splice_site",
      "splice",
      "splice_region",
      "splice_acceptor_variant",
      "splice_donor_variant",
      "splice_region_variant",
      "splice_polypyrimidine_tract_variant",
    ].includes(vc)
  ) {
    return "splice";
  }

  if (
    [
      "in_frame_del",
      "in_frame_ins",
      "in_frame",
      "inframe_deletion",
      "inframe_insertion",
    ].includes(vc)
  ) {
    return "inframe";
  }

  if (
    [
      "missense_mutation",
      "snp_missense",
      "missense",
      "missense_variant",
    ].includes(vc)
  ) {
    return "missense";
  }

  if (
    [
      "silent",
      "synonymous",
      "synonymous_variant",
      "stop_retained_variant",
    ].includes(vc)
  ) {
    return "synonymous";
  }

  return "other";
}

function hexToRgb(hex) {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return m
    ? { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) }
    : { r: 0, g: 0, b: 0 };
}

function withAlpha(hex, alpha = 0.15) {
  const { r, g, b } = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function isMissingLike(v) {
  const s = String(v ?? "").trim();
  if (!s) return true;
  const low = s.toLowerCase();
  return (
    low === "-" ||
    low === "na" ||
    low === "n/a" ||
    low === "none" ||
    low === "null"
  );
}

/* Do not classify as other only because Protein_Change is missing */
function getRowGroup(row) {
  const vc =
    row?.Variant_Classification ??
    row?.variant_classification ??
    row?.Consequence ??
    row?.consequence ??
    row?.Mutation_Type ??
    row?.mutation_type ??
    "";

  return toGroup(vc);
}

/* -------------------- Summary panel -------------------- */
const SimpleStatsPanel = ({ stats }) => {
  const order = [
    "truncating",
    "splice",
    "inframe",
    "missense",
    "synonymous",
    "other",
  ];
  const total = stats.total || 0;

  return (
    <Paper elevation={1} sx={{ p: 2, width: 340, flex: "0 0 340px" }}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ mb: 1 }}
      >
        <Typography variant="subtitle1" sx={{ color: "#000" }}>
          Summary
        </Typography>
      </Stack>

      <Stack alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="body2" color="#000">
          Total rows
        </Typography>
        <Typography variant="h6" color="#000">
          {total}
        </Typography>
      </Stack>

      <Divider sx={{ mb: 1 }} />

      <Stack direction="row" spacing={2} sx={{ px: 1, mb: 0.5 }}>
        <Typography variant="caption" sx={{ flex: 1, color: "#000" }}>
          Variant group
        </Typography>
        <Typography
          variant="caption"
          sx={{ width: 140, textAlign: "right", color: "#000" }}
        >
          Count ( % )
        </Typography>
      </Stack>

      <Stack spacing={0.5}>
        {order.map((g) => {
          const cnt = stats.byType[g]?.count || 0;
          const pct = total ? (cnt * 100) / total : 0;
          const base = CATEGORY_COLORS[g] || CATEGORY_COLORS.other;

          const rowBgAlpha = g === "truncating" ? 0.18 : 0.1;
          const pillBgAlpha = g === "truncating" ? 0.22 : 0.25;
          const borderAlpha = g === "truncating" ? 0.65 : 0.35;

          return (
            <Stack
              key={g}
              direction="row"
              alignItems="center"
              spacing={1}
              sx={{
                border: `1px solid ${withAlpha(base, borderAlpha)}`,
                borderRadius: 1,
                px: 1,
                py: 0.5,
                background: withAlpha(base, rowBgAlpha),
              }}
            >
              <Typography variant="body2" sx={{ flex: 1, color: "#000" }}>
                {CATEGORY_LABELS[g] || g}
              </Typography>
              <Box
                sx={{
                  minWidth: 140,
                  textAlign: "right",
                  borderRadius: "16px",
                  border: `1px solid ${base}`,
                  background: withAlpha(base, pillBgAlpha),
                  color: "#000000",
                  fontSize: 13,
                  px: 1,
                  py: 0.2,
                }}
              >
                {cnt} ({pct.toFixed(1)}%)
              </Box>
            </Stack>
          );
        })}
      </Stack>
    </Paper>
  );
};

/* -------------------- isoform / field detection -------------------- */
function getIsoformValueFromRow(row) {
  if (!row) return "";
  return String(
    row?.Protein_ID ?? row?.protein_id ?? row?.refseq_protein ?? ""
  ).trim();
}

function detectProteinChangeKey(rows) {
  if (!rows || !rows[0]) return "Protein_Change";
  return (
    Object.keys(rows[0]).find((k) => k.toLowerCase() === "protein_change") ||
    "Protein_Change"
  );
}

function filterMafByIsoform(mafRowsRaw, isoformID) {
  if (!isoformID) return mafRowsRaw;
  if (!Array.isArray(mafRowsRaw) || mafRowsRaw.length === 0) return mafRowsRaw;

  return mafRowsRaw.filter(
    (r) => getIsoformValueFromRow(r) === String(isoformID).trim()
  );
}

/* Recalculate the isoform counts shown in parentheses */
function buildIsoformCounts(mafRowsRaw, isoforms) {
  const counts = {};

  for (const iso of isoforms || []) {
    counts[String(iso.isoformID)] = 0;
  }

  for (const row of mafRowsRaw || []) {
    const iso = getIsoformValueFromRow(row);
    if (!iso) continue;
    if (!(iso in counts)) counts[iso] = 0;
    counts[iso] += 1;
  }

  return counts;
}

/* -------------------- Build mutations from MAF; only use Protein_Change for plotting -------------------- */
function buildMutationsFromMaf(mafRowsRaw, proteinChangeKey = "Protein_Change") {
  const byKey = {};

  for (const r of mafRowsRaw || []) {
    const label = String(r?.[proteinChangeKey] ?? "").trim();
    if (!label) continue; // Rows without Protein_Change are not plotted in the lollipop chart

    const m = label.match(/(\d+)/);
    if (!m) continue;

    const aaPos = Number(m[1]);
    const key = `${aaPos}|${label}`;

    if (!byKey[key]) {
      const group = getRowGroup(r);
      byKey[key] = {
        aaPos,
        label,
        class:
          r.Variant_Classification ||
          r.variant_classification ||
          r.Consequence ||
          r.consequence ||
          "",
        color: CATEGORY_COLORS[group] || CATEGORY_COLORS.other,
        yValue: 0,
      };
    }

    byKey[key].yValue += 1;
  }

  return Object.values(byKey).sort((a, b) => b.yValue - a.yValue);
}

function niceTicks(maxValue, maxTicks = 5) {
  if (!(maxValue > 0)) return [];
  const order = Math.pow(10, Math.floor(Math.log10(maxValue)));
  const candidates = [1, 2, 2.5, 5, 10].map((m) => m * order);

  let step = candidates[0];
  for (const s of candidates) {
    if (Math.ceil(maxValue / s) <= maxTicks) {
      step = s;
      break;
    }
  }

  const niceMax = Math.ceil(maxValue / step) * step;
  const ticks = [];
  for (let v = 0; v <= niceMax; v += step) ticks.push(v);
  return ticks.filter((v) => v > 0);
}

function ConsequenceCell({ value, row }) {
  const text = String(value ?? "").trim();
  if (!text) return <div style={{ whiteSpace: "pre-wrap" }} />;

  const group = getRowGroup(row);
  const color = CATEGORY_COLORS[group] || CATEGORY_COLORS.other;

  return (
    <div style={{ whiteSpace: "pre-wrap", width: "100%", paddingTop: 4, paddingBottom: 4 }}>
      <span
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 12,
          border: `1px solid ${color}`,
          background: withAlpha(color, 0.16),
          color: "#111827",
          fontSize: 12,
          lineHeight: 1.4,
        }}
      >
        {text}
      </span>
    </div>
  );
}

/* ============================== Main component ============================== */
const MutationViewer = ({ data, maf, width = 1000, height = 360 }) => {
  let mafRowsRaw = [];
  try {
    mafRowsRaw = typeof maf === "string" ? JSON.parse(maf) : Array.isArray(maf) ? maf : [];
  } catch {
    mafRowsRaw = [];
  }

  const isoforms = Array.isArray(data?.isoforms) ? data.isoforms : null;

  const [isoformID, setIsoformID] = useState(() => {
    if (isoforms && isoforms.length) {
      return data?.defaultIsoform || isoforms[0]?.isoformID || "";
    }
    return "";
  });

  useEffect(() => {
    if (isoforms && isoforms.length) {
      setIsoformID(data?.defaultIsoform || isoforms[0]?.isoformID || "");
    } else {
      setIsoformID("");
    }
  }, [data?.defaultIsoform, isoforms?.length]);

  const isoformCounts = useMemo(() => {
    return buildIsoformCounts(mafRowsRaw, isoforms || []);
  }, [mafRowsRaw, isoforms]);

  const curData = useMemo(() => {
    if (!isoforms || !isoforms.length) return data;
    const hit = isoforms.find((x) => String(x.isoformID) === String(isoformID));
    return hit || isoforms[0];
  }, [data, isoforms, isoformID]);

  const mafRowsForPlot = useMemo(() => {
    if (!isoforms || !isoforms.length) return mafRowsRaw;
    return filterMafByIsoform(mafRowsRaw, isoformID);
  }, [mafRowsRaw, isoforms, isoformID]);

  const proteinChangeKeyPlot = useMemo(
    () => detectProteinChangeKey(mafRowsForPlot),
    [mafRowsForPlot]
  );

  /* The table no longer excludes rows without Protein_Change */
  const mafRowsForTable = useMemo(() => {
    if (!isoforms || !isoforms.length) return mafRowsRaw;

    const isoRows = filterMafByIsoform(mafRowsRaw, isoformID);

    const noPcRows = mafRowsRaw.filter((r) => {
      const proteinChange = r?.Protein_Change ?? r?.protein_change;
      const proteinId = getIsoformValueFromRow(r);
      return isMissingLike(proteinChange) && isMissingLike(proteinId);
    });

    const seen = new Set();

    const keyOf = (r) =>
      [
        r.Chromosome,
        r.Start_Position,
        r.End_Position,
        r.Reference_Allele,
        r.Tumor_Seq_Allele2,
        r.Tumor_Sample_Barcode,
        r.Protein_ID,
        r.Protein_Change,
        r.Consequence,
      ]
        .map((x) => String(x ?? ""))
        .join("|");

    const out = [];

    for (const r of isoRows) {
      const k = keyOf(r);
      if (seen.has(k)) continue;
      seen.add(k);
      out.push(r);
    }

    for (const r of noPcRows) {
      const k = keyOf(r);
      if (seen.has(k)) continue;
      seen.add(k);
      out.push(r);
    }

    return out;
  }, [mafRowsRaw, isoforms, isoformID]);

  const proteinChangeKeyTable = useMemo(
    () => detectProteinChangeKey(mafRowsForTable),
    [mafRowsForTable]
  );

  const stats = useMemo(() => {
    const res = { total: 0, byType: {} };

    for (const r of mafRowsForTable) {
      const group = getRowGroup(r);
      if (!res.byType[group]) res.byType[group] = { count: 0 };
      res.byType[group].count += 1;
      res.total += 1;
    }

    ["truncating", "splice", "inframe", "missense", "synonymous", "other"].forEach((g) => {
      if (!res.byType[g]) res.byType[g] = { count: 0 };
    });

    return res;
  }, [mafRowsForTable]);

  const padding = 60;
  const topPad = 70;
  const barY = topPad + (height - topPad) / 2;

  const proteinLength = Number(curData?.proteinLength || 0) || 1;
  const STEM_BASE_Y = barY - 10;

  const mutations = useMemo(() => {
    const built = buildMutationsFromMaf(mafRowsForPlot, proteinChangeKeyPlot);
    if (built.length > 0) return built;

    return (curData?.mutations || []).map((m) => ({
      aaPos: m.aaPos,
      label: m.label,
      class: m.class,
      color: m.color || CATEGORY_COLORS[toGroup(m.class)] || CATEGORY_COLORS.other,
      yValue: m.yValue ?? 1,
    }));
  }, [mafRowsForPlot, proteinChangeKeyPlot, curData?.mutations]);

  const groupsByPosAndY = useMemo(() => {
    const map = new Map();

    for (const m of mutations) {
      if (!map.has(m.aaPos)) map.set(m.aaPos, new Map());
      const inner = map.get(m.aaPos);
      const y = Number(m.yValue) || 0;
      if (!inner.has(y)) inner.set(y, []);
      inner.get(y).push(m);
    }

    for (const [, inner] of map) {
      for (const [, list] of inner) {
        list.sort((a, b) => String(a.label).localeCompare(String(b.label)));
      }
    }

    return map;
  }, [mutations]);

  const [selectedByPosY, setSelectedByPosY] = useState({});
  const [selectedPC, setSelectedPC] = useState(null);

  useEffect(() => {
    setSelectedByPosY({});
    setSelectedPC(null);
  }, [isoformID]);

  const displayMutations = useMemo(() => {
    const out = [];

    for (const [aaPos, inner] of groupsByPosAndY.entries()) {
      const yVals = Array.from(inner.keys()).sort((a, b) => a - b);

      for (const y of yVals) {
        const list = inner.get(y);

        if (list.length === 1) {
          out.push({ ...list[0], _hasConflictSameY: false, _options: list });
        } else {
          const key = `${aaPos}|${y}`;
          const wanted = selectedByPosY[key];
          let chosen = list[0];

          if (wanted) {
            const found = list.find((x) => String(x.label) === String(wanted));
            if (found) chosen = found;
          }

          out.push({ ...chosen, _hasConflictSameY: true, _options: list });
        }
      }
    }

    out.sort((a, b) => a.aaPos - b.aaPos || Number(a.yValue || 0) - Number(b.yValue || 0));
    return out;
  }, [groupsByPosAndY, selectedByPosY]);

  const { yScale, yTicks, yMaxForScale } = useMemo(() => {
    const maxV = Math.max(1, ...displayMutations.map((m) => +m.yValue || 0));
    const ticks = niceTicks(maxV, 5);
    const niceMax = ticks.length ? ticks[ticks.length - 1] : maxV;

    const topLimit = topPad + 8;
    const available = Math.max(20, STEM_BASE_Y - topLimit);
    const unit = available / (niceMax + 0.25);

    const scale = (v) => {
      const vv = Math.max(0, Math.min(niceMax, +v || 0));
      const y = STEM_BASE_Y - vv * unit;
      return Math.max(topLimit, Math.min(STEM_BASE_Y, y));
    };

    return { yScale: scale, yTicks: ticks, yMaxForScale: niceMax };
  }, [displayMutations, STEM_BASE_Y]);

  const [tooltip, setTooltip] = useState(null);
  const containerRef = useRef(null);

  const showTip = (e, text) => {
    const rect = containerRef.current?.getBoundingClientRect?.();
    if (!rect) return;
    const x = e.clientX - rect.left + 10;
    const y = e.clientY - rect.top + 10;
    setTooltip({ x, y, text });
  };

  const hideTip = () => setTooltip(null);

  const [menuAnchor, setMenuAnchor] = useState(null);
  const [menuKey, setMenuKey] = useState(null);
  const [menuOptions, setMenuOptions] = useState([]);

  const openConflictMenu = (evt, aaPos, yValue, options) => {
    setMenuAnchor(evt.currentTarget);
    setMenuKey(`${aaPos}|${yValue}`);
    setMenuOptions(options);
  };

  const closeConflictMenu = () => {
    setMenuAnchor(null);
    setMenuKey(null);
    setMenuOptions([]);
  };

  const chooseOption = (opt) => {
    setSelectedByPosY((prev) => ({ ...prev, [menuKey]: opt.label }));
    setSelectedPC((prev) => (prev === opt.label ? prev : opt.label));
    closeConflictMenu();
  };

  const TABLE_FIELD_CONFIG = [
    { field: "Diagnosis", headerName: "Diagnosis", width: 160 },
    { field: "Chromosome", headerName: "Chromosome", width: 120 },
    { field: "Start_Position", headerName: "Start_Position", width: 140 },
    { field: "End_Position", headerName: "End_Position", width: 140 },
    { field: "Reference_Allele", headerName: "Reference_Allele", width: 150 },
    { field: "Alternative_Allele", headerName: "Alternative_Allele", width: 150 },
    { field: "Tumor_Sample_Barcode", headerName: "Tumor_Sample_Barcode", width: 180 },
    { field: "Mutation_Type", headerName: "Mutation Type", width: 220 },
    { field: "Protein_Change", headerName: "Protein_Change", width: 160 },
  ];

  const mafColumns = TABLE_FIELD_CONFIG.map((col) => ({
    field: col.field,
    headerName: col.headerName,
    width: col.width,
    renderCell: (params) => {
      if (col.field === "Mutation_Type") {
        return <ConsequenceCell value={params.value} row={params.row} />;
      }
      return <div style={{ whiteSpace: "pre-wrap" }}>{String(params.value ?? "")}</div>;
    },
  }));

  const mafRowsAll =
    mafRowsForTable && mafRowsForTable.length
      ? mafRowsForTable.map((r, i) => ({
          id: i,
          Chromosome: r.Chromosome ?? "",
          Start_Position: r.Start_Position ?? "",
          End_Position: r.End_Position ?? "",
          Reference_Allele: r.Reference_Allele ?? "",
          Alternative_Allele: r.Tumor_Seq_Allele2 ?? "",
          Tumor_Sample_Barcode: r.Tumor_Sample_Barcode ?? "",
          Diagnosis: r.diagnosis ?? "",
          Mutation_Type: r.Consequence ?? "",
          Protein_Change: r.Protein_Change ?? "",
          Variant_Classification: r.Variant_Classification ?? r.variant_classification ?? "",
          Consequence: r.Consequence ?? "",
        }))
      : [];

  const mafRowsShown =
    selectedPC && mafRowsAll.length
      ? mafRowsAll.filter((r) => String(r[proteinChangeKeyTable]) === String(selectedPC))
      : mafRowsAll;

  const parsedTitle = parseTitle(curData?.title?.text);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box sx={{ display: "flex", gap: 2 }}>
        <Paper elevation={1} sx={{ p: 1, flex: 1 }}>
          {isoforms && isoforms.length > 0 && (
            <Box
              sx={{
                px: 1,
                pt: 1,
                display: "flex",
                gap: 2,
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <FormControl size="small" sx={{ minWidth: 320 }}>
                <InputLabel id="isoform-select-label">Isoform</InputLabel>
                <Select
                  labelId="isoform-select-label"
                  value={isoformID || ""}
                  label="Isoform"
                  onChange={(e) => setIsoformID(e.target.value)}
                >
                  {isoforms.map((x) => (
                    <MenuItem key={x.isoformID} value={x.isoformID}>
                      {x.isoformID} ({isoformCounts[x.isoformID] ?? 0})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Typography variant="body2" sx={{ color: "#000" }}>
                Protein length: <b>{proteinLength}</b>
              </Typography>
            </Box>
          )}

          <div ref={containerRef} style={{ position: "relative", textAlign: "center", height }}>
            <svg width={width} height={height} style={{ display: "inline-block" }}>
              {parsedTitle ? (
                <>
                  <text x={width / 2} y={24} textAnchor="middle" fontSize="18" fontWeight="bold" fill="#000">
                    {parsedTitle.gene}
                  </text>
                  {isoforms && isoforms.length > 0 && isoformID ? (
                    <text x={width / 2} y={44} textAnchor="middle" fontSize="12" fill="#334155">
                      {isoformID}
                    </text>
                  ) : null}
                </>
              ) : (
                <>
                  <text x={width / 2} y={30} textAnchor="middle" fontSize="18" fontWeight="bold" fill="#000">
                    {curData?.title?.text || ""}
                  </text>
                  {isoforms && isoforms.length > 0 && isoformID ? (
                    <text x={width / 2} y={50} textAnchor="middle" fontSize="12" fill="#334155">
                      {isoformID}
                    </text>
                  ) : null}
                </>
              )}

              <rect x={60} y={barY - 10} width={width - 120} height={20} fill="#888" />

              {yTicks.length > 0 && (
                <>
                  <line
                    x1={padding - 24}
                    y1={yScale(yMaxForScale)}
                    x2={padding - 24}
                    y2={STEM_BASE_Y + 6}
                    stroke="#000"
                  />
                  <text
                    x={padding - 54}
                    y={(yScale(yMaxForScale) + (STEM_BASE_Y + 12)) / 2}
                    textAnchor="middle"
                    fontSize="12"
                    fill="#000"
                    transform={`rotate(-90 ${padding - 54} ${(yScale(yMaxForScale) + (STEM_BASE_Y + 6)) / 2})`}
                  >
                    Sample count
                  </text>
                  {yTicks.map((t, i) => {
                    const y = yScale(t);
                    return (
                      <g key={`yt-${i}`}>
                        <line x1={padding - 28} y1={y} x2={padding - 20} y2={y} stroke="#000" />
                        <text x={padding - 32} y={y + 4} textAnchor="end" fontSize="11" fill="#000">
                          {t}
                        </text>
                        <line
                          x1={padding}
                          y1={y}
                          x2={width - padding}
                          y2={y}
                          stroke="#000"
                          strokeOpacity="0.15"
                          strokeDasharray="3 3"
                        />
                      </g>
                    );
                  })}
                </>
              )}

              {(curData?.domains || []).map((d, i) => {
                const x0 = (d.startAA / proteinLength) * (width - 2 * padding) + padding;
                const x1 = (d.endAA / proteinLength) * (width - 2 * padding) + padding;
                const w = Math.max(0, x1 - x0);

                return (
                  <rect
                    key={`dom-${i}`}
                    x={x0}
                    y={barY - 15}
                    width={w}
                    height={30}
                    fill={d.color}
                    stroke="#000"
                    onMouseEnter={(e) => showTip(e, `${d.name}\n${d.startAA}–${d.endAA}`)}
                    onMouseLeave={hideTip}
                  />
                );
              })}

              {displayMutations.map((m, i) => {
                const x = (m.aaPos / proteinLength) * (width - 2 * padding) + padding;
                const y = yScale(m.yValue);
                const isActive = selectedPC === m.label;

                const exX = x + 10;
                const exY = y - 12;

                return (
                  <g key={`mut-${i}`}>
                    <line
                      x1={x}
                      y1={STEM_BASE_Y}
                      x2={x}
                      y2={y}
                      stroke={m.color}
                      strokeWidth={isActive ? 2.5 : 1.5}
                      opacity={selectedPC && !isActive ? 0.3 : 1}
                    />
                    <circle
                      cx={x}
                      cy={y}
                      r={isActive ? 7 : 6}
                      fill={m.color}
                      stroke="#000"
                      opacity={selectedPC && !isActive ? 0.3 : 1}
                      onMouseEnter={(e) =>
                        showTip(
                          e,
                          `${m.label}\nAA pos: ${m.aaPos}\nCount: ${m.yValue}\nClass: ${
                            CATEGORY_LABELS[toGroup(m.class)] || m.class
                          }`
                        )
                      }
                      onMouseLeave={hideTip}
                      onClick={() => setSelectedPC((prev) => (prev === m.label ? null : m.label))}
                      style={{ cursor: "pointer" }}
                    />

                    {m._hasConflictSameY && (
                      <foreignObject x={exX - 10} y={exY - 10} width={24} height={24}>
                        <IconButton
                          size="small"
                          onClick={(evt) => openConflictMenu(evt, m.aaPos, m.yValue, m._options)}
                          title={`This position (AA ${m.aaPos}) has ${m._options.length} variants with the same sample count (${m.yValue}). Click to choose which one to display.`}
                          sx={{ p: 0, width: 24, height: 24, background: "rgba(255,255,255,0.9)" }}
                        >
                          <ErrorOutlineIcon fontSize="small" />
                        </IconButton>
                      </foreignObject>
                    )}
                  </g>
                );
              })}

              {(() => {
                const ticks = curData?.axis?.xTicks || [];
                const minLabelGap = 28;

                return ticks.map((t, i) => {
                  const x = (t / proteinLength) * (width - 2 * padding) + padding;

                  let showLabel = true;

                  // Hide the second-to-last label if it is too close to the last label
                  if (i === ticks.length - 2 && ticks.length >= 2) {
                    const lastTick = ticks[ticks.length - 1];
                    const lastX =
                      (lastTick / proteinLength) * (width - 2 * padding) + padding;

                    if (Math.abs(lastX - x) < minLabelGap) {
                      showLabel = false;
                    }
                  }

                  return (
                    <g key={`tick-${i}`}>
                      <line x1={x} y1={barY + 12} x2={x} y2={barY + 18} stroke="#000" />
                      {showLabel && (
                        <text
                          x={x}
                          y={barY + 32}
                          textAnchor="middle"
                          fontSize="11"
                          fill="#000"
                        >
                          {t}
                        </text>
                      )}
                    </g>
                  );
                });
              })()}
            </svg>

            {tooltip && (
              <div
                style={{
                  position: "absolute",
                  left: tooltip.x,
                  top: tooltip.y,
                  background: "rgba(255,255,255,0.95)",
                  border: "1px solid #888",
                  borderRadius: 4,
                  padding: "6px 10px",
                  fontSize: 12,
                  pointerEvents: "none",
                  whiteSpace: "pre-line",
                  boxShadow: "0 2px 6px rgba(0,0,0,0.2)",
                  color: "#000",
                }}
              >
                {tooltip.text}
              </div>
            )}
          </div>
        </Paper>

        <SimpleStatsPanel stats={stats} />
      </Box>

      <Paper elevation={1} sx={{ p: 1 }}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mb: 1, flexWrap: "wrap", gap: 1 }}
        >
          <Typography variant="subtitle1" color="#000">
            MAF Table
          </Typography>

          {selectedPC && (
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="body2" color="#000">
                Filtered by Protein_Change = <b>{selectedPC}</b>
              </Typography>
              <Button size="small" onClick={() => setSelectedPC(null)}>
                Clear
              </Button>
            </Stack>
          )}
        </Stack>

        <div style={{ height: TABLE_HEIGHT, width: "100%" }}>
          <DataGrid
            rows={mafRowsShown.map((r, i) => ({ id: i, ...r }))}
            columns={mafColumns}
            pageSize={10}
            rowsPerPageOptions={[10, 20, 50, 100]}
          />
        </div>
      </Paper>

      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={closeConflictMenu}
        anchorOrigin={{ vertical: "top", horizontal: "left" }}
        transformOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        {menuOptions.map((opt, idx) => {
          const group = toGroup(opt.class);
          const color = CATEGORY_COLORS[group] || CATEGORY_COLORS.other;

          return (
            <MenuItem
              key={`${menuKey}-${idx}-${opt.label}`}
              onClick={() => chooseOption(opt)}
              sx={{ display: "flex", gap: 1 }}
            >
              <span
                style={{
                  display: "inline-block",
                  width: 10,
                  height: 10,
                  borderRadius: 2,
                  background: color,
                  border: "1px solid #000",
                }}
              />
              <span style={{ minWidth: 70 }}>{opt.label}</span>
              <span style={{ color: "#555" }}>
                class: {CATEGORY_LABELS[group] || opt.class || "NA"}
              </span>
              <span style={{ marginLeft: "auto", color: "#000" }}>
                count: {opt.yValue}
              </span>
            </MenuItem>
          );
        })}
      </Menu>
    </Box>
  );
};

export default MutationViewer;
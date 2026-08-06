// src/component/VUS/oncoprint.jsx
import React, { useMemo, useRef, useState } from "react";

/** Backward compatible: extract sample id from source_table */
export function extractSampleId(sourceTable = "") {
  const s = String(sourceTable).trim();
  if (!s) return "";
  let tok = (s.split(/\s+/).pop() || s).trim();
  tok = tok.replace(/^vep_annovar_merge_/, "");
  return tok;
}

function pointerXY(evt, dx = 10, dy = 10) {
  const e = evt?.touches && evt.touches[0] ? evt.touches[0] : evt;
  return { x: (e?.clientX || 0) + dx, y: (e?.clientY || 0) + dy };
}

/* =========================================================
 * Diagnosis colors: high-contrast palette
 * ========================================================= */

/** Use a high-contrast palette first; automatically generate more colors when needed */
const DIAGNOSIS_DISTINCT_PALETTE = [
  "#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e",
  "#17becf", "#8c564b", "#e377c2", "#bcbd22", "#7f7f7f",
  "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
  "#3182bd", "#31a354", "#756bb1", "#e6550d", "#636363",
  "#6baed6", "#74c476", "#9e9ac8", "#fd8d3c", "#969696",
  "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00",
  "#ffff33", "#a65628", "#f781bf", "#999999"
];

function hash32(str) {
  let h = 0 >>> 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h >>> 0;
}

/** Fallback: golden-angle HSL to reduce color collisions */
function hslToHex(h, s, l) {
  s /= 100;
  l /= 100;
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const hp = h / 60;
  const x = c * (1 - Math.abs((hp % 2) - 1));

  let r = 0, g = 0, b = 0;
  if (0 <= hp && hp < 1) [r, g, b] = [c, x, 0];
  else if (1 <= hp && hp < 2) [r, g, b] = [x, c, 0];
  else if (2 <= hp && hp < 3) [r, g, b] = [0, c, x];
  else if (3 <= hp && hp < 4) [r, g, b] = [0, x, c];
  else if (4 <= hp && hp < 5) [r, g, b] = [x, 0, c];
  else if (5 <= hp && hp < 6) [r, g, b] = [c, 0, x];

  const m = l - c / 2;
  const toHex = (v) => {
    const n = Math.round((v + m) * 255);
    return n.toString(16).padStart(2, "0");
  };

  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

function distinctColorFromIndex(i) {
  if (i < DIAGNOSIS_DISTINCT_PALETTE.length) return DIAGNOSIS_DISTINCT_PALETTE[i];
  const hue = (i * 137.508) % 360;
  const sat = 65;
  const light = 48;
  return hslToHex(hue, sat, light);
}

/** For diagnosis: assign stable colors by sorted unique diagnosis labels */
export function buildDiagnosisColorMap(labels = []) {
  const uniq = Array.from(new Set((labels || []).map((x) => String(x || "").trim()).filter(Boolean))).sort();
  const out = {};
  uniq.forEach((lab, idx) => {
    out[lab] = distinctColorFromIndex(idx);
  });
  return out;
}

/** Keep the legacy function, but no longer use a small palette */
export function stringToColorStable(s) {
  const h = hash32(String(s ?? ""));
  return distinctColorFromIndex(h % DIAGNOSIS_DISTINCT_PALETTE.length);
}

export function normalizeGeneLabel(q = "") {
  const s = String(q || "").trim();
  if (!s) return "";
  return s.split(/[.\s]/)[0].toUpperCase();
}

/* =========================================================
 * diagnosis-only data
 * ========================================================= */

export function buildOncoByDiagnosis(fullResults = [], allTables = []) {
  const samples = [];
  const addUnique = (arr, v) => {
    if (v != null && v !== "" && !arr.includes(v)) arr.push(v);
  };

  const sampleDiag = new Map();
  for (const row of fullResults || []) {
    const sid = extractSampleId(row.source_table || "");
    if (!sid) continue;
    addUnique(samples, sid);
    const diag = (row.diagnosis ?? row.Diagnosis ?? "").toString().trim();
    if (diag && !sampleDiag.has(sid)) sampleDiag.set(sid, diag);
  }
  for (const t of allTables || []) {
    const sid = extractSampleId(t);
    if (sid) addUnique(samples, sid);
  }

  const genes = ["Diagnosis"];
  const alterations = [];
  for (const sid of samples) {
    const diag = sampleDiag.get(sid);
    if (diag) alterations.push({ sample: sid, gene: "Diagnosis", type: "diagnosis", value: diag });
  }

  const diagnosisColors = buildDiagnosisColorMap(Array.from(sampleDiag.values()));

  return { genes, samples, alterations, meta: { kind: "diagnosis", diagnosisColors } };
}

/* =========================================================
 * Mutation classes: collapsed into 5 categories
 * ========================================================= */

export const ALTERATION_COLOR_MAP = {
  truncating: "#111111",
  missense: "#26A537",
  splice: "#FF8C00",
  inframe: "#7A4CC2",
  synonymous: "#BDBDBD",
};

export const ALTERATION_LABEL_MAP = {
  truncating: "Truncating Mutation",
  missense: "Missense Mutation",
  splice: "Splice-site Mutation",
  inframe: "Inframe Mutation",
  synonymous: "Synonymous Mutation",
};

const ALTERATION_PRIORITY = [
  "truncating",
  "splice",
  "inframe",
  "missense",
  "synonymous",
];

function collapseOncoPrintClass(rawType = "") {
  const t = String(rawType || "").trim();

  if (["stopgain", "stoploss", "frameshift", "startloss"].includes(t)) return "truncating";
  if (t === "splicing") return "splice";
  if (["inframe_insertion", "inframe_deletion"].includes(t)) return "inframe";
  if (t === "missense") return "missense";
  if (t === "synonymous") return "synonymous";

  return null;
}

function chooseDominantAlteration(types = []) {
  if (!types.length) return null;
  const uniq = Array.from(new Set(types));
  uniq.sort((a, b) => {
    const ia = ALTERATION_PRIORITY.indexOf(a);
    const ib = ALTERATION_PRIORITY.indexOf(b);
    const va = ia === -1 ? 999 : ia;
    const vb = ib === -1 ? 999 : ib;
    return va - vb;
  });
  return uniq[0];
}

/* =========================================================
 * overview oncoprint data
 * ========================================================= */

export function buildQueryOncoPrint(perQueryData = {}, queryList = []) {
  const sampleSet = new Set();
  const sampleDiagnosis = new Map();
  const geneEventMap = new Map();

  const queryGenes = Array.from(
    new Set((queryList || []).map(normalizeGeneLabel).filter(Boolean))
  );

  for (const gene of queryGenes) {
    geneEventMap.set(gene, new Map());
  }

  for (const q of queryList || []) {
    const gene = normalizeGeneLabel(q);
    const d = perQueryData?.[q];
    if (!d || !gene) continue;

    const rows = Array.isArray(d.oncoprint_maf) ? d.oncoprint_maf : [];

    for (const row of rows) {
      const rowGene = String(row.Hugo_Symbol || "").toUpperCase().trim();
      if (rowGene !== gene) continue;

      const sid = String(row.Tumor_Sample_Barcode || "").trim();
      if (!sid) continue;

      sampleSet.add(sid);

      const diag = String(row.diagnosis || "").trim();
      if (diag && !sampleDiagnosis.has(sid)) {
        sampleDiagnosis.set(sid, diag);
      }

      const rawType = String(row.OncoPrint_Class || "other").trim() || "other";
      const altType = collapseOncoPrintClass(rawType);

      if (!altType) continue;

      if (!geneEventMap.get(gene).has(sid)) {
        geneEventMap.get(gene).set(sid, {
          types: [],
          rows: [],
        });
      }

      const obj = geneEventMap.get(gene).get(sid);
      obj.types.push(altType);
      obj.rows.push(row);
    }
  }

  const samples = Array.from(sampleSet);

  const hitCountMap = new Map();
  for (const sid of samples) {
    let c = 0;
    for (const gene of queryGenes) {
      if (geneEventMap.get(gene)?.has(sid)) c += 1;
    }
    hitCountMap.set(sid, c);
  }

  samples.sort((a, b) => {
    const ca = hitCountMap.get(a) || 0;
    const cb = hitCountMap.get(b) || 0;
    if (cb !== ca) return cb - ca;

    const da = sampleDiagnosis.get(a) || "";
    const db = sampleDiagnosis.get(b) || "";
    if (da !== db) return da.localeCompare(db);

    return a.localeCompare(b);
  });

  const diagnosisColors = buildDiagnosisColorMap(Array.from(sampleDiagnosis.values()));

  const alterations = [];

  for (const sid of samples) {
    const diag = sampleDiagnosis.get(sid);
    if (diag) {
      alterations.push({
        sample: sid,
        gene: "__DIAGNOSIS__",
        type: "diagnosis",
        value: diag,
      });
    }
  }

  for (const gene of queryGenes) {
    for (const sid of samples) {
      const info = geneEventMap.get(gene)?.get(sid);
      if (!info) continue;

      const dominantType = chooseDominantAlteration(info.types);

      alterations.push({
        sample: sid,
        gene,
        type: dominantType || null,
        value: dominantType || null,
        allTypes: Array.from(new Set(info.types)),
        rowCount: info.rows.length,
        rows: info.rows,
      });
    }
  }

  return {
    genes: queryGenes,
    samples,
    alterations,
    meta: {
      kind: "query_oncoprint",
      diagnosisColors,
      alterationColors: ALTERATION_COLOR_MAP,
      alterationLabels: ALTERATION_LABEL_MAP,
    },
  };
}

/* =========================================================
 * diagnosis count
 * ========================================================= */

export function buildDiagnosisCounts(data) {
  const colors = data?.meta?.diagnosisColors || {};
  const counts = new Map();
  for (const a of data?.alterations || []) {
    if (a.type !== "diagnosis") continue;
    const k = String(a.value || "");
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([label, count]) => ({
      label,
      count,
      color: colors[label] || stringToColorStable(label),
    }))
    .sort((a, b) => b.count - a.count);
}

export function DiagnosisBarChart({
  data,
  title = "Diagnosis count",
  barW = 22,
  gap = 10,
  maxH = 160,
  margin = { top: 12, right: 40, bottom: 100, left: 48 },
}) {
  const items = useMemo(() => buildDiagnosisCounts(data), [data]);
  if (!items.length) {
    return <div style={{ padding: 8, fontSize: 12, color: "#64748b" }}>No diagnosis to chart</div>;
  }

  const n = items.length;
  const leftPad = 10;
  const rightPad = 24;
  const innerW = n * barW + (n - 1) * gap + leftPad + rightPad;
  const innerH = maxH;

  const titleH = 20;
  const svgW = innerW + margin.left + margin.right;
  const svgH = innerH + margin.top + margin.bottom + titleH;

  const maxCount = Math.max(...items.map((d) => d.count), 1);
  const yScale = (v) => innerH - Math.round((v / maxCount) * innerH);

  return (
    <svg width={svgW} height={svgH} style={{ display: "block", background: "#ffffff" }}>
      <text x={margin.left} y={margin.top + 14} fontSize={12} fontWeight={600} fill="#0f172a">
        {title}
      </text>

      <g transform={`translate(${margin.left},${margin.top + titleH})`}>
        <line x1={0} y1={0} x2={0} y2={innerH} stroke="#e5e7eb" />
        <text x={-6} y={4} textAnchor="end" fontSize={10} fill="#64748b">{maxCount}</text>
        <text x={-6} y={innerH} textAnchor="end" fontSize={10} fill="#64748b">0</text>
      </g>

      <g transform={`translate(${margin.left},${margin.top + titleH})`}>
        {items.map((d, i) => {
          const x = leftPad + i * (barW + gap);
          const y = yScale(d.count);
          const h = innerH - y;
          const countY = h >= 14 ? y + 12 : y - 4;
          const countFill = h >= 14 ? "#ffffff" : "#334155";

          return (
            <g key={d.label}>
              <rect x={x} y={y} width={barW} height={h} fill={d.color} />
              <text x={x + barW / 2} y={countY} textAnchor="middle" fontSize={10} fill={countFill}>
                {d.count}
              </text>
              <g transform={`translate(${x + barW / 2},${innerH + 6}) rotate(45)`}>
                <text textAnchor="start" fontSize={10} fill="#475569">{d.label}</text>
              </g>
            </g>
          );
        })}
        <line x1={0} y1={innerH} x2={innerW} y2={innerH} stroke="#0f172a" />
      </g>
    </svg>
  );
}

/* =========================================================
 * main overview component
 * ========================================================= */

export function QueryOncoPrint({ data, title = "Queried genes overview" }) {
  const [cellW, setCellW] = useState(14);
  const [cellH, setCellH] = useState(18);
  const [tip, setTip] = useState(null);
  const [showDiagnosisLegend, setShowDiagnosisLegend] = useState(false);

  const leftLabelW = 140;
  const leftPctW = 56;
  const topTrackH = 18;
  const topGap = 12;
  const rowGap = 6;
  const labelX = 8;

  const diagnosisColors = data?.meta?.diagnosisColors || {};
  const alterationColors = data?.meta?.alterationColors || ALTERATION_COLOR_MAP;
  const alterationLabels = data?.meta?.alterationLabels || ALTERATION_LABEL_MAP;

  const samples = data?.samples || [];
  const genes = data?.genes || [];

  const totalW = leftLabelW + leftPctW + samples.length * cellW + 24;
  const totalH = topTrackH + topGap + genes.length * (cellH + rowGap) + 40;

  const cellMap = useMemo(() => {
    const m = new Map();
    m.set("__DIAGNOSIS__", new Map());
    for (const gene of genes) m.set(gene, new Map());

    for (const a of data?.alterations || []) {
      if (!m.has(a.gene)) m.set(a.gene, new Map());
      m.get(a.gene).set(a.sample, a);
    }
    return m;
  }, [data, genes]);

  const percentOfGene = (gene) => {
    if (!samples.length) return "0%";
    let hit = 0;
    for (const s of samples) {
      if (cellMap.get(gene)?.has(s)) hit += 1;
    }
    return `${Math.round((hit / samples.length) * 100)}%`;
  };

  if (!data || !samples.length || !genes.length) {
    return <div style={{ padding: 8, fontSize: 12 }}>No OncoPrint data.</div>;
  }

  return (
    <div style={{ width: "100%", overflow: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, padding: 8 }}>
        <div style={{ fontSize: 14, fontWeight: 600 }}>{title}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12 }}>
          <label>
            W{" "}
            <input
              type="range"
              min={8}
              max={28}
              value={cellW}
              onChange={(e) => setCellW(+e.target.value)}
            />
          </label>
          <label>
            H{" "}
            <input
              type="range"
              min={14}
              max={28}
              value={cellH}
              onChange={(e) => setCellH(+e.target.value)}
            />
          </label>
        </div>
      </div>

      <svg width={totalW} height={totalH} style={{ background: "#ffffff", display: "block" }}>
        <g transform={`translate(${leftLabelW + leftPctW}, 10)`}>
          <text
            x={-leftLabelW - leftPctW + labelX}
            y={topTrackH - 2}
            textAnchor="start"
            fill="#0f172a"
            style={{ fontSize: 12, fontWeight: 600 }}
          >
            Diagnosis
          </text>

          {samples.map((s, i) => {
            const evt = cellMap.get("__DIAGNOSIS__")?.get(s);
            const label = evt?.value || "";
            const col = label ? diagnosisColors[label] || "#e5e7eb" : "#e5e7eb";
            const x = i * cellW;

            return (
              <g key={`diag-${s}`}>
                <rect x={x} y={0} width={cellW} height={topTrackH} fill={col} stroke="#ffffff" strokeWidth={0.6} />
                <rect
                  x={x}
                  y={0}
                  width={cellW}
                  height={topTrackH}
                  fill="transparent"
                  onMouseEnter={(e) => {
                    const { x, y } = pointerXY(e);
                    setTip({
                      x,
                      y,
                      html: `<div style='font-size:12px'>• Sample: <b>${s}</b><br/>• Diagnosis: <b>${label || "NA"}</b></div>`,
                    });
                  }}
                  onMouseMove={(e) => {
                    const { x, y } = pointerXY(e);
                    setTip({
                      x,
                      y,
                      html: `<div style='font-size:12px'>• Sample: <b>${s}</b><br/>• Diagnosis: <b>${label || "NA"}</b></div>`,
                    });
                  }}
                  onMouseLeave={() => setTip(null)}
                />
              </g>
            );
          })}
        </g>

        {genes.map((g, r) => {
          const y = 10 + topTrackH + topGap + r * (cellH + rowGap);

          return (
            <g key={g}>
              <text
                x={labelX}
                y={y + cellH - 4}
                textAnchor="start"
                fill="#0f172a"
                style={{ fontSize: 12, fontWeight: 600 }}
              >
                {g}
              </text>

              <text
                x={leftLabelW + leftPctW - 8}
                y={y + cellH - 4}
                textAnchor="end"
                fill="#475569"
                style={{ fontSize: 11, fontWeight: 600 }}
              >
                {percentOfGene(g)}
              </text>

              <rect
                x={leftLabelW + leftPctW}
                y={y}
                width={samples.length * cellW}
                height={cellH}
                fill="#f8fafc"
              />

              {samples.map((s, i) => {
                const evt = cellMap.get(g)?.get(s);
                const x = leftLabelW + leftPctW + i * cellW;
                const mainType = evt?.type || null;
                const fill = mainType ? (alterationColors[mainType] || "#14B8A6") : "#d9d9d9";

                const allTypes = evt?.allTypes || [];
                const allTypeText = allTypes.length
                  ? Array.from(new Set(allTypes.map((t) => alterationLabels[t] || t))).join(", ")
                  : "No alteration";

                const mutationLabels = (evt?.rows || [])
                  .map((r) => r.Protein_Change)
                  .filter(Boolean);

                const uniqueMutationLabels = Array.from(new Set(mutationLabels));
                let proteinText = uniqueMutationLabels.length ? uniqueMutationLabels.join(", ") : "NA";

                if (!uniqueMutationLabels.length && evt?.type === "synonymous") {
                  proteinText = "synonymous (HGVS protein unavailable)";
                }

                return (
                  <g key={`${g}-${s}`}>
                    <rect
                      x={x}
                      y={y}
                      width={cellW}
                      height={cellH}
                      fill={fill}
                      stroke="#ffffff"
                      strokeWidth={0.6}
                    />
                    <rect
                      x={x}
                      y={y}
                      width={cellW}
                      height={cellH}
                      fill="transparent"
                      onMouseEnter={(e) => {
                        const { x, y } = pointerXY(e);
                        setTip({
                          x,
                          y,
                          html: `<div style='font-size:12px'>
                            • Gene: <b>${g}</b><br/>
                            • Sample: <b>${s}</b><br/>
                            • Main type: <b>${mainType ? (alterationLabels[mainType] || mainType) : "No alteration"}</b><br/>
                            • All types: ${allTypeText}<br/>
                            • Protein change: ${proteinText}<br/>
                            • Event count: <b>${evt?.rowCount || 0}</b>
                          </div>`,
                        });
                      }}
                      onMouseMove={(e) => {
                        const { x, y } = pointerXY(e);
                        setTip({
                          x,
                          y,
                          html: `<div style='font-size:12px'>
                            • Gene: <b>${g}</b><br/>
                            • Sample: <b>${s}</b><br/>
                            • Main type: <b>${mainType ? (alterationLabels[mainType] || mainType) : "No alteration"}</b><br/>
                            • All types: ${allTypeText}<br/>
                            • Protein change: ${proteinText}<br/>
                            • Event count: <b>${evt?.rowCount || 0}</b>
                          </div>`,
                        });
                      }}
                      onMouseLeave={() => setTip(null)}
                    />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      {/* Mutation legend */}
      <div style={{ padding: "10px 12px 4px 12px" }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 8 }}>
          Mutation type
        </div>
        <div
          style={{
            fontSize: 12,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 10,
          }}
        >
          {Object.entries(alterationColors).map(([key, color]) => (
            <LegendSwatch
              key={key}
              label={alterationLabels[key] || key}
              color={color}
            />
          ))}
          <LegendSwatch label="No alteration" color="#d9d9d9" />
        </div>
      </div>

      {/* Diagnosis legend */}
      <div style={{ padding: "10px 12px 8px 12px" }}>
        <button
          type="button"
          onClick={() => setShowDiagnosisLegend((v) => !v)}
          style={{
            border: "1px solid #cbd5e1",
            background: "#ffffff",
            borderRadius: 6,
            padding: "6px 10px",
            fontSize: 12,
            fontWeight: 600,
            cursor: "pointer",
            color: "#334155",
          }}
        >
          {showDiagnosisLegend ? "Hide diagnosis legend" : "Show diagnosis legend"}
        </button>

        {showDiagnosisLegend && (
          <div style={{ marginTop: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#334155", marginBottom: 8 }}>
              Diagnosis
            </div>
            <div
              style={{
                fontSize: 12,
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 12,
              }}
            >
              {Object.keys(diagnosisColors).length ? (
                Object.entries(diagnosisColors).map(([label, color]) => (
                  <LegendSwatch key={label} label={label} color={color} />
                ))
              ) : (
                <div style={{ color: "#64748b" }}>No diagnosis legend</div>
              )}
            </div>
          </div>
        )}
      </div>

      {tip && (
        <div
          style={{
            position: "fixed",
            pointerEvents: "none",
            zIndex: 50,
            left: tip.x,
            top: tip.y,
            background: "rgba(255,255,255,0.97)",
            border: "1px solid #cbd5e1",
            borderRadius: 6,
            padding: 8,
            fontSize: 12,
            color: "#0f172a",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            maxWidth: 340,
          }}
          dangerouslySetInnerHTML={{ __html: tip.html }}
        />
      )}
    </div>
  );
}

/* =========================================================
 * diagnosis-only oncoprint
 * ========================================================= */

export default function OncoPrintLite({ data, title = "" }) {
  const [cellW, setCellW] = useState(22);
  const [cellH, setCellH] = useState(22);

  const leftLabelW = 120;
  const topSummaryH = 34;
  const rowGap = 6;
  const labelX = 8;

  const idx = useMemo(() => buildIndexDiagnosis(data), [data, cellW, cellH]);
  const totalW = useMemo(() => (idx ? leftLabelW + idx.samples.length * cellW + 24 : 0), [idx, cellW]);
  const totalH = useMemo(() => (idx ? topSummaryH + idx.genes.length * (cellH + rowGap) + 14 : 0), [idx, cellH]);
  const svgRef = useRef(null);
  const [tip, setTip] = useState(null);

  if (!data || !data.genes || !data.samples) {
    return <div style={{ padding: 8, fontSize: 12 }}>No OncoPrint data.</div>;
  }

  const diagnosisColors = data?.meta?.diagnosisColors || {};

  return (
    <div style={{ width: "100%", overflow: "auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, padding: 8 }}>
        {title ? <div style={{ fontSize: 14, fontWeight: 600 }}>{title}</div> : <div />}
        <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 12 }}>
          <label>
            W{" "}
            <input type="range" min={8} max={36} value={cellW} onChange={(e) => setCellW(+e.target.value)} />
          </label>
          <label>
            H{" "}
            <input type="range" min={12} max={28} value={cellH} onChange={(e) => setCellH(+e.target.value)} />
          </label>
        </div>
      </div>

      <svg ref={svgRef} width={totalW} height={totalH} style={{ background: "#ffffff" }}>
        <g transform={`translate(${leftLabelW}, 6)`}>
          {idx.samples.map((s, i) => {
            const x = i * cellW;
            const tipHtml = `<div style='font-size:12px'>• Sample ID: <b>${s}</b></div>`;
            const hasDiag = idx.sampleHasEvent.get(s) || false;
            return (
              <g key={s}>
                <rect x={x} y={20} width={cellW} height={6} fill={hasDiag ? "#64748b" : "#e5e7eb"} />
                <rect
                  x={x}
                  y={0}
                  width={cellW}
                  height={26}
                  fill="transparent"
                  style={{ cursor: "pointer" }}
                  onMouseEnter={(e) => {
                    const { x, y } = pointerXY(e);
                    setTip({ x, y, html: tipHtml });
                  }}
                  onMouseMove={(e) => {
                    const { x, y } = pointerXY(e);
                    setTip({ x, y, html: tipHtml });
                  }}
                  onMouseLeave={() => setTip(null)}
                />
              </g>
            );
          })}

          <text
            x={-leftLabelW + labelX}
            y={23}
            dominantBaseline="middle"
            textAnchor="start"
            fill="#64748b"
            style={{ fontSize: 10, fontWeight: 500 }}
          >
            # Samples ID
          </text>
        </g>

        {idx.genes.map((g, r) => {
          const y = topSummaryH + r * (cellH + rowGap);
          return (
            <g key={g}>
              <text
                x={labelX}
                y={y + cellH - 4}
                textAnchor="start"
                fill="#0f172a"
                style={{ fontSize: 12, fontWeight: 600 }}
              >
                {g}
              </text>

              <rect x={leftLabelW} y={y} width={idx.samples.length * cellW} height={cellH} fill="#f8fafc" />
              {idx.samples.map((s, i) => (
                <line
                  key={`${g}-${s}-grid`}
                  x1={leftLabelW + i * cellW}
                  y1={y}
                  x2={leftLabelW + i * cellW}
                  y2={y + cellH}
                  stroke="#e5e7eb"
                  strokeWidth={1}
                />
              ))}

              {idx.samples.map((s, i) => {
                const evts = idx.cell.get(g).get(s) || [];
                const diagEvt = evts.find((e) => e.type === "diagnosis");
                const label = diagEvt?.value || "";
                const col = diagnosisColors?.[label] || "#d9d9d9";
                const tipHtml = diagEvt
                  ? `<div style='font-size:12px'>• Diagnosis: <b>${label}</b><br/>• Sample: <b>${s}</b></div>`
                  : `<div style='font-size:12px'>• Sample: <b>${s}</b><br/>• Diagnosis: <i>NA</i></div>`;
                const x = leftLabelW + i * cellW;

                return (
                  <g key={`${g}-${s}`}>
                    <rect
                      x={x + 1}
                      y={y + 2}
                      width={cellW - 2}
                      height={cellH - 4}
                      fill={evts.length ? col : "#f3f4f6"}
                      stroke="#ffffff"
                      strokeWidth={1}
                    />
                    <rect
                      x={x}
                      y={y}
                      width={cellW}
                      height={cellH}
                      fill="transparent"
                      onMouseEnter={(e) => {
                        const { x, y } = pointerXY(e);
                        setTip({ x, y, html: tipHtml });
                      }}
                      onMouseMove={(e) => {
                        const { x, y } = pointerXY(e);
                        setTip({ x, y, html: tipHtml });
                      }}
                      onMouseLeave={() => setTip(null)}
                      style={{ cursor: "pointer" }}
                    />
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>

      <div
        style={{
          padding: "8px 12px",
          fontSize: 12,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: 12,
        }}
      >
        {Object.keys(diagnosisColors).length ? (
          Object.entries(diagnosisColors).map(([label, color]) => (
            <LegendSwatch key={label} label={label} color={color} />
          ))
        ) : (
          <div style={{ color: "#64748b" }}>No diagnosis legend</div>
        )}
      </div>

      {tip && (
        <div
          style={{
            position: "fixed",
            pointerEvents: "none",
            zIndex: 50,
            left: tip.x,
            top: tip.y,
            background: "rgba(255,255,255,0.95)",
            border: "1px solid #cbd5e1",
            borderRadius: 6,
            padding: 8,
            fontSize: 12,
            color: "#0f172a",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
          }}
          dangerouslySetInnerHTML={{ __html: tip.html }}
        />
      )}
    </div>
  );
}

function buildIndexDiagnosis(d) {
  const genes = (d?.geneOrder?.length ? d.geneOrder : d?.genes || []).slice();
  const samples = (d?.sampleOrder?.length ? d.sampleOrder : d?.samples || []).slice();

  const cell = new Map();
  for (const g of genes) cell.set(g, new Map(samples.map((s) => [s, []])));

  for (const a of d?.alterations || []) {
    if (a.type !== "diagnosis") continue;
    if (!cell.has(a.gene)) continue;
    const m = cell.get(a.gene);
    if (!m.has(a.sample)) continue;
    m.get(a.sample).push(a);
  }

  const sampleHasEvent = new Map(samples.map((s) => [s, false]));
  for (const g of genes) {
    const m = cell.get(g);
    for (const s of samples) if ((m.get(s) || []).length) sampleHasEvent.set(s, true);
  }

  return { genes, samples, cell, sampleHasEvent };
}

function LegendSwatch({ label, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div
        style={{
          width: 24,
          height: 12,
          background: color || "#ccc",
          border: "1px solid #9aa0a6",
          borderRadius: 2,
        }}
      />
      <div style={{ fontSize: 12, color: "#334155" }}>{label}</div>
    </div>
  );
}
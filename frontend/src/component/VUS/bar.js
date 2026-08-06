// === 放在 oncoprint.js 裡（imports 之後、export 之前）===
// 若檔案裡已經有 stringToColorStable / PALETTE，請保留一份即可。

import React, { useMemo } from "react";

/** 穩定色盤（同診斷同色） */
const DIAG_PALETTE = ["#E69F00","#56B4E9","#009E73","#F0E442","#0072B2","#D55E00","#CC79A7","#000000"];
function hash32(str){let h=0>>>0;for(let i=0;i<str.length;i++) h=(h*31+str.charCodeAt(i))>>>0;return h>>>0;}
export function stringToColorStable(s){
  const h = hash32(String(s ?? ""));
  return DIAG_PALETTE[h % DIAG_PALETTE.length];
}

/** 統計每個診斷的樣本數 → [{label, count, color}]（依 count 由大到小） */
export function buildDiagnosisCounts(data) {
  const colors = data?.meta?.diagnosisColors || {};
  const counts = new Map();
  for (const a of data?.alterations || []) {
    if (a.type !== "diagnosis") continue;
    const k = String(a.value || "");
    counts.set(k, (counts.get(k) || 0) + 1);
  }
  const arr = Array.from(counts.entries())
    .map(([label, count]) => ({ label, count, color: colors[label] || stringToColorStable(label) }))
    .sort((a, b) => b.count - a.count);
  return arr;
}

/** 簡易長條圖：每個診斷的樣本數 */
export function DiagnosisBarChart({
  data,
  barW = 18,
  maxH = 160,
  margin = { top: 8, right: 12, bottom: 80, left: 48 },
}) {
  const items = useMemo(() => buildDiagnosisCounts(data), [data]);
  if (!items.length) {
    return <div style={{ padding: 8, fontSize: 12, color: "#64748b" }}>No diagnosis to chart</div>;
  }

  const n = items.length;
  const innerW = n * (barW + 8); // 欄寬 + 間距
  const innerH = maxH;
  const width = innerW + margin.left + margin.right;
  const height = innerH + margin.top + margin.bottom;

  const maxCount = Math.max(...items.map((d) => d.count), 1);
  const yScale = (v) => innerH - Math.round((v / maxCount) * innerH);

  return (
    <svg width={width} height={height} style={{ display: "block", background: "#ffffff" }}>
      {/* y 軸刻度（0, maxCount） */}
      <g transform={`translate(${margin.left},${margin.top})`}>
        {/* y 軸線 */}
        <line x1={0} y1={0} x2={0} y2={innerH} stroke="#e5e7eb" />
        {/* 上下兩個刻度 */}
        <g>
          <text x={-6} y={4} textAnchor="end" fontSize={10} fill="#64748b">
            {maxCount}
          </text>
          <text x={-6} y={innerH} textAnchor="end" fontSize={10} fill="#64748b">
            0
          </text>
        </g>
      </g>

      {/* bars + x 軸 */}
      <g transform={`translate(${margin.left},${margin.top})`}>
        {items.map((d, i) => {
          const x = i * (barW + 8) + 10; // 10 為左側內距，讓 y 軸有空間
          const y = yScale(d.count);
          const h = innerH - y;
          return (
            <g key={d.label}>
              <rect x={x} y={y} width={barW} height={h} fill={d.color} />
              {/* 數字（可選）：小於 14px 高時移到柱上方 */}
              {h >= 14 ? (
                <text x={x + barW / 2} y={y + 12} textAnchor="middle" fontSize={10} fill="#ffffff">
                  {d.count}
                </text>
              ) : (
                <text x={x + barW / 2} y={y - 4} textAnchor="middle" fontSize={10} fill="#334155">
                  {d.count}
                </text>
              )}
              {/* x 標籤（旋轉避免擠） */}
              <g transform={`translate(${x + barW / 2},${innerH + 6}) rotate(45)`}>
                <text textAnchor="start" fontSize={10} fill="#475569">
                  {d.label}
                </text>
              </g>
            </g>
          );
        })}
        {/* x 軸線 */}
        <line x1={0} y1={innerH} x2={innerW + 20} y2={innerH} stroke="#0f172a" />
      </g>

      {/* 標題（可改） */}
      <text x={margin.left} y={14} fontSize={12} fontWeight={600} fill="#0f172a">
        Diagnosis counts (samples)
      </text>
    </svg>
  );
}

// src/components/PathwayViewer.jsx
import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { createPortal } from "react-dom";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";

cytoscape.use(dagre);

const INITIAL_SCALE = 0.95;
const FIT_PADDING = 80;
const POSITION_SPREAD = 1.25;

const TOP_N = 100;
const TOP_RANGE_MIN = 0.35;
const TOP_STRETCH = 0.45;
const SOMATIC_DOT_SIZE = 16;

const SOMATIC_DOT_SVG = `data:image/svg+xml;utf8,${encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 22 22">
  <circle cx="11" cy="11" r="8" fill="#16a34a" stroke="#ffffff" stroke-width="3"/>
  <circle cx="11" cy="11" r="8" fill="none" stroke="#111827" stroke-width="1"/>
</svg>
`)}`;

const normId = (v) => String(v ?? "").trim();
const normGene = (v) => String(v ?? "").trim().toUpperCase();

function normalizeScoreMap(scoreMap = {}) {
  const out = {};

  Object.entries(scoreMap || {}).forEach(([key, value]) => {
    const gene = normGene(key);
    const num = Number(value);

    if (!gene) return;
    if (Number.isNaN(num)) return;

    out[gene] = num;
  });

  return out;
}


function normalizeVariantGeneMap(variantGeneMap = {}) {
  if (!variantGeneMap) return {};

  const rawMap = variantGeneMap.by_gene || variantGeneMap;
  const out = {};

  if (Array.isArray(rawMap)) {
    rawMap.forEach((item) => {
      const gene = normGene(item?.gene || item?.Gene || item?.Gene_refGene);
      if (!gene) return;
      out[gene] = out[gene] || [];
      out[gene].push(item);
    });
    return out;
  }

  Object.entries(rawMap || {}).forEach(([key, value]) => {
    const gene = normGene(key);
    if (!gene) return;

    if (Array.isArray(value)) {
      out[gene] = value.filter(Boolean);
    } else if (value && typeof value === "object") {
      out[gene] = [value];
    } else if (value) {
      out[gene] = [{ gene, protein_change: String(value) }];
    }
  });

  return out;
}

function cleanDisplayValue(value, fallback = "Not reported") {
  const s = String(value ?? "").trim();
  if (!s || s === "." || s.toLowerCase() === "nan") return fallback;
  return s;
}

function getPrimaryVariant(records = []) {
  if (!Array.isArray(records) || records.length === 0) return null;

  return (
    records.find((r) => cleanDisplayValue(r?.protein_change, "") !== "") ||
    records[0]
  );
}

function parseVariantRecordsJson(raw = "[]") {
  try {
    const parsed = JSON.parse(raw || "[]");
    return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
  } catch (e) {
    return [];
  }
}

function getVariantTooltipPayloadFromMarker(marker) {
  const records = parseVariantRecordsJson(marker?.variantRecordsJson);

  return {
    gene: String(marker?.gene || "").trim(),
    records,
  };
}

function getSafeTooltipPosition(event) {
  const margin = 14;
  const estimatedWidth = 460;
  const estimatedHeight = 520;

  let x = Number(event?.clientX || 0) + margin;
  let y = Number(event?.clientY || 0) + margin;

  if (typeof window !== "undefined") {
    if (x + estimatedWidth > window.innerWidth - 12) {
      x = Number(event?.clientX || 0) - estimatedWidth - margin;
    }

    if (y + estimatedHeight > window.innerHeight - 12) {
      y = Number(event?.clientY || 0) - estimatedHeight - margin;
    }
  }

  return {
    x: Math.max(12, x),
    y: Math.max(12, y),
  };
}

function toElements(json, scoreMap = {}, scoreDigits = 3, variantGeneMap = {}) {
  if (!json) return [];

  const normalizedScoreMap = normalizeScoreMap(scoreMap);

  const normalizedVariantGeneMap = normalizeVariantGeneMap(variantGeneMap);
  const variantSet = new Set(Object.keys(normalizedVariantGeneMap));
  const entries = Object.entries(normalizedScoreMap).filter(
    ([, v]) => typeof v === "number" && !Number.isNaN(v)
  );

  entries.sort((a, b) => a[1] - b[1]);

  const rankMap = {};
  const nRank = entries.length;

  for (let i = 0; i < nRank; i++) {
    const k = normGene(entries[i][0]);
    rankMap[k] = nRank > 1 ? i / (nRank - 1) : 1;
  }

  const rawNodes = json.nodes || [];
  const posNodes = rawNodes.filter((n) => n.x != null && n.y != null);

  let cx = 0;
  let cy = 0;

  if (posNodes.length) {
    cx = posNodes.reduce((s, n) => s + Number(n.x), 0) / posNodes.length;
    cy = posNodes.reduce((s, n) => s + Number(n.y), 0) / posNodes.length;
  }

  const normalizedNodes = rawNodes.map((n) => {
    const id = normId(n.id);
    const parent = n.parent != null ? normId(n.parent) : undefined;

    return {
      ...n,
      id,
      parent,
    };
  });

  const childrenByParent = {};

  normalizedNodes.forEach((n) => {
    if (n.parent) {
      childrenByParent[n.parent] = (childrenByParent[n.parent] || 0) + 1;
    }
  });

  const nodeIds = new Set(normalizedNodes.map((n) => n.id));

  {
    const missingParents = [];

    for (const n of normalizedNodes) {
      if (n.parent && !nodeIds.has(n.parent)) {
        missingParents.push(n.parent);
      }
    }

    if (missingParents.length) {
      const uniq = Array.from(new Set(missingParents));

      uniq.forEach((pid) => {
        normalizedNodes.push({
          id: pid,
          name: "",
          type: "FAMILY",
          width: 160,
          height: 60,
        });

        nodeIds.add(pid);
      });
    }
  }

  const nodes = normalizedNodes.map((n) => {
    const isOrphanFamily = n.type === "FAMILY" && !childrenByParent[n.id];

    const key = normGene(n.name || "");
    const rawScore = normalizedScoreMap[key];

    const hasScore =
      typeof rawScore === "number" && !Number.isNaN(rawScore);

    const variantRecords = key ? normalizedVariantGeneMap[key] || [] : [];

    // 只以 df_functional.csv 整理出的 variant_gene_map 判斷「實際突變」，
    // 避免把只有 MRWR 分數、但沒有變異摘要的基因誤標成突變基因。
    const hasSomaticVariant = n.type === "GENE" && key && variantSet.has(key);

    let colorScore = 0;

    if (hasScore && nRank > 1) {
      const pctl = typeof rankMap[key] === "number" ? rankMap[key] : 0;

      const rankFromTop = Math.max(
        1,
        Math.round((1 - pctl) * (nRank - 1)) + 1
      );

      if (rankFromTop <= TOP_N) {
        const u = TOP_N > 1 ? (rankFromTop - 1) / (TOP_N - 1) : 0;
        const a = 1 - u;
        const a2 = 1 - Math.pow(1 - a, TOP_STRETCH);

        colorScore = TOP_RANGE_MIN + (1 - TOP_RANGE_MIN) * a2;
      } else {
        const restN = nRank - TOP_N;
        const v =
          restN > 1
            ? (rankFromTop - (TOP_N + 1)) / (restN - 1)
            : 1;
        const b = 1 - v;

        colorScore = TOP_RANGE_MIN * b;
      }
    }

    let displayLabel = n.name ?? "";

    if (n.type === "GENE") {
      const labelParts = [n.name ?? ""];

      if (hasScore) {
        labelParts.push(rawScore.toFixed(scoreDigits));
      }

      displayLabel = labelParts.filter(Boolean).join("\n");
    }

    const pos =
      n.x != null && n.y != null
        ? {
            x: cx + (Number(n.x) - cx) * POSITION_SPREAD,
            y: cy + (Number(n.y) - cy) * POSITION_SPREAD,
          }
        : undefined;

    return {
      data: {
        id: n.id,
        label: n.name,
        displayLabel,
        type: n.type,
        ...(n.parent ? { parent: n.parent } : {}),
        width: (Number(n.width) || 120) * 0.9,
        height: (Number(n.height) || 40) * 0.9,
        isOrphanFamily: isOrphanFamily ? "true" : "false",
        hasScore: hasScore ? "true" : "false",
        hasSomaticVariant: hasSomaticVariant ? "true" : "false",
        variantCount: variantRecords.length,
        variantRecordsJson: JSON.stringify(variantRecords),
        rawScore: hasScore ? rawScore : 0,
        score: colorScore,
      },
      ...(pos ? { position: pos } : {}),
    };
  });

  const rawEdges = json.edges || [];
  const edges = [];
  const skipped = [];

  for (let i = 0; i < rawEdges.length; i++) {
    const r = rawEdges[i];

    const id = normId(r.id) || `e${i}`;
    const source = normId(r.source);
    const target = normId(r.target);
    const type = r.type;

    const ok = nodeIds.has(source) && nodeIds.has(target);

    if (!ok) {
      skipped.push({
        id,
        source,
        target,
        sourceExists: nodeIds.has(source),
        targetExists: nodeIds.has(target),
      });

      continue;
    }

    edges.push({
      data: {
        id,
        source,
        target,
        type,
      },
    });
  }

  if (skipped.length) {
    console.table(skipped);
  }

  return [...nodes, ...edges];
}

function LegendCard({ title, children }) {
  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div style={styles.cardAccent} />
        <div style={styles.cardTitle}>{title}</div>
      </div>

      <div style={styles.cardBody}>{children}</div>
    </div>
  );
}

function NodePreview({ label, variant }) {
  const base = { ...styles.nodePreviewBase };

  const styleMap = {
    GENE: styles.nodeGene,
    SEED_GENE: styles.nodeSeedGene,
    FAMILY: styles.nodeFamily,
    COMPLEX: styles.nodeComplex,
    COMPARTMENT: styles.nodeCompartment,
    PROCESS: styles.nodeProcess,
  };

  return (
    <div style={styles.legendItem}>
      <div style={{ ...base, ...(styleMap[variant] || {}) }} />
      <div style={styles.legendLabel}>{label}</div>
    </div>
  );
}

function EdgePreview({ label, variant, idx }) {
  const ids = {
    tri: `tri-${idx}`,
    tee: `tee-${idx}`,
  };

  const cfg = {
    dashed: variant === "INDUCES" || variant === "REPRESSES",
    triangle: variant === "ACTIVATES" || variant === "INDUCES",
    tee: variant === "INHIBITS" || variant === "REPRESSES",
    none: variant === "BINDS",
  };

  return (
    <div style={styles.legendItem}>
      <svg width="96" height="26">
        <defs>
          <marker
            id={ids.tri}
            markerWidth="10"
            markerHeight="10"
            refX="9"
            refY="5"
            orient="auto"
          >
            <path d="M0,0 L10,5 L0,10 z" fill="#111" />
          </marker>

          <marker
            id={ids.tee}
            markerWidth="10"
            markerHeight="10"
            refX="10"
            refY="5"
            orient="auto"
          >
            <path d="M10,0 L10,10" stroke="#111" strokeWidth="2" />
          </marker>
        </defs>

        <line
          x1="8"
          y1="13"
          x2="86"
          y2="13"
          stroke="#111"
          strokeWidth="2.2"
          strokeDasharray={cfg.dashed ? "6 4" : "0"}
          markerEnd={
            cfg.none
              ? undefined
              : cfg.triangle
              ? `url(#${ids.tri})`
              : cfg.tee
              ? `url(#${ids.tee})`
              : undefined
          }
        />
      </svg>

      <div style={styles.legendLabel}>{label}</div>
    </div>
  );
}

function Legend() {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.sidebarInner}>
        <LegendCard title="Node Palette">
          <NodePreview label="Gene" variant="GENE" />
          <NodePreview label="Family" variant="FAMILY" />
          <NodePreview label="Complex" variant="COMPLEX" />
          <NodePreview label="Compartment" variant="COMPARTMENT" />
          <NodePreview label="Process" variant="PROCESS" />
        </LegendCard>

        <LegendCard title="Interaction Palette">
          {["ACTIVATES", "INHIBITS", "INDUCES", "REPRESSES", "BINDS"].map(
            (t, i) => (
              <EdgePreview
                key={t}
                label={t[0] + t.slice(1).toLowerCase()}
                variant={t}
                idx={i}
              />
            )
          )}
        </LegendCard>
      </div>
    </aside>
  );
}

export default function PathwayViewer({
  pathwayData,
  title,
  height = "720px",
  mrwrScores = {},
  variantGeneMap = {},
  scoreDigits = 5,
  analysisScope = "",
  onGeneClick,
}) {
  const cyRef = useRef(null);
  const [elements, setElements] = useState([]);
  const [variantMarkers, setVariantMarkers] = useState([]);
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    setElements(
      toElements(pathwayData, mrwrScores, scoreDigits, variantGeneMap)
    );
  }, [pathwayData, mrwrScores, scoreDigits, variantGeneMap]);

  const updateVariantMarkers = useCallback(() => {
    const cy = cyRef.current;

    if (!cy) {
      setVariantMarkers([]);
      return;
    }

    const nextMarkers = cy
      .nodes('node[type = "GENE"][hasSomaticVariant = "true"]')
      .map((node) => {
        const pos = node.renderedPosition();
        const renderedHeight =
          typeof node.renderedHeight === "function"
            ? node.renderedHeight()
            : Number(node.data("height") || 40);

        return {
          id: node.id(),
          gene: String(node.data("label") || "").trim(),
          x: Number(pos?.x || 0),
          y: Number(pos?.y || 0) + renderedHeight / 2,
          variantCount: Number(node.data("variantCount") || 0),
          variantRecordsJson: node.data("variantRecordsJson") || "[]",
        };
      });

    setVariantMarkers(nextMarkers);
  }, []);

  const showMarkerTooltip = useCallback((event, marker) => {
    event.stopPropagation();
    const pos = getSafeTooltipPosition(event);

    setTooltip({
      ...getVariantTooltipPayloadFromMarker(marker),
      ...pos,
    });
  }, []);

  const moveMarkerTooltip = useCallback((event) => {
    event.stopPropagation();
    const pos = getSafeTooltipPosition(event);

    setTooltip((prev) => (prev ? { ...prev, ...pos } : prev));
  }, []);

  const stylesheet = useMemo(
    () => [
      {
        selector: "node",
        style: {
          shape: "roundrectangle",
          "background-color": "#fff",
          "border-width": 2,
          "border-color": "#111",
          label: "data(displayLabel)",
          "font-size": 14,
          "text-valign": "center",
          "text-halign": "center",
          "text-wrap": "wrap",
          "text-max-width": "140px",
          "line-height": 1.0,
          width: "data(width)",
          height: "data(height)",
          padding: "8px",
          "text-justification": "center",
          "transition-property":
            "background-color, color, border-color, border-width",
          "transition-duration": "200ms",
        },
      },

      {
        selector: 'node[type = "GENE"][hasScore = "true"]',
        style: {
          "background-color": "mapData(score, 0, 1, #ffffff, #ff2d2d)",
        },
      },

      {
        selector: 'node[type = "GENE"][hasSomaticVariant = "true"]',
        style: {
          "border-color": "#111827",
        },
      },

      {
        selector: 'node[type = "GENE"][hasScore = "true"][score >= 0.85]',
        style: {
          color: "#fff",
        },
      },

      {
        selector: 'node[type = "FAMILY"]',
        style: {
          "background-color": "#f2f4f7",
          "background-opacity": 0.6,
          "border-width": 2,
          "border-color": "#111",
          "text-valign": "top",
          "text-halign": "center",
          "font-size": 13,
          padding: "22px",
          color: "#0f172a",
        },
      },

      {
        selector: 'node[type = "FAMILY"][isOrphanFamily = "true"]',
        style: {
          "background-color": "#f2f4f7",
          "background-opacity": 0.6,
          "border-width": 2,
          "border-color": "#111",
          "text-valign": "center",
          "text-halign": "center",
          "font-size": 14,
          padding: "12px",
          color: "#0f172a",
        },
      },

      {
        selector: 'node[type = "COMPLEX"]',
        style: {
          "border-style": "double",
          "border-width": 6,
          "border-color": "#111",
          "background-color": "#fff",
          "background-opacity": 1,
        },
      },

      {
        selector: 'node[type = "COMPARTMENT"]',
        style: {
          shape: "rectangle",
          "border-style": "solid",
          "border-width": 5,
          "border-color": "#111",
          "background-color": "#f3f4f6",
          "background-opacity": 0.75,
          "text-valign": "top",
          padding: "30px",
        },
      },

      {
        selector: 'node[type = "PROCESS"]',
        style: {
          "border-style": "dashed",
          "border-width": 2,
        },
      },

      {
        selector: "edge",
        style: {
          "curve-style": "bezier",
          "line-color": "#111",
          "target-arrow-color": "#111",
          "source-distance-from-node": 4,
          "target-distance-from-node": 4,
          width: 2,
        },
      },

      {
        selector: 'edge[type = "ACTIVATES"]',
        style: {
          "line-style": "solid",
          "target-arrow-shape": "triangle",
        },
      },

      {
        selector: 'edge[type = "INHIBITS"]',
        style: {
          "line-style": "solid",
          "target-arrow-shape": "tee",
        },
      },

      {
        selector: 'edge[type = "INDUCES"]',
        style: {
          "line-style": "dashed",
          "target-arrow-shape": "triangle",
        },
      },

      {
        selector: 'edge[type = "REPRESSES"]',
        style: {
          "line-style": "dashed",
          "target-arrow-shape": "tee",
        },
      },

      {
        selector: 'edge[type = "BINDS"]',
        style: {
          "line-style": "solid",
          "target-arrow-shape": "none",
        },
      },
    ],
    []
  );

  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;

    cy.minZoom(0.2);
    cy.maxZoom(2.5);

    const hasPreset = elements.some((el) => el.position);

    const layout = cy.layout({
      name: hasPreset ? "preset" : "dagre",
      fit: true,
      padding: FIT_PADDING,
      ...(hasPreset
        ? {}
        : {
            nodeSep: 60 * POSITION_SPREAD,
            rankSep: 100 * POSITION_SPREAD,
            edgeSep: 30,
          }),
    });

    layout.run();

    cy.fit(undefined, FIT_PADDING);
    cy.zoom(cy.zoom() * INITIAL_SCALE);
    cy.center();

    window.setTimeout(updateVariantMarkers, 0);
  }, [elements, updateVariantMarkers]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const handleViewportChange = () => {
      setTooltip(null);
      updateVariantMarkers();
    };

    cy.on("pan zoom resize", handleViewportChange);
    window.addEventListener("resize", handleViewportChange);
    window.setTimeout(updateVariantMarkers, 0);

    return () => {
      cy.off("pan zoom resize", handleViewportChange);
      window.removeEventListener("resize", handleViewportChange);
    };
  }, [elements, updateVariantMarkers]);

  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;

    const handler = (evt) => {
      const n = evt.target;

      if (!n) return;
      if (n.data("type") !== "GENE") return;

      const gene = String(n.data("label") || "").trim();

      if (!gene) return;

      if (typeof onGeneClick === "function") {
        onGeneClick(gene);
      }
    };

    cy.on("tap", 'node[type = "GENE"]', handler);

    return () => {
      cy.off("tap", 'node[type = "GENE"]', handler);
    };
  }, [onGeneClick, elements]);



  return (
    <div style={{ ...styles.shell, minHeight: height }}>
      <Legend />

      <div style={styles.canvasWrap}>
        <header style={styles.canvasHeader}>
          <div style={styles.titleBlock}>
            <div style={styles.title}>
              {title || pathwayData?.name || "Pathway"}
            </div>

            {analysisScope && (
              <div style={styles.scopeText}>{analysisScope}</div>
            )}
          </div>
        </header>

        <div style={styles.canvasBody}>
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            style={{ width: "100%", height: "100%" }}
            cy={(cy) => {
              cyRef.current = cy;
            }}
            wheelSensitivity={0.2}
          />

          <div style={styles.canvasVariantHint}>
            <span style={styles.canvasVariantHintDot} />
            <span>Functional somatic variant; hover the green marker for details.</span>
          </div>

          {variantMarkers.map((marker) => (
            <button
              key={marker.id}
              type="button"
              aria-label={`Show somatic variants for ${marker.gene}`}
              title={`${marker.gene}: ${marker.variantCount} variant(s)`}
              style={{
                ...styles.somaticDotMarker,
                left: marker.x,
                top: marker.y,
              }}
              onMouseEnter={(event) => showMarkerTooltip(event, marker)}
              onMouseMove={moveMarkerTooltip}
              onMouseLeave={() => setTooltip(null)}
              onFocus={(event) => showMarkerTooltip(event, marker)}
              onBlur={() => setTooltip(null)}
              onClick={(event) => showMarkerTooltip(event, marker)}
            />
          ))}

          {tooltip?.records?.length > 0 &&
            typeof document !== "undefined" &&
            createPortal(
              <div
                style={{
                  ...styles.tooltip,
                  left: tooltip.x,
                  top: tooltip.y,
                }}
              >
                <div style={styles.tooltipHeaderRow}>
                  <div>
                    <div style={styles.tooltipKicker}>Somatic variant gene</div>
                    <div style={styles.tooltipGene}>{tooltip.gene}</div>
                  </div>

                  <div style={styles.tooltipBadge}>
                    {tooltip.records.length} variant
                    {tooltip.records.length === 1 ? "" : "s"}
                  </div>
                </div>

                <div style={styles.tooltipVariantList}>
                  {tooltip.records.map((record, idx) => (
                    <div key={idx} style={styles.tooltipVariantCard}>
                      {tooltip.records.length > 1 && (
                        <div style={styles.tooltipVariantIndex}>
                          Variant {idx + 1}
                        </div>
                      )}

                      <div style={styles.tooltipFieldRow}>
                        <span style={styles.tooltipFieldLabel}>Mutation type</span>
                        <span style={styles.tooltipFieldValue}>
                          {cleanDisplayValue(record?.mutation_type)}
                        </span>
                      </div>

                      <div style={styles.tooltipFieldRow}>
                        <span style={styles.tooltipFieldLabel}>Protein change</span>
                        <span style={styles.tooltipFieldValue}>
                          {cleanDisplayValue(record?.protein_change)}
                        </span>
                      </div>
                      <div style={styles.tooltipSourceBlock}>
                        <div style={styles.tooltipSourceTitle}>Clinical databases</div>

                        <div style={styles.tooltipFieldRow}>
                          <span style={styles.tooltipFieldLabel}>ClinVar</span>
                          <span style={styles.tooltipFieldValue}>
                            {cleanDisplayValue(record?.clinvar)}
                          </span>
                        </div>

                        <div style={styles.tooltipFieldRow}>
                          <span style={styles.tooltipFieldLabel}>LOVD</span>
                          <span style={styles.tooltipFieldValue}>
                            {cleanDisplayValue(record?.lovd)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>,
              document.body
            )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  shell: {
    display: "grid",
    gridTemplateColumns: "250px 1fr",
    gap: 0,
    width: "100%",
    border: "1px solid #e5e7eb",
    borderRadius: 14,
    overflow: "visible",
    background: "#fafbfc",
  },

  sidebar: {
    height: "100%",
    background: "linear-gradient(180deg,#f7fbfb 0%,#f3f6f8 100%)",
    borderRight: "1px solid #e6e9ef",
    position: "relative",
  },

  sidebarInner: {
    padding: 16,
    height: "100%",
    overflowY: "auto",
  },

  card: {
    background: "#fff",
    borderRadius: 12,
    boxShadow: "0 6px 18px rgba(0,0,0,0.06)",
    border: "1px solid #eef1f5",
    marginBottom: 14,
  },

  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 12px",
    borderBottom: "1px solid #f0f3f7",
    background: "linear-gradient(90deg,#35c2ad 0%,#52d3c2 100%)",
    color: "#fff",
    borderTopLeftRadius: 12,
    borderTopRightRadius: 12,
  },

  cardAccent: {
    width: 8,
    height: 8,
    borderRadius: 4,
    background: "rgba(255,255,255,0.8)",
    boxShadow: "0 0 0 3px rgba(255,255,255,0.2)",
  },

  cardTitle: {
    fontWeight: 700,
    letterSpacing: 0.2,
  },

  cardBody: {
    padding: 12,
  },

  legendItem: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "8px 6px",
    borderRadius: 8,
    transition: "background 0.2s",
    marginBottom: 6,
  },

  legendLabel: {
    fontSize: 14,
    color: "#0f172a",
    fontWeight: 500,
  },


  nodePreviewBase: {
    width: 84,
    height: 30,
    borderRadius: 10,
    background: "#fff",
    border: "2px solid #111",
    boxShadow: "0 1px 0 rgba(17,17,17,0.06)",
  },

  nodeGene: {},

  nodeSeedGene: {},

  nodeFamily: {
    background: "rgba(17,17,17,0.06)",
  },

  nodeComplex: {
    border: "2px solid #111",
    boxShadow: "inset 0 0 0 4px #fff, inset 0 0 0 6px #111",
    background: "#fff",
  },

  nodeCompartment: {
    width: 92,
    height: 34,
    borderWidth: 5,
    borderRadius: 3,
    background: "#f3f4f6",
  },

  nodeProcess: {
    borderStyle: "dashed",
  },

  canvasWrap: {
    display: "grid",
    gridTemplateRows: "48px 1fr",
    height: "100%",
  },

  canvasHeader: {
    display: "flex",
    alignItems: "center",
    padding: "0 16px",
    background: "#fff",
    borderBottom: "1px solid #e6e9ef",
  },

  titleBlock: {
    minWidth: 0,
  },

  title: {
    fontSize: 15,
    fontWeight: 700,
    color: "#0f172a",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },

  scopeText: {
    marginTop: 2,
    fontSize: 11,
    fontWeight: 700,
    color: "#64748b",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },

  canvasBody: {
    background: "#fff",
    position: "relative",
    overflow: "hidden",
  },

  canvasVariantHint: {
    position: "absolute",
    left: 18,
    bottom: 14,
    zIndex: 4,
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "7px 10px",
    borderRadius: 999,
    background: "rgba(255,255,255,0.82)",
    border: "1px solid #e2e8f0",
    boxShadow: "0 8px 24px rgba(15,23,42,0.08)",
    color: "#475569",
    fontSize: 12,
    fontWeight: 700,
    pointerEvents: "none",
  },

  canvasVariantHintDot: {
    width: 11,
    height: 11,
    borderRadius: "50%",
    background: "#22c55e",
    border: "2px solid #ffffff",
    boxShadow: "0 0 0 1px #111827, 0 2px 5px rgba(15,23,42,0.2)",
    display: "inline-block",
    flex: "0 0 auto",
  },

  somaticDotMarker: {
    position: "absolute",
    zIndex: 8,
    width: SOMATIC_DOT_SIZE,
    height: SOMATIC_DOT_SIZE,
    borderRadius: "50%",
    background: "#22c55e",
    border: "2px solid #ffffff",
    boxShadow: "0 0 0 1px #111827, 0 2px 5px rgba(15,23,42,0.22)",
    padding: 0,
    margin: 0,
    cursor: "pointer",
    transform: "translate(-50%, -50%)",
    pointerEvents: "auto",
  },

  tooltip: {
    position: "fixed",
    zIndex: 9999,
    width: 440,
    maxWidth: "calc(100vw - 24px)",
    maxHeight: "calc(100vh - 24px)",
    overflowY: "auto",
    borderRadius: 14,
    background: "rgba(255,255,255,0.99)",
    border: "1px solid #dbe3ef",
    boxShadow: "0 24px 70px rgba(15,23,42,0.22)",
    pointerEvents: "none",
    color: "#111827",
    fontSize: 13,
    lineHeight: 1.45,
  },

  tooltipHeaderRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: 12,
    padding: "16px 18px 14px",
    borderBottom: "1px solid #e5eaf2",
    background: "linear-gradient(180deg,#fbfdff 0%,#f8fafc 100%)",
  },

  tooltipKicker: {
    fontSize: 11,
    fontWeight: 800,
    letterSpacing: 0.8,
    textTransform: "uppercase",
    color: "#64748b",
    marginBottom: 4,
  },

  tooltipGene: {
    fontSize: 20,
    fontWeight: 900,
    color: "#1e293b",
  },

  tooltipBadge: {
    borderRadius: 999,
    padding: "4px 10px",
    background: "#dcfce7",
    border: "1px solid #86efac",
    color: "#15803d",
    fontSize: 12,
    fontWeight: 800,
    whiteSpace: "nowrap",
  },

  tooltipVariantList: {
    padding: 12,
  },

  tooltipVariantCard: {
    border: "1px solid #e5eaf2",
    borderRadius: 10,
    overflow: "hidden",
    marginBottom: 10,
    background: "#fff",
  },

  tooltipVariantIndex: {
    padding: "7px 10px",
    background: "#f8fafc",
    borderBottom: "1px solid #e5eaf2",
    color: "#475569",
    fontSize: 11,
    fontWeight: 800,
    letterSpacing: 0.4,
    textTransform: "uppercase",
  },

  tooltipFieldRow: {
    display: "grid",
    gridTemplateColumns: "150px minmax(0, 1fr)",
    gap: 12,
    padding: "9px 10px",
    borderBottom: "1px solid #eef2f7",
  },

  tooltipFieldLabel: {
    color: "#64748b",
    fontWeight: 750,
  },

  tooltipFieldValue: {
    color: "#111827",
    fontWeight: 750,
    wordBreak: "break-word",
  },

  tooltipSourceBlock: {
    background: "#fbfdff",
  },

  tooltipSourceTitle: {
    padding: "9px 10px 5px",
    color: "#475569",
    fontSize: 11,
    fontWeight: 850,
    letterSpacing: 0.7,
    textTransform: "uppercase",
  },
};
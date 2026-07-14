import React, {
  useMemo,
  useState,
  useCallback,
  useRef,
  useEffect,
  useLayoutEffect,
} from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceCollide } from "d3-force";

export default function GraphViewPanel({ data }) {
  const [selected, setSelected] = useState(null);
  const [graphKey, setGraphKey] = useState(0);

  useEffect(() => {
    setGraphKey((prev) => prev + 1); // 每次 data 改變就讓 key 改變
  }, [data]);

  const rootColor = "#e74c3c";
  const fixedColor = "#4a90e2";

  const graphData = useMemo(() => {
    const targetSet = new Set(data.links.map((l) => l.target));
    const buildLevels = (nodes, links) => {
      const inDegree = {};
      const graph = {};
      nodes.forEach(n => {
        inDegree[n.id] = 0;
        graph[n.id] = [];
      });
      links.forEach(({ source, target }) => {
        graph[source].push(target);
        inDegree[target]++;
      });
      const levels = {};
      const queue = nodes
        .filter(n => inDegree[n.id] === 0)
        .map(n => ({ id: n.id, level: 0 }));
      while (queue.length) {
        const { id, level } = queue.shift();
        levels[id] = level;
        graph[id].forEach(next => {
          inDegree[next]--;
          if (inDegree[next] === 0) {
            queue.push({ id: next, level: level + 1 });
          }
        });
      }
      return levels;
    };

    const levels = buildLevels(data.nodes, data.links);
    const layerSpacingX = 500;
    const nodeSpacingY = 450;

    const nodesAll = data.nodes.map((n) => {
      const level = levels[n.id] ?? 0;
      const siblings = data.nodes.filter(nd => (levels[nd.id] ?? 0) === level);
      const indexInLevel = siblings.findIndex(nd => nd.id === n.id);
      return {
        ...n,
        x: level * layerSpacingX - 1000,
        y: (indexInLevel - (siblings.length - 1) / 2) * nodeSpacingY,
        short: n.label.split("\n").find((l) => l.trim())?.trim() ?? "",
        color: !targetSet.has(n.id) ? rootColor : fixedColor,
      };
    });

    const nodeIdSet = new Set(nodesAll.map((n) => n.id));
    const links = data.links
      .filter((l) => nodeIdSet.has(l.source) && nodeIdSet.has(l.target))
      .map((l) => ({ ...l }));

    return { nodes: nodesAll, links };
  }, [data]);

  const [zoomEnabled, setZoomEnabled] = useState(false);
  useEffect(() => {
    const down = (e) => {
      if (e.key === "Shift" || e.key === "Control") setZoomEnabled(true);
    };
    const up = (e) => {
      if (e.key === "Shift" || e.key === "Control") setZoomEnabled(false);
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
    };
  }, []);

  const fgRef = useRef();
  useLayoutEffect(() => {
    if (!fgRef.current) return;
    const fg = fgRef.current;
    fg.d3Force("charge").strength(-100).distanceMax(1000);
    fg.d3Force("link").strength(0.001);
    fg.d3Force("collision", forceCollide().radius(220));
    fg.d3ReheatSimulation(); // ⭐重新模擬
    fg.zoom(0.4, 0, 0);       // ⭐初始縮放
  }, [graphKey]);             // ⭐每次 key 改變時重新設定

  const nodeCanvasObject = useCallback((node, ctx) => {
    const size = 380;
    const half = size / 2;
    const radius = 30;
    ctx.fillStyle = node.color;
    ctx.beginPath();
    const x = node.x - half;
    const y = node.y - half;
    const w = size;
    const h = size;
    ctx.moveTo(x + radius, y);
    ctx.lineTo(x + w - radius, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + radius);
    ctx.lineTo(x + w, y + h - radius);
    ctx.quadraticCurveTo(x + w, y + h, x + w - radius, y + h);
    ctx.lineTo(x + radius, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - radius);
    ctx.lineTo(x, y + radius);
    ctx.quadraticCurveTo(x, y, x + radius, y);
    ctx.closePath();
    ctx.fill();

    const fontSize = 40;
    ctx.font = `${fontSize}px sans-serif`;
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const maxWidth = size * 0.9;
    const words = node.short.split(" ");
    let lines = [], line = "";
    words.forEach((w) => {
      const test = line ? `${line} ${w}` : w;
      if (ctx.measureText(test).width <= maxWidth) line = test;
      else { lines.push(line); line = w; }
    });
    if (line) lines.push(line);

    const lineHeight = fontSize * 1.2;
    const maxLines = Math.floor((size * 0.9) / lineHeight);
    if (lines.length > maxLines) {
      lines = lines.slice(0, maxLines);
      let last = lines[maxLines - 1];
      while (ctx.measureText(last + "…").width > maxWidth && last.length > 0)
        last = last.slice(0, -1);
      lines[maxLines - 1] = last + "…";
    }

    const totalHeight = lines.length * lineHeight;
    const startY = node.y - totalHeight / 2 + lineHeight / 2;
    lines.forEach((l, i) => ctx.fillText(l, node.x, startY + i * lineHeight));
    node.__bckgDimensions = [size, size];
  }, []);

  const nodePointerAreaPaint = useCallback((node, color, ctx) => {
    if (!node.__bckgDimensions) return;
    const [d] = node.__bckgDimensions;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, d / 2, 0, 2 * Math.PI);
    ctx.fill();
  }, []);

  const containerRef = useRef();
  const [graphSize, setGraphSize] = useState({ width: 0, height: 0 });
  useLayoutEffect(() => {
    if (!containerRef.current) return;
    const updateSize = () => {
      setGraphSize({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });
    };
    updateSize();
    const ro = new ResizeObserver(updateSize);
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  return (
    <div style={{ display: "flex", height: "100vh" }}>
      <div
        ref={containerRef}
        style={{
          width: "75%",
          height: "90%",
          position: "relative",
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {graphData.nodes.length > 0 ? (
          <ForceGraph2D
            key={graphKey}  // ⭐ 強制重新掛載
            ref={fgRef}
            width={graphSize.width}
            height={graphSize.height}
            graphData={graphData}
            linkDirectionalArrowLength={35}
            linkDirectionalArrowRelPos={0.5}
            linkDirectionalArrowColor={() => "#444"}
            linkWidth={1.5}
            linkLabel={(l) => `${l.source} → ${l.target}`}
            enableZoomPanInteraction={zoomEnabled}
            nodeLabel={(n) => n.label}
            onNodeClick={setSelected}
            nodeCanvasObject={nodeCanvasObject}
            nodePointerAreaPaint={nodePointerAreaPaint}
            warmupTicks={2000}
            cooldownTicks={2000}
            enableNodeDrag={true}
            enableZoomInteraction={zoomEnabled}
            enablePanInteraction={zoomEnabled}
            autoPauseRedraw={true}
          />
        ) : (
          <div style={{ fontSize: "24px", color: "#666", textAlign: "center" }}>
            No matching data
          </div>
        )}

        {graphData.nodes.length > 0 && (
          <div
            style={{
              position: "absolute",
              top: 10,
              left: 10,
              background: "#ffffffcc",
              padding: "6px 10px",
              borderRadius: "6px",
              fontSize: "13px",
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
            }}
          >
            <kbd>Shift</kbd> or <kbd>Ctrl</kbd> + scroll / drag → Zoom, Pan
          </div>
        )}
      </div>

      <aside
        style={{
          width: "25%",
          height: "90%",
          background: "#f8f8f8",
          padding: "1rem",
          overflowY: "auto",
          zIndex: 1,
        }}
      >
        <h3>Node Information</h3>
        {selected ? (
          <div style={{ whiteSpace: "pre-wrap" }}>
            <p><strong>ID:</strong> {selected.id}</p>
            <p><strong>Label:</strong><br />{selected.label}</p>
            <p><strong>Category:</strong> {selected.category}</p>
            <p><strong>Disease:</strong> {selected.disease}</p>
            <p><strong>Page:</strong> {selected.page}</p>
          </div>
        ) : (
          <p>Click a node to view its details</p>
        )}
      </aside>
    </div>
  );
}

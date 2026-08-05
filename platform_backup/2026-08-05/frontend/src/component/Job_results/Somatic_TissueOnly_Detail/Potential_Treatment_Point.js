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
  /* ---------- 1. 搜尋狀態 ---------- */
  const [variantQ, setVariantQ] = useState("");
  const [diseaseQ, setDiseaseQ] = useState("");
  const [drugQ, setDrugQ] = useState("");
  const [selected, setSelected] = useState(null);

  /* ---------- 2. 篩選節點／邊 ---------- */
  const rootColor = "#e74c3c";     // 根節點顏色（紅色）
  const fixedColor = "#4a90e2";    // 其他節點顏色（藍色）
  
  const graphData = useMemo(() => {
    // 找出所有被當作 target 的節點 ID
    const targetSet = new Set(data.links.map((l) => l.target));
  
    const nodesAll = data.nodes.map((n) => {
      const isRoot = !targetSet.has(n.id); // 沒有入邊就是根節點
      return {
        ...n,
        short: n.label.split("\n").find((l) => l.trim())?.trim() ?? "",
        color: isRoot ? rootColor : fixedColor
      };
    });
  
    const nodes = nodesAll.filter((n) => {
      const labelLower = n.label.toLowerCase();
      const diseaseLower = n.disease.toLowerCase();
      return (
        (!variantQ || labelLower.includes(variantQ.toLowerCase())) &&
        (!diseaseQ || diseaseLower.includes(diseaseQ.toLowerCase())) &&
        (!drugQ || labelLower.includes(drugQ.toLowerCase()))
      );
    });
  
    const nodeIdSet = new Set(nodes.map((n) => n.id));
    const links = data.links
      .filter((l) => nodeIdSet.has(l.source) && nodeIdSet.has(l.target))
      .map((l) => ({ ...l }));
  
    return { nodes, links };
  }, [data, variantQ, diseaseQ, drugQ]);
  
  

  /* ---------- 3. Shift/Ctrl 切換縮放 ---------- */
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

  /* ---------- 4. Force‑Graph 設定 ---------- */
  const fgRef = useRef();
  useLayoutEffect(() => {
    if (!fgRef.current) return;
    // 1. 斥力強度
    fgRef.current.d3Force("charge").strength(-100).distanceMax(1000);
    // 2. link 強度
    fgRef.current.d3Force("link").strength(0.001);
    // 3. collision 範圍
    fgRef.current.d3Force("collision", forceCollide().radius(200));
    // 4. 初始縮放
    fgRef.current.zoom(0.4, 0, 0);
  
 }, []);  // 改用 useLayoutEffect，確保在預熱前就設定好所有 force


  /* ---------- 5. Canvas 畫節點（固定大小字體，不溢出） ---------- */
const nodeCanvasObject = useCallback((node, ctx) => {
  const size = 300;            // 方块固定大小
  const half = size / 2;

  // 1. 画方块
  ctx.fillStyle = node.color;
  ctx.fillRect(node.x - half, node.y - half, size, size);

  // 2. 固定字号
  const fontSize = 40;         // 始终 12px
  ctx.font = `${fontSize}px sans-serif`;
  ctx.fillStyle = "#fff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  // 3. 水平换行
  const maxWidth = size * 0.9;
  const words = node.short.split(" ");
  let lines = [];
  let line = "";
  words.forEach((w) => {
    const test = line ? `${line} ${w}` : w;
    if (ctx.measureText(test).width <= maxWidth) {
      line = test;
    } else {
      lines.push(line);
      line = w;
    }
  });
  if (line) lines.push(line);

  // 4. 垂直裁剪＋尾部省略
  const lineHeight = fontSize * 1.2;
  const maxLines = Math.floor((size * 0.9) / lineHeight);
  if (lines.length > maxLines) {
    lines = lines.slice(0, maxLines);
    let last = lines[maxLines - 1];
    // 给最后一行加省略号，并保证宽度合适
    while (ctx.measureText(last + "…").width > maxWidth && last.length > 0) {
      last = last.slice(0, -1);
    }
    lines[maxLines - 1] = last + "…";
  }

  // 5. 绘制文字，垂直居中
  const totalHeight = lines.length * lineHeight;
  const startY = node.y - totalHeight / 2 + lineHeight / 2;
  lines.forEach((l, i) => {
    ctx.fillText(l, node.x, startY + i * lineHeight);
  });

  // 6. 更新拾取范围（可选）
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

  /* ---------- 6. 追蹤容器尺寸 ---------- */
  const containerRef = useRef();
  const [graphSize, setGraphSize] = useState({ width: 0, height: 0 });

  useLayoutEffect(() => {
    if (!containerRef.current) return;

    // 初始化
    const updateSize = () => {
      setGraphSize({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });
    };
    updateSize();

    // 監聽 resize
    const ro = new ResizeObserver(updateSize);
    ro.observe(containerRef.current);

    return () => ro.disconnect();
  }, []);

  
  /* ---------- 7. JSX ---------- */
  return (
    <div style={{ display: "flex", height: "100vh" }}>
      {/* ===== 左邊圖形區 ===== */}
      <div
        ref={containerRef}
        style={{
          width: "75%",
          height: "90%",
          position: "relative",
          overflow: "hidden", // 不讓 canvas 溢出
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {graphData.nodes.length > 0 ? (
          <ForceGraph2D
            ref={fgRef}
            width={graphSize.width}
            height={graphSize.height}
            graphData={graphData}              
            // nodeAutoColorBy="category"
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
            warmupTicks={1000}
            cooldownTicks={1000}
            enableNodeDrag={true}
            enableZoomInteraction={zoomEnabled}
            enablePanInteraction={zoomEnabled}
            autoPauseRedraw={true}
          />
        ) : (
          <div
            style={{
              fontSize: "24px",
              color: "#666",
              textAlign: "center",
            }}
          >
            No matching data
          </div>
        )}
  
        {/* 操作提示 */}
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
  
      {/* ===== 右側資訊欄 ===== */}
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
            <p>
              <strong>ID:</strong> {selected.id}
            </p>
            <p>
              <strong>Label:</strong>
              <br />
              {selected.label}
            </p>
            <p>
              <strong>Category:</strong> {selected.category}
            </p>
            <p>
              <strong>Disease:</strong> {selected.disease}
            </p>
            <p>
              <strong>Page:</strong> {selected.page}
            </p>
          </div>
        ) : (
          <p>Click a node to view its details</p>
        )}
                </aside>
    </div>
  );
  
}

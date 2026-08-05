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

/*********************************************************************
 * v4 修正：避免 Force‑Graph **in‑place 變異** 影響 data.links
 * ------------------------------------------------------------------
 * ForceGraph2D 會把 link.source / link.target 直接替換成節點物件，
 * 導致你返回頁面時，再次計算 rootSet 失敗 (因為 targetSet 變成物件)。
 *
 * ➜ 解法：**每次運算都先對 `data.links` 做淺複製**，
 *   確保傳給 Force‑Graph 的 link 物件與原始 data 分離，
 *   任何內部 mutate 不會污染來源資料。
 *********************************************************************/

export default function GraphViewPanel({ data }) {
  const [selected, setSelected] = useState(null);
  const [graphKey, setGraphKey] = useState(0);

  useEffect(() => setGraphKey((p) => p + 1), [data]);

  const rootColor = "#e74c3c";
  const fixedColor = "#4a90e2";

  /* ========================= 主要計算 ========================= */
  const graphData = useMemo(() => {
    /* ---------- 0. 對 links 做淺複製 ---------- */
    const linksCopy = data.links.map((l) => ({ ...l }));

    /* ---------- 便利索引 ---------- */
    const nodeIdSet = new Set(data.nodes.map((n) => n.id));
    const targetSet = new Set(linksCopy.map((l) => l.target));
    const rootSet = new Set(
      data.nodes.filter((n) => !targetSet.has(n.id)).map((n) => n.id)
    );

    /* ---------- 1. 先取有效連線 ---------- */
    const validLinks = linksCopy.filter(
      ({ source, target }) => nodeIdSet.has(source) && nodeIdSet.has(target)
    );

    /* ---------- 2. 分割「拓撲用鏈」與「額外鏈」 ---------- */
    const pairKey = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);
    const pairBuckets = new Map();
    validLinks.forEach((l) => {
      const key = pairKey(l.source, l.target);
      (pairBuckets.get(key) || pairBuckets.set(key, []).get(key)).push(l);
    });

    const topoLinks = [];
    const extraLinks = [];
    pairBuckets.forEach((arr) => {
      topoLinks.push({ ...arr[0] }); // 再複製一次，與 extra 分開
      if (arr.length > 1) extraLinks.push(...arr.slice(1).map((x) => ({ ...x })));
    });

    /* ---------- 3. 無向表 (component 與鎖定邏輯須用完整 validLinks) ---------- */
    const undirected = {};
    data.nodes.forEach((n) => (undirected[n.id] = []));
    validLinks.forEach(({ source, target }) => {
      undirected[source].push(target);
      undirected[target].push(source);
    });

    /* ---------- 4. 找 weakly‑connected components ---------- */
    const visited = new Set();
    const components = [];
    const bfs = (start) => {
      const q = [start];
      const compNodes = new Set([start]);
      visited.add(start);
      while (q.length) {
        const cur = q.shift();
        undirected[cur].forEach((nx) => {
          if (!visited.has(nx)) {
            visited.add(nx);
            compNodes.add(nx);
            q.push(nx);
          }
        });
      }
      return compNodes;
    };

    rootSet.forEach((r) => {
      if (!visited.has(r)) {
        const nodesInComp = bfs(r);
        const rootsInComp = new Set(
          [...nodesInComp].filter((id) => rootSet.has(id))
        );
        components.push({ roots: rootsInComp, nodes: nodesInComp });
      }
    });
    data.nodes.forEach((n) => {
      if (!visited.has(n.id)) {
        components.push({ roots: new Set(), nodes: new Set([n.id]) });
        visited.add(n.id);
      }
    });

    /* ---------- 5. 拓撲層級 ---------- */
    const rawLevel = {};
    const topoLevels = (nodeArr, linkArr) => {
      const inDeg = {}, g = {};
      nodeArr.forEach((id) => ((inDeg[id] = 0), (g[id] = [])));
      linkArr.forEach(({ source, target }) => {
        if (nodeArr.includes(source) && nodeArr.includes(target)) {
          g[source].push(target);
          inDeg[target]++;
        }
      });
      const q = nodeArr.filter((id) => inDeg[id] === 0).map((id) => ({ id, l: 0 }));
      while (q.length) {
        const { id, l } = q.shift();
        rawLevel[id] = l;
        g[id].forEach((nx) => {
          if (--inDeg[nx] === 0) q.push({ id: nx, l: l + 1 });
        });
      }
    };
    components.forEach(({ nodes }) => topoLevels([...nodes], topoLinks));

    /* ---------- 6. finalLevel ---------- */
    const finalLevel = {};
    data.nodes.forEach((n) => {
      finalLevel[n.id] = rootSet.has(n.id) ? 0 : (rawLevel[n.id] ?? 0) + 1;
    });

    /* ---------- 7. 邊界鎖定 ---------- */
    const node2CompIdx = {};
    components.forEach((c, idx) => c.nodes.forEach((id) => (node2CompIdx[id] = idx)));

    const dataOrderIdx = Object.fromEntries(data.nodes.map((n, i) => [n.id, i]));
    const compRootRank = {};
    components.forEach((comp, idx) => {
      const arr = [...comp.roots].sort((a, b) => dataOrderIdx[a] - dataOrderIdx[b]);
      const rankMap = {};
      arr.forEach((id, i) => (rankMap[id] = { rank: i, total: arr.length }));
      compRootRank[idx] = rankMap;
    });

    const directive = {};
    data.nodes.forEach((n) => {
      if (rootSet.has(n.id)) return;
      const compIdx = node2CompIdx[n.id];
      let connectedRoots = [], connectedOthers = 0;
      undirected[n.id].forEach((nbr) => {
        if (rootSet.has(nbr)) connectedRoots.push(nbr);
        else connectedOthers += 1;
      });
      if (connectedRoots.length && connectedOthers) {
        const rootId = connectedRoots[0];
        const { rank, total } = compRootRank[compIdx][rootId] || {
          rank: 0,
          total: 1,
        };
        directive[n.id] = rank <= (total - 1) / 2 ? "top" : "bottom";
      }
    });

    /* ---------- 8. 座標計算 ---------- */
    const LAYER_X = 500;
    const NODE_SIZE = 380;
    const NODE_Y = NODE_SIZE + 250;
    const GAP_Y = 1000;

    const compBaseY = [];
    let yCursor = 0;
    components.forEach(({ nodes }, idx) => {
      const lvlCnt = {};
      nodes.forEach((id) => {
        const lv = finalLevel[id];
        lvlCnt[lv] = (lvlCnt[lv] || 0) + 1;
      });
      const height = (Math.max(...Object.values(lvlCnt)) - 1) * NODE_Y;
      compBaseY[idx] = yCursor + height / 2;
      yCursor += height + GAP_Y;
    });

    const sortSiblings = (ids) => {
      return ids
        .slice()
        .sort((a, b) => {
          const da = directive[a] || "mid";
          const db = directive[b] || "mid";
          if (da === db) return 0;
          if (da === "top") return -1;
          if (db === "top") return 1;
          if (da === "bottom") return 1;
          if (db === "bottom") return -1;
          return 0;
        });
    };

    const nodesAll = data.nodes.map((n) => {
      const lv = finalLevel[n.id];
      const compIdx = node2CompIdx[n.id];
      const peers = [...components[compIdx].nodes].filter((id) => finalLevel[id] === lv);
      const siblings = sortSiblings(peers);
      const yWithin = (siblings.indexOf(n.id) - (siblings.length - 1) / 2) * NODE_Y;

      return {
        ...n,
        x: lv * LAYER_X - 1000,
        y: compBaseY[compIdx] + yWithin,
        fx: lv * LAYER_X - 1000,
        fy: compBaseY[compIdx] + yWithin,
        short: n.label.split("\n").find((l) => l.trim())?.trim() ?? "",
        color: rootSet.has(n.id) ? rootColor : fixedColor,
      };
    });

    const allLinks = [...topoLinks, ...extraLinks];
    return { nodes: nodesAll, links: allLinks };
  }, [data]);

  /* ========================= 畫布設定 ========================= */
  const [zoomEnabled, setZoomEnabled] = useState(false);
  useEffect(() => {
    const down = (e) => (e.key === "Shift" || e.key === "Control") && setZoomEnabled(true);
    const up = (e) => (e.key === "Shift" || e.key === "Control") && setZoomEnabled(false);
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
    fg.d3Force("collision", forceCollide().radius(() => 380 / 2 + 40));
    fg.d3ReheatSimulation();
    fg.zoom(0.4, 0, 0);
  }, [graphKey]);

  /* -------------------- 節點繪製 -------------------- */
  const nodeCanvasObject = useCallback((node, ctx) => {
    const SIZE = 380, R = 30, HALF = SIZE / 2;
    ctx.fillStyle = node.color;
    ctx.beginPath();
    const x = node.x - HALF, y = node.y - HALF;
    ctx.moveTo(x + R, y);
    ctx.lineTo(x + SIZE - R, y);
    ctx.quadraticCurveTo(x + SIZE, y, x + SIZE, y + R);
    ctx.lineTo(x + SIZE, y + SIZE - R);
    ctx.quadraticCurveTo(x + SIZE, y + SIZE, x + SIZE - R, y + SIZE);
    ctx.lineTo(x + R, y + SIZE);
    ctx.quadraticCurveTo(x, y + SIZE, x, y + SIZE - R);
    ctx.lineTo(x, y + R);
    ctx.quadraticCurveTo(x, y, x + R, y);
    ctx.closePath();
    ctx.fill();

    const FONT = 40, MAX_W = SIZE * 0.9;
    ctx.font = `${FONT}px sans-serif`;
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const words = node.short.split(" ");
    const lines = [];
    let cur = "";
    words.forEach((w) => {
      const test = cur ? `${cur} ${w}` : w;
      if (ctx.measureText(test).width <= MAX_W) cur = test;
      else {
        lines.push(cur);
        cur = w;
      }
    });
    if (cur) lines.push(cur);

    const LINE_H = FONT * 1.2;
    const MAX_LN = Math.floor((SIZE * 0.9) / LINE_H);
    if (lines.length > MAX_LN) {
      lines.length = MAX_LN;
      while (ctx.measureText(lines[MAX_LN - 1] + "…").width > MAX_W) lines[MAX_LN - 1] = lines[MAX_LN - 1].slice(0, -1);
      lines[MAX_LN - 1] += "…";
    }
    const baseY = node.y - (lines.length * LINE_H) / 2 + LINE_H / 2;
    lines.forEach((l, i) => ctx.fillText(l, node.x, baseY + i * LINE_H));

    node.__bckgDimensions = [SIZE, SIZE];
  }, []);

  const nodePointerAreaPaint = useCallback((n, color, ctx) => {
    if (!n.__bckgDimensions) return;
    const [d] = n.__bckgDimensions;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(n.x, n.y, d / 2, 0, 2 * Math.PI);
    ctx.fill();
  }, []);

  /* -------------------- Resize Observer -------------------- */
  const containerRef = useRef();
  const [graphSize, setGraphSize] = useState({ width: 0, height: 0 });
  useLayoutEffect(() => {
    if (!containerRef.current) return;
    const update = () =>
      setGraphSize({
        width: containerRef.current.clientWidth,
        height: containerRef.current.clientHeight,
      });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, []);

  /* -------------------- Render -------------------- */
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
        {graphData.nodes.length ? (
          <ForceGraph2D
            key={graphKey}
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
            enableNodeDrag
            enableZoomInteraction={zoomEnabled}
            enablePanInteraction={zoomEnabled}
            autoPauseRedraw
          />
        ) : (
          <div style={{ fontSize: 24, color: "#666" }}>No matching data</div>
        )}

        {graphData.nodes.length > 0 && (
          <div
            style={{
              position: "absolute",
              top: 10,
              left: 10,
              background: "#ffffffcc",
              padding: "6px 10px",
              borderRadius: 6,
              fontSize: 13,
              boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
            }}
          >
            <kbd>Shift</kbd> / <kbd>Ctrl</kbd> + scroll 或 drag → Zoom, Pan
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

import React, { useState } from "react";
import axios from "axios";
import Potential_Treatment_Path from './Potential_Treatment_Path.js'
import Potential_Treatment_Point from './Potential_Treatment_Point.js'
import Potential_Treatment_Table from './Potential_Treatment_Table.js'
import Potential_treatment_workup from './Potential_treatment_workup.js'
import { config } from "../../../constant";  // 這裡改成相對路徑

export default function GraphView() {
  const [activeTab, setActiveTab] = useState("alt_path");
  const [variant, setVariant] = useState("BRAF V600E");
  const [mmrStatus, setMmrStatus] = useState("dMMR/MSI-H");
  const [cancerStatus, setCancerStatus] = useState("Colon Cancer");
  const [graphData1, setGraphData1] = useState(null);
  const [graphData2, setGraphData2] = useState(null);
  const [graphData3, setGraphData3] = useState(null); 
  const [workupData, setWorkupData] = useState(null); 


  const tabList = [
    { id: "alt_path", label: "Alternative Path" },
    { id: "cure_way", label: "Cure way" },
    { id: "recommendation_treatment", label: "Recommendation Treatment" },
    { id: "workup_exam", label: "Initial Workup" }, 
  ];

  const handleSubmit = async () => {
    try {
      const response = await axios.post(`${config.rootApiIP}/potential_treatment`, {
        variant: variant,
        mmr_status: mmrStatus,
        cancer_status: cancerStatus,
      });

      setGraphData1(response.data.treatment_graph);
      setGraphData2(response.data.treatment_point);
      setGraphData3(response.data.treatment_form);
      setWorkupData(response.data.workup);  

  console.log("🚀 [GraphViewPanel] 接收到的 1111data：", response);

    } catch (error) {
      console.error("送出時發生錯誤:", error);
      alert("資料讀取失敗！");
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      {/* ===== 1. Variant 輸入框 ===== */}
        <div style={{
    display: "flex",
    alignItems: "center",
    gap: "12px",
    padding: "0.5rem 1rem",
    borderBottom: "none",
    fontSize: "14px"
  }}>
    {/* MMR/MSI 狀態 */}
    <label htmlFor="cancer_type" style={{ fontWeight: "bold" }}>
    cancer_type:
    </label>
    <select
      id="cancer_type"
      value={cancerStatus}
      onChange={(e) => setCancerStatus(e.target.value)}
      style={{
        height: "32px",
        padding: "4px 8px",
        border: "1px solid #ccc",
        borderRadius: 4,
        minWidth: "160px"
      }}
    >
      <option value="Colon Cancer">Colon Cancer</option>
      {/* <option value="pMMR/MSS">pMMR / MSS</option> */}
      {/* <option value="unclassified / unknown">unclassified / unknown</option> */}
    </select>
    <label htmlFor="mmr-select" style={{ fontWeight: "bold" }}>
      MMR/MSI status:
    </label>
    <select
      id="mmr-select"
      value={mmrStatus}
      onChange={(e) => setMmrStatus(e.target.value)}
      style={{
        height: "32px",
        padding: "4px 8px",
        border: "1px solid #ccc",
        borderRadius: 4,
        minWidth: "160px"
      }}
    >
      <option value="dMMR/MSI-H">dMMR / MSI-H</option>
      <option value="pMMR/MSS">pMMR / MSS</option>
      <option value="unclassified / unknown">unclassified / unknown</option>
    </select>

    {/* Variant 輸入框 */}
    <label htmlFor="variant-input" style={{ fontWeight: "bold" }}>
      Variant:
    </label>
    <input
      id="variant-input"
      type="text"
      placeholder="e.g. BRAF V600E"
      value={variant}
      onChange={(e) => setVariant(e.target.value)}
      style={{
        height: "32px",
        padding: "4px 8px",
        border: "1px solid #ccc",
        borderRadius: 4,
        minWidth: "200px"
      }}
    />

    {/* 提交按鈕 */}
    <button
      onClick={handleSubmit}
      style={{
        height: "32px",
        padding: "4px 16px",
        background: "skyblue",
        color: "#fff",
        border: "none",
        borderRadius: 4,
        cursor: "pointer"
      }}
    >
      submit
    </button>
  </div>

      {/* ===== 2. 只有送出後（有資料）才顯示 Tabs 和內容 ===== */}
      {(graphData1 || graphData2 || graphData3) && (
        <>
          {/* Tabs header */}
          <div
            style={{
              display: "flex",
              borderBottom: "2px solid #ddd",
              justifyContent: "center",
              marginBottom: "0.5rem",
              fontSize: "14px",
              fontWeight: "bold",
              letterSpacing: "0.5px",
            }}
          >
            {tabList.map((tab) => (
              <div
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  cursor: "pointer",
                  padding: "10px 16px",
                  color: activeTab === tab.id ? "#a000a0" : "#666",
                  borderBottom:
                    activeTab === tab.id ? "3px solid #a000a0" : "3px solid transparent",
                }}
              >
                {tab.label}
              </div>
            ))}
          </div>
  
          {/* Tab content */}
          <div style={{ flex: 1 }}>
            {activeTab === "alt_path" && graphData1 && (
              <Potential_Treatment_Path
                data={graphData1}
                // variant={variant}
              />
            )}
            {activeTab === "cure_way" && graphData2 && (
              <Potential_Treatment_Path
                data={graphData2}
                // variant={variant}
              />
            )}
            {activeTab === "recommendation_treatment" && graphData3 && (
              <Potential_Treatment_Table variantData={graphData3} />
            )}
            {activeTab === "workup_exam" && workupData && (
              <Potential_treatment_workup
                data={workupData}
    // variant={variant} ← 若不需要可移除
              />
            )}
          </div>
        </>
      )}
    </div>
  );
  
}

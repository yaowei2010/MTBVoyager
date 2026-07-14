import React from "react";

export default function VariantTable({ variantData = [] }) {
  return (
    <div style={{ padding: "1rem", fontFamily: "Arial" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          tableLayout: "fixed",
        }}
      >
        <thead>
          <tr>
            <th style={thStyle}>Variant</th>
            <th style={thStyle}>Label</th>
            <th style={thStyle}>Category</th>
          </tr>
        </thead>
        <tbody>
          {variantData.length > 0 ? (
            variantData.map((row, idx) => (
              <tr key={idx}>
                <td style={tdStyle}>{row.variant}</td>
                <td style={{ ...tdStyle, whiteSpace: "pre-wrap" }}>{row.label}</td>
                <td style={tdStyle}>{row.category}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td style={tdStyle} colSpan="3" align="center">
                沒有資料
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const thStyle = {
  border: "1px solid #ccc",
  padding: "8px",
  backgroundColor: "#f0f0f0",
  textAlign: "left",
};

const tdStyle = {
  border: "1px solid #ccc",
  padding: "8px",
  verticalAlign: "top",
};

import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { Box, Typography, Paper, Grid, Alert, AlertTitle, Button, Stack } from "@mui/material";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { GlobalWorkerOptions, getDocument } from "pdfjs-dist";
import { config } from "../../../constant";

GlobalWorkerOptions.workerSrc = process.env.PUBLIC_URL + "/pdf.worker.mjs";

const Cancer_Type_Prediction = ({ onGoMutSig }) => {
  const [predictionSummary, setPredictionSummary] = useState([]);
  const [pdfBase64, setPdfBase64] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ✅ 新增：缺少 mutation signature 前置資料
  const [missingMutSig, setMissingMutSig] = useState(false);

  // ✅ 新增：保留 jobId 方便跳轉
  const [jobId, setJobId] = useState("");

  const canvasRef = useRef(null);

  const renderPdf = async (pdfBase64Data, canvasRef) => {
    if (pdfBase64Data && canvasRef.current) {
      try {
        const pdfData = Uint8Array.from(atob(pdfBase64Data), (c) => c.charCodeAt(0));
        const pdf = await getDocument({ data: pdfData }).promise;
        const page = await pdf.getPage(1);

        const canvas = canvasRef.current;
        const context = canvas.getContext("2d");
        const viewport = page.getViewport({ scale: 1.5 });

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const renderContext = {
          canvasContext: context,
          viewport: viewport,
        };

        await page.render(renderContext).promise;
      } catch (err) {
        console.error("Error rendering PDF:", err);
      }
    }
  };

  useEffect(() => {
    const fetchPrediction = async () => {
      setLoading(true);
      try {
        const newjobid = window.location.pathname.split("/").pop();
        setJobId(newjobid);
        console.log("Fetching prediction for newjobid:", newjobid);

        const response = await axios.post(`${config.rootApiIP}/cancertype_prediction`, {
          newjobid: newjobid,
        });

        console.log("API response:", response.data);

        // ✅ 成功：清掉 prereq 提示
        setMissingMutSig(false);

        setPredictionSummary(response.data.prediction_summary_preview || []);
        setPdfBase64(response.data.pdf_base64 || "");
        setError(null);
      } catch (err) {
        console.error("Error fetching prediction:", err);

        const status = err?.response?.status;
        const data = err?.response?.data;

        // ✅ 後端回傳缺少前置流程（mutation signature）
        if (
          status === 409 &&
          data?.status === "missing_prereq" &&
          data?.missing === "mutation_signature"
        ) {
          setMissingMutSig(true);
          setError(null);
          setPredictionSummary([]);
          setPdfBase64("");
        } else {
          setMissingMutSig(false);
          setError("Failed to fetch prediction.");
          setPredictionSummary([]);
          setPdfBase64("");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPrediction();
  }, []);

  useEffect(() => {
    renderPdf(pdfBase64, canvasRef);
  }, [pdfBase64]);

  return (
    <Box sx={{ p: 3 }}>
      {loading && <Typography>Loading...</Typography>}
      {error && <Typography color="error">{error}</Typography>}

      {/* ✅ 更好看的 warning 提示 */}
      {!loading && !error && missingMutSig && (
      <Alert
        severity="warning"
        icon={<WarningAmberRoundedIcon fontSize="inherit" />}
        sx={{
          mb: 2,
          borderRadius: 2,
          alignItems: "flex-start",
          "& .MuiAlert-message": { width: "100%" },
        }}
      >
        <AlertTitle sx={{ fontWeight: 800 }}>請先完成 Mutation Signature 流程</AlertTitle>

        <Typography variant="body2" sx={{ mb: 0.75 }}>
          Cancer Type Prediction 需要先產生下列檔案：
        </Typography>

        {/* ✅ 讓 code 區塊與按鈕同一列，且垂直對齊 */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",   // ✅ 垂直對齊
            gap: 2,
          }}
        >
          <Box
            component="code"
            sx={{
              flex: 1,              // ✅ 讓 code 區塊吃滿剩餘寬度
              display: "block",
              px: 1.25,
              py: 0.75,
              borderRadius: 1.5,
              bgcolor: "rgba(0,0,0,0.06)",
              fontSize: 13,
              overflowX: "auto",
              minHeight: 36,        // ✅ 給一個穩定高度（可調）
              lineHeight: "20px",
            }}
          >
            Assignment_Solution_Activities.txt
          </Box>

          <Button
            variant="contained"
            size="small"
            onClick={() => {
              if (typeof onGoMutSig === "function") onGoMutSig();
            }}
            sx={{
              whiteSpace: "nowrap",
              height: 36,           // ✅ 和 code 區塊 minHeight 對齊
              px: 2,
            }}
          >
            前往 MUTATION SIGNATURE
          </Button>
        </Box>

        <Typography variant="caption" sx={{ display: "block", mt: 1, opacity: 0.8 }}>
          完成後回到此頁即可自動讀取並產生報告。
        </Typography>
      </Alert>

      )}

      {/* ✅ 只有在不是 missingMutSig 才顯示原本內容 */}
      {!loading && !error && !missingMutSig && (
        <>
          <Typography variant="h4" gutterBottom>
            Prediction Summary
          </Typography>

          {predictionSummary.length === 0 ? (
            <Typography>No prediction summary available.</Typography>
          ) : (
            <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
              {predictionSummary.map((item, index) => (
                <Grid container spacing={2} key={index}>
                  {[...Object.entries(item)]
                    .filter(([key]) => key !== "explanation_plot")
                    .sort(([keyA], [keyB]) => {
                      if (keyA === "pred_cancer") return -1;
                      if (keyB === "pred_cancer") return 1;
                      return 0;
                    })
                    .map(([key, value]) => {
                      let label = key;
                      if (key === "pred_prob") label = "Prediction Probability";
                      if (key === "pred_cancer") label = "Prediction Cancer";

                      return (
                        <React.Fragment key={key}>
                          <Grid item xs={4}>
                            <Typography fontWeight="bold">{label}</Typography>
                          </Grid>
                          <Grid item xs={8}>
                            <Typography>{String(value)}</Typography>
                          </Grid>
                        </React.Fragment>
                      );
                    })}
                </Grid>
              ))}
            </Paper>
          )}

          {pdfBase64 && (
            <>
              <Typography variant="h4" gutterBottom>
                Prediction Report
              </Typography>
              <canvas ref={canvasRef} style={{ border: "3px solid #ccc" }}></canvas>
            </>
          )}
        </>
      )}
    </Box>
  );
};

export default Cancer_Type_Prediction;

import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { DataGrid } from "@mui/x-data-grid";
import { config } from '../../../constant';

// import 'pdfjs-dist/build/pdf.worker.entry';
// import { getDocument } from 'pdfjs-dist';

// import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist';
// GlobalWorkerOptions.workerSrc = process.env.PUBLIC_URL + "/pdf.worker.mjs";

import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist';

GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.mjs', import.meta.url).toString();




const MutationSignature = () => {
    const [activities, setActivities] = useState([]);
    const [pdfBase64, setPdfBase64] = useState("");
    const [pdfBase64TMBPlot, setPdfBase64TMBPlot] = useState("");
    const [pdfBase64ActivityPlot, setPdfBase64ActivityPlot] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const canvasRef = useRef(null);
    const canvasRefTMB = useRef(null);
    const canvasRefActivity = useRef(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                console.log("Fetching MutationSignature...");
                const response = await axios.post(`${config.rootApiIP}/mutation_signature`, {
                    newjobid: window.location.pathname.split('/').pop(),
                });
                console.log("Response:", response);
                setActivities(response.data.activities);
                setPdfBase64(response.data.pdf_base64);
                setPdfBase64TMBPlot(response.data.pdf_base64_TMB_plot);
                setPdfBase64ActivityPlot(response.data.pdf_base64_activity_plot);
                setError(null);
            } catch (err) {
                setError("Failed to fetch data.");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const renderPdf = async (pdfBase64Data, canvasRef) => {
        if (pdfBase64Data && canvasRef.current) {
            try {
                const pdfData = atob(pdfBase64Data);
                const pdf = await getDocument({ data: pdfData }).promise;
                const page = await pdf.getPage(1);

                const canvas = canvasRef.current;
                const context = canvas.getContext("2d");
                const viewport = page.getViewport({ scale: 1.7 });

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
        renderPdf(pdfBase64, canvasRef);
    }, [pdfBase64]);

    useEffect(() => {
        renderPdf(pdfBase64TMBPlot, canvasRefTMB);
    }, [pdfBase64TMBPlot]);

    useEffect(() => {
        renderPdf(pdfBase64ActivityPlot, canvasRefActivity);
    }, [pdfBase64ActivityPlot]);

    const transposedRows = activities.length > 0
        ? Object.keys(activities[0])
            .filter(key => !key.includes("description") && !key.includes("rate") && key !== "Samples")
            .map((key, index) => {
                const row = {
                    id: index,
                    field: key,
                    description: activities[0][`${key}_description`] || "",
                    rate: activities[0][`${key}_rate`] || "",
                };
                activities.forEach((activity, idx) => {
                    row[`Sample${idx + 1}`] = activity[key];
                });
                return row;
            })
        : [];

    const transposedColumns = [
        {
            field: "field",
            headerName: "SBS Type",
            width: 200,
            renderCell: (params) => {
                const baseUrl = "https://cancer.sanger.ac.uk/signatures/sbs/";
                const sbsType = params.value.toLowerCase();
                const url = `${baseUrl}${sbsType}/`;
                return (
                    <a href={url} target="_blank" rel="noopener noreferrer">
                        {params.value}
                    </a>
                );
            },
        },
        { field: "description", headerName: "Description", width: 600 },
        { field: "rate", headerName: "SBS Rate", width: 150 },
        ...activities.map((_, index) => ({
            field: `Sample${index + 1}`,
            headerName: `Sample`,
            width: 100,
        })),
    ];

    return (
        <div style={{ padding: "20px" }}>
            {loading && <p>Loading...</p>}
            {error && <p style={{ color: "red" }}>{error}</p>}

            {!loading && !error && (
                <div>
                    <h1>Activities</h1>
                    <div style={{ height: 400, width: "100%" }}>
                        <DataGrid
                            rows={transposedRows}
                            columns={transposedColumns}
                            pageSize={10}
                            rowsPerPageOptions={[10]}
                        />
                    </div>

                    {pdfBase64 && (
                        <div style={{ marginTop: "20px" }}>
                            <h1>Mutation Signature</h1>
                            <canvas ref={canvasRef} style={{ border: "3px solid #ccc" }}></canvas>
                        </div>
                    )}

                    {/* {(pdfBase64TMBPlot || pdfBase64ActivityPlot) && (
                        <div style={{ marginTop: "20px", display: "flex", justifyContent: "space-between" }}>
                            {pdfBase64TMBPlot && (
                                <div style={{ flex: 1, marginRight: "10px" }}>
                                    <h1>TMB Plot</h1>
                                    <canvas ref={canvasRefTMB} style={{ border: "3px solid #ccc", width: "100%" }}></canvas>
                                </div>
                            )}
                            {pdfBase64ActivityPlot && (
                                <div style={{ flex: 1, marginLeft: "10px" }}>
                                    <h1>Activity Plot</h1>
                                    <canvas ref={canvasRefActivity} style={{ border: "3px solid #ccc", width: "100%" }}></canvas>
                                </div>
                            )}
                        </div>
                    )} */}
                </div>
            )}
        </div>
    );
};

export default MutationSignature;

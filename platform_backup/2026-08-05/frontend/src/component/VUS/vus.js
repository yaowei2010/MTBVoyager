import React, { useState, useRef, useLayoutEffect, useMemo, useEffect, useContext } from "react";
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  CircularProgress,
  Chip,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Pagination,
  InputAdornment,
  Tooltip,
} from "@mui/material";
import { Tabs, Tab } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import axios from "axios";
import PathwayViewer from "./PathwayContain";
import MutationViewer from "./mutation";
import {
  buildOncoByDiagnosis,
  buildQueryOncoPrint,
  QueryOncoPrint,
  DiagnosisBarChart,
} from "./oncoprint";
import { config } from "../../constant";
import { AuthContext } from "../Auth/AuthContext";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import SearchIcon from "@mui/icons-material/Search";
import {
  DETAIL_FIELDS_PER_PAGE,
  getFieldGroupName,
  groupFields,
  buildRows,
  getAllFields,
  getSummaryFields,
  getDefaultDetailFields,
  getSelectableDetailFields,
  getFilteredSelectableDetailFields,
  getDetailDialogPagedFields,
  createDataGridColumns,
} from "./dataResultUtils";

const MIN_CHART_W = 720;
const EXAMPLES = ["TP53", "KRAS.p.A146T", "EGFR", "BRAF.p.V600E", "PIK3CA"];

function useContainerWidth() {
  const ref = useRef(null);
  const [width, setWidth] = useState(0);

  useLayoutEffect(() => {
    if (ref.current) {
      const w = ref.current.getBoundingClientRect().width || 0;
      if (w) setWidth(w);
    }
  }, []);

  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const ro = new ResizeObserver((entries) => {
      const cr = entries[0]?.contentRect;
      if (cr?.width != null) setWidth(cr.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return [ref, width];
}

function parseQueries(raw, max = 20) {
  const s = String(raw || "")
    .replace(/[\uFF0C\u3001\uFF1B\uFF1B]/g, ",")
    .replace(/[,\s]+/g, "\n");

  const tokens = s
    .split(/\n+/)
    .map((t) => t.trim())
    .filter(Boolean);

  const uniq = Array.from(new Set(tokens));
  return uniq.slice(0, max);
}

function GeneProteinInputMui() {
  const [inputValue, setInputValue] = useState("");
  const [submittedList, setSubmittedList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [perQueryData, setPerQueryData] = useState({});
  const [activeKey, setActiveKey] = useState("");

  const [tabIndex, setTabIndex] = useState(0);
  const { userId } = useContext(AuthContext);

  const [detailPageByRow, setDetailPageByRow] = useState({});
  const [fieldDialogOpen, setFieldDialogOpen] = useState(false);
  const [fieldSearch, setFieldSearch] = useState("");

  const [rowDetailOpen, setRowDetailOpen] = useState(false);
  const [selectedRow, setSelectedRow] = useState(null);
  const [detailDialogPage, setDetailDialogPage] = useState(1);

  const searchRef = useRef(null);
  const [searchH, setSearchH] = useState(96);

  useLayoutEffect(() => {
    const measure = () => {
      if (!searchRef.current) return;
      setSearchH(searchRef.current.getBoundingClientRect().height);
    };
    measure();
    window.addEventListener("resize", measure);
    return () => window.removeEventListener("resize", measure);
  }, []);

  const [chartsWrapRef, chartsWrapWidth] = useContainerWidth();
  const chartWidth = Math.max(MIN_CHART_W, chartsWrapWidth - 32);

  const hasAnyData = Object.keys(perQueryData).length > 0;

  const handleChange = (e) => setInputValue(e.target.value);

  const handleInsertExample = (example) => {
    const exist = parseQueries(inputValue);
    if (exist.includes(example)) return;
    if (!inputValue.trim()) {
      setInputValue(example);
    } else {
      setInputValue((prev) => prev.replace(/\s+$/, "") + "\n" + example);
    }
  };

  const handleFillPreset = () => {
    setInputValue(EXAMPLES.slice(0, 3).join("\n"));
  };

  const handleClearInput = () => setInputValue("");

  const handleSubmit = async () => {
    const queries = parseQueries(inputValue);
    if (queries.length === 0) {
      alert("Please enter at least one query. Use a new line or comma to separate multiple queries.");
      return;
    }

    setLoading(true);
    setError("");
    setSubmittedList(queries);
    setDetailPageByRow({});
    setRowDetailOpen(false);
    setSelectedRow(null);
    setDetailDialogPage(1);

    try {
      const reqs = queries.map((q) =>
        axios
          .post(`${config.rootApiIP}/vus`, { query: q, user_id: userId })
          .then((r) => ({ key: q, data: r.data }))
          .catch((e) => ({ key: q, error: e }))
      );

      const results = await Promise.all(reqs);
      const map = {};
      for (const { key, data } of results) {
        if (data) map[key] = data;
      }

      setPerQueryData(map);

      const firstAvailable = queries.find((q) => map[q]);
      setActiveKey(firstAvailable || "");
    } catch (err) {
      console.error(err);
      setError(err.message || "An error occurred during the query.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleDetailClick = (row) => {
    const sourceTable = row.source_table || "";
    const parts = sourceTable.split("_");
    const id = parts[parts.length - 1];
    if (id) window.open(`${config.rootPathPrefix}/Job_results/detail_somatic/${id}`, "_blank");
    else alert("Invalid source_table format.");
  };

  const currentData = useMemo(() => perQueryData[activeKey] || null, [activeKey, perQueryData]);
  const hasResults = Boolean(currentData?.full_results?.length);

  const rows = useMemo(() => buildRows(currentData), [currentData]);
  const allFields = useMemo(() => getAllFields(rows), [rows]);
  const summaryFields = useMemo(() => getSummaryFields(allFields), [allFields]);

  const defaultDetailFields = useMemo(
    () => getDefaultDetailFields(allFields, summaryFields),
    [allFields, summaryFields]
  );

  const [detailFields, setDetailFields] = useState([]);

  useEffect(() => {
    if (!allFields.length) {
      setDetailFields([]);
      return;
    }

    setDetailFields((prev) => {
      if (prev.length > 0) {
        const filtered = prev.filter((f) => allFields.includes(f) && !summaryFields.includes(f));
        if (filtered.length > 0 || prev.length === 0) return filtered;
      }

      return defaultDetailFields.filter(
        (f) => getFieldGroupName(f) !== "Rankscores"
      );
    });
  }, [allFields, summaryFields, defaultDetailFields]);

  useEffect(() => {
    setDetailPageByRow((prev) => {
      const next = {};
      Object.keys(prev).forEach((rowId) => {
        next[rowId] = 1;
      });
      return next;
    });
  }, [detailFields]);

  const selectableDetailFields = useMemo(
    () => getSelectableDetailFields(allFields, summaryFields),
    [allFields, summaryFields]
  );

  const filteredSelectableDetailFields = useMemo(
    () => getFilteredSelectableDetailFields(selectableDetailFields, fieldSearch),
    [selectableDetailFields, fieldSearch]
  );

  const groupedSelectableFields = useMemo(() => {
    return groupFields(filteredSelectableDetailFields);
  }, [filteredSelectableDetailFields]);

  const groupedSelectedFields = useMemo(() => {
    return groupFields(detailFields);
  }, [detailFields]);



  const openRowDetailDialog = (row) => {
    setSelectedRow(row);
    setDetailDialogPage(1);
    setRowDetailOpen(true);
  };

  const closeRowDetailDialog = () => {
    setRowDetailOpen(false);
    setSelectedRow(null);
    setDetailDialogPage(1);
  };

  const detailDialogPagedData = useMemo(() => {
    return getDetailDialogPagedFields(detailFields, detailDialogPage);
  }, [detailFields, detailDialogPage]);

  const oncoDatadiagnosis = useMemo(() => {
    if (!currentData) return null;
    return buildOncoByDiagnosis(currentData.full_results || [], currentData.all_tables || []);
  }, [currentData]);

  const oncoPrintOverviewData = useMemo(() => {
    if (!submittedList.length) return null;
    return buildQueryOncoPrint(perQueryData, submittedList);
  }, [perQueryData, submittedList]);

  const plotData = useMemo(() => {
    if (!currentData) return null;
    const pd = currentData.plot_data;
    return typeof pd === "string" ? JSON.parse(pd) : pd || null;
  }, [currentData]);

  const mafForMutation = useMemo(() => {
    const m = currentData?.maf;
    if (!m) return [];
    if (typeof m === "string") {
      try {
        return JSON.parse(m);
      } catch {
        return [];
      }
    }
    return Array.isArray(m) ? m : [];
  }, [currentData]);

  const dataGridColumns = useMemo(() => {
    return createDataGridColumns(summaryFields, openRowDetailDialog);
  }, [summaryFields]);

  return (
    <Box sx={{ position: "relative", minHeight: "100vh", pb: "72px", overflowX: "hidden" }}>
      <Box
        ref={searchRef}
        sx={{
          position: "relative",
          top: 80,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 1200,
          width: "100%",
          maxWidth: "1100px",
          px: 2,
          pt: 1.5,
          background: "linear-gradient(180deg, rgba(255,255,255,0.98), rgba(255,255,255,0.94))",
          boxShadow: "0 6px 16px rgba(0,0,0,0.08)",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        <Paper elevation={0} sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 700 }}>
            Search Database (e.g., TP53, KRAS, EGFR)
          </Typography>

          <Box sx={{ mt: 1.25 }}>
            <Typography variant="caption" sx={{ mr: 1 }}>
              Examples:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
              {EXAMPLES.map((ex) => (
                <Chip
                  key={ex}
                  label={ex}
                  variant="outlined"
                  clickable
                  onClick={() => handleInsertExample(ex)}
                  sx={{ cursor: "pointer" }}
                />
              ))}
              <Chip
                label="Fill Example List"
                color="primary"
                variant="outlined"
                clickable
                onClick={handleFillPreset}
                sx={{ cursor: "pointer" }}
              />
              <Chip
                label="Clear"
                variant="outlined"
                clickable
                onClick={handleClearInput}
                sx={{ cursor: "pointer" }}
              />
            </Stack>
          </Box>

          <br />

          <Box sx={{ display: "flex", gap: 1 }}>
            <TextField
              fullWidth
              label="Enter query (Enter to submit, Shift+Enter for a new line)"
              variant="outlined"
              value={inputValue}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              multiline
              minRows={2}
              maxRows={6}
            />
            <Button variant="contained" color="primary" onClick={handleSubmit} sx={{ whiteSpace: "nowrap" }}>
              Submit
            </Button>
          </Box>

          {loading && (
            <Box sx={{ mt: 2, display: "flex", alignItems: "center", gap: 1 }}>
              <CircularProgress size={20} />
              <Typography variant="body2">Searching...</Typography>
            </Box>
          )}

          {error && <Typography sx={{ mt: 2, color: "red" }}>Error: {error}</Typography>}
        </Paper>
      </Box>

      <Box sx={{ height: searchH + 80 }} />

      {hasAnyData && (
        <Box sx={{ width: "90%", mx: "auto", mt: 2 }}>
          <Paper elevation={2}>
            <Tabs
              value={tabIndex}
              onChange={(e, v) => setTabIndex(v)}
              indicatorColor="primary"
              textColor="primary"
              variant="fullWidth"
            >
              <Tab label="Database Result" />
              <Tab label="Mutation" />
              {/* <Tab label="Pathway Viewer" /> */}
            </Tabs>
          </Paper>

          {tabIndex === 0 && (
            <Box sx={{ mt: 2 }}>
              <Paper sx={{ p: 1.5, mb: 1 }}>
                <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>
                  Gene switch
                </Typography>
                <ToggleButtonGroup
                  value={activeKey}
                  exclusive
                  onChange={(_, v) => v && setActiveKey(v)}
                  size="small"
                  sx={{ flexWrap: "wrap", gap: 1 }}
                >
                  {submittedList.map((q) => (
                    <ToggleButton key={q} value={q}>
                      {q}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              </Paper>

              {hasResults && (
                <Paper sx={{ p: 2, mb: 1 }}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 2,
                      flexWrap: "wrap",
                    }}
                  >
                    <Box sx={{ flex: 1, minWidth: 260 }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                        Detail Field Settings
                      </Typography>

                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" sx={{ color: "text.secondary" }}>
                            {detailFields.length} fields selected
                          </Typography>

                          {detailFields.length > 0 && (
                            <Box sx={{ mt: 1, display: "flex", gap: 1, flexWrap: "wrap" }}>
                              {Object.entries(groupedSelectedFields).map(([groupName, fields]) => (
                                <Tooltip
                                  key={groupName}
                                  arrow
                                  placement="top"
                                  title={
                                      <Box sx={{ maxWidth: 420, py: 0.5 }}>
                                        <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 0.5 }}>
                                          {groupName}
                                        </Typography>
                                        <Box component="ul" sx={{ m: 0, pl: 2 }}>
                                          {fields.map((field) => (
                                            <Box
                                              key={field}
                                              component="li"
                                              sx={{ fontSize: 12, lineHeight: 1.5 }}
                                            >
                                              {field}
                                            </Box>
                                          ))}
                                        </Box>
                                      </Box>
                                    }
                                >
                                  <Chip
                                    size="small"
                                    variant="outlined"
                                    label={`${groupName} (${fields.length})`}
                                  />
                                </Tooltip>
                              ))}
                            </Box>
                          )}
                        </Box>
                    </Box>

                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<ViewColumnIcon />}
                      onClick={() => setFieldDialogOpen(true)}
                      sx={{ whiteSpace: "nowrap" }}
                    >
                      Configure Detail Fields
                    </Button>
                  </Box>
                </Paper>
              )}

              {hasResults ? (
                <Paper sx={{ width: "100%", overflow: "hidden" }}>
                  <Box sx={{ width: "100%" }}>
                    <DataGrid
                      rows={rows}
                      columns={dataGridColumns}
                      getRowId={(row) => row.id}
                      disableRowSelectionOnClick
                      pagination
                      pageSizeOptions={[5, 10, 20, 50]}
                      initialState={{
                        pagination: {
                          paginationModel: { pageSize: 10, page: 0 },
                        },
                      }}
                      rowHeight={72}
                      sx={{
                        border: 0,
                        backgroundColor: "#fff",
                        "& .MuiDataGrid-columnHeaders": {
                          backgroundColor: "#f8f8f8",
                          borderBottom: "1px solid #e0e0e0",
                        },
                        "& .MuiDataGrid-columnHeader": {
                          backgroundColor: "#f8f8f8",
                          fontWeight: 700,
                        },
                        "& .MuiDataGrid-cell": {
                          borderBottom: "1px solid #f0f0f0",
                          alignItems: "flex-start",
                          py: 1,
                        },
                        "& .MuiDataGrid-cell:focus, & .MuiDataGrid-columnHeader:focus": {
                          outline: "none",
                        },
                        "& .MuiDataGrid-row:hover": {
                          backgroundColor: "#fafcff",
                        },
                      }}
                    />
                  </Box>
                </Paper>
              ) : (
                <Typography variant="body2" sx={{ mt: 2 }}>
                  {activeKey ? "No query result yet." : "Please submit a query first."}
                </Typography>
              )}
            </Box>
          )}

          {tabIndex === 1 && (
            <Box sx={{ mt: 2, width: "100%" }}>
              <Box ref={chartsWrapRef} sx={{ width: "100%", display: "grid", gap: 2 }}>
                <Box sx={{ width: "100%", border: "1px solid #e0e0e0", p: 1, borderRadius: 1, overflowX: "auto" }}>
                  {oncoPrintOverviewData ? (
                    <QueryOncoPrint data={oncoPrintOverviewData} title="Queried genes overview" />
                  ) : (
                    <Typography variant="body2">No oncoprint data.</Typography>
                  )}
                </Box>

                <Paper sx={{ p: 1.5, mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>
                    Gene switch
                  </Typography>
                  <ToggleButtonGroup
                    value={activeKey}
                    exclusive
                    onChange={(_, v) => v && setActiveKey(v)}
                    size="small"
                    sx={{ flexWrap: "wrap", gap: 1 }}
                  >
                    {submittedList.map((q) => (
                      <ToggleButton key={q} value={q}>
                        {q}
                      </ToggleButton>
                    ))}
                  </ToggleButtonGroup>
                </Paper>

                <Accordion
                  defaultExpanded={false}
                  disableGutters
                  sx={{
                    width: "100%",
                    border: "1px solid #e0e0e0",
                    borderRadius: 1,
                    boxShadow: "none",
                    "&:before": { display: "none" },
                  }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="subtitle2">Diagnosis count</Typography>
                  </AccordionSummary>

                  <AccordionDetails sx={{ p: 1, overflowX: "auto" }}>
                    {oncoDatadiagnosis ? (
                      <DiagnosisBarChart data={oncoDatadiagnosis} barW={22} gap={10} maxH={160} />
                    ) : (
                      <Typography variant="body2">No diagnosis to chart.</Typography>
                    )}
                  </AccordionDetails>
                </Accordion>

                <Box sx={{ width: "100%", border: "1px solid #ccc", p: 1, borderRadius: 1, overflowX: "auto" }}>
                  {plotData ? (
                    <MutationViewer
                      key={`mut-${activeKey}-${chartWidth}`}
                      data={plotData}
                      maf={mafForMutation}
                      width={chartWidth}
                      height={300}
                    />
                  ) : (
                    <Typography variant="body2">
                      {activeKey ? "No plot data available." : "Please submit a query and select a gene first."}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>
          )}

          {/* {tabIndex === 2 && (
            <Box sx={{ mt: 2, height: "600px", width: "100%", border: "1px solid #ccc", overflowX: "auto" }}>
              <PathwayViewer />
            </Box>
          )} */}
        </Box>
      )}

      <Dialog open={fieldDialogOpen} onClose={() => setFieldDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Configure Detail Fields</DialogTitle>

        <DialogContent dividers>
          <TextField
            fullWidth
            size="small"
            placeholder="Search field name"
            value={fieldSearch}
            onChange={(e) => setFieldSearch(e.target.value)}
            sx={{ mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

          <Box sx={{ display: "flex", gap: 1, mb: 2, flexWrap: "wrap" }}>
            <Button size="small" onClick={() => setDetailFields(defaultDetailFields)}>
              Default
            </Button>
            <Button size="small" onClick={() => setDetailFields(selectableDetailFields)}>
              Select All
            </Button>
            <Button size="small" onClick={() => setDetailFields([])}>
              Clear
            </Button>
          </Box>

          <Divider sx={{ mb: 2 }} />

          <Box sx={{ display: "grid", gap: 2 }}>
            {Object.entries(groupedSelectableFields).map(([groupName, fields]) => (
              <Paper
                key={groupName}
                variant="outlined"
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: "#fafafa",
                }}
              >
                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    mb: 1.25,
                    flexWrap: "wrap",
                    gap: 1,
                  }}
                >
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                      {groupName}
                    </Typography>

                    <Typography variant="caption" color="text.secondary">
                      {fields.filter((f) => detailFields.includes(f)).length} / {fields.length} selected
                    </Typography>
                  </Box>

                  <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                    <Button
                      size="small"
                      onClick={() => {
                        setDetailFields((prev) => Array.from(new Set([...prev, ...fields])));
                      }}
                    >
                      Select This Group
                    </Button>

                    <Button
                      size="small"
                      onClick={() => {
                        setDetailFields((prev) => prev.filter((f) => !fields.includes(f)));
                      }}
                    >
                      Clear This Group
                    </Button>
                  </Box>
                </Box>

                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                  {fields.map((field) => {
                    const checked = detailFields.includes(field);
                    return (
                      <Chip
                        key={field}
                        label={field}
                        clickable
                        color={checked ? "primary" : "default"}
                        variant={checked ? "filled" : "outlined"}
                        onClick={() => {
                          setDetailFields((prev) =>
                            prev.includes(field)
                              ? prev.filter((f) => f !== field)
                              : [...prev, field]
                          );
                        }}
                      />
                    );
                  })}
                </Box>
              </Paper>
            ))}
          </Box>

          {filteredSelectableDetailFields.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              No matching fields found
            </Typography>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={() => setFieldDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={rowDetailOpen}
        onClose={closeRowDetailDialog}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Variant Details</DialogTitle>

        <DialogContent dividers>
          {!selectedRow ? (
            <Typography variant="body2" color="text.secondary">
              No data available
            </Typography>
          ) : detailFields.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No detail fields are currently selected.
            </Typography>
          ) : (
            <>
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" sx={{ color: "text.secondary" }}>
                  Showing page {detailDialogPagedData.currentPage} / {detailDialogPagedData.totalPages}
                </Typography>
              </Box>

              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableBody>
                    {detailDialogPagedData.fields.map((field) => (
                      <TableRow key={field}>
                        <TableCell
                          sx={{
                            width: 220,
                            fontWeight: 700,
                            backgroundColor: "#fcfcfc",
                            borderBottom: "1px solid #eee",
                            whiteSpace: "nowrap",
                            verticalAlign: "top",
                          }}
                        >
                          {field}
                        </TableCell>
                        <TableCell
                          sx={{
                            borderBottom: "1px solid #eee",
                            verticalAlign: "top",
                          }}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              overflowWrap: "anywhere",
                            }}
                          >
                            {selectedRow[field] == null || selectedRow[field] === ""
                              ? "-"
                              : String(selectedRow[field])}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              {detailDialogPagedData.totalPages > 1 && (
                <Box sx={{ mt: 2, display: "flex", justifyContent: "center" }}>
                  <Pagination
                    count={detailDialogPagedData.totalPages}
                    page={detailDialogPagedData.currentPage}
                    onChange={(_, page) => setDetailDialogPage(page)}
                    size="small"
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
        </DialogContent>

        <DialogActions>
          <Button onClick={closeRowDetailDialog}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default GeneProteinInputMui;
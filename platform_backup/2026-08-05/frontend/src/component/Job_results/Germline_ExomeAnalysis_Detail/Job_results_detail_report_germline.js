import React, { useState, useEffect } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import { Button, Stack, Collapse } from '@mui/material';
import { config } from '../../../constant.js';
import PDFGenerator from './PDFGenerator';

function Job_results_detail_report() {
  const [combinedData, setCombinedData] = useState([]);
  const [selectedRows, setSelectedRows] = useState({});
  const [loading, setLoading] = useState(true);
  const [jsonData, setJsonData] = useState(null);
  const [isPanelExpanded, setIsPanelExpanded] = useState(false);
  const [isDeleteDisabled, setIsDeleteDisabled] = useState(true);

  // table_name 的顯示順序
  const tableOrder = [
    'Known Pathogenic Pheno',
    'Known Pathogenic ACMG',
    'Known Pathogenic Other',
    'Predicted Suspect Pheno',
    'Predicted Suspect ACMG',
    'Predicted Suspect Other',
    'Other Variants',
    'Drug Responses'
  ];

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const urlSegments = window.location.pathname.split('/');
        const newJobID = urlSegments[urlSegments.length - 2];
        const response = await axios.post(
          `${config.rootApiIP}/summary_page`,
          { newJobID }
        );
        console.log('Response data:', response.data);
        let payload;
        if (typeof response.data === 'string') {
          // 把 NaN 換成 null 再 parse
          const safe = response.data.replace(/\bNaN\b/g, 'null');
          payload = JSON.parse(safe);
        } else {
          payload = response.data;
        }

        const combined = Array.isArray(payload.combinedData)
          ? payload.combinedData
          : [];
        setCombinedData(combined);
        setJsonData(payload?.jsonData ?? null);

      } catch (err) {
        console.error('Fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // 控制 Delete 按鈕
  useEffect(() => {
    const total = Object.values(selectedRows).reduce(
      (sum, arr) => sum + arr.length,
      0
    );
    setIsDeleteDisabled(total === 0);
  }, [selectedRows]);

  const handleTogglePanel = () => {
    setIsPanelExpanded(open => !open);
  };

  const getRowHeight = () => 'auto';

  // 欄位定義
  const baseCols = [
    { field: 'Location', headerName: 'Location', flex: 1, minWidth: 250 },
    { field: 'Gene', headerName: 'Genes', flex: 1, minWidth: 120 },
    { field: 'RSID', headerName: 'RS ID', flex: 1, minWidth: 110 },
    { field: 'MAF', headerName: 'MAF', flex: 1, minWidth: 150 },
    { field: 'GenotypeVAF', headerName: 'Genotype VAF(#ref/#alt)', flex: 2, minWidth: 300 },
    { field: 'Evidence', headerName: 'Evidence', flex: 2, minWidth: 350 },
    { field: 'Domain', headerName: 'Domain', flex: 2, minWidth: 350 },
    { field: 'Pathogenicity', headerName: 'Pathogenicity', flex: 1, minWidth: 180 },
    { field: 'SplicingEffect', headerName: 'Splicing effect', flex: 1, minWidth: 210 },
    { field: 'OMIM', headerName: 'OMIM', flex: 1, minWidth: 100 },
    { field: 'AmelieMaxScore', headerName: 'Amelie Max score', flex: 1, minWidth: 170 },
    { field: 'AmelieMeanScore', headerName: 'Amelie Mean score', flex: 1, minWidth: 170 },
  ].map(col => ({
    ...col,
    headerClassName: 'super-app-theme--header',
    renderCell: params => (
      <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
        {params.value}
      </div>
    ),
  }));

  const drugCols = [
    { field: 'Location', headerName: 'Location', flex: 1, minWidth: 250 },
    { field: 'Gene', headerName: 'Genes', flex: 1, minWidth: 120 },
    { field: 'RSID', headerName: 'RS ID', flex: 1, minWidth: 110 },
    { field: 'Drugevidence', headerName: 'Drug Evidence', flex: 1, minWidth: 200 },
    { field: 'Chemical', headerName: 'Chemical', flex: 1, minWidth: 200 },
    { field: 'ClinVar', headerName: 'ClinVar', flex: 1, minWidth: 150 },
  ].map(col => ({
    ...col,
    headerClassName: 'super-app-theme--header',
    renderCell: params => (
      <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
        {params.value}
      </div>
    ),
  }));

  // 取得所有 gene 的列表
  const genes = Array.from(
    new Set(combinedData.map(item => item.Gene).filter(Boolean))
  );

  return (
    <div>
      {loading ? (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          height="100vh"
        >
          <CircularProgress size={150} />
        </Box>
      ) : (
        <>
          {/* 上方參數卡片 */}
          <Box sx={{
            display: 'flex',
            flexWrap: 'wrap',
            '& > :not(style)': { m: 1, width: 1280 },
          }}>
            <Paper sx={{ backgroundColor: 'lightgray', p: 2 }} elevation={8}>
              {(() => {
                const gp0 = jsonData?.genePanelList?.GenePanelList?.[0];
                const panelName = gp0?.panelName ?? 'N/A';
                const genePanelStr = gp0?.genePanel ?? '';
                const geneCount = genePanelStr ? genePanelStr.split('、').length : 0;

                if (!jsonData) return <p>No selected data</p>;

                return (
                  <>
                    <h2>Panel Name : {panelName}</h2>
                    <h5>Subject ID : {jsonData?.subject_id ?? 'N/A'}</h5>
                    <h5>MAF Cutoff : {jsonData?.maf_cutoff ?? 'N/A'}</h5>
                    <h5>Min AAF : {jsonData?.min_aaf ?? 'N/A'}</h5>
                    <h5>Min DP Cutoff : {jsonData?.min_dp_cutoff ?? 'N/A'}</h5>

                    <h5>
                      Gene Panel : {panelName} ({geneCount} genes)
                    </h5>

                    {genePanelStr ? (
                      <>
                        <Button
                          variant="outlined"
                          onClick={handleTogglePanel}
                          sx={{ mt: 1, mb: 1 }}
                        >
                          {isPanelExpanded ? '收起' : '展開'} Gene Panel
                        </Button>

                        <Collapse in={isPanelExpanded} timeout="auto" unmountOnExit>
                          <pre style={{ whiteSpace: 'pre-wrap' }}>
                            {genePanelStr.replace(/\n/g, ', ')}
                          </pre>
                        </Collapse>
                      </>
                    ) : (
                      <p>Gene panel data missing.</p>
                    )}
                  </>
                );
              })()}
            </Paper>

          </Box>

          {/* PDF + Delete 按鈕 */}
          <Stack spacing={2} direction="row" sx={{ mt: 4 }}>
            <PDFGenerator
              combinedData={combinedData}
              jsonData={jsonData}
            />
            <Button
              variant="contained"
              sx={{ width: 200, height: 70, fontSize: 20 }}
              disabled={isDeleteDisabled}
            >
              Delete
            </Button>
          </Stack>

          {/* 先以 Gene 分類，再以 table_name 顯示 */}
          <div style={{ marginBottom: 120 }}>
            {genes.map(gene => (
              <div key={gene} style={{ marginTop: 50 }}>
                <h1>{gene}</h1>
                {tableOrder.map(table => {
                  const rows = combinedData.filter(
                    item => item.Gene === gene && item.table_name === table
                  );
                  if (!rows.length) return null;
                  const isDrug = table === 'Drug Responses';
                  return (
                    <div key={table} style={{ marginTop: 30 }}>
                      <h2>{table}</h2>
                      <div
                        style={{
                          height: isDrug ? 400 : 450,
                          width: '95%',
                        }}
                      >
                        <DataGrid
                          rows={rows}
                          columns={isDrug ? drugCols : baseCols}
                          getRowHeight={getRowHeight}
                          initialState={{
                            pagination: {
                              paginationModel: { page: 0, pageSize: 5 },
                            },
                          }}
                          pageSizeOptions={[5, 10]}
                          {...(!isDrug && {
                            checkboxSelection: true,
                            onRowSelectionModelChange: newSelection => {
                              const selectedData = newSelection
                                .map(id => rows.find(r => r.id === id))
                                .filter(Boolean);
                              const key = `${gene}_${table}`;
                              setSelectedRows(prev => ({
                                ...prev,
                                [key]: selectedData,
                              }));
                            },
                          })}
                          sx={{
                            '& .MuiDataGrid-cell': {
                              whiteSpace: 'normal',
                              wordWrap: 'break-word',
                              lineHeight: '2em',
                              display: 'flex',
                              alignItems: 'center',
                              p: 1,
                            },
                            '& .super-app-theme--header': {
                              backgroundColor: 'lightgray',
                            },
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export default Job_results_detail_report;

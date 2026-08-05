import React, { useState, useEffect } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import CircularProgress from '@mui/material/CircularProgress';
import { Button, Stack, Collapse } from '@mui/material';
import PDFGenerator from './PDFGenerator_somatic';
import { config } from '../../../constant';

// 新增下拉選單與 Tooltip 所需的元件
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import Tooltip from '@mui/material/Tooltip';

function Job_results_detail_report() {
  // 定義 table name 的對應文字
  const tableNameMapping = {
    single_snp_actionable: 'Single SNP - Actionable',
    single_snp_cosmic: 'Single SNP - Cosmic',
    single_snp_hereidty: 'Single SNP - Hereidty',
    single_snp_prediction: 'Single SNP - Prediction',
    single_snp_germline_prediction: 'Single SNP - Germline Prediction',
    muti_snp_cosmic: 'Multiple SNP - Cosmic',
    muti_snp_civic: 'Multiple SNP - Civic',
  };

  const [groupedDataByTable, setGroupedDataByTable] = useState({});
  // selectedRows 結構： { [tableName]: { [gene]: Array<rowObject> } }
  const [selectedRows, setSelectedRows] = useState({});
  const [loading, setLoading] = useState(true);
  const [jsonData, setJsonData] = useState(null);
  const [isPanelExpanded, setIsPanelExpanded] = useState(false);
  const [isDeleteDisabled, setIsDeleteDisabled] = useState(true);
  // 新增下拉選單狀態，供 single_snp_actionable table 使用
  const [dropdownValues, setDropdownValues] = useState({});

  // 下拉選單變更處理函式
  const handleChange = (id) => (event) => {
    const newValue = event.target.value;
    setDropdownValues((prev) => ({
      ...prev,
      [id]: newValue,
    }));
    // 如有需求可同步更新選取的資料（例如更新 selectedRows 中對應 row 的 groupValue）
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        // 取得網址最後一段當作 newJobID
        const urlSegments = window.location.pathname.split('/');
        const secondLastSegment = urlSegments[urlSegments.length - 2];
        const response = await axios.post(`${config.rootApiIP}/summary_page_somatic`, {
          newJobID: secondLastSegment,
        });
        console.log(typeof response.data);
        console.log('response.data:', response.data);

        // 取出後端回傳資料
        let combinedData = response.data.combinedData;
        let jsonData = response.data.jsonData;
        console.log('--------------------------------');
        console.log('combinedData', combinedData);
        console.log('jsonData', jsonData);

        setJsonData(jsonData);

        // 1) 依 table_name 分組
        const groupedByTable = combinedData.reduce((acc, item) => {
          const tableName = item.table_name || 'Unknown_Table';
          if (!acc[tableName]) {
            acc[tableName] = [];
          }
          acc[tableName].push(item);
          return acc;
        }, {});

        // 2) 依 Gene 做第二層分組
        const finalGroupedData = {};
        Object.keys(groupedByTable).forEach((tableName) => {
          const rows = groupedByTable[tableName];
          const groupedByGene = rows.reduce((acc, row) => {
            const gene = row.Gene || 'Unknown_Gene';
            if (!acc[gene]) {
              acc[gene] = [];
            }
            acc[gene].push(row);
            return acc;
          }, {});
          finalGroupedData[tableName] = groupedByGene;
        });

        setGroupedDataByTable(finalGroupedData);
        setLoading(false);
      } catch (error) {
        console.error('請求錯誤：', error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  // 監聽 selectedRows 變化，判斷是否有任何行被勾選，控制 Delete 按鈕是否可用
  useEffect(() => {
    let totalSelected = 0;
    // selectedRows[tableName][gene] 都是陣列
    Object.values(selectedRows).forEach((geneObj) => {
      Object.values(geneObj).forEach((arr) => {
        totalSelected += arr.length;
      });
    });
    setIsDeleteDisabled(totalSelected === 0);
  }, [selectedRows]);

  // 工具函式：一般欄位定義（僅用於非 single_snp_actionable 的 table）
  const colDef = (field, header, minWidth = 150) => ({
    field,
    headerName: header,
    flex: 1,
    minWidth,
    renderCell: (params) => cellWrap(params.value),
  });

  // cellWrap 用於一般欄位自動換行
  const cellWrap = (value) => (
    <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
      {value === null || value === undefined || String(value) === 'NaN'
        ? ''
        : Array.isArray(value)
        ? JSON.stringify(value)
        : String(value)}
    </div>
  );

  // 根據 tableName 回傳對應欄位定義，若 table 為 single_snp_actionable，採用第二段 code 格式
  const getColumnsForTable = (tableName) => {
    if (tableName === 'single_snp_actionable') {
      return [
        {
          field: 'Location',
          headerName: 'Location',
          flex: 1,
          minWidth: 260,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'Gene',
          headerName: 'Genes',
          flex: 1,
          minWidth: 130,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'RSID',
          headerName: 'RS ID',
          flex: 1,
          minWidth: 120,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'MAF',
          headerName: 'MAF',
          flex: 1,
          minWidth: 380,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'Domain',
          headerName: 'Domain',
          flex: 2,
          minWidth: 700,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'Pathogenicity',
          headerName: 'Pathogenicity',
          flex: 1,
          minWidth: 240,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'Prediction',
          headerName: 'Prediction',
          flex: 1,
          minWidth: 260,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'Match',
          headerName: 'Match',
          flex: 1,
          minWidth: 210,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'AminoAcidChange',
          headerName: 'Amino acid change',
          flex: 1,
          minWidth: 200,
          renderCell: (params) => (
            <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
              {params.value}
            </div>
          ),
        },
        {
          field: 'Avalibility',
          headerName: 'Avalibility',
          flex: 1,
          minWidth: 500,
          renderCell: (params) => {
            const avalibilityData = Array.isArray(params.value) ? params.value : [params.value];
            const avalibilityDescriptions = Array.isArray(params.row.AvalibilityDescription)
              ? params.row.AvalibilityDescription
              : [];
            return (
              <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
                {avalibilityData.map((item, index) => (
                  <div key={index} style={{ marginBottom: '8px' }}>
                    <Tooltip
                      title={
                        <span style={{ fontSize: '14px' }}>
                          {avalibilityDescriptions[index] || '無詳細說明'}
                        </span>
                      }
                      arrow
                    >
                      <span>{item}</span>
                    </Tooltip>
                  </div>
                ))}
              </div>
            );
          },
        },
      ];
    }

    // 針對其它 table_name，依原本 colDef 回傳欄位定義
    switch (tableName) {
      case 'single_snp_cosmic':
        return [
          colDef('Location', 'Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
          colDef('AminoAcidChange', 'Amino Acid Change', 180),
        ];
      case 'single_snp_hereidty':
        return [
          colDef('Location', 'Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
          colDef('AminoAcidChange', 'Amino Acid Change', 180),
        ];
      case 'single_snp_prediction':
        return [
          colDef('Location', 'Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
          colDef('AminoAcidChange', 'Amino Acid Change', 180),
        ];
      case 'single_snp_germline_prediction':
        return [
          colDef('Location', 'Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
          colDef('AminoAcidChange', 'Amino Acid Change', 180),
        ];
      case 'muti_snp_cosmic':
        return [
          colDef('Location', 'Location', 250),
          colDef('DetailedLocation', 'Detailed Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
          colDef('DRUGCOMBINATION', 'Drug Combination', 250),
          colDef('Phenotype', 'Phenotype', 150),
          colDef('CosmicPreprocessor', 'Cosmic Preprocessor', 150),
        ];
      case 'muti_snp_civic':
        return [
          colDef('Location', 'Location', 250),
          colDef('DetailedLocation', 'Detailed Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
          colDef('Phenotype', 'Phenotype', 150),
          colDef('Therapies', 'Therapies', 180),
          colDef('CivicVariantName', 'Civic Variant', 180),
        ];
      default:
        return [
          colDef('Location', 'Location', 250),
          colDef('Gene', 'Gene', 120),
          colDef('RSID', 'RS ID', 110),
          colDef('MAF', 'MAF', 150),
          colDef('Domain', 'Domain', 180),
          colDef('Prediction', 'Prediction', 180),
          colDef('Pathogenicity', 'Pathogenicity', 180),
        ];
    }
  };

  // DataGrid checkboxSelection 改變時：更新 selectedRows
  const onRowSelectionChange = (tableName, gene, newSelection) => {
    setSelectedRows((prevSelected) => {
      const oldTableObj = prevSelected[tableName] || {};
      const oldGeneArr = oldTableObj[gene] || [];
      // 在 groupedDataByTable[tableName][gene] 找出被勾選的 row object
      const tableGeneRows = groupedDataByTable[tableName][gene] || [];

      const newSelectedRowData = newSelection.map((id) =>
        tableGeneRows.find((row) => row.id === id)
      );

      // 合併舊選擇
      const merged = [...new Set([...oldGeneArr, ...newSelectedRowData])];

      // 只保留仍在 newSelection 裡的 row
      const finalGeneArr = merged.filter((row) => newSelection.includes(row.id));

      return {
        ...prevSelected,
        [tableName]: {
          ...oldTableObj,
          [gene]: finalGeneArr,
        },
      };
    });
  };

  const handleTogglePanel = () => {
    setIsPanelExpanded((prev) => !prev);
  };

  return (
    <div>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
          <CircularProgress size={150} />
        </Box>
      ) : (
        <>
          {/* 上方資料呈現 (Subject, Panel, 等) */}
          <Box
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              '& > :not(style)': {
                m: 1,
                width: 1280,
              },
            }}
          >
            <Paper sx={{ backgroundColor: 'lightgray', padding: 2 }} elevation={8}>
              {jsonData ? (
                <div>
                  <h2>Diagnosis : {jsonData.diagnosis}</h2>
                  <h5>Subject ID : {jsonData.subject_id}</h5>
                  <h5>MAF Cutoff : {jsonData.maf_cutoff}</h5>
                  <h5>Min AAF : {jsonData.min_aaf}</h5>
                  <h5>Min DP Cutoff : {jsonData.min_dp_cutoff}</h5>
                  <h5>
                    Gene Panel :{' '}
                    {jsonData.gene_panel_list.GenePanelList[0].genePanel.split('\n').length} genes
                  </h5>

                  <Button
                    variant="outlined"
                    onClick={handleTogglePanel}
                    style={{ marginTop: '5px', marginBottom: '7px' }}
                  >
                    {isPanelExpanded ? '收起' : '展開'} Gene Panel
                  </Button>

                  <Collapse in={isPanelExpanded} timeout="auto" unmountOnExit>
                    <p>
                      {jsonData.gene_panel_list.GenePanelList[0].genePanel
                        .replace(/\n/g, ', ')
                        .split(', ')
                        .reduce((acc, curr, idx) => {
                          return idx % 10 === 0 && idx !== 0
                            ? acc + '\n' + curr
                            : acc + ', ' + curr;
                        })}
                    </p>
                  </Collapse>
                </div>
              ) : (
                <p>No selected data</p>
              )}
            </Paper>
          </Box>

          <Stack spacing={2} direction="row" style={{ marginTop: '40px' }}>
            {/* 下載 PDF 與 Delete 按鈕示範 */}
            <PDFGenerator groupedData={groupedDataByTable} jsonData={jsonData} />
            <Button
              variant="contained"
              sx={{ width: '200px', height: '70px', fontSize: '20px' }}
              disabled={isDeleteDisabled}
            >
              Delete
            </Button>
          </Stack>

          {/* 分別顯示各個 table_name，下的各 Gene */}
          <div style={{ marginBottom: '120px' }}>
            {Object.keys(groupedDataByTable).map((tableName) => {
              const groupedByGene = groupedDataByTable[tableName];
              const columns = getColumnsForTable(tableName);

              return (
                <div key={tableName} style={{ marginTop: '50px' }}>
                  <h2 style={{ color: '#1976d2' }}>
                    {tableNameMapping[tableName] || tableName}
                  </h2>
                  {Object.keys(groupedByGene).map((gene) => (
                    <div key={gene} style={{ marginTop: '50px' }}>
                      <h1>{gene}</h1>
                      <div style={{ height: 450, width: '95%' }}>
                        <DataGrid
                          rows={groupedByGene[gene]}
                          columns={columns}
                          getRowHeight={() => 'auto'} // 自動高度
                          initialState={{
                            pagination: {
                              paginationModel: { page: 0, pageSize: 5 },
                            },
                          }}
                          pageSizeOptions={[5, 10]}
                          checkboxSelection
                          onRowSelectionModelChange={(newSelection) =>
                            onRowSelectionChange(tableName, gene, newSelection)
                          }
                          sx={{
                            '& .MuiDataGrid-cell': {
                              whiteSpace: 'normal',
                              wordWrap: 'break-word',
                              lineHeight: '1.6em',
                              display: 'flex',
                              alignItems: 'center',
                              padding: '8px',
                            },
                            '& .MuiDataGrid-columnHeaders': {
                              backgroundColor: 'lightgray',
                            },
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

export default Job_results_detail_report;

import * as React from 'react';
import {
  DataGrid,
  GridToolbarContainer,
} from '@mui/x-data-grid';
import {
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Button,
  Tooltip,
} from '@mui/material';

function MultipleSNP_Civic_data({
  data,
  onSelectionChange,
  rowSelectionModel,
  setrowSelectionModel,
}) {
  /**
   * 1) 下拉選單 State：記錄每行選了哪個 Group
   */
  const [dropdownValues, setDropdownValues] = React.useState({});

  /**
   * 2) 顯示/隱藏欄位的 Model
   *    - partialModel：僅顯示指定欄位（Prediction, Phenotype, Therapies, CivicVariantName）
   *    - allTrueModel：等一下會根據 columns 全部欄位都設為 true
   */
  const partialModel = {
    Rank: true,
    Location: false,
    DetailedLocation: false,
    Gene: false,
    RSID: false,
    MAF: false,
    Domain: false,
    Pathogenicity: false,

    // 這四個欄位預設顯示
    Prediction: false,
    Phenotype: true,
    Therapies: true,
    CivicVariantName: true,
  };

  const allTrueModel = {};

  /**
   * 3) showAll：用來判斷當前是「顯示全部欄位」或「顯示部分欄位」
   *    - false: 顯示部分欄位
   *    - true:  顯示全部欄位
   */
  const [showAll, setShowAll] = React.useState(false);

  // 預設先載入部分欄位
  const [columnVisibilityModel, setColumnVisibilityModel] =
    React.useState(partialModel);

  /**
   * 4) 欄位定義（含 renderCell 等功能）
   *    預設都放進 columns，實際顯示透過 columnVisibilityModel 控制
   */
  const columns = [
    {
      field: 'Rank',
      headerName: 'Rank',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => {
        return (
          <FormControl sx={{ m: 1, minWidth: 120 }}>
            <InputLabel id={`select-${params.id}`}>選擇</InputLabel>
            <Select
              labelId={`select-${params.id}`}
              id={`select-${params.id}`}
              value={dropdownValues[params.id] || '1'}
              onChange={handleChange(params.id)}
              autoWidth
              label="選擇"
              disabled={!rowSelectionModel.includes(params.id)}
            >
              <MenuItem value={1}>Group 1</MenuItem>
              <MenuItem value={2}>Group 2</MenuItem>
              <MenuItem value={3}>Group 3</MenuItem>
            </Select>
          </FormControl>
        );
      },
    },
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
      field: 'DetailedLocation',
      headerName: 'Detailed Location',
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
      minWidth: 200,
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
      field: 'Phenotype',
      headerName: 'Phenotype',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      ),
    },
    {
      field: 'Therapies',
      headerName: 'Therapies',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      ),
    },
    {
      field: 'CivicVariantName',
      headerName: 'Civic Variant Name',
      flex: 1,
      minWidth: 180,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      ),
    },
  ];

  // 依照 columns 把所有欄位都設為 true
  columns.forEach((col) => {
    allTrueModel[col.field] = true;
  });

  /**
   * 5) 按鈕：顯示全部 or 顯示部分
   */
  const handleToggleColumns = () => {
    if (showAll) {
      // 若目前是顯示全部，就切回「部分欄位」
      setColumnVisibilityModel(partialModel);
      setShowAll(false);
    } else {
      // 若目前是顯示部分，就切回「全部欄位」
      setColumnVisibilityModel(allTrueModel);
      setShowAll(true);
    }
  };

  /**
   * 6) 自訂工具列
   */
  const CustomToolbar = () => {
    return (
      <GridToolbarContainer>
        <Button variant="contained" onClick={handleToggleColumns}>
          {showAll ? '顯示部分欄位' : '顯示全部欄位'}
        </Button>
      </GridToolbarContainer>
    );
  };

  /**
   * 7) Event handlers 相關
   */
  // 下拉選單選擇 Group
  const handleChange = (id) => (event) => {
    const newValue = event.target.value;
    setDropdownValues((prev) => ({
      ...prev,
      [id]: newValue,
    }));

    // 如果這個 row 有被選中，就更新 groupValue
    if (rowSelectionModel.includes(id)) {
      const updatedSelectedRows = data
        .filter((row) => rowSelectionModel.includes(row.id))
        .map((row) => ({
          ...row,
          groupValue: row.id === id ? newValue : dropdownValues[row.id] || '1',
        }));

      console.log('Updated selected rows with group values:', updatedSelectedRows);
      onSelectionChange(updatedSelectedRows);
    }
  };

  // 選取行
  const handleSelectionChange = (newSelection) => {
    const selectedRows = data
      .filter((row) => newSelection.includes(row.id))
      .map((row) => ({
        ...row,
        groupValue: dropdownValues[row.id] || '1',
      }));

    console.log('Selected rows with group values:', selectedRows);
    onSelectionChange(selectedRows);
    setrowSelectionModel(newSelection);
  };

  // 動態行高
  const getRowHeight = () => 'auto';

  return (
    <div style={{ height: 500, width: '100%' }}>
      <DataGrid
        rows={data}
        columns={columns}
        getRowHeight={getRowHeight}
        // 透過狀態控制顯示/隱藏哪些欄位
        columnVisibilityModel={columnVisibilityModel}
        onColumnVisibilityModelChange={(newModel) =>
          setColumnVisibilityModel(newModel)
        }
        // 選取功能
        checkboxSelection
        rowSelectionModel={rowSelectionModel}
        onRowSelectionModelChange={(newSelection) => {
          handleSelectionChange(newSelection);
        }}
        // 分頁
        pageSizeOptions={[5, 10]}
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: 5 },
          },
        }}
        // 自訂工具列 (右上角)
        slots={{
          toolbar: CustomToolbar,
        }}
        // 排版調整
        sx={{
          '& .MuiDataGrid-cell': {
            whiteSpace: 'normal',
            wordWrap: 'break-word',
            lineHeight: '2em',
            display: 'flex',
            alignItems: 'center', // 垂直置中
            padding: '8px',       // 調整內邊距
          },
        }}
      />
    </div>
  );
}

export default MultipleSNP_Civic_data;

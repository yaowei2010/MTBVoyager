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

function MultipleSNP_Actionable_data({
  data,
  onSelectionChange,
  rowSelectionModel,
  setrowSelectionModel,
}) {
  // ---- 1) 原本的狀態 ----
  const [dropdownValues, setDropdownValues] = React.useState({});

  // 預設只顯示指定欄位 (true)，其他欄位隱藏 (false)
  const partialModel = {
    Rank: true,
    Prediction: false,
    DRUGCOMBINATION: true,
    Phenotype: true,
    CosmicPreprocessor: true,

    Location: false,
    DetailedLocation: false,
    Gene: false,
    RSID: false,
    MAF: false,
    Domain: false,
    Pathogenicity: false,
  };

  // 這裡 columns 後面會再用 forEach 轉成全部 true
  const allTrueModel = {};

  // ---- 2) showAll 狀態：false = 顯示部分欄位；true = 顯示全部欄位 ----
  const [showAll, setShowAll] = React.useState(false);

  // 以狀態方式控制欄位顯示/隱藏，一開始先用 partialModel
  const [columnVisibilityModel, setColumnVisibilityModel] = React.useState(partialModel);

  // 定義所有 columns（下面要用它來生成 allTrueModel）
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
      field: 'DRUGCOMBINATION',
      headerName: 'DRUG COMBINATION',
      flex: 1,
      minWidth: 200,
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
      field: 'CosmicPreprocessor',
      headerName: 'Cosmic Preprocessor',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      ),
    },
  ];

  // 讓 allTrueModel 變成：欄位名 => true
  columns.forEach((col) => {
    allTrueModel[col.field] = true;
  });

  // ---- 3) 顯示全部 or 顯示部分 ----
  const handleToggleColumns = () => {
    if (showAll) {
      // 若已是顯示全部 -> 改為顯示部分
      setColumnVisibilityModel(partialModel);
      setShowAll(false);
    } else {
      // 若是顯示部分 -> 改為顯示全部
      setColumnVisibilityModel(allTrueModel);
      setShowAll(true);
    }
  };

  // ---- 自訂 ToolBar ----
  const CustomToolbar = () => {
    return (
      <GridToolbarContainer>
        <Button variant="contained" onClick={handleToggleColumns}>
          {showAll ? '顯示部分欄位' : '顯示全部欄位'}
        </Button>
      </GridToolbarContainer>
    );
  };

  // ---- 其餘功能 ----
  const handleChange = (id) => (event) => {
    const newValue = event.target.value;
    setDropdownValues((prev) => ({
      ...prev,
      [id]: newValue,
    }));

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

  const getRowHeight = () => 'auto';

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

  return (
    <div style={{ height: 500, width: '100%' }}>
      <DataGrid
        rows={data}
        columns={columns}
        getRowHeight={getRowHeight}
        // 依據 columnVisibilityModel 來顯示/隱藏欄位
        columnVisibilityModel={columnVisibilityModel}
        onColumnVisibilityModelChange={(newModel) =>
          setColumnVisibilityModel(newModel)
        }
        // 選取功能
        checkboxSelection
        rowSelectionModel={rowSelectionModel}
        onRowSelectionModelChange={handleSelectionChange}
        // 分頁
        pageSizeOptions={[5, 10]}
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: 5 },
          },
        }}
        // 右上角自訂工具列
        slots={{
          toolbar: CustomToolbar,
        }}
        // 排版微調
        sx={{
          '& .MuiDataGrid-cell': {
            whiteSpace: 'normal',
            wordWrap: 'break-word',
            lineHeight: '2em',
            display: 'flex',
            alignItems: 'center', // 垂直置中
            padding: '8px',       // 調整內邊距以增加空間
          },
        }}
      />
    </div>
  );
}

export default MultipleSNP_Actionable_data;

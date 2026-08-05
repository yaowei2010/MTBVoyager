import * as React from 'react';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import { DataGrid } from '@mui/x-data-grid';





// const rows = [
//   { id: 1, location: 'Snow', genes: 'Jon', rs_id: 35 },
// ];

function Drug_Response({data, onSelectionChange, rowSelectionModel, setrowSelectionModel}) {

  const [dropdownValues, setDropdownValues] = React.useState({});

  const handleChange = (id) => (event) => {
    const newValue = event.target.value;
    setDropdownValues((prev) => ({
      ...prev,
      [id]: newValue,
    }));
  
    // 如果這個 id 在目前選擇的行中，更新其 groupValue
    if (rowSelectionModel.includes(id)) {
      const updatedSelectedRows = data
        .filter((row) => rowSelectionModel.includes(row.id))
        .map((row) => ({
          ...row,
          groupValue: id === row.id ? newValue : dropdownValues[row.id] || '1',
        }));
  
      console.log('Updated selected rows with group values:', updatedSelectedRows);
      onSelectionChange(updatedSelectedRows);
    }
  };


  const getRowHeight = () => {
    return 'auto'; // 根據內容自動調整行高度
  };

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
      }
    },
    { 
      field: 'Location', 
      headerName: 'Location', 
      flex: 1,
      minWidth: 250,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'Gene', 
      headerName: 'Genes', 
      flex: 1,
      minWidth: 120,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'RSID', 
      headerName: 'RS ID', 
      flex: 1,
      minWidth: 140,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'Drugevidence', 
      headerName: 'Drug evidence', 
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'Chemical', 
      headerName: 'Chemical', 
      flex: 1,
      minWidth: 380,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'ClinVar', 
      headerName: 'ClinVar', 
      flex: 1,
      minWidth: 160,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
  ];
  





  
  const handleSelectionChange = (newSelection) => {
    const selectedRows = data
      .filter((row) => newSelection.includes(row.id))
      .map((row) => ({
        ...row,
        groupValue: dropdownValues[row.id] || '1', // 將選擇的 Group 值添加到行數據中
      }));
  
    console.log('Selected rows with group values:', selectedRows); // 查看包含 Group 值的選擇行
    onSelectionChange(selectedRows);
    setrowSelectionModel(newSelection);
  };


  return (
    <div style={{ height: 600, width: '100%' }}>
      <DataGrid
        rows={data}
        columns={columns}
        getRowHeight={getRowHeight}
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: 5 },
          },
        }}
        pageSizeOptions={[5, 10]}
        checkboxSelection
        rowSelectionModel={rowSelectionModel}
        onRowSelectionModelChange={(newSelection) => {
          handleSelectionChange(newSelection);
        }}
        sx={{
          '& .MuiDataGrid-cell': {
            whiteSpace: 'normal',
            wordWrap: 'break-word',
            lineHeight: '2em',
            display: 'flex',
            alignItems: 'center', // 垂直置中
            padding: '8px', // 調整內邊距以增加空間
          },
        }}
      />
    </div>
  );
}

export default Drug_Response;



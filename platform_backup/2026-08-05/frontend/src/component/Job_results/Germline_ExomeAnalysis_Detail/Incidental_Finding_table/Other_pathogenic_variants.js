// import * as React from 'react';
import * as React from 'react';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import { DataGrid } from '@mui/x-data-grid';




// const rows = [
//   { id: 1, location: 'Snow', genes: 'Jon', rs_id: 35 },
// ];

function Other_pathogenic_variants({OtherpathogenicVariantsData, OtherpathogenicSelectionChange, OtherpathogenicrowSelectionModel, OtherpathogenicsetrowSelectionModel}) {

  const [dropdownValues, setDropdownValues] = React.useState({});

  const handleChange = (id) => (event) => {
    const newValue = event.target.value;
    setDropdownValues((prev) => ({
      ...prev,
      [id]: newValue,
    }));
  
    // 如果這個 id 在目前選擇的行中，更新其 groupValue
    if (OtherpathogenicrowSelectionModel.includes(id)) {
      const updatedSelectedRows = OtherpathogenicVariantsData
        .filter((row) => OtherpathogenicrowSelectionModel.includes(row.id))
        .map((row) => ({
          ...row,
          groupValue: id === row.id ? newValue : dropdownValues[row.id] || '1',
        }));
  
      console.log('Updated selected rows with group values:', updatedSelectedRows);
      OtherpathogenicSelectionChange(updatedSelectedRows);
    }
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
              disabled={!OtherpathogenicrowSelectionModel.includes(params.id)}
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
      minWidth: 110,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'MAF', 
      headerName: 'MAF', 
      flex: 1,
      minWidth: 150,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'GenotypeVAF', 
      headerName: 'Genotype VAF(#ref/#alt)', 
      flex: 2,
      minWidth: 300,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'Evidence', 
      headerName: 'Evidence', 
      flex: 2,
      minWidth: 350,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'Domain', 
      headerName: 'Domain', 
      flex: 2,
      minWidth: 350,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'Pathogenicity', 
      headerName: 'Pathogenicity', 
      flex: 1,
      minWidth: 180,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'SplicingEffect', 
      headerName: 'Splicing effect', 
      flex: 1,
      minWidth: 210,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'OMIM', 
      headerName: 'OMIM', 
      flex: 1,
      minWidth: 100,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'AmelieMaxScore', 
      headerName: 'Amelie Max score', 
      flex: 1,
      minWidth: 170,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
    { 
      field: 'AmelieMeanScore', 
      headerName: 'Amelie Mean score', 
      flex: 1,
      minWidth: 170,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      )
    },
  ];


  const getRowHeight = () => {
    return 'auto'; // 根據內容自動調整行高度
  };


  const handleSelectionChange = (newSelection) => {
    const selectedRows = OtherpathogenicVariantsData
      .filter((row) => newSelection.includes(row.id))
      .map((row) => ({
        ...row,
        groupValue: dropdownValues[row.id] || '1', // 將選擇的 Group 值添加到行數據中
      }));

    console.log('Selected rows with group values:', selectedRows);
    OtherpathogenicSelectionChange(selectedRows);
    OtherpathogenicsetrowSelectionModel(newSelection);
  };



  return (
    <div style={{ height: 600, width: '100%' }}>
      <DataGrid
        rows={OtherpathogenicVariantsData}
        columns={columns}
        getRowHeight={getRowHeight}
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: 5 },
          },
        }}
        pageSizeOptions={[5, 10]}
        checkboxSelection
        rowSelectionModel={OtherpathogenicrowSelectionModel}
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


export default Other_pathogenic_variants;
import * as React from 'react';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import { DataGrid } from '@mui/x-data-grid';
import Tooltip from '@mui/material/Tooltip';


function Actionable_detail({ data, onSelectionChange, rowSelectionModel, setrowSelectionModel, }) {



const [dropdownValues, setDropdownValues] = React.useState({});



  // const handleChange = (id) => (event) => {
  //   setDropdownValues((prev) => ({
  //     ...prev,
  //     [id]: event.target.value,
  //   }));
  // };



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
    minWidth: 260,
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
    minWidth: 130,
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
    minWidth: 120,
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
    minWidth: 380,
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
    minWidth: 700,
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
    minWidth: 240,
    renderCell: (params) => (
    <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
        {params.value}
    </div>
    )
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
    )
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
    )
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
    )
},
{
    field: 'Avalibility',
    headerName: 'Avalibility',
    flex: 1,
    minWidth: 500,
    renderCell: (params) => {
      // 把來源排序權重先列好（小到大即高到低）
      const sourcePriority = {
        oncokb: 0,
        civic: 1,
        cgi: 2,
        cosmic: 3,
        mycancergenome: 4
      };
  
      // 把資料和說明配對好後一起排序，避免內容和說明錯位
      const pairs = (Array.isArray(params.value) ? params.value : [params.value])
        .map((item, idx) => ({
          item,                                               // 例如 "Tier 1B, DACOMITINIB, MyCancerGenome, 1"
          desc: Array.isArray(params.row.AvalibilityDescription)
                ? params.row.AvalibilityDescription[idx] || '無詳細說明'
                : '無詳細說明'
        }))
        .sort((a, b) => {
          const srcA = (a.item.split(',')[2] || '').trim().toLowerCase();
          const srcB = (b.item.split(',')[2] || '').trim().toLowerCase();
          return (sourcePriority[srcA] ?? 99) - (sourcePriority[srcB] ?? 99);
        });
  
      // 按照排好序的資料輸出
      return (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {pairs.map(({ item, desc }, idx) => (
            <div key={idx} style={{ marginBottom: 8 }}>
              <Tooltip title={<span style={{ fontSize: 14 }}>{desc}</span>} arrow>
                <span>{item}</span>
              </Tooltip>
            </div>
          ))}
        </div>
      );
    }
  }
  
];



// const handleSelectionChange = (newSelection) => {
//   console.log('New selection:', newSelection); // 查看選擇狀態
//   const selectedRows = data.filter((row) => newSelection.includes(row.id));
//   console.log('Selected rows:', selectedRows); // 查看選擇的行
//   onSelectionChange(selectedRows);
//   setrowSelectionModel(newSelection);
//   console.log('selectionModel', rowSelectionModel)
// };


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
<div style={{ height: 500, width: '100%' }}>
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

export default Actionable_detail;
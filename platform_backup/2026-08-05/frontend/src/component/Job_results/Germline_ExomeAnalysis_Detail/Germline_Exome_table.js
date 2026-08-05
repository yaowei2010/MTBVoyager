import * as React from 'react';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import { DataGrid } from '@mui/x-data-grid';
import Tooltip from '@mui/material/Tooltip';
function Germline_Exome_table({
  data,
  onSelectionChange,
  rowSelectionModel,
  setrowSelectionModel,
}) {
  const [dropdownValues, setDropdownValues] = React.useState({});

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
          groupValue: id === row.id ? newValue : dropdownValues[row.id] || '1',
        }));

      console.log('Updated selected rows with group values:', updatedSelectedRows);
      onSelectionChange(updatedSelectedRows);
    }
  };

  const getRowHeight = () => 'auto';

  const columns = [
    {
      field: 'Rank',
      headerName: 'Rank',
      flex: 1,
      minWidth: 200,
      renderCell: (params) => (
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
      ),
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
      ),
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
      ),
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
      ),
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
      ),
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
      ),
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
      ),
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
      ),
    },
    {
      field: 'Pathogenicity',
      headerName: 'Pathogenicity',
      flex: 1,
      minWidth: 150,
      renderCell: (params) => {
        const summaryMatch = params.value.match(/Summary:\s*\((\d+)\/(\d+)\)/);
        const current = summaryMatch ? parseInt(summaryMatch[1], 10) : 0;
        const total = summaryMatch ? parseInt(summaryMatch[2], 10) : 1;
        const percentage = (current / total) * 100;
      
        const cleanedValue = params.value.replace(/^Summary:\s*\(\d+\/\d+\)\s*/, '');

        const lines = cleanedValue
          .split(/\s+(?=\w+?:)/)
          .map((s) => s.trim())
          .filter(Boolean);
      
        return (
          <Tooltip
            title={
              <div style={{ display: 'flex', flexDirection: 'column',fontSize: '14px', }}>
                {lines.map((line, idx) => (
                  <div key={idx}>{line}</div>
                ))}
              </div>
            }
            arrow
            placement="top"
          >
            <div
              style={{
                width: '100px',
                height: '16px',
                backgroundColor: '#eee',
                borderRadius: '10px',
                position: 'relative',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  width: `${percentage}%`,
                  height: '100%',
                  backgroundColor: '#d32f2f',
                  borderRadius: percentage === 100 ? '10px' : '10px 0 0 10px',
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  color: '#000',
                }}
              >
                ({current}/{total})
              </div>
            </div>
          </Tooltip>
        );
      },
    },
    {
      field: 'SplicingEffect',
      headerName: 'Splicing effect',
      flex: 1,
      minWidth: 150,


      renderCell: (params) => {
        const summaryMatch = params.value.match(/Summary:\s*\((\d+)\/(\d+)\)/);
        const current = summaryMatch ? parseInt(summaryMatch[1], 10) : 0;
        const total = summaryMatch ? parseInt(summaryMatch[2], 10) : 1;
        const percentage = (current / total) * 100;
      
        // 分行
        // 去掉 Summary:
        const cleanedValue = params.value.replace(/^Summary:\s*\(\d+\/\d+\)\s*/, '');

        const lines = cleanedValue
        .split(/\s*(\w[\w\s]*?:)/) // 分割「有冒號的 key」
        .map(s => s.trim())
        .filter(Boolean)
        .reduce((acc, val, idx, arr) => {
          if (val.endsWith(':')) {
            // 如果是key，和下一個一起組合
            acc.push(val + ' ' + (arr[idx + 1] || ''));
          } else if (arr[idx - 1] && arr[idx - 1].endsWith(':')) {
            // 已經處理過
          } else {
            acc.push(val);
          }
          return acc;
        }, []);
      
      
        return (
          <Tooltip
            title={
              <div style={{ display: 'flex', flexDirection: 'column',fontSize: '14px',  }}>
                {lines.map((line, idx) => (
                  <div key={idx}>{line}</div>
                ))}
              </div>
            }
            arrow
            placement="top"
          >
            <div
              style={{
                width: '100px',
                height: '16px',
                backgroundColor: '#eee',
                borderRadius: '10px',
                position: 'relative',
                cursor: 'pointer',
              }}
            >
              <div
                style={{
                  width: `${percentage}%`,
                  height: '100%',
                  backgroundColor: '#d32f2f',
                  borderRadius: percentage === 100 ? '10px' : '10px 0 0 10px',
                }}
              />
              <div
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 'bold',
                  color: '#000',
                }}
              >
                ({current}/{total})
              </div>
            </div>
          </Tooltip>
        );
      },
      
    },
    {
      field: 'OMIM',
      headerName: 'OMIM',
      flex: 1,
      minWidth: 400,
      renderCell: (params) => (
        <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
          {params.value}
        </div>
      ),
    },
    // {
    //   field: 'AmelieMaxScore',
    //   headerName: 'Amelie Max score',
    //   flex: 1,
    //   minWidth: 170,
    //   renderCell: (params) => (
    //     <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
    //       {params.value}
    //     </div>
    //   ),
    // },
    // {
    //   field: 'AmelieMeanScore',
    //   headerName: 'Amelie Mean score',
    //   flex: 1,
    //   minWidth: 170,
    //   renderCell: (params) => (
    //     <div style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
    //       {params.value}
    //     </div>
    //   ),
    // },
  ];

  const handleSelectionChange = (newSelection) => {
    const selectedRows = data
      .filter((row) => newSelection.includes(row.id))
      .map((row) => ({
        ...row,
        groupValue: dropdownValues[row.id] || '1',
      }));

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
            alignItems: 'center',
            padding: '8px',
          },
        }}
      />
    </div>
  );
}

export default Germline_Exome_table;

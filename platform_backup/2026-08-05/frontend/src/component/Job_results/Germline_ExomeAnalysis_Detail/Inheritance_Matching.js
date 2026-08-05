// import * as React from 'react';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';
import React, { useState, useEffect } from 'react';

const columns = [
  { field: 'Location', headerName: 'Location', width: 120 },
  { field: 'Gene', headerName: 'Genes', width: 80 },
  { field: 'RSID', headerName: 'RS ID', width: 100 },
  { 
    field: 'MAF', 
    headerName: 'MAF', 
    width: 100, 
    renderCell: (params) => (
      <div style={{ whiteSpace: 'normal', wordWrap: 'break-word' }}>
        {params.value}
      </div>
    )
  },
  { field: 'GenotypeVAF', headerName: 'Genotype VAF(#ref/#alt)', width: 200 },
  { field: 'Evidence', headerName: 'Evidence', width: 130 },
  { field: 'Domain', headerName: 'Domain', width: 130 },
  { field: 'Pathogenicity', headerName: 'Pathogenicity', width: 150 },
  { field: 'SplicingEffect', headerName: 'Splicing effect', width: 170 },
  { field: 'OMIM', headerName: 'OMIM', width: 100 },
  { field: 'AmelieMaxScore', headerName: 'Amelie Max score', width: 200 },
  { field: 'AmelieMeanScore', headerName: 'Amelie Mean score', width: 200 },
];

// const rows = [
//   { id: 1, location: 'Snow', genes: 'Jon', rs_id: 35 },
// ];

function Inheritance_Matching({data}) {
  
  

  return (
    <div style={{ height: 400, width: '100%' }}>
      <DataGrid
        rows={data}
        columns={columns}
        // loading={loading}
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: 5 },
          },
        }}
        pageSizeOptions={[5, 10]}
        checkboxSelection
      />
    </div>
  );
}
export default Inheritance_Matching;
import React, { useRef } from 'react';
import { Button, TextField, Box, Typography } from '@mui/material';

function File_upload({ bam_ic, bam_f, bam_m, setbam_ic, setbam_f, setbam_m }) {
  const inputbam_ic = useRef(null);
  const inputbam_f = useRef(null);
  const inputbam_m = useRef(null);

  const handleFileUpload = (event, setFile) => {
    setFile(event.target.files[0]);
  };

  const renderFileInput = (label, file, ref, setFile) => (
    <Box sx={{ mb: 3 }}>
      <Typography sx={{ fontWeight: 'bold', fontSize: '24px', mb: 1 }}>
        Upload <span style={{ color: 'red' }}>{label}</span> bam file (.bam)
      </Typography>
      <input
        type="file"
        ref={ref}
        onChange={(e) => handleFileUpload(e, setFile)}
        style={{ display: 'none' }}
      />
      <TextField
        variant="standard"
        value={file ? file.name : ''}
        sx={{ width: '600px', mr: 2 }}
        disabled
        InputProps={{
          sx: {
            fontSize: '22px',
            bgcolor: '#DCDCDC', // 背景顏色
            borderRadius: '4px', // 圓角
            padding: '7px', // 內邊距
            '& .MuiInputBase-input': {
              color: '#FFA500 !important', // 重要：覆蓋禁用樣式的顏色
            },
          },
        }}
        
      />
      <Button variant="contained" 
              onClick={() => ref.current.click()}
              sx={{ height: '50px', }}
              >
        Browse
      </Button>
    </Box>
  );

  return (
    <Box sx={{ ml: 4 }}>
      {renderFileInput('Proband', bam_ic, inputbam_ic, setbam_ic)}
      {renderFileInput('Father', bam_f, inputbam_f, setbam_f)}
      {renderFileInput('Mother', bam_m, inputbam_m, setbam_m)}
    </Box>
  );
}

export default File_upload;

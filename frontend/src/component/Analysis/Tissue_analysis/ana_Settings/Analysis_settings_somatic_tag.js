import React from 'react';
import { Box, Typography, Grid, Divider, TextField } from '@mui/material';
import Diagnosis_AutoComplete from '../ana_Settings/diagnosis_AutoComplete';

function Analysis_settings_somatic_tab({
  alleleFrequency,
  setAlleleFrequency,
  diagnosis,          // 字串
  setDiagnosis,       // set 字串
}) {
  const handleAlleleFrequencyChange = (event) => setAlleleFrequency(event.target.value);

  return (
    <Box>
      {/* Allele Frequency Input */}
      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
              Retain variants with alternative allele frequency (MAF) below:
            </Typography>
            <TextField
              fullWidth
              hiddenLabel
              id="maf_cutoff"
              name="maf_cutoff"
              variant="filled"
              size="small"
              value={alleleFrequency}
              onChange={handleAlleleFrequencyChange}
              InputProps={{ sx: { fontSize: '22px' } }}
              InputLabelProps={{ sx: { fontSize: '22px' } }}
            />
          </Grid>
        </Grid>
      </Box>

      <Divider sx={{ margin: '20px 0' }} />

      {/* Diagnosis (free input + 建議清單) */}
      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
              Disease name:
            </Typography>
            <Diagnosis_AutoComplete
              diagnosis={diagnosis}          // 字串
              setDiagnosis={setDiagnosis}    // set 字串
            />
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
}

export default Analysis_settings_somatic_tab;

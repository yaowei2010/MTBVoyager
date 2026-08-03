import React from 'react';
import { Box, Chip, Step, StepLabel, Stepper, Typography } from '@mui/material';

const steps = ['Subject', 'Input files', 'Settings'];

export default function WgsAnalysisHeader({ activeStep }) {
  return (
    <Box sx={{ textAlign: 'center', mb: { xs: 5, md: 7 } }}>
      <Chip label="CLINICAL GENOMICS" size="small" sx={{ mb: 2, px: 1, color: '#0b5cab', bgcolor: '#e8f3ff', fontWeight: 800, letterSpacing: '.08em' }} />
      <Typography variant="h1" sx={{ fontSize: { xs: 38, sm: 52, md: 64 }, lineHeight: 1.08, fontWeight: 800, letterSpacing: '-0.04em', color: '#102a43' }}>
        WGS Germline Analysis
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 1.5, mb: { xs: 4, md: 5 }, fontSize: { xs: 16, md: 18 } }}>
        From genomic inputs to phenotype-aware clinical interpretation
      </Typography>
      <Box sx={{ maxWidth: 820, mx: 'auto', px: { xs: 0, sm: 2 } }}>
        <Stepper activeStep={activeStep} alternativeLabel>
          {steps.map((label) => <Step key={label}><StepLabel>{label}</StepLabel></Step>)}
        </Stepper>
      </Box>
    </Box>
  );
}

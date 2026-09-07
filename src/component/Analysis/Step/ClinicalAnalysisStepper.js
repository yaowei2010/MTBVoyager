import React from 'react';
import { Box, Step, StepLabel, Stepper } from '@mui/material';

const steps = ['Protocol', 'Subject', 'Input files', 'Settings'];

export default function ClinicalAnalysisStepper({ activeStep }) {
  return (
    <Box sx={{ width: '100%', maxWidth: 900, mx: 'auto', px: { xs: 0, sm: 2 } }}>
      <Stepper
        activeStep={activeStep}
        alternativeLabel
        sx={{
          '& .MuiStepLabel-label': {
            mt: 1,
            color: '#627d98',
            fontSize: { xs: 12, sm: 14 },
            fontWeight: 650,
          },
          '& .MuiStepLabel-label.Mui-active': {
            color: '#102a43',
            fontWeight: 800,
          },
          '& .MuiStepLabel-label.Mui-completed': {
            color: '#0d756d',
            fontWeight: 700,
          },
          '& .MuiStepIcon-root': {
            color: '#d9e2ec',
            fontSize: { xs: 30, sm: 36 },
          },
          '& .MuiStepIcon-root.Mui-active': {
            color: '#0b67b2',
            filter: 'drop-shadow(0 4px 7px rgba(11, 103, 178, .22))',
          },
          '& .MuiStepIcon-root.Mui-completed': { color: '#0d8f80' },
          '& .MuiStepIcon-text': { fill: '#fff', fontWeight: 800 },
          '& .MuiStepConnector-root': { top: { xs: 14, sm: 17 } },
          '& .MuiStepConnector-line': {
            borderColor: '#d9e2ec',
            borderTopWidth: 3,
            borderRadius: 2,
          },
          '& .MuiStepConnector-root.Mui-active .MuiStepConnector-line, & .MuiStepConnector-root.Mui-completed .MuiStepConnector-line': {
            borderColor: '#0d8f80',
          },
        }}
      >
        {steps.map((label) => (
          <Step key={label}>
            <StepLabel>{label}</StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}


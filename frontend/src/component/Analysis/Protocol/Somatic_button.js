


import React from 'react';
import { Button, Stack, Box } from '@mui/material';
import { config } from '../../../constant';

export default function SomaticButtons() {
  return (
    <Box sx={{ mt: 4, textAlign: 'center' }}>
      <Stack
        direction="row"
        spacing={3}
        useFlexGap
        flexWrap="wrap"
        justifyContent="center"
      >
        <Button
          variant="contained"
          color="primary"
          href={`${config.rootPathPrefix}/Analysis/Tissue/Subject`}
          sx={{
            textTransform: 'none',
            width: '230px',
            height: '60px',
            fontSize: '19px',
            boxShadow: 3,
            '&:hover': {
              bgcolor: '#1565c0',
            },
          }}
        >
          Tissue only
        </Button>
        <Button
          variant="contained"
          color="secondary"
          href={`${config.rootPathPrefix}/Analysis/Subject`}
          sx={{
            textTransform: 'none',
            width: '230px',
            height: '60px',
            fontSize: '19px',
            boxShadow: 3,
            '&:hover': {
              bgcolor: '#ad1457',
            },
          }}
        >
          Paired sample
        </Button>
        <Button
          variant="contained"
          color="success"
          href={`${config.rootPathPrefix}/Analysis/WGS_hg38_Somatic`}
          sx={{
            textTransform: 'none',
            width: '230px',
            height: '60px',
            fontSize: '19px',
            boxShadow: 3,
            '&:hover': {
              bgcolor: '#2e7d32',
            },
          }}
        >
          WGS hg38 somatic
        </Button>
      </Stack>
    </Box>
  );
}

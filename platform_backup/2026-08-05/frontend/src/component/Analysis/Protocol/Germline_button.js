

import React from 'react';
import { Button, Stack, Box } from '@mui/material';
import { config } from '../../../constant';
import { Link } from 'react-router-dom';

export default function GermlineButtons() {
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
          href={`${config.rootPathPrefix}/Analysis/Exome/Subject`}
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
          Exome analysis
        </Button>
        <Button
          variant="contained"
          color="secondary"
          href={`${config.rootPathPrefix}/Analysis/Exome_Trio/Subject`}
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
          Exome Trio analysis
        </Button>
        <Button
          variant="contained"
          color="success"
          component={Link}
          to={`${config.rootPathPrefix}/Analysis/WGS_Germline/Subject`}
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
          WGS hg38 germline
        </Button>
      </Stack>
    </Box>
  );
}

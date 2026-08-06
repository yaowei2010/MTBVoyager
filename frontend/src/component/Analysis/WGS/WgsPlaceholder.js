import React from 'react';
import { Box, Button, Card, CardContent, Typography } from '@mui/material';
import { config } from '../../../constant';

export default function WgsPlaceholder({ analysisType }) {
  return (
    <Box
      sx={{
        p: '32px',
        minHeight: '80vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Card sx={{ width: '100%', maxWidth: 680, boxShadow: 3 }}>
        <CardContent sx={{ p: 5, textAlign: 'center' }}>
          <Typography variant="h3" component="h1" gutterBottom fontWeight="bold">
            {analysisType}
          </Typography>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 4 }}>
            Analysis workflow is under construction.
          </Typography>
          <Button
            variant="contained"
            href={`${config.rootPathPrefix}/Analysis/Protocol`}
            sx={{ textTransform: 'none' }}
          >
            Back to Analysis
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
}

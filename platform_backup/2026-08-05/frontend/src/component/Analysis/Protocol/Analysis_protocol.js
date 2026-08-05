import React from 'react';
import { Chip, Grid, Typography, Box, Card, CardContent, Stack } from '@mui/material';
import BiotechOutlinedIcon from '@mui/icons-material/BiotechOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import Step_protocol from '../Step/Step_protocol';
import Germline_button from './Germline_button';
import Somatic_button from './Somatic_button';

function Analysis_protocol() {
  return (
    <Box sx={{ px: { xs: 2, md: 5 }, py: 5, minHeight: '100vh', mb: 5, maxWidth: 1280, mx: 'auto' }}>
      <Box sx={{ textAlign: 'center', mb: 5 }}><Chip label="ANALYSIS WORKSPACE" sx={{ mb: 2, bgcolor: '#e8f7f2', color: '#087f5b', fontWeight: 800, letterSpacing: '.06em' }} />
      <Typography
        variant="h1"
        component="h1"
        align="center"
        mb="40px"
        gutterBottom
        sx={{
          fontSize: { xs: "42px", md: "64px" },
          fontWeight: "bold", // 字體粗細
          fontFamily: "'Roboto', sans-serif", // 自定義字體系列
          color: "#102a43",
        }}
      >
        Select an analysis
    </Typography>
      <Typography color="text.secondary" sx={{ fontSize: 18 }}>Choose a clinical workflow based on specimen and inheritance context.</Typography></Box>


      <Box sx={{ mb: 7 }}>
        <Step_protocol />
      </Box>

      <Grid container spacing={4}>
        <Grid item xs={12} md={6}>
          <Card sx={{ minHeight: 270, borderRadius: 3, bgcolor: '#fff' }}>
            <CardContent sx={{ p: 3.5 }}>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}><Box sx={{ p: 1, display: 'flex', bgcolor: '#e7f4ff', color: '#0b67b2', borderRadius: 2 }}><BiotechOutlinedIcon /></Box>
              <Typography variant="h5" component="h2" gutterBottom
              sx={{
                fontWeight: "bold", // 字體粗細
                fontFamily: "'Roboto', sans-serif", // 自定義字體系列
                color: "#333", // 字體顏色
              }}>
                Germline
              </Typography>
              </Stack>
              <Typography color="text.secondary">Inherited variant prioritization for singleton, trio, exome and whole-genome analyses.</Typography>
              <Germline_button />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card sx={{ minHeight: 270, borderRadius: 3, bgcolor: '#fff' }}>
            <CardContent sx={{ p: 3.5 }}>
              <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 2 }}><Box sx={{ p: 1, display: 'flex', bgcolor: '#e8f7f2', color: '#087f5b', borderRadius: 2 }}><ScienceOutlinedIcon /></Box>
              <Typography variant="h5" component="h2" gutterBottom
              sx={{
                fontWeight: "bold", // 字體粗細
                fontFamily: "'Roboto', sans-serif", // 自定義字體系列
                color: "#333", // 字體顏色
              }}>
                Somatic
              </Typography>
              </Stack>
              <Typography color="text.secondary">Tumor-focused interpretation with actionable evidence and molecular signatures.</Typography>
              <Somatic_button />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Analysis_protocol;

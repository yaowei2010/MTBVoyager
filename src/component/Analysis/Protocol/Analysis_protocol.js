import React from 'react';
import { Grid, Typography, Box, Card, CardContent } from '@mui/material';
import Step_protocol from '../Step/Step_protocol';
import Germline_button from './Germline_button';
import Somatic_button from './Somatic_button';

function Analysis_protocol() {
  return (
    <Box sx={{ p: '32px', bgcolor: '#WHITE', minHeight: '80vh', mb: "36px" }}>
      <Typography
        variant="h1"
        component="h1"
        align="center"
        mb="40px"
        gutterBottom
        sx={{
          fontSize: "80px", // 字體大小
          fontWeight: "bold", // 字體粗細
          fontFamily: "'Roboto', sans-serif", // 自定義字體系列
          color: "#333", // 字體顏色
        }}
      >
        Analysis
    </Typography>


      <Box sx={{ mb: '100px' }}>
        <Step_protocol />
      </Box>

      <Grid container spacing={4}>
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: '#e3f2fd', boxShadow: 3 }}>
            <CardContent>
              <Typography variant="h5" component="h2" gutterBottom
              sx={{
                fontWeight: "bold", // 字體粗細
                fontFamily: "'Roboto', sans-serif", // 自定義字體系列
                color: "#333", // 字體顏色
              }}>
                Germline
              </Typography>
              <Germline_button />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: '#e3f2fd', boxShadow: 3 }}>
            <CardContent>
              <Typography variant="h5" component="h2" gutterBottom
              sx={{
                fontWeight: "bold", // 字體粗細
                fontFamily: "'Roboto', sans-serif", // 自定義字體系列
                color: "#333", // 字體顏色
              }}>
                Somatic
              </Typography>
              <Somatic_button />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Analysis_protocol;

import React, { useState, useEffect, useContext } from 'react';
import Job_table from './Job_table.js';
import Button from '@mui/material/Button';
import { config } from '../../constant.js';
import axios from 'axios';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { AuthContext } from '../Auth/AuthContext.js';
import { Box, Chip, Paper, Stack, Typography } from '@mui/material';
import AddCircleOutlineIcon from '@mui/icons-material/AddCircleOutline';

// Theme for customizing TableCell styles
const theme = createTheme({
  components: {
    MuiTableCell: {
      styleOverrides: {
        root: {
          fontSize: '1.2rem',
          padding: '10px',
        },
      },
    },
  },
});

// Helper function to create data rows
function createData(ID, analysis_ID, subject, protocol, phenotypes, status, genome_build, action) {
  return {
    ID,
    analysis_ID,
    subject,
    protocol,
    phenotypes,
    status,
    genome_build,
    action,
  };
}

function Job_results() {
  const [rows, setRows] = useState([]);
  const { userId } = useContext(AuthContext);

  const fetchData = async () => {
    try {
      const response = await axios.post(`${config.rootApiIP}/job_list`, {
        user_id: userId,
      });

      const JobData = JSON.parse(response.data.jobs);
      const fieldsArray = JobData.map((job) => job.fields);

      const newRows = fieldsArray.map((fields) =>
        createData(
          `${fields.jobID}${fields.name}${fields.date}`, // unique ID
          fields.jobID,
          fields.subject_id,
          fields.name,
          fields.dob,
          fields.status,
          fields.genome_build ?? 'hg19', // ✅ Genome build（後端沒給就預設 hg19）
          fields.processID // action（若 Job_table 需要用）
        )
      );

      setRows(newRows);
    } catch (error) {
      console.error('Request Error:', error);
    }
  };

  // 首次載入時先 fetch，並設定每分鐘自動重新 fetch
  useEffect(() => {
    fetchData();

    const interval = setInterval(() => {
      fetchData();
    }, 60000);

    return () => clearInterval(interval);
  }, [userId]); // ✅ userId 變了要重新拉

  const refreshRows = async () => {
    try {
      const response = await axios.post(`${config.rootApiIP}/job_list`, {
        user_id: userId,
      });

      const JobData = JSON.parse(response.data.finished_jobs || response.data.jobs);
      const fieldsArray = JobData.map((job) => job.fields);

      const newRows = fieldsArray.map((fields) =>
        createData(
          `${fields.jobID}${fields.name}${fields.date}`, // ✅ 維持一致的 unique ID
          fields.jobID,
          fields.subject_id,
          fields.name,
          fields.dob,
          fields.status,
          fields.genome_build ?? 'hg19', // ✅ Genome build
          fields.processID
        )
      );

      setRows(newRows);
    } catch (error) {
      console.error('Request Error:', error);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <Box sx={{ px: { xs: 2, md: 4 }, py: 4, maxWidth: 1500, mx: 'auto' }}>
        {/* Header Section */}
        <Stack direction={{ xs: 'column', md: 'row' }} alignItems={{ md: 'center' }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
          <Box><Chip label="ANALYSIS OPERATIONS" size="small" sx={{ mb: 1.5, bgcolor: '#e8f7f2', color: '#087f5b', fontWeight: 800, letterSpacing: '.06em' }} /><Typography variant="h3" sx={{ fontSize: { xs: 36, md: 50 }, fontWeight: 800 }}>Analysis jobs</Typography><Typography color="text.secondary">Monitor pipelines and review completed clinical interpretation results.</Typography></Box>

          <Button
            variant="contained"
            startIcon={<AddCircleOutlineIcon />}
            style={{
              fontSize: '1.2rem',
              padding: '0.75rem 1.5rem',
            }}
            href={config.rootPathPrefix + '/Analysis/Protocol'}
          >
            Start new analysis
          </Button>
        </Stack>

        {/* Job Table Section */}
        <Paper sx={{ p: { xs: 1, md: 2 }, borderRadius: 3, border: '1px solid #dce7f0', boxShadow: '0 12px 34px rgba(27,72,111,.08)', mb: 6 }}>
          {rows.length > 0 && <Job_table rows={rows} refreshRows={refreshRows} />}
        </Paper>
      </Box>
    </ThemeProvider>
  );
}

export default Job_results;

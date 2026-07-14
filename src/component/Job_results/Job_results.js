import React, { useState, useEffect, useContext } from 'react';
import Job_table from './Job_table.js';
import Button from '@mui/material/Button';
import { config } from '../../constant.js';
import axios from 'axios';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { AuthContext } from '../Auth/AuthContext.js';

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
      <div style={{ padding: '0.7rem' }}>
        {/* Header Section */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '0.5rem',
          }}
        >
          <h1
            style={{
              fontSize: '3.5rem',
              fontWeight: 'bold',
              margin: 0,
            }}
          >
            Job Results
          </h1>

          <Button
            variant="contained"
            style={{
              fontSize: '1.2rem',
              padding: '0.75rem 1.5rem',
              marginRight: '55px',
            }}
            href={config.rootPathPrefix + '/Analysis/Protocol'}
          >
            Start new analysis
          </Button>
        </div>

        {/* Job Table Section */}
        <div style={{ marginRight: '3rem', marginBottom: '4rem' }}>
          {rows.length > 0 && <Job_table rows={rows} refreshRows={refreshRows} />}
        </div>
      </div>
    </ThemeProvider>
  );
}

export default Job_results;

import React, { useState, useContext } from 'react';
import { Box, Button, Backdrop, Grid, Typography } from '@mui/material';
import Step_sample from '../../Step/Step_sample';
import FileUpload from './File_upload';
import { config } from '../../../../constant';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Loading from '../../../Loading';
import ErrorDialog from '../../../ErrorDialog'; // 引入 ErrorDialog Component
import { AuthContext } from '../../../Auth/AuthContext.js';

function Analysis_sample() {
  const [SNVFile, setSNV_File] = useState(null);
  const [CNVFile, setCNV_File] = useState(null);
  const [biomarkers_File, set_biomarkers_File] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const { userId } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleNext = async () => {
    setLoading(true);
    setError('');

    if (!SNVFile) {
      setError('SNV file is required.');
      setErrorDialogOpen(true);
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('myfile', SNVFile);

    try {
      const response = await axios.post(
        `${config.rootApiIP}/react_send_page2`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      console.log('檔案上傳回應:', response.data);
      setTimeout(() => navigate(`${config.rootPathPrefix}/Analysis/Exome/Settings`), 500);
    } catch (error) {
      console.error('File upload error:', error);
      setError('Error occurred during file upload.');
      setErrorDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseErrorDialog = () => {
    setErrorDialogOpen(false);
  };

  return (
    <Box sx={{ p: 4, bgcolor: '#WHITE', minHeight: '100vh', mb: "80px" }}>
      <Typography
        variant="h1"
        component="h1"
        align="center"
        mb="40px"
        gutterBottom
        sx={{
          fontSize: "80px", 
          fontWeight: "bold", 
          fontFamily: "'Roboto', sans-serif", 
          color: "#333", 
        }}
      >
        Analysis
      </Typography>

      <Box sx={{ mb: '100px' }}>
        <Step_sample />
      </Box>

      <FileUpload
        SNVFile={SNVFile}
        
        CNVFile={CNVFile}
        biomarkers_File={biomarkers_File}
        setSNV_File={setSNV_File}
        
        setCNV_File={setCNV_File}
        set_biomarkers_File={set_biomarkers_File}
      />

      {loading && (
        <Backdrop
          sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}
          open={loading}
        >
          <Loading show={loading} />
        </Backdrop>
      )}

      <Box sx={{ textAlign: 'center', mt: 6 }}>
        <Button 
          variant="outlined" 
          href={`${config.rootPathPrefix}/Analysis/Exome/Subject`} 
          sx={{ 
            mr: 4,
            width: '230px',
            height: '60px',
            fontSize: '19px',
            boxShadow: 3,
            '&:hover': { bgcolor: '#DCDCDC' },
          }}
        >
          Previous
        </Button>
        <Button 
          variant="contained" 
          onClick={handleNext}
          sx={{ 
            mr: 2,
            width: '230px',
            height: '60px',
            fontSize: '19px',
            boxShadow: 3,
            '&:hover': { bgcolor: '#1565c0' },
          }}
        >
          Next
        </Button>
      </Box>

      {/* 使用 ErrorDialog Component */}
      <ErrorDialog open={errorDialogOpen} onClose={handleCloseErrorDialog} errorMessage={error} />
    </Box>
  );
}

export default Analysis_sample;

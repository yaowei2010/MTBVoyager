import React, { useState } from 'react';
import { Box, Button, Backdrop, Grid, Typography } from '@mui/material';
import Step_sample from '../../Step/Step_sample';
import FileUpload from './File_upload';
import { config } from '../../../../constant';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Loading from '../../../Loading';
import ErrorDialog from '../../../ErrorDialog'; // 引入 ErrorDialog Component

function Analysis_sample() {

  // 改輸入bam 先保留舊參數
  // const [gVCF_ic, setgVCF_ic] = useState(null);
  // const [gVCF_f, setgVCF_f] = useState(null);
  // const [gVCF_m, setgVCF_m] = useState(null);

  const [bam_ic, setbam_ic] = useState(null);
  const [bam_f, setbam_f] = useState(null);
  const [bam_m, setbam_m] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  const navigate = useNavigate();

  const handleNext = async () => {
    setLoading(true);
    setError('');

    if (!bam_ic) {
      setError('bam file is required.');
      setErrorDialogOpen(true);
      setLoading(false);
      return;
    }

    const formData = new FormData();
    formData.append('BAM_ic_file', bam_ic);
    formData.append('BAM_f_file', bam_f);
    formData.append('BAM_m_file', bam_m);

    try {
      const response = await axios.post(
        `${config.rootApiIP}/react_send_page2_trio`, 
        formData, 
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );
      console.log('檔案上傳回應:', response.data);
      setTimeout(() => navigate(`${config.rootPathPrefix}/Analysis/Exome_Trio/Settings`), 500);
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
    <Box sx={{ p: { xs: 2, md: 4 }, minHeight: '100vh', mb: 10, maxWidth: 1280, mx: 'auto' }}>
      <Typography
        variant="h1"
        component="h1"
        align="center"
        mb="40px"
        gutterBottom
        sx={{
          fontSize: { xs: "42px", md: "64px" },
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
        bam_ic={bam_ic}
        bam_f={bam_f}
        bam_m={bam_m}
        setbam_ic={setbam_ic}
        setbam_f={setbam_f}
        setbam_m={setbam_m}
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
          href={`${config.rootPathPrefix}/Analysis/Exome_Trio/Subject`} 
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

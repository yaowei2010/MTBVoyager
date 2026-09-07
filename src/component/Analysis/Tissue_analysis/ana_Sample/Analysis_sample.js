import React, { useState } from 'react';
import {
    Box,
    Button,
    Backdrop,
    Grid,
    Typography,
    LinearProgress,
} from '@mui/material';
import Step_sample from '../../Step/Step_sample';
import FileUpload from './File_upload';
import { config } from '../../../../constant';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import ErrorDialog from '../../../ErrorDialog';

function Analysis_sample() {
    const [SNVFile, setSNV_File] = useState(null);
    const [BAMFile, setBAM_File] = useState(null);
    const [CNVFile, setCNV_File] = useState(null);
    const [biomarkers_File, set_biomarkers_File] = useState(null);
    const [QC_report, set_QC_report] = useState(null);

    const [loading, setLoading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);
    const [uploadStatus, setUploadStatus] = useState('');

    const [error, setError] = useState('');
    const [errorDialogOpen, setErrorDialogOpen] = useState(false);

    const navigate = useNavigate();

    const handleNext = async () => {
        setLoading(true);
        setError('');
        setUploadProgress(0);
        setUploadStatus('Preparing upload...');

        if (!SNVFile) {
            setError('SNV file is required.');
            setErrorDialogOpen(true);
            setLoading(false);
            return;
        }

        const formData = new FormData();
        formData.append('myfile', SNVFile);

        if (BAMFile) {
            formData.append('mybam', BAMFile);
        }

        try {
            console.log('Start uploading files...');
            setUploadStatus('Uploading files...');

            const response = await axios.post(
                `${config.rootApiIP}/react_send_page2`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    timeout: 600000,
                    onUploadProgress: (progressEvent) => {
                        if (progressEvent.total) {
                            const percent = Math.round(
                                (progressEvent.loaded * 100) / progressEvent.total
                            );

                            setUploadProgress(percent);
                            console.log(`Upload progress: ${percent}%`);

                            if (percent < 100) {
                                setUploadStatus('Uploading files...');
                            } else {
                                setUploadStatus('Upload completed. Waiting for server response...');
                            }
                        }
                    },
                }
            );

            console.log('檔案上傳回應:', response.data);
            setUploadStatus('Upload successful. Redirecting...');

            setTimeout(() => {
                navigate(`${config.rootPathPrefix}/Analysis/Tissue/Settings`);
            }, 500);

        } catch (error) {
            console.error('File upload error:', error);

            if (error.code === 'ECONNABORTED') {
                setError('Upload timeout. Please check file size or server connection.');
            } else {
                setError('Error occurred during file upload.');
            }

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
                    fontSize: { xs: '42px', md: '64px' },
                    fontWeight: 'bold',
                    fontFamily: "'Roboto', sans-serif",
                    color: '#333',
                }}
            >
                Analysis
            </Typography>

            <Box sx={{ mb: '100px' }}>
                <Step_sample />
            </Box>

            <FileUpload
                SNVFile={SNVFile}
                BAMFile={BAMFile}
                CNVFile={CNVFile}
                biomarkers_File={biomarkers_File}
                QC_report={QC_report}
                setSNV_File={setSNV_File}
                setBAM_File={setBAM_File}
                setCNV_File={setCNV_File}
                set_biomarkers_File={set_biomarkers_File}
                set_QC_report={set_QC_report}
            />

            {loading && (
                <Backdrop
                    sx={{
                        color: '#fff',
                        zIndex: (theme) => theme.zIndex.drawer + 1,
                    }}
                    open={loading}
                >
                    <Box
                        sx={{
                            width: '430px',
                            bgcolor: 'white',
                            color: '#333',
                            borderRadius: '14px',
                            p: 4,
                            textAlign: 'center',
                            boxShadow: 6,
                        }}
                    >
                        <Typography
                            variant="h5"
                            sx={{
                                fontWeight: 'bold',
                                mb: 2,
                            }}
                        >
                            Uploading Files
                        </Typography>

                        <Typography
                            sx={{
                                mb: 2,
                                color: '#555',
                            }}
                        >
                            {uploadStatus}
                        </Typography>

                        <Typography
                            sx={{
                                mb: 1,
                                fontWeight: 'bold',
                                fontSize: '20px',
                            }}
                        >
                            {uploadProgress}%
                        </Typography>

                        <LinearProgress
                            variant="determinate"
                            value={uploadProgress}
                            sx={{
                                height: 12,
                                borderRadius: 6,
                                mb: 2,
                            }}
                        />

                        <Typography
                            variant="body2"
                            sx={{
                                color: '#777',
                            }}
                        >
                            Please do not close this page.
                        </Typography>
                    </Box>
                </Backdrop>
            )}

            <Box sx={{ textAlign: 'center', mt: 6 }}>
                <Button
                    variant="outlined"
                    href={`${config.rootPathPrefix}/Analysis/Tissue/Subject`}
                    sx={{
                        mr: 4,
                        width: '230px',
                        height: '60px',
                        fontSize: '19px',
                        boxShadow: 3,
                        '&:hover': {
                            bgcolor: '#DCDCDC',
                        },
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
                        '&:hover': {
                            bgcolor: '#1565c0',
                        },
                    }}
                >
                    Next
                </Button>
            </Box>

            <ErrorDialog
                open={errorDialogOpen}
                onClose={handleCloseErrorDialog}
                errorMessage={error}
            />
        </Box>
    );
}

export default Analysis_sample;

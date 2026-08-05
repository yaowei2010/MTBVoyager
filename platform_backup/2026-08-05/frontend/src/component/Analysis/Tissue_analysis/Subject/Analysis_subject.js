import React, { useState } from 'react';
import {
    TextField,
    Radio,
    RadioGroup,
    FormControlLabel,
    FormControl,
    FormLabel,
    Button,
    Box,
    Grid,
    Backdrop,
    Typography,
} from '@mui/material';
import Step_subjects from '../../Step/Step_subject';
import { config } from '../../../../constant';
import axios from 'axios';
import Loading from '../../../Loading';
import ErrorDialog from '../../../ErrorDialog'; // 引入 ErrorDialog Component
import { useContext } from 'react';
import { AuthContext } from '../../../Auth/AuthContext.js';

function Analysis_subject() {
    const [subject_id, setSubjectID] = useState('');
    const [name, setName] = useState('Somatic');
    const [dob, setDob] = useState('');
    const [gender, setGender] = useState('');
    const [history, setHistory] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [errorDialogOpen, setErrorDialogOpen] = useState(false);
    const { userId } = useContext(AuthContext);

    const handleGenderChange = (event) => {
        setGender(event.target.value);
    };

    const handleNextClick = async (event) => {
        event.preventDefault();
        setLoading(true);
        setError('');

        // 欄位驗證
        if (!subject_id || !dob || !gender) {
            let missingFields = [];
            if (!subject_id) missingFields.push('Subject ID');
            if (!dob) missingFields.push('Date of Birth');
            if (!gender) missingFields.push('Gender');

            setError(`${missingFields.join(', ')} is required.`);
            setErrorDialogOpen(true);
            setLoading(false);
            return;
        }

        try {
            const response = await axios.post(`${config.rootApiIP}/react_send_page1`, {
                subject_id: subject_id,
                name: name,
                dob: dob,
                gender: gender,
                history: history,
                user_id: userId, 
            });
            console.log('API Response:', response.data);
            window.location.href = `${config.rootPathPrefix}/Analysis/Tissue/Sample`;
        } catch (error) {
            console.error('Error saving data:', error);
            setError('An error occurred while saving data.');
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
                    fontWeight: "bold", // 字體粗細
                    fontFamily: "'Roboto', sans-serif", // 自定義字體系列
                    color: "#333", // 字體顏色
                }}
            >
                Analysis
            </Typography>

            <Box sx={{ mb: '100px' }}>
                <Step_subjects />
            </Box>

            <Grid container spacing={4}>
                <Grid item xs={12} md={6}>
                    <TextField
                        label="Subject ID"
                        variant="filled"
                        fullWidth
                        value={subject_id}
                        onChange={(e) => setSubjectID(e.target.value)}
                        InputProps={{
                            sx: {
                                fontSize: '28px', // 輸入字體大小
                            },
                        }}
                        InputLabelProps={{
                            sx: {
                                fontSize: '22px', // 標籤字體大小
                            },
                        }}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <TextField
                        label="Protocol"
                        variant="filled"
                        fullWidth
                        disabled
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        InputProps={{
                            sx: {
                                fontSize: '28px', // 輸入字體大小
                            },
                        }}
                        InputLabelProps={{
                            sx: {
                                fontSize: '22px', // 標籤字體大小
                            },
                        }}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <TextField
                        label="Date of Birth"
                        type="date"
                        InputProps={{
                            sx: {
                                fontSize: '28px', // 輸入字體大小
                            },
                        }}
                        InputLabelProps={{
                            shrink: true,
                            sx: { fontSize: '22px' }, // 標籤字體大小
                        }}
                        variant="filled"
                        fullWidth
                        value={dob}
                        onChange={(e) => setDob(e.target.value)}
                    />
                </Grid>
                <Grid item xs={12} md={6}>
                    <FormControl>
                        <FormLabel sx={{ fontSize: '22px' }}>
                            Gender
                        </FormLabel>
                        <RadioGroup row value={gender} onChange={handleGenderChange}>
                            <FormControlLabel value="male" control={<Radio />} label="Male" />
                            <FormControlLabel value="female" control={<Radio />} label="Female" />
                        </RadioGroup>
                    </FormControl>
                </Grid>
                <Grid item xs={12}>
                    <TextField
                        label="History/Description"
                        variant="filled"
                        multiline
                        rows={3}
                        fullWidth
                        value={history}
                        onChange={(e) => setHistory(e.target.value)}
                        InputProps={{
                            sx: {
                                fontSize: '28px', // 輸入字體大小
                            },
                        }}
                        InputLabelProps={{
                            sx: {
                                fontSize: '22px', // 標籤字體大小
                            },
                        }}
                    />
                </Grid>
            </Grid>

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
                    href={`${config.rootPathPrefix}/Analysis/Protocol`}
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
                    color="primary"
                    onClick={handleNextClick}
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

            <ErrorDialog open={errorDialogOpen} onClose={handleCloseErrorDialog} errorMessage={error} />
        </Box>
    );
}

export default Analysis_subject;

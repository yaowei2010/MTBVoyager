import React, { useRef } from 'react';
import { Button, TextField, Box, Typography } from '@mui/material';


function File_upload({ SNVFile, BAMFile, CNVFile, biomarkers_File, QC_report, setSNV_File, setBAM_File, setCNV_File, set_biomarkers_File, set_QC_report }) {

    const inputSNV_Ref = useRef(null);
    const inputBAM_Ref = useRef(null);
    const inputCNV_Ref = useRef(null);
    const input_biomarkers_Ref = useRef(null);
    const input_QC_Ref = useRef(null);


    const handleFileUpload = (event, setFile) => {
        setFile(event.target.files[0]);
    };
    
    const renderFileInput = (label, file, ref, setFile) => (
        <Box sx={{ mb: 3 }}>
            <Typography sx={{
                fontWeight: 'bold',
                fontSize: '24px',
                mb: 1,
                color: label === 'Upload QC report' ? 'red' : 'inherit', // 動態設置顏色
                }}
                >
                {label}
            </Typography>
            <input
                type="file"
                ref={ref}
                onChange={(e) => handleFileUpload(e, setFile)}
                style={{ display: 'none' }}
            />
            <TextField
                variant="standard"
                value={file ? file.name : ''}
                sx={{ width: '600px', mr: 2 }}
                disabled
                InputProps={{
                sx: {
                    fontSize: '22px',
                    bgcolor: '#DCDCDC', // 背景顏色
                    borderRadius: '4px', // 圓角
                    padding: '7px', // 內邊距
                    '& .MuiInputBase-input': {
                    color: '#FFA500 !important', // 重要：覆蓋禁用樣式的顏色
                    },
                },
                }}
                
            />
            <Button variant="contained" 
                    onClick={() => ref.current.click()}
                    sx={{ height: '50px', }}
                    >
                Browse
            </Button>
        </Box>
    );
        
        return (
            <Box sx={{ ml: 4 }}>
            {renderFileInput('Upload SNV file (.vcf)', SNVFile, inputSNV_Ref, setSNV_File)}
            {renderFileInput('Upload BAM file (.bam)', BAMFile, inputBAM_Ref, setBAM_File)}
            {/* {renderFileInput('Upload CNV file (.vcf)', CNVFile, inputCNV_Ref, setCNV_File)} */}
            {/* {renderFileInput('Upload biomarkers', biomarkers_File, input_biomarkers_Ref, set_biomarkers_File)} */}
            {/* {renderFileInput('Upload QC report', QC_report, input_QC_Ref, set_QC_report)} */}
            </Box>
        );
        }
    
    export default File_upload;

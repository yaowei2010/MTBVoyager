import React, { useState, useRef } from 'react';
import { Box, Typography, Grid, Divider, TextField, Button, Switch, FormControlLabel } from '@mui/material';
import Radio_change from './Radio_change';
import Gene_panels from './Gene_panels';

function Analysis_settings_germline_tab({
    alleleFrequency,
    setAlleleFrequency,
    genePanelsData,
    setGenePanelsData,
    panel_auto_Info,
    setPanelInfo,
    isGermlineEnabled,
    setIsGermlineEnabled
}) {

    const [autoFillTargetIndex, setAutoFillTargetIndex] = useState(genePanelsData.length - 1);
    const panelRefs = useRef([]); // 用於收集每個 gene panel 對應的 DOM ref

    const handleToggleSwitch = () => setIsGermlineEnabled(!isGermlineEnabled);
    const handleAlleleFrequencyChange = (event) => setAlleleFrequency(event.target.value);
    const handleGenePanelChange = (index, newData) => {
        const updatedData = [...genePanelsData];
        updatedData[index] = { ...updatedData[index], ...newData }; 
        setGenePanelsData(updatedData);
    };

    const handleMoreButtonClick = () => {
        const newIndex = genePanelsData.length;
        setGenePanelsData([...genePanelsData, { panelName: '', genes: '' }]);
        setAutoFillTargetIndex(newIndex); // 新 panel 才接受 auto-fill

        setTimeout(() => {
        if (panelRefs.current[newIndex]) {
        panelRefs.current[newIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        }, 300); // 給 DOM render 一點時間
  };

    const handleLessButtonClick = () => {
        if (genePanelsData.length > 1) {
        const updatedData = [...genePanelsData];
        updatedData.pop();
        setGenePanelsData(updatedData);
        const newIndex = updatedData.length - 1;
        setAutoFillTargetIndex(updatedData.length - 1); // 回到前一筆作為 auto-fill 目標
        

        setTimeout(() => {
        if (panelRefs.current[newIndex]) {
            panelRefs.current[newIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        }, 300);

    }
    };

    return (
        <Box>
            {/* Enable/Disable Switch */}
            <Box sx={{ padding: '20px', marginBottom: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
                <FormControlLabel
                    control={
                        <Switch color="primary" checked={isGermlineEnabled} onChange={handleToggleSwitch} />
                    }
                    label={
                        <Typography sx={{ fontWeight: 'bold', fontSize: '30px' }}>
                            Germline Prediction 
                        </Typography>
                    }
                />
            </Box>

            <Divider sx={{ margin: '20px 0' }} />

            {/* Allele Frequency Input */}
            <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
                <Grid container spacing={4}>
                    <Grid item xs={12}>
                        <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
                        Retain variants with alternative allele frequency (MAF) below:
                        </Typography>
                        <TextField
                            fullWidth
                            hiddenLabel
                            id="maf_cutoff"
                            name="maf_cutoff"
                            variant="filled"
                            size="small"
                            value={alleleFrequency} 
                            onChange={handleAlleleFrequencyChange}
                            InputProps={{
                                sx: {
                                    fontSize: '22px',
                                },
                            }}
                            InputLabelProps={{
                                sx: {
                                    fontSize: '22px',
                                },
                            }}
                        />
                    </Grid>
                </Grid>
            </Box>

            <Divider sx={{ margin: '20px 0' }} />

            {/* Gene Panels and Radio Change */}
            <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
            <Typography variant="h3" sx={{ mb: 1, fontWeight: 700, ml: 60 }}>
                Optional Field
            </Typography>
            <Divider sx={{ mb: 2 }} />
                <Grid container spacing={4}>
          {genePanelsData.map((data, index) => (
            <React.Fragment key={index}>
              {index === autoFillTargetIndex ? (
                <>
                  {/* 左側：Radio_change + More/Less */}
                  <Grid item xs={12} md={6}>
                    <Radio_change
                      panel_auto_Info={panel_auto_Info}
                      setPanelInfo={setPanelInfo}
                    />
                    <Box sx={{ textAlign: 'left', mt: 4 }}>
                      <Button
                        variant="contained"
                        size="medium"
                        onClick={handleMoreButtonClick}
                        sx={{
                          mr: 2,
                          width: '200px',
                          height: '60px',
                          fontSize: '19px',
                          boxShadow: 3,
                          '&:hover': { bgcolor: '#1565c0' },
                        }}
                      >
                        More
                      </Button>
                      <Button
                        variant="contained"
                        size="medium"
                        onClick={handleLessButtonClick}
                        sx={{
                          width: '200px',
                          height: '60px',
                          fontSize: '18px',
                          boxShadow: 3,
                          '&:hover': { bgcolor: '#1565c0' },
                        }}
                      >
                        Less
                      </Button>
                    </Box>
                  </Grid>
                  
                  
                  {/* 右側：該筆 panel 的輸入欄位 */}
                  <Grid item xs={12} md={6}>
                    <div ref={(el) => (panelRefs.current[index] = el)}>
                    <Gene_panels
                      index={index}
                      panelData={data}
                      onChange={handleGenePanelChange}
                      panel_auto_Info={panel_auto_Info}
                      setPanelInfo={setPanelInfo}
                      autoFillTargetIndex={autoFillTargetIndex}
                    />
                    </div>
                  </Grid>
                </>
              ) : (
                <>
                  {/* 空欄 + 非 active panel */}
                  <Grid item xs={12} md={6}></Grid>
                  <Grid item xs={12} md={6}>
                    <div ref={(el) => (panelRefs.current[index] = el)}>
                    <Gene_panels
                      index={index}
                      panelData={data}
                      onChange={handleGenePanelChange}
                      panel_auto_Info={panel_auto_Info}
                      setPanelInfo={setPanelInfo}
                      autoFillTargetIndex={autoFillTargetIndex}
                    />
                    </div>
                  </Grid>
                </>
              )}
            </React.Fragment>
          ))}
        </Grid>
            </Box>
        </Box>
    );
}

export default Analysis_settings_germline_tab;

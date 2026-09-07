import React, { useState, useEffect, useRef  } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import Step_settings from '../../Step/Step_setting';
import { Typography, Grid, Box, Divider } from '@mui/material';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import { config } from '../../../../constant';
import TextField from '@mui/material/TextField';
import Gene_panels from './Gene_panels';
import Radio_change from './Radio_change';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormControl from '@mui/material/FormControl';
import axios from 'axios';
import Backdrop from '@mui/material/Backdrop';
import Loading from '../../../Loading';
import ErrorDialog from '../../../ErrorDialog'; // 使用 ErrorDialog Component


function Analysis_settings() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);
  

  const [alleleFrequency, setAlleleFrequency] = useState('0.01');
  const [minDepthCutoff, setMinDepthCutoff] = useState('20');
  const [minAltAlleleFreq, setMinAltAlleleFreq] = useState('0.2');
  const [configName, setConfigName] = useState('default');
  const [genePanelsData, setGenePanelsData] = useState([{ panelName: '', genes: '' , extraGene: ''}]);
  const [panel_auto_Info, setPanelInfo] = useState({ panelName: '', genes: '' });
  const [autoFillTargetIndex, setAutoFillTargetIndex] = useState(genePanelsData.length - 1);



  const panelRefs = useRef([]); // 用於收集每個 gene panel 對應的 DOM ref

  const handleAlleleFrequencyChange = (event) => {
    setAlleleFrequency(event.target.value);
  };
  const handleMinDepthCutoffChange = (event) => {
    setMinDepthCutoff(event.target.value);
  };
  const handleMinAltAlleleFreqChange = (event) => {
    setMinAltAlleleFreq(event.target.value);
  };
  const handleConfigNameChange = (event) => {
    setConfigName(event.target.value);
  };
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

  const handleSaveButtonClick = (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    let hasEmptyGenePanel = false;
    genePanelsData.forEach((panel, index) => {
      const warningElement = document.getElementById(`warning${index}`);
      if (panel.panelName.trim() === '' || panel.genes.trim() === '') {
        hasEmptyGenePanel = true;
        if (warningElement) {
          warningElement.classList.remove('hidden');
        }
      } else {
        if (warningElement) {
          warningElement.classList.add('hidden');
        }
      }
    });

    // 驗證
    if (alleleFrequency.trim() === '' && hasEmptyGenePanel) {
      setError('Allele frequency and Gene panels are required');
      setErrorDialogOpen(true);
      setLoading(false);
      return;
    } else if (alleleFrequency.trim() === '') {
      setError('Allele frequency is required');
      setErrorDialogOpen(true);
      setLoading(false);
      return;
    } else if (hasEmptyGenePanel) {
      setError('Gene panels are required');
      setErrorDialogOpen(true);
      setLoading(false);
      return;
    }

    // 組裝要送出的資料
    const genePanelList = genePanelsData.map((panel) => {
      const genes = panel.genes.trim();
      const extra = panel.extraGene?.trim();
      let fullGenes = genes;
      if (extra) {
        fullGenes = genes ? `${genes}、${extra}` : extra;
      }
      return {
        panelName: panel.panelName,
        genePanel: fullGenes,
      };
    });
    const jsonStr = { GenePanelList: genePanelList };

    console.log('送出前的檢查資料:', {
      alleleFrequency,
      minDepthCutoff,
      minAltAlleleFreq,
      configName,
      jsonStr,
    });

    // 1. 非同步送出資料（不加 await）
    axios
      .post(`${config.rootApiIP}/react_send_page3_trio`, {
        maf_cutoff: alleleFrequency,
        min_dp_cutoff: minDepthCutoff,
        min_aaf: minAltAlleleFreq,
        configName: configName,
        genePanelList: jsonStr,
      })
      .then((response) => {
        console.log('API 回應:', response.data);
      })
      .catch((error) => {
        console.error('保存數據時出錯:', error);
        if (error.response) {
          console.error('回應數據:', error.response.data);
          console.error('回應狀態:', error.response.status);
          console.error('回應標頭:', error.response.headers);
        } else if (error.request) {
          console.error('請求數據:', error.request);
        } else {
          console.error('錯誤消息:', error.message);
        }
      })
      .finally(() => {
        setLoading(false);
      });

    // 2. 不等待回應，直接跳轉
    window.location.href = `${config.rootPathPrefix}/Job_results`;
  };

  useEffect(() => {
    console.log("alleleFrequency changed:", alleleFrequency);
    console.log("minDepthCutoff changed:", minDepthCutoff);
    console.log("minAltAlleleFreq changed:", minAltAlleleFreq);
    console.log("configName changed:", configName);
    console.log("genePanelsData changed:", genePanelsData);
  }, [alleleFrequency, minDepthCutoff, minAltAlleleFreq, configName, genePanelsData]);

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
        <Step_settings />
      </Box>

      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
              Variant filtering
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <label style={{ fontSize: '24px' }}>Filtering</label>
            <RadioGroup
              row
              aria-labelledby="demo-row-radio-buttons-group-label"
              name="row-radio-buttons-group"
              defaultValue="Use_all_variants"
            >
              <FormControlLabel
                value="Use_all_variants"
                control={<Radio />}
                label="Use all variants"
                sx={{
                  '& .MuiFormControlLabel-label': {
                    fontSize: '22px',
                  },
                }}
              />
              <FormControlLabel
                value="Use_only_PASS_variants"
                control={<Radio />}
                label="Use only PASS variants"
                sx={{
                  '& .MuiFormControlLabel-label': {
                    fontSize: '22px',
                  },
                }}
              />
            </RadioGroup>
          </Grid>
          <Grid item xs={12} md={6}>
            <label style={{ fontSize: '24px' }}>
                Retain variants with minimum depth greater than:
            </label>
            <TextField
              fullWidth
              hiddenLabel
              id="min_dp_cutoff"
              name="min_dp_cutoff"
              variant="filled"
              size="small"
              value={minDepthCutoff} 
              onChange={handleMinDepthCutoffChange}
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
          <Grid item xs={12} md={6}>
            <label style={{ fontSize: '24px' }}>
              Retain variants with alternative allele frequency (VAF) greater than or equal to :
            </label>
            <TextField
              fullWidth
              hiddenLabel
              id="min_aaf"
              name="min_aaf"
              variant="filled"
              size="small"
              value={minAltAlleleFreq} 
              onChange={handleMinAltAlleleFreqChange}
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
          <Grid item xs={12} md={6}>
            {/* <label style={{ fontSize: '24px' }}>Save this configuration as</label>
            <RadioGroup
              row
              aria-labelledby="demo-row-radio-buttons-group-label"
              name="row-radio-buttons-group"
              defaultValue="default"
              onChange={handleConfigNameChange}
            >
              <FormControlLabel
                value="default"
                control={<Radio />}
                label="default"
                sx={{
                  '& .MuiFormControlLabel-label': {
                    fontSize: '22px',
                  },
                }}
              />
              <FormControlLabel
                value="manual"
                control={<Radio />}
                label="manual"
                sx={{
                  '& .MuiFormControlLabel-label': {
                    fontSize: '22px',
                  },
                }}
              />
            </RadioGroup> */}
          </Grid>
        </Grid>
      </Box>

      <Divider sx={{ margin: '20px 0' }} />
      
      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
                Retain variants with allele frequency (MAF)  below:
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

      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
        
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

      {loading && (
        <Backdrop
          sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}
          open={loading}
        >
          <Loading show={loading} />
        </Backdrop>
      )}

      <Divider sx={{ margin: '20px 0' }} />

      

      <Divider sx={{ margin: '20px 0' }} />

      <Box sx={{ textAlign: 'center', mt: 5 }}>
        <Button 
          variant="outlined" 
          href={config.rootPathPrefix + "/Analysis/Exome_Trio/Sample"}
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
          style={{ marginLeft: '30px' }}
          onClick={handleSaveButtonClick}
          id="btn_layer"
          value="true"
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
          Run
        </Button>
      </Box>

      <ErrorDialog open={errorDialogOpen} onClose={handleCloseErrorDialog} errorMessage={error} />
    </Box>
  );
}

export default Analysis_settings;

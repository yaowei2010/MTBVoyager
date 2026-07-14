import React, { useState, useEffect, useRef } from 'react';
import Step_settings from '../../Step/Step_setting';
import { Typography, Grid, Box, Divider } from '@mui/material';
import Button from '@mui/material/Button';
import { config } from '../../../../constant';
import TextField from '@mui/material/TextField';
import Gene_panels from './Gene_panels';
import Radio_change from './Radio_change';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import axios from 'axios';
import Backdrop from '@mui/material/Backdrop';
import Loading from '../../../Loading';
import ErrorDialog from '../../../ErrorDialog';

// ✅ 新增：hg19/hg38 切換按鈕
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

function Analysis_settings() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  const [alleleFrequency, setAlleleFrequency] = useState('0.01');
  const [minDepthCutoff, setMinDepthCutoff] = useState('20');
  const [minAltAlleleFreq, setMinAltAlleleFreq] = useState('0.2');
  const [configName, setConfigName] = useState('default');
  const [genePanelsData, setGenePanelsData] = useState([{ panelName: '', genes: '', extraGene: '' }]);
  const [panel_auto_Info, setPanelInfo] = useState({ panelName: '', genes: '' });
  const [autoFillTargetIndex, setAutoFillTargetIndex] = useState(genePanelsData.length - 1);

  // ✅ 新增：選擇 hg19 / hg38（預設 hg38）
  const [genomeBuild, setGenomeBuild] = useState('hg38');

  const panelRefs = useRef([]);

  const handleAlleleFrequencyChange = (event) => setAlleleFrequency(event.target.value);
  const handleMinDepthCutoffChange = (event) => setMinDepthCutoff(event.target.value);
  const handleMinAltAlleleFreqChange = (event) => setMinAltAlleleFreq(event.target.value);
  const handleConfigNameChange = (event) => setConfigName(event.target.value);

  const handleGenomeBuildChange = (event, newBuild) => {
    if (newBuild !== null) setGenomeBuild(newBuild);
  };

  const handleGenePanelChange = (index, newData) => {
    const updatedData = [...genePanelsData];
    updatedData[index] = { ...updatedData[index], ...newData };
    setGenePanelsData(updatedData);
  };

  const handleMoreButtonClick = () => {
    const newIndex = genePanelsData.length;
    setGenePanelsData([...genePanelsData, { panelName: '', genes: '', extraGene: '' }]);
    setAutoFillTargetIndex(newIndex);

    setTimeout(() => {
      if (panelRefs.current[newIndex]) {
        panelRefs.current[newIndex].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 300);
  };

  const handleLessButtonClick = () => {
    if (genePanelsData.length > 1) {
      const updatedData = [...genePanelsData];
      updatedData.pop();
      setGenePanelsData(updatedData);
      const newIndex = updatedData.length - 1;
      setAutoFillTargetIndex(newIndex);

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
        if (warningElement) warningElement.classList.remove('hidden');
      } else {
        if (warningElement) warningElement.classList.add('hidden');
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
      if (extra) fullGenes = genes ? `${genes}、${extra}` : extra;
      return { panelName: panel.panelName, genePanel: fullGenes };
    });
    const jsonStr = { GenePanelList: genePanelList };

    const payload = {
      maf_cutoff: alleleFrequency,
      min_dp_cutoff: minDepthCutoff,
      min_aaf: minAltAlleleFreq,
      configName: configName,
      genePanelList: jsonStr,
    };

    // ✅ 依 genomeBuild 選擇不同 API
    const endpoint =
      genomeBuild === 'hg38'
        ? `${config.rootApiIP}/react_send_page3_hg38`
        : `${config.rootApiIP}/react_send_page3`;

    // ✅ 你要「前端直接跳轉 Job_results」
    // 這裡用 keepalive 的 fetch 讓跳轉後請求也盡量能送完
    try {
      fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch((e) => console.error('send request failed:', e));
    } catch (e) {
      // 某些舊環境 keepalive 可能不支援
      axios.post(endpoint, payload).catch((e2) => console.error('send request failed:', e2));
    }

    window.location.href = `${config.rootPathPrefix}/Job_results`;
  };

  useEffect(() => {
    console.log('alleleFrequency changed:', alleleFrequency);
    console.log('minDepthCutoff changed:', minDepthCutoff);
    console.log('minAltAlleleFreq changed:', minAltAlleleFreq);
    console.log('configName changed:', configName);
    console.log('genePanelsData changed:', genePanelsData);
    console.log('genomeBuild changed:', genomeBuild);
  }, [alleleFrequency, minDepthCutoff, minAltAlleleFreq, configName, genePanelsData, genomeBuild]);

  const handleCloseErrorDialog = () => setErrorDialogOpen(false);

  return (
    <Box sx={{ p: 4, bgcolor: 'WHITE', minHeight: '100vh', mb: '80px' }}>
      <Typography
        variant="h1"
        component="h1"
        align="center"
        mb="40px"
        gutterBottom
        sx={{
          fontSize: '80px',
          fontWeight: 'bold',
          fontFamily: "'Roboto', sans-serif",
          color: '#333',
        }}
      >
        Analysis
      </Typography>

      <Box sx={{ mb: '100px' }}>
        <Step_settings />
      </Box>

      {/* ✅ Genome build selector */}
      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px', mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px' }}>
              Genome build
            </Typography>
          </Grid>
          <Grid item xs={12} md={8}>
            <ToggleButtonGroup
              value={genomeBuild}
              exclusive
              onChange={handleGenomeBuildChange}
              sx={{ mt: 1 }}
            >
              <ToggleButton value="hg19" sx={{ fontSize: '20px', px: 3 }}>
                hg19
              </ToggleButton>
              <ToggleButton value="hg38" sx={{ fontSize: '20px', px: 3 }}>
                hg38
              </ToggleButton>
            </ToggleButtonGroup>
          </Grid>
        </Grid>
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
                sx={{ '& .MuiFormControlLabel-label': { fontSize: '22px' } }}
              />
              <FormControlLabel
                value="Use_only_PASS_variants"
                control={<Radio />}
                label="Use only PASS variants"
                sx={{ '& .MuiFormControlLabel-label': { fontSize: '22px' } }}
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
              InputProps={{ sx: { fontSize: '22px' } }}
              InputLabelProps={{ sx: { fontSize: '22px' } }}
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
              InputProps={{ sx: { fontSize: '22px' } }}
              InputLabelProps={{ sx: { fontSize: '22px' } }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            {/* 你原本 configName 的 UI 註解掉，保持不動 */}
          </Grid>
        </Grid>
      </Box>

      <Divider sx={{ margin: '20px 0' }} />

      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px' }}>
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
              Retain variants with allele frequency (MAF) below:
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
              InputProps={{ sx: { fontSize: '22px' } }}
              InputLabelProps={{ sx: { fontSize: '22px' } }}
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
                  <Grid item xs={12} md={6}>
                    <Radio_change panel_auto_Info={panel_auto_Info} setPanelInfo={setPanelInfo} />
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
        <Backdrop sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }} open={loading}>
          <Loading show={loading} />
        </Backdrop>
      )}

      <Divider sx={{ margin: '20px 0' }} />

      <Box sx={{ textAlign: 'center', mt: 5 }}>
        <Button
          variant="outlined"
          href={config.rootPathPrefix + '/Analysis/Exome/Sample'}
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
            '&:hover': { bgcolor: '#1565c0' },
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

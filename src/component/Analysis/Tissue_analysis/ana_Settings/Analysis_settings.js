import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import Step_settings from '../../Step/Step_setting';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import { config } from '../../../../constant';
import Loading from '../../../Loading';
import Backdrop from '@mui/material/Backdrop';
import Analysis_settings_somatic_tab from './Analysis_settings_somatic_tag';
import Analysis_settings_germline_prediction_tab from './Analysis_settings_germline_prediction_tag';
import { Box, Typography, Grid, TextField, Button, RadioGroup, FormControlLabel, Radio } from '@mui/material';
import ErrorDialog from '../../../ErrorDialog';

function Analysis_settings() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [errorDialogOpen, setErrorDialogOpen] = useState(false);

  // Shared states
  const [alleleFrequencySomatic, setAlleleFrequencySomatic] = useState('0.01');
  const [diagnosis, setDiagnosis] = useState('');
  const [alleleFrequencyGermline, setAlleleFrequencyGermline] = useState('0.3');
  const [minDepthCutoff, setMinDepthCutoff] = useState('20');
  const [minAltAlleleFreq, setMinAltAlleleFreq] = useState('0.05');
  const [configName, setConfigName] = useState('default');
  const [genePanelsData, setGenePanelsData] = useState([{ panelName: '', genes: '' }]);
  const [panel_auto_Info, setPanelInfo] = useState({ panelName: '', genes: '' });

  // Record Germline Prediction toggle status
  const [isGermlineEnabled, setIsGermlineEnabled] = useState(true);

  // Tab state
  const [selectedTab, setSelectedTab] = useState(0);

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };
  const handleMinDepthCutoffChange = (event) => setMinDepthCutoff(event.target.value);
  const handleMinAltAlleleFreqChange = (event) => setMinAltAlleleFreq(event.target.value);
  const handleConfigNameChange = (event) => setConfigName(event.target.value);

  const handleSaveButtonClick = (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');

    let hasEmptyGenePanel = false;
    genePanelsData.forEach((panel, index) => {
      const warningElement = document.getElementById(`warning${index}`); // 修正：加上反引號
      if ((panel.panelName || '').trim() === '' || (panel.genes || '').trim() === '') {
        hasEmptyGenePanel = true;
        if (warningElement) warningElement.classList.remove('hidden');
      } else {
        if (warningElement) warningElement.classList.add('hidden');
      }
    });

    // Validation（維持你原本的規則）
    if (alleleFrequencySomatic.trim() === '' && hasEmptyGenePanel) {
      setError('Allele frequency and Gene panels are required');
      setErrorDialogOpen(true);
      setLoading(false);
      return;
    } else if (alleleFrequencySomatic.trim() === '') {
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

    // Prepare data to send
    const genePanelList = genePanelsData.map(panel => ({
      panelName: panel.panelName,
      genePanel: panel.genes
    }));
    const jsonStr = { GenePanelList: genePanelList };

    const diagnosisString = typeof diagnosis === 'string' ? diagnosis : (diagnosis?.label || '');
    console.log('送出的 diagnosis 字串為:', diagnosisString);

    const payload = {
      maf_cutoff: alleleFrequencySomatic,
      maf_cutoff_germline: alleleFrequencyGermline,
      min_dp_cutoff: minDepthCutoff,
      min_aaf: minAltAlleleFreq,
      configName: configName,
      genePanelList: jsonStr,
      diagnosis: diagnosisString,
    };

    // --- Fire-and-forget + keepalive：允許在跳頁時送出 ---
    fetch(`${config.rootApiIP}/vep_test_page4`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true,            // 這行是關鍵
    }).catch((err) => {
      // 即使失敗也不阻擋跳轉；僅在開發時記錄
      console.error('POST /vep_test_page4 failed (ignored due to immediate redirect):', err);
    }).finally(() => {
      setLoading(false);
    });

    // 立刻跳轉（不等待回應）
    window.location.href = `${config.rootPathPrefix}/Job_results`;
  };

  useEffect(() => {
    console.log("Shared state changed:", {
      alleleFrequencySomatic,
      alleleFrequencyGermline,
      minDepthCutoff,
      minAltAlleleFreq,
      configName,
      genePanelsData,
      isGermlineEnabled,
      diagnosis,
    });
  }, [alleleFrequencyGermline, alleleFrequencySomatic, minDepthCutoff, minAltAlleleFreq, configName, genePanelsData, isGermlineEnabled, diagnosis]);

  const handleCloseErrorDialog = () => {
    setErrorDialogOpen(false);
  };

  return (
    <Box sx={{ p: { xs: 2, md: 4 }, minHeight: '100vh', mb: 10, maxWidth: 1280, mx: 'auto' }}>
      {/* Title */}
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

      {/* Step Settings */}
      <Box sx={{ mb: '100px' }}>
        <Step_settings />
      </Box>

      {/* Variant Filtering */}
      <Box sx={{ padding: '20px', backgroundColor: '#F2F9FF', borderRadius: '8px', mb: 6 }}>
        <Grid container spacing={4}>
          <Grid item xs={12}>
            <Typography sx={{ fontWeight: 'bold', fontSize: '30px', mb: 1 }}>
              Variant Quality Control
            </Typography>
          </Grid>

          {/* 第一列：Filter Radio */}
          <Grid item xs={12} md={6}>
            <RadioGroup
              row
              aria-labelledby="filtering-radio-group"
              name="filtering-radio-group"
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

          {/* 第一列右側空白 */}
          <Grid item xs={12} md={6}></Grid>

          {/* 第二列：左右輸入框同一排 */}
          <Grid item xs={12} md={6}>
            <label style={{ fontSize: '24px' }}>
              Retain variants with allele frequency greater than:
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
            />
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
            />
          </Grid>
        </Grid>
      </Box>

      {/* Tabs */}
      <Box sx={{ border: '5px solid #ccc', borderRadius: '8px', p: 3, mb: 3 }}>
        <Tabs value={selectedTab} onChange={handleTabChange} sx={{ mb: 3 }}>
          <Tab label="Somatic" sx={{ fontSize: '1.3rem', fontWeight: 'bold' }} />
          <Tab label="Germline Prediction" sx={{ fontSize: '1.3rem', fontWeight: 'bold' }} />
        </Tabs>

        {selectedTab === 0 && (
          <Box sx={{ mt: 3 }}>
            <Analysis_settings_somatic_tab
              alleleFrequency={alleleFrequencySomatic}
              setAlleleFrequency={setAlleleFrequencySomatic}
              diagnosis={diagnosis}
              setDiagnosis={setDiagnosis}
            />
          </Box>
        )}

        {selectedTab === 1 && (
          <Box sx={{ mt: 3 }}>
            <Analysis_settings_germline_prediction_tab
              alleleFrequency={alleleFrequencyGermline}
              setAlleleFrequency={setAlleleFrequencyGermline}
              genePanelsData={genePanelsData}
              setGenePanelsData={setGenePanelsData}
              panel_auto_Info={panel_auto_Info}
              setPanelInfo={setPanelInfo}
              isGermlineEnabled={isGermlineEnabled}
              setIsGermlineEnabled={setIsGermlineEnabled}
            />
          </Box>
        )}
      </Box>

      {/* Error Dialog */}
      <ErrorDialog
        open={errorDialogOpen}
        onClose={handleCloseErrorDialog}
        errorMessage={error}
      />

      {/* Buttons */}
      <Box sx={{ textAlign: 'center', mt: 5 }}>
        <Button
          variant="outlined"
          href={`${config.rootPathPrefix}/Analysis/Tissue/Sample`}  // 修正模板字串
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
          onClick={handleSaveButtonClick}
          sx={{
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

      {loading && (
        <Backdrop
          sx={{ color: '#fff', zIndex: (theme) => theme.zIndex.drawer + 1 }}
          open={loading}
        >
          <Loading show={loading} />
        </Backdrop>
      )}
    </Box>
  );
}

export default Analysis_settings;

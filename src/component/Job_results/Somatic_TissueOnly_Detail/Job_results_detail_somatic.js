import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { config } from '../../../constant.js'

import Box from '@mui/material/Box';
import Tab from '@mui/material/Tab';
import TabContext from '@mui/lab/TabContext';
import TabList from '@mui/lab/TabList';
import TabPanel from '@mui/lab/TabPanel';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import CircularProgress from '@mui/material/CircularProgress';
import { styled } from '@mui/material/styles';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';

import Actionable_data from './Actionable_data.js';
import Heredity_data from './Heredity_data.js'
import GermlinePrediction_data from './GermlinePrediction_data.js'
import Cosmic_data from './Cosmic_data.js';
import Prediction_data from './Prediction_data.js'
import MultipleSNP_Actionable_data from './MultipleSNP_Actionable_data.js'
import MultipleSNP_Civic_data from './MultipleSNP_Civic_data.js'
import Mutation_signature from './Mutation_signature.js'
import Fusion_gene from './Fusion_Gene.js'
import Potential_Treatment_Bar from './Potential_Treatment_Bar.js'
import Pathway from './Pathway_viewer.js'
import Cancer_Type_Prediction from './Cancer_Type_Prediction.js'
import WgsResultTable from '../WGS_Germline_Detail/WgsResultTable.js'
import LegacyMtbDraftReport from './LegacyMtbDraftReport.js'

const Item = styled(Paper)(({ theme }) => ({
  backgroundColor: '#C0C0C0',
  ...theme.typography.body2,
  padding: theme.spacing(1),
  textAlign: 'center',
  color: theme.palette.text.secondary,
  width: '170px',
  height: '95px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '19px',
  ...theme.applyStyles?.('dark', {
    backgroundColor: '#1A2027',
  }),
}));

function DirectionStack({ totalSelectedCount }) {
  return (
    <div>
      <Stack direction="row" spacing={2} >
        <Item>Total Selected: {totalSelectedCount}</Item>
      </Stack>
    </div>
  );
}

function ResultMetric({ label, value, tone = 'primary' }) {
  return (
    <Paper variant="outlined" sx={{ p: 2.25, height: '100%', borderTop: 4, borderTopColor: `${tone}.main` }}>
      <Typography color="text.secondary" variant="body2" fontWeight={700}>{label}</Typography>
      <Typography variant="h4" fontWeight={850} sx={{ mt: .5 }}>{value ?? '—'}</Typography>
    </Paper>
  );
}

function Job_results_detail_somatic() {
  const [valueOUT, setValueOUT] = React.useState('1');
  const [valueIN1, setValueIN1] = React.useState('1');
  const [valueIN2, setValueIN2] = React.useState('1');

  const handleChangeOUT = (event, newValue) => setValueOUT(newValue);
  const handleChangeIN1 = (event, newValue) => setValueIN1(newValue);
  const handleChangeIN2 = (event, newValue) => setValueIN2(newValue);

  const [selectedTotal, setSelectedTotal] = useState(0);

  const [SomaticDetailData, SetSomaticDetailData] = useState([]);
  const [HeredityData, SetHeredityData] = useState([]);
  const [GermlinePredictionData, SetGermlinePredictionData] = useState([]);
  const [CosmicData, SetCosmicData] = useState([]);
  const [PredictionData, SetPredictionData] = useState([]);
  const [OncogenicityData, SetOncogenicityData] = useState([]);
  const [oncogenicitySummary, setOncogenicitySummary] = useState(null);
  const [oncogenicityError, setOncogenicityError] = useState('');
  const [MultipleSNPActionableData, SetMultipleSNPActionableData] = useState([]);
  const [MultipleSNPCivicData, SetMultipleSNPCivicData] = useState([]);

  const [selectedSomaticdata, setSelectedSomaticdata] = useState([]);
  const [selectedReadHeredity, setSelectedReadHeredity] = useState([]);
  const [selectedGermlinePredictionData, setSelectedGermlinePredictionData] = useState([]);
  const [selectedCosmicData, setSelectedCosmicData] = useState([]);
  const [selectedPredictionData, setSelectedPredictionData] = useState([]);
  const [selectedMultipleSNPActionableData, setSelectedMultipleSNPActionableData] = useState([]);
  const [selectedMultipleSNPCivicData, setSelectedMultipleSNPCivicData] = useState([]);

  const [selectedSomaticdataRowsid, setSelectedSomaticdataRowsid] = useState([]);
  const [selectedReadHeredityRowsid, setSelectedReadHeredityRowsid] = useState([]);
  const [selectedGermlinePredictionDataRowsid, setSelectedGermlinePredictionDataRowsid] = useState([]);
  const [selectedCosmicDataRowsid, setSelectedCosmicDataRowsid] = useState([]);
  const [selectedPredictionDataRowsid, setSelectedPredictionDataRowsid] = useState([]);
  const [selectedMultipleSNPActionableDataRowsid, setSelectedMultipleSNPActionableDataRowsid] = useState([]);
  const [selectedMultipleSNPCivicDataRowsid, setselectedMultipleSNPCivicDataRowsid] = useState([]);

  const [loading, setLoading] = useState(true);

  const pathnameParts = window.location.pathname.split('/');
  const newJobID = pathnameParts[4];
  const goToMutationSignature = () => {
    setValueOUT("3"); // 外層 Tab value="3" 就是 Mutation Signature
  };
  // 送選取到後端產生 summary
  const handleSaveToReport = async () => {
    try {
      let allData = [];
      const processData = (data, tableName) => data.map(item => ({ table_name: tableName, ...item }));

      if (selectedSomaticdata.length > 0) {
        allData = [...allData, ...processData(selectedSomaticdata, 'single_snp_actionable')];
      }
      if (selectedReadHeredity.length > 0) {
        allData = [...allData, ...processData(selectedReadHeredity, 'single_snp_heredity')]; // 拼字修正
      }
      if (selectedGermlinePredictionData.length > 0) {
        allData = [...allData, ...processData(selectedGermlinePredictionData, 'single_snp_germline_prediction')];
      }
      if (selectedCosmicData.length > 0) {
        allData = [...allData, ...processData(selectedCosmicData, 'single_snp_cosmic')];
      }
      if (selectedPredictionData.length > 0) {
        allData = [...allData, ...processData(selectedPredictionData, 'single_snp_prediction')];
      }

      if (allData.length === 0) {
        console.log('沒有資料需要保存');
        return;
      }

      const jobId = window.location.pathname.split('/')[4];
      const response = await axios.post(`${config.rootApiIP}/get_summary_info_somatic`, {
        newJobID: jobId,
        dataframe: allData
      });
      console.log('API 回應:', response.data);
    } catch (error) {
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
    } finally {
      const currentUrl = window.location.href;
      const analysisIdFromUrl = currentUrl.split('/').pop();
      window.location.href = config.rootPathPrefix + `/Job_results/detail/${analysisIdFromUrl}/summary_report_somatic`;
    }
  };

  // 計算已勾選筆數
  useEffect(() => {
    const totalSelectedCount =
      selectedSomaticdata.length +
      selectedReadHeredity.length +
      selectedGermlinePredictionData.length +
      selectedCosmicData.length +
      selectedPredictionData.length;
    setSelectedTotal(totalSelectedCount);
  }, [
    selectedSomaticdata,
    selectedReadHeredity,
    selectedGermlinePredictionData,
    selectedCosmicData,
    selectedPredictionData
  ]);

  // =========================
  // 通用解析與容錯工具（重要）
  // =========================

  // 安全取得資料陣列：成功回傳 data.data，否則回 []
  const extractData = (resp) => {
    if (!resp || !resp.data) return [];
    if (resp.data.status === 'error') {
      console.warn('Endpoint error:', resp.data.message);
      return [];
    }
    return Array.isArray(resp.data.data) ? resp.data.data : [];
  };

  // 正規化 Python 風味 JSON 字串 → 可 JSON.parse 的字串
  const toJsonString = (val) => {
    if (val == null) return null;
    if (typeof val === 'object') return JSON.stringify(val);
    if (typeof val !== 'string') return String(val);

    let s = val;

    // Python 的 None/True/False → JS 的 null/true/false
    s = s.replace(/\bNone\b/g, 'null')
         .replace(/\bTrue\b/g, 'true')
         .replace(/\bFalse\b/g, 'false');

    // 將 key 的單引號轉雙引號： { 'key': ... } 或 , 'key':
    s = s.replace(/([{,]\s*)'([^']+)'\s*:/g, '$1"$2":');

    // 將 value 的單引號字串轉雙引號： : 'text'
    s = s.replace(/:\s*'([^']*)'/g, ': "$1"');

    return s;
  };

  const safeParseObject = (val, fallback = {}) => {
    if (val == null) return fallback;
    if (typeof val === 'object' && !Array.isArray(val)) return val;
    if (typeof val === 'string') {
      const s = toJsonString(val);
      if (s == null) return fallback;
      try {
        const obj = JSON.parse(s);
        return (obj && typeof obj === 'object' && !Array.isArray(obj)) ? obj : fallback;
      } catch (e) {
        console.error('safeParseObject failed:', e, 'value=', val);
        return fallback;
      }
    }
    return fallback;
  };

  const safeParseArray = (val, fallback = []) => {
    if (val == null) return fallback;
    if (Array.isArray(val)) return val;
    if (typeof val === 'string') {
      const s = toJsonString(val);
      if (s == null) return fallback;
      try {
        const arr = JSON.parse(s);
        return Array.isArray(arr) ? arr : fallback;
      } catch (e) {
        console.error('safeParseArray failed:', e, 'value=', val);
        return fallback;
      }
    }
    return fallback;
  };

  // 專門處理 Availability：確保每個元素都有 Description 欄位
  const parseAvailability = (val) => {
    const arr = safeParseArray(val, []);
    return arr.map((item) => {
      if (item && typeof item === 'object') {
        const desc = item.Description ?? '';
        return { ...item, Description: desc };
      }
      return item;
    });
  };

  // 物件印成多行 "key: value"
  const objectToMultiline = (obj) => {
    if (obj == null) return '';
    if (typeof obj !== 'object') return String(obj);
    return Object.entries(obj)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n');
  };

  // 兼容不同 RSID 欄位名稱
  const getRSID = (item) => item?.['RS ID'] ?? item?.['RS_ID'] ?? item?.RSID ?? '';

  // =========================
  // 各資料表格式化器（重寫）
  // =========================
  const formatSomaticData = (data = []) =>
    (Array.isArray(data) ? data : []).map((item, index) => {
      const parsedMAF           = safeParseObject(item?.MAF, {});
      const parsedPathogenicity = safeParseObject(item?.Pathogenicity, {});
      const parsedPrediction    = safeParseObject(item?.Prediction, {});
      const availabilityArr     = parseAvailability(item?.Avalibility ?? item?.Availability);

      return {
        id: index + 1,
        Location: item?.Location ?? '',
        Gene: item?.Gene ?? '',
        RSID: getRSID(item),
        MAF: objectToMultiline(parsedMAF),
        Domain: item?.Domain ?? '',
        Prediction: objectToMultiline(parsedPrediction),
        Pathogenicity: objectToMultiline(parsedPathogenicity),
        Match: item?.Match ?? '',
        AminoAcidChange: (item?.Gene ?? '') + '   ' + (item?.['Amino acid change'] ?? ''),
        Avalibility: availabilityArr.map(av => `${av?.Tier ?? ''},  ${av?.Drug ?? ''},  ${av?.Database ?? ''},  ${av?.Count ?? ''}`),
        AvalibilityDescription: availabilityArr.map(av => {
          const d = av?.Description;
          return `Description: ${typeof d === 'object' ? JSON.stringify(d) : (d ?? '')}`;
        }),
      };
    });

  const formatData = (data = []) =>
    (Array.isArray(data) ? data : []).map((item, index) => {
      const parsedMAF           = safeParseObject(item?.MAF, {});
      const parsedPathogenicity = safeParseObject(item?.Pathogenicity, {});
      const parsedPrediction    = safeParseObject(item?.Prediction, {});
      return {
        id: index + 1,
        Location: item?.Location ?? '',
        Gene: item?.Gene ?? '',
        RSID: getRSID(item),
        MAF: objectToMultiline(parsedMAF),
        Domain: item?.Domain ?? '',
        Prediction: objectToMultiline(parsedPrediction),
        Pathogenicity: objectToMultiline(parsedPathogenicity),
        AminoAcidChange: item?.['Amino acid change'] ?? '',
      };
    });

  const formatMultipleSNPActionableData = (data = []) =>
    (Array.isArray(data) ? data : []).map((item, index) => {
      const parsedMAF        = safeParseObject(item?.MAF, {});
      const parsedPrediction = safeParseObject(item?.Prediction, {});
      return {
        id: index + 1,
        Location: item?.Location ?? '',
        DetailedLocation: item?.Detailed_Location ?? '',
        Gene: item?.Gene ?? '',
        RSID: getRSID(item),
        MAF: objectToMultiline(parsedMAF),
        Domain: item?.Domain ?? '',
        Prediction: objectToMultiline(parsedPrediction),
        Pathogenicity: item?.Pathogenicity ?? '',
        DRUGCOMBINATION: item?.DRUG_COMBINATION ?? '',
        Phenotype: item?.Phenotype ?? '',
        CosmicPreprocessor: item?.cosmic_preprocessor ?? '',
      };
    });

  const formatMultipleSNPCivicData = (data = []) =>
    (Array.isArray(data) ? data : []).map((item, index) => {
      const parsedMAF        = safeParseObject(item?.MAF, {});
      const parsedPrediction = safeParseObject(item?.Prediction, {});
      return {
        id: index + 1,
        Location: item?.Location ?? '',
        DetailedLocation: item?.Detailed_Location ?? '',
        Gene: item?.Gene ?? '',
        RSID: getRSID(item),
        MAF: objectToMultiline(parsedMAF),
        Domain: item?.Domain ?? '',
        Prediction: objectToMultiline(parsedPrediction),
        Pathogenicity: item?.Pathogenicity ?? '',
        Phenotype: item?.Phenotype ?? '',
        Therapies: item?.Therapies ?? '',
        CivicVariantName: item?.civic_variant_name ?? '',
      };
    });

  // 取資料
  useEffect(() => {
    const fetchAllData = async () => {
      try {
        setLoading(true);
        const jobId = window.location.pathname.split('/').pop();

        const somatic_response = await axios
          .post(`${config.rootApiIP}/somatic_result`, { newjobid: jobId })
          .catch((error) => {
            console.error('Somatic API error:', error);
            return { data: { data: [] } };
          });

        const oncogenicity_response = await axios
          .post(`${config.rootApiIP}/wgs-somatic/legacy-oncogenicity`, { newjobid: jobId })
          .catch((error) => {
            console.error('Oncogenicity API error:', error);
            setOncogenicityError(error.response?.data?.detail || 'Unable to calculate oncogenicity.');
            return { data: { data: [], summary: null } };
          });

        const heredity_response = await axios
          .post(`${config.rootApiIP}/read_heredity`, { newjobid: jobId })
          .catch((error) => {
            console.error('Heredity API error:', error);
            return { data: { data: [] } };
          });

        const germlinePrediction_response = await axios
          .post(`${config.rootApiIP}/read_germline_prediction`, { newjobid: jobId })
          .catch((error) => {
            console.error('Germline Prediction API error:', error);
            return { data: { data: [] } };
          });

        const cosmic_response = await axios
          .post(`${config.rootApiIP}/read_cosmic`, { newjobid: jobId })
          .catch((error) => {
            console.error('Cosmic API error:', error);
            return { data: { data: [] } };
          });

        const prediction_response = await axios
          .post(`${config.rootApiIP}/read_suspect`, { newjobid: jobId })
          .catch((error) => {
            console.error('Prediction API error:', error);
            return { data: { data: [] } };
          });

        const multipleSNPActionable_response = await axios
          .post(`${config.rootApiIP}/analysis_cosmic`, { newjobid: jobId })
          .catch((error) => {
            console.error('MultipleSNPActionable API error:', error);
            return { data: { data: [] } };
          });

        const multipleSNPCivic_response = await axios
          .post(`${config.rootApiIP}/mutisnp_civic`, { newjobid: jobId })
          .catch((error) => {
            console.error('MultipleSNPCivic API error:', error);
            return { data: [] };
          });

        // 兼容某些 endpoint 回傳結構
        const somaticData = extractData(somatic_response);
        const heredityData = extractData(heredity_response);
        const germlinePredictionData = extractData(germlinePrediction_response);
        const cosmicData = extractData(cosmic_response);
        const predictionData = extractData(prediction_response);
        const multiActionableData = extractData(multipleSNPActionable_response);

        // /mutisnp_civic 可能直接回 array 或 {data:{data:[]}}
        const multiCivicData = Array.isArray(multipleSNPCivic_response?.data)
          ? multipleSNPCivic_response.data
          : extractData(multipleSNPCivic_response);

        SetSomaticDetailData(formatSomaticData(somaticData));
        SetHeredityData(formatData(heredityData));
        SetGermlinePredictionData(formatData(germlinePredictionData));
        SetCosmicData(formatData(cosmicData));
        SetPredictionData(formatData(predictionData));
        SetOncogenicityData(Array.isArray(oncogenicity_response?.data?.data) ? oncogenicity_response.data.data : []);
        setOncogenicitySummary(oncogenicity_response?.data?.summary || null);
        SetMultipleSNPActionableData(formatMultipleSNPActionableData(multiActionableData));
        SetMultipleSNPCivicData(formatMultipleSNPCivicData(multiCivicData));
      } catch (error) {
        console.error('請求錯誤：', error);
      } finally {
        setLoading(false);
      }
    };
    fetchAllData();
  }, []);

  return (
    <Box className="analysis-result-page" sx={{ p: { xs: 2, md: 4 }, maxWidth: 1600, mx: 'auto', bgcolor: '#f5f8fb', minHeight: '100vh' }}>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} alignItems={{ md: 'center' }}>
            <Box>
              <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap', gap: .5 }}>
                <Chip label="TUMOR-ONLY" color="warning" />
                <Chip label="GRCh37 / hg19" variant="outlined" />
                <Chip label="PANEL" color="primary" variant="outlined" />
              </Stack>
              <Typography variant="h3" fontWeight={850}>Tumor-only report</Typography>
              <Typography color="text.secondary">Legacy tumor-only analysis presented in the unified MTB result framework.</Typography>
            </Box>
            <Paper variant="outlined" sx={{ p: 2, minWidth: 300 }}>
              <Typography fontWeight={800}>{newJobID}</Typography>
              <Typography variant="body2" color="text.secondary">Analysis {newJobID}</Typography>
              <Chip size="small" sx={{ mt: 1 }} label="RESULT AVAILABLE" color="success" />
            </Paper>
          </Stack>

          <Alert severity="warning" sx={{ my: 3 }}>
            This is a GRCh37/hg19 tumor-only interpretation without liftover. Somatic origin and possible germline findings require confirmation with matched normal testing.
          </Alert>

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={6} md={3}><ResultMetric label="Actionable candidates" value={SomaticDetailData.length} tone="success" /></Grid>
            <Grid item xs={6} md={3}><ResultMetric label="High-risk candidates" value={oncogenicitySummary?.high_risk ?? OncogenicityData.length} tone="error" /></Grid>
            <Grid item xs={6} md={3}><ResultMetric label="Hereditary candidates" value={HeredityData.length} tone="warning" /></Grid>
            <Grid item xs={6} md={3}><ResultMetric label="Selected for report" value={selectedTotal} /></Grid>
          </Grid>

          <Stack className="analysis-result-actions" spacing={2} direction={{ xs: 'column', sm: 'row' }} sx={{ mb: 3 }}>
              <Button
                variant="contained"
                onClick={handleSaveToReport}
                sx={{ minWidth: 160 }}
              >
                Preview Summary
              </Button>
              <DirectionStack totalSelectedCount={selectedTotal} />
              <Button
                variant="contained"
                sx={{
                  width: '75px',
                  backgroundColor: 'Crimson',
                  '&:hover': { backgroundColor: 'darkred' },
                }}
              >
                QC Report
              </Button>
          </Stack>

          <Paper className="analysis-result-panel" sx={{ overflow: 'hidden', border: '1px solid #dbe6ee', mb: 10 }}>
            <Box sx={{ width: '100%', typography: 'body1' }}>
              <TabContext value={valueOUT}>
                <Box sx={{ borderBottom: '1px solid #dbe6ee', bgcolor: '#fff', px: 1 }}>
                  <TabList onChange={handleChangeOUT} aria-label="Tumor-only result sections" variant="scrollable" scrollButtons="auto">
                    <Tab label="single snp" value="1" />
                    <Tab label="Multiple-SNP Combination" value="2" />
                    <Tab label="Mutation Signature" value="3" />
                    <Tab label="Fusion Gene Prediction" value="4" />
                    <Tab label="Potential Treatment from Guideline" value="5" />
                    <Tab label="Cancer Type Prediction" value="6" />
                    <Tab label="Pathway Viewer" value="7" />
                    <Tab label="MTB Draft Report" value="8" sx={{ mx: .75, my: .75, minHeight: 42, borderRadius: 1.5, fontWeight: 850, bgcolor: '#fff0c2', color: '#7a4b00', '&:hover': { bgcolor: '#ffe49a' }, '&.Mui-selected': { bgcolor: '#f59e0b', color: '#fff' } }} />
                  </TabList>
                </Box>

                {/* 外層 1 */}
                <TabPanel value="1">
                  <TabContext value={valueIN1}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                      <TabList
                        onChange={handleChangeIN1}
                        centered
                        aria-label="secondary tabs example"
                        textColor="secondary"
                        indicatorColor="secondary"
                      >
                        <Tab label="actionable" value="1" />
                        <Tab label="heredity" value="2" />
                        <Tab label="Germline Prediction" value="3" />
                        <Tab label="Somatic" value="4" />
                        <Tab label="prediction" value="5" />
                        <Tab label="High Risk / Oncogenicity" value="6" />
                      </TabList>
                    </Box>
                    <TabPanel value="1">
                      <Actionable_data
                        data={SomaticDetailData}
                        onSelectionChange={setSelectedSomaticdata}
                        rowSelectionModel={selectedSomaticdataRowsid}
                        setrowSelectionModel={setSelectedSomaticdataRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="2">
                      <Heredity_data
                        data={HeredityData}
                        onSelectionChange={setSelectedReadHeredity}
                        rowSelectionModel={selectedReadHeredityRowsid}
                        setrowSelectionModel={setSelectedReadHeredityRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="3">
                      <GermlinePrediction_data
                        data={GermlinePredictionData}
                        onSelectionChange={setSelectedGermlinePredictionData}
                        rowSelectionModel={selectedGermlinePredictionDataRowsid}
                        setrowSelectionModel={setSelectedGermlinePredictionDataRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="4">
                      <Cosmic_data
                        data={CosmicData}
                        onSelectionChange={setSelectedCosmicData}
                        rowSelectionModel={selectedCosmicDataRowsid}
                        setrowSelectionModel={setSelectedCosmicDataRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="5">
                      <Prediction_data
                        data={PredictionData}
                        onSelectionChange={setSelectedPredictionData}
                        rowSelectionModel={selectedPredictionDataRowsid}
                        setrowSelectionModel={setSelectedPredictionDataRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="6">
                      <Alert severity="warning" sx={{ mb: 2 }}>
                        Legacy Tumor-Only uses GRCh37/hg19 gene/protein annotations without liftover. High risk follows the WGS core gate: non-synonymous AND (ClinVar P/LP OR oncogenicity O/LO). Every record requires manual review.
                        {oncogenicitySummary ? ` Profile: ${oncogenicitySummary.profile}; candidates: ${oncogenicitySummary.variants}; high risk: ${oncogenicitySummary.high_risk ?? 0}.` : ''}
                      </Alert>
                      <WgsResultTable
                        rows={OncogenicityData}
                        error={oncogenicityError}
                        emptyMessage="No variants were available for oncogenicity annotation."
                      />
                    </TabPanel>
                  </TabContext>
                </TabPanel>

                {/* 外層 2 */}
                <TabPanel value="2">
                  <TabContext value={valueIN2}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                      <TabList
                        onChange={handleChangeIN2}
                        centered
                        aria-label="secondary tabs example"
                        textColor="secondary"
                        indicatorColor="secondary"
                      >
                        <Tab label="cosmic" value="1" />
                        <Tab label="civic" value="2" />
                      </TabList>
                    </Box>
                    <TabPanel value="1">
                      <MultipleSNP_Actionable_data
                        data={MultipleSNPActionableData}
                        onSelectionChange={setSelectedMultipleSNPActionableData}
                        rowSelectionModel={selectedMultipleSNPActionableDataRowsid}
                        setrowSelectionModel={setSelectedMultipleSNPActionableDataRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="2">
                      <MultipleSNP_Civic_data
                        data={MultipleSNPCivicData}
                        onSelectionChange={setSelectedMultipleSNPCivicData}
                        rowSelectionModel={selectedMultipleSNPCivicDataRowsid}
                        setrowSelectionModel={setselectedMultipleSNPCivicDataRowsid}
                      />
                    </TabPanel>
                  </TabContext>
                </TabPanel>

                {/* 外層 3 */}
                <TabPanel value="3">
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Mutation_signature />
                  </Box>
                </TabPanel>

                {/* 外層 4 */}
                <TabPanel value="4">
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Fusion_gene />
                  </Box>
                </TabPanel>

                {/* 外層 5 */}
                <TabPanel value="5">
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Potential_Treatment_Bar />
                  </Box>
                </TabPanel>

                <TabPanel value="6">
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Cancer_Type_Prediction onGoMutSig={goToMutationSignature} />

                  </Box>
                </TabPanel>

                <TabPanel value="7">
                  <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                    <Pathway />
                  </Box>
                </TabPanel>
                <TabPanel value="8">
                  <LegacyMtbDraftReport analysisId={newJobID} />
                </TabPanel>
              </TabContext>
            </Box>
          </Paper>
        </>
      )}
    </Box>
  );
}

export default Job_results_detail_somatic;

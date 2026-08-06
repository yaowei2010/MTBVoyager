// Job_results_detail_hg38.js (patched)
// 重點修正：
// 1) knotannotsv_url 的 HTML 只在 newJobID 改變時下載一次（避免勾選就重抓）
// 2) formatData / formatDrugResponseData 全面防呆，避免 Object.entries(undefined) / map(undefined)
// 3) get_summary_info 統一送 newjobID（與其他 API 一致）
// 4) useEffect 內加入 cancelled 避免 race condition（頁面切換或 jobid 變更）
// 5) postMessage 增加 origin 檢查（需要依你的後端 domain 設定 expectedOrigin）

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import axios from 'axios';

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
import { config } from '../../../constant.js';

// components
import Germline_Exome_table from './Germline_Exome_table.js';
import Drug_Response from './Drug_Response.js';
// import Appendix_Data from './Appendix_Data.js';

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
  ...theme.applyStyles('dark', {
    backgroundColor: '#1A2027',
  }),
}));

function DirectionStack({ totalSelectedCount }) {
  return (
    <div>
      <Stack direction="row" spacing={2}>
        <Item>Total Selected: {totalSelectedCount}</Item>
      </Stack>
    </div>
  );
}

// --------- helpers ----------
const safeObj = (v) => (v && typeof v === 'object' && !Array.isArray(v) ? v : {});
const safeArr = (v) => (Array.isArray(v) ? v : []);
const entries = (v) => Object.entries(safeObj(v));

function Job_results_detail_hg38() {
  // --------------------- React State: 各表格資料 & 勾選狀態 ---------------------
  const [knownPathogenicData, setKnownPathogenicData] = useState([]);
  const [selectedKnownPathogenic, setSelectedKnownPathogenic] = useState([]);
  const [selectedKnownPathogenicRowsid, setSelectedKnownPathogenicRowsid] = useState([]);

  const [knownACMGData, setKnownACMGData] = useState([]);
  const [selectedKnownACMG, setSelectedKnownACMG] = useState([]);
  const [selectedKnownACMGRowsid, setSelectedKnownACMGRowsid] = useState([]);

  const [knownOtherData, setKnownOtherData] = useState([]);
  const [selectedKnownOther, setSelectedKnownOther] = useState([]);
  const [selectedKnownOtherRowsid, setSelectedKnownOtherRowsid] = useState([]);

  const [PredictedSuspectData, setPredictedSuspectData] = useState([]);
  const [selectedPredictedSuspect, setSelectedPredictedSuspect] = useState([]);
  const [selectedPredictedSuspectRowsid, setselectedPredictedSuspectRowsid] = useState([]);

  const [PredictedACMGData, setPredictedACMGData] = useState([]);
  const [selectedPredictedACMG, setSelectedPredictedACMG] = useState([]);
  const [selectedPredictedACMGRowsid, setselectedPredictedACMGRowsid] = useState([]);

  const [PredictedOtherData, setPredictedOtherData] = useState([]);
  const [selectedPredictedOther, setSelectedPredictedOther] = useState([]);
  const [selectedPredictedOtherRowsid, setselectedPredictedOtherRowsid] = useState([]);

  const [OtherVariantsData, setOtherVariantsData] = useState([]);
  const [selectedOtherVariants, setSelectedOtherVariants] = useState([]);
  const [selectedOtherVariantsRowsid, setSelectedOtherVariantsRowsid] = useState([]);

  const [DrugResponseData, setDrugResponseData] = useState([]);
  const [selectedDrugResponses, setSelectedDrugResponse] = useState([]);
  const [selectedDrugResponsesRowsid, setSelectedDrugResponseRowsid] = useState([]);

  // URL parsing（保留你的寫法，但加防呆）
  const pathnameParts = useMemo(() => window.location.pathname.split('/'), []);
  const newJobID = pathnameParts?.[4] || '';
  const currentJobType = pathnameParts?.[3]?.includes('germline') ? 'Germline' : 'Somatic';

  // --------------------- SV/CNV HTML 相關 ---------------------
  const [htmlContent, setHtmlContent] = useState('');
  const [checkedSVRows, setCheckedSVRows] = useState({});

  // --------------------- 其他 ---------------------
  const [selectedTotal, setSelectedTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const [value, setValue] = useState('1');
  const [valueKnown, setValueKnown] = useState('1');
  const [valuePredict, setValuePredict] = useState('1');

  const handleChange = (event, newValue) => setValue(newValue);
  const handleChangeKnown = (event, newValue) => setValueKnown(newValue);
  const handleChangePredict = (event, newValue) => setValuePredict(newValue);

  // --------------------- Summary 按鈕 ---------------------
  const handleSaveToReport = async () => {
    try {
      let allData = [];
      const processData = (data, tableName) =>
        safeArr(data).map((item) => ({
          table_name: tableName,
          ...item,
        }));

      if (selectedKnownPathogenic.length > 0) allData = allData.concat(processData(selectedKnownPathogenic, 'Known Pathogenic Pheno'));
      if (selectedKnownACMG.length > 0) allData = allData.concat(processData(selectedKnownACMG, 'Known Pathogenic ACMG'));
      if (selectedKnownOther.length > 0) allData = allData.concat(processData(selectedKnownOther, 'Known Pathogenic Other'));
      if (selectedPredictedSuspect.length > 0) allData = allData.concat(processData(selectedPredictedSuspect, 'Predicted Suspect Pheno'));
      if (selectedPredictedACMG.length > 0) allData = allData.concat(processData(selectedPredictedACMG, 'Predicted Suspect ACMG'));
      if (selectedPredictedOther.length > 0) allData = allData.concat(processData(selectedPredictedOther, 'Predicted Suspect Other'));
      if (selectedOtherVariants.length > 0) allData = allData.concat(processData(selectedOtherVariants, 'Other Variants'));
      if (selectedDrugResponses.length > 0) allData = allData.concat(processData(selectedDrugResponses, 'Drug Responses'));

      // SV/CNV 勾選（如你要也能送入 summary，這裡先保留 count-only；要送就自行展開 rowId）
      // const selectedSVCount = Object.values(checkedSVRows).filter(Boolean).length;

      if (allData.length === 0) return;

      // ✅ 統一用 newjobID（你其他 API 都這樣）
      await axios.post(`${config.rootApiIP}/get_summary_info`, {
        newjobID: newJobID,
        dataframe: allData,
      });
    } catch (error) {
      console.error('保存數據時出錯:', error);
      if (error.response) {
        console.error('回應數據:', error.response.data);
        console.error('回應狀態:', error.response.status);
      }
    } finally {
      const currentUrl = window.location.href;
      const analysisIdFromUrl = currentUrl.split('/').pop();
      window.location.href = config.rootPathPrefix + `/Job_results/detail/${analysisIdFromUrl}/summary_report_germline`;
    }
  };

  // =======================================================================================
  // ✅ knotannotsv HTML：只在 newJobID 改變時下載一次，不要綁 checkedSVRows
  // =======================================================================================
  useEffect(() => {
    if (!newJobID) return;

    let cancelled = false;

    (async () => {
      try {
        const response = await axios.post(`${config.rootApiIP}/knotannotsv_url`, { newjobID: newJobID });
        if (cancelled) return;

        const parser = new DOMParser();
        const doc = parser.parseFromString(response.data, 'text/html');

        // (a) 移除特定 style div（可選）
        doc.querySelectorAll('div').forEach((div) => {
          if (
            div.getAttribute('style') ===
            'width: 98%; margin: 10px 10px 10px 10px; text-align:right;display: inline-block'
          ) {
            div.remove();
          }
        });

        // (b) 修改 script 預設
        doc.querySelectorAll('script').forEach((scriptEl) => {
          let text = scriptEl.textContent || '';
          text = text.replace(/var\s+keyType\s*=\s*"3";/g, 'var keyType = "4";');
          text = text.replace(/var\s+keyAnnotID\s*=\s*"0";/g, 'var keyAnnotID = "1";');
          scriptEl.textContent = text;
        });

        // (c) thead 加 Select
        const headRow = doc.querySelector('#tabFULLSPLIT thead tr');
        if (headRow && !headRow.innerText.includes('Select')) {
          const th = doc.createElement('th');
          th.innerText = 'Select';
          headRow.insertBefore(th, headRow.firstChild);
        }

        // (d) tbody 插 checkbox（初次載入全部 unchecked）
        const rows = doc.querySelectorAll('#tabFULLSPLIT tbody tr');
        rows.forEach((tr, index) => {
          let rowId = tr.id;
          if (!rowId) {
            const tdWithDataSearch = tr.querySelector('[data-search]');
            rowId = tdWithDataSearch ? tdWithDataSearch.getAttribute('data-search') : `row_${index}`;
          }

          const td = doc.createElement('td');
          td.innerHTML = `
            <input
              type="checkbox"
              onchange="onCheckboxChange('${rowId}', this.checked)"
            />
          `;
          tr.insertBefore(td, tr.firstChild);
        });

        // (e) 注入 onCheckboxChange
        const customScript = doc.createElement('script');
        customScript.textContent = `
          function onCheckboxChange(rowId, checked) {
            window.parent.postMessage(
              { type: 'ROW_CHECKED_CHANGE', rowId: rowId, checked: checked },
              '*'
            );
          }
        `;
        doc.body.appendChild(customScript);

        setHtmlContent(doc.documentElement.outerHTML);
      } catch (e) {
        console.error('Error downloading HTML file:', e);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [newJobID]);

  // --------------------- 監聽 postMessage: row checkbox 改變 ---------------------
  useEffect(() => {
    // 你可以設定成你的後端 origin，例如：https://your-domain.com
    // 若你是同源、或 dev 會變，先用 config 解析成 origin
    let expectedOrigin = '';
    try {
      expectedOrigin = new URL(config.rootApiIP).origin;
    } catch {
      expectedOrigin = ''; // 無法解析就不檢查（建議你補好）
    }

    const handleMessage = (event) => {
      // ✅ origin 防護（若 expectedOrigin 設得出來才檢查）
      if (expectedOrigin && event.origin !== expectedOrigin) return;

      if (event.data?.type === 'ROW_CHECKED_CHANGE') {
        const { rowId, checked } = event.data || {};
        if (!rowId) return;
        setCheckedSVRows((prev) => ({ ...prev, [rowId]: !!checked }));
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // --------------------- 計算總勾選數量 ---------------------
  useEffect(() => {
    const selectedSVCount = Object.values(checkedSVRows).filter(Boolean).length;

    const totalSelectedCount =
      safeArr(selectedKnownPathogenic).length +
      safeArr(selectedKnownACMG).length +
      safeArr(selectedKnownOther).length +
      safeArr(selectedPredictedSuspect).length +
      safeArr(selectedPredictedACMG).length +
      safeArr(selectedPredictedOther).length +
      safeArr(selectedOtherVariants).length +
      safeArr(selectedDrugResponses).length +
      selectedSVCount;

    setSelectedTotal(totalSelectedCount);
  }, [
    selectedKnownPathogenic,
    selectedKnownACMG,
    selectedKnownOther,
    selectedPredictedSuspect,
    selectedPredictedACMG,
    selectedPredictedOther,
    selectedOtherVariants,
    selectedDrugResponses,
    checkedSVRows,
  ]);

  // --------------------- Step 3. 請求其他表格資料 ---------------------
  useEffect(() => {
    if (!newJobID) return;

    let cancelled = false;

    const fetchAllData = async () => {
      try {
        setLoading(true);

        const formatData = (data) =>
          safeArr(data).map((item, index) => {
            const maf = safeObj(item?.MAF);
            const gtVaf = safeObj(item?.['Genotype / VAF']);
            const evd = safeObj(item?.Evidence);
            const patho = safeObj(item?.Pathogenicity);
            const splice = safeObj(item?.['Splicing effect']);
            const omim = safeObj(item?.OMIM_number);

            return {
              id: index + 1,
              Location: item?.Location ?? '',
              Gene: item?.Gene ?? '',
              RSID: item?.['RS ID'] ?? '',
              MAF: entries(maf).map(([k, v]) => `${k}: ${v}`).join('\n'),
              GenotypeVAF: entries(gtVaf).map(([k, v]) => `${k}: ${v}`).join('\n'),
              Evidence: entries(evd).map(([k, v]) => `${k}: ${v}`).join('\n'),
              Domain: item?.Domain ?? '',
              Pathogenicity: entries(patho)
                .map(([key, value]) => {
                  if (key === 'Summary') {
                    const m = String(value || '').match(/\((\d+)\/\d+\)/);
                    const numerator = m ? m[1] : '0';
                    return `Summary: (${numerator}/8)`;
                  }
                  return `${key}: ${value ?? ''}`;
                })
                .join('\n'),
              SplicingEffect: entries(splice)
                .map(([key, value]) => {
                  if (key === 'Summary') {
                    const m = String(value || '').match(/\((\d+)\/\d+\)/);
                    const numerator = m ? m[1] : '0';
                    return `Summary: (${numerator}/3)`;
                  }
                  return `${key}: ${value ?? ''}`;
                })
                .join('\n'),
              OMIM: (() => {
                if (!omim || Object.keys(omim).length === 0) return '-';

                const omimID = omim.OMIM_number || '-';
                const rawPheno = String(omim.Phenotype || '');
                const matchFlag = omim['符合條件'] || '-';

                let phenoName = '';
                let phenoID = '';
                let inheritance = '';

                const matchFormat1 = rawPheno.match(/\{(.+?)\},?\s*(\d+)?(?:\s*\(\d+\))?\((\w+)\)?/);
                const matchFormat2 = rawPheno.match(/^(.+?),.+?,.+?,\s*(\d+)\s*\(\d+\)\((\w+)\)/);
                const matchFormat3 = rawPheno.match(/^(.+?),.*?,\s*(\d+)\s*\(\d+\)\((\w+)\)/);

                if (matchFormat1) {
                  phenoName = matchFormat1[1];
                  phenoID = matchFormat1[2] || '';
                  inheritance = matchFormat1[3] || '';
                } else if (matchFormat2) {
                  phenoName = matchFormat2[1];
                  phenoID = matchFormat2[2];
                  inheritance = matchFormat2[3];
                } else if (matchFormat3) {
                  phenoName = matchFormat3[1];
                  phenoID = matchFormat3[2];
                  inheritance = matchFormat3[3];
                }

                return `OMIM: ${omimID}\nPhenotype: ${phenoName} (${phenoID})\nInheritance: ${inheritance}\nMatch: ${matchFlag}`;
              })(),
              AmelieMaxScore: item?.['Amelie Max score'] ?? '',
              AmelieMeanScore: item?.['Amelie Mean score'] ?? '',
            };
          });

        const formatDrugResponseData = (data) =>
          safeArr(data).map((item, index) => ({
            id: index + 1,
            Location: item?.Location ?? '',
            Gene: item?.Gene ?? '',
            RSID: item?.['RS ID'] ?? '',
            Drugevidence: item?.['Drug evidence'] ?? '',
            Chemical: String(item?.Chemical ?? '').replace(/;/g, ';\n'),
            ClinVar: item?.ClinVar ?? '.',
          }));

        // 1) Known Pathogenic
        const knownPathogenicResponse = await axios.post(`${config.rootApiIP}/known_pathogenic_to_json`, { newjobID: newJobID });
        if (cancelled) return;
        setKnownPathogenicData(formatData(knownPathogenicResponse.data));

        // Incidental finding (ACMG / other)
        const incidental_finding = await axios.post(`${config.rootApiIP}/incidental_finding_variant`, { newjobID: newJobID });
        if (cancelled) return;
        setKnownACMGData(formatData(incidental_finding.data?.data1));
        setKnownOtherData(formatData(incidental_finding.data?.data2));

        // 2) Predicted Suspect
        const predictedSuspectResponse = await axios.post(`${config.rootApiIP}/predicted_suspect_variant`, { newjobID: newJobID });
        if (cancelled) return;
        setPredictedSuspectData(formatData(predictedSuspectResponse.data));

        const predictedACMGResponse = await axios.post(`${config.rootApiIP}/predicted_ACMG_variant`, { newjobID: newJobID });
        if (cancelled) return;
        setPredictedACMGData(formatData(predictedACMGResponse.data));

        const predictedOtherResponse = await axios.post(`${config.rootApiIP}/predicted_other_variant`, { newjobID: newJobID });
        if (cancelled) return;
        setPredictedOtherData(formatData(predictedOtherResponse.data));

        // 3) Other Variants
        const otherVariantsResponse = await axios.post(`${config.rootApiIP}/other_variant`, { newjobID: newJobID });
        if (cancelled) return;
        setOtherVariantsData(formatData(otherVariantsResponse.data));

        // 6) Drug Response
        const drugResponseResponse = await axios.post(`${config.rootApiIP}/drug_response_variant`, { newjobID: newJobID });
        if (cancelled) return;
        setDrugResponseData(formatDrugResponseData(drugResponseResponse.data?.data));

        setLoading(false);
      } catch (error) {
        console.error('請求錯誤：', error);
        setLoading(false);
      }
    };

    fetchAllData();

    return () => {
      cancelled = true;
    };
  }, [newJobID]);

  // --------------------- Render ---------------------
  return (
    <div style={{ marginRight: '80px' }}>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
          <CircularProgress />
        </Box>
      ) : (
        <>
          <div style={{ display: 'flex', marginTop: '15px' }}>
            <h1 style={{ display: 'flex', marginTop: '15px' }}>Results</h1>
            <Box
              sx={{
                marginTop: '5px',
                marginLeft: '40px',
                padding: '20px',
                border: '2px solid #1976d2',
                borderRadius: '12px',
                backgroundColor: '#f0f7ff',
                width: '900px',
                boxShadow: '0 4px 10px rgba(0, 0, 0, 0.1)',
              }}
            >
              <Grid container spacing={2}>
                <Grid item xs={6} sm={6} md={3}>
                  <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>
                    Current Job
                  </Typography>
                  <Typography variant="body1">{currentJobType}</Typography>
                </Grid>
                <Grid item xs={6} sm={6} md={3}>
                  <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>
                    Sample ID
                  </Typography>
                  <Typography variant="body1">{newJobID}</Typography>
                </Grid>
                <Grid item xs={6} sm={6} md={3}>
                  <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>
                    Syndrome
                  </Typography>
                  <Typography variant="body1">___________</Typography>
                </Grid>
                <Grid item xs={6} sm={6} md={3}>
                  <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>
                    Gene Panel
                  </Typography>
                  <Typography variant="body1">___________</Typography>
                </Grid>
              </Grid>
            </Box>
            <Stack spacing={2} direction="row" style={{ marginLeft: '20px' }}>
              <Button variant="contained" onClick={handleSaveToReport} sx={{ width: '110px' }}>
                Preview Summary
              </Button>
              <DirectionStack totalSelectedCount={selectedTotal} />
            </Stack>
          </div>

          <Paper elevation={3} style={{ padding: '20px', marginTop: '40px', marginBottom: '80px' }}>
            <Box sx={{ width: '100%', typography: 'body1' }}>
              <TabContext value={value}>
                <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                  <TabList onChange={handleChange} aria-label="lab API tabs example" centered>
                    <Tab label="Known Pathogenic" value="1" />
                    <Tab label="Predicted Suspect" value="2" />
                    <Tab label="Other Variants" value="3" />
                    <Tab label="Drug Response" value="6" />
                  </TabList>
                </Box>

                <TabPanel value="1">
                  <TabContext value={valueKnown}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                      <TabList onChange={handleChangeKnown} centered aria-label="secondary tabs example" textColor="secondary" indicatorColor="secondary">
                        <Tab label="pheno variants" value="1" />
                        <Tab label="acmg variants" value="2" />
                        <Tab label="other variants" value="3" />
                      </TabList>
                    </Box>
                    <TabPanel value="1">
                      <Germline_Exome_table
                        data={knownPathogenicData}
                        onSelectionChange={setSelectedKnownPathogenic}
                        rowSelectionModel={selectedKnownPathogenicRowsid}
                        setrowSelectionModel={setSelectedKnownPathogenicRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="2">
                      <Germline_Exome_table
                        data={knownACMGData}
                        onSelectionChange={setSelectedKnownACMG}
                        rowSelectionModel={selectedKnownACMGRowsid}
                        setrowSelectionModel={setSelectedKnownACMGRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="3">
                      <Germline_Exome_table
                        data={knownOtherData}
                        onSelectionChange={setSelectedKnownOther}
                        rowSelectionModel={selectedKnownOtherRowsid}
                        setrowSelectionModel={setSelectedKnownOtherRowsid}
                      />
                    </TabPanel>
                  </TabContext>
                </TabPanel>

                <TabPanel value="2">
                  <TabContext value={valuePredict}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                      <TabList onChange={handleChangePredict} centered aria-label="secondary tabs example" textColor="secondary" indicatorColor="secondary">
                        <Tab label="pheno variants" value="1" />
                        <Tab label="acmg variants" value="2" />
                        <Tab label="other variants" value="3" />
                      </TabList>
                    </Box>
                    <TabPanel value="1">
                      <Germline_Exome_table
                        data={PredictedSuspectData}
                        onSelectionChange={setSelectedPredictedSuspect}
                        rowSelectionModel={selectedPredictedSuspectRowsid}
                        setrowSelectionModel={setselectedPredictedSuspectRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="2">
                      <Germline_Exome_table
                        data={PredictedACMGData}
                        onSelectionChange={setSelectedPredictedACMG}
                        rowSelectionModel={selectedPredictedACMGRowsid}
                        setrowSelectionModel={setselectedPredictedACMGRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="3">
                      <Germline_Exome_table
                        data={PredictedOtherData}
                        onSelectionChange={setSelectedPredictedOther}
                        rowSelectionModel={selectedPredictedOtherRowsid}
                        setrowSelectionModel={setselectedPredictedOtherRowsid}
                      />
                    </TabPanel>
                  </TabContext>
                </TabPanel>

                <TabPanel value="3">
                  <Germline_Exome_table
                    data={OtherVariantsData}
                    onSelectionChange={setSelectedOtherVariants}
                    rowSelectionModel={selectedOtherVariantsRowsid}
                    setrowSelectionModel={setSelectedOtherVariantsRowsid}
                  />
                </TabPanel>

                <TabPanel value="6">
                  <Drug_Response
                    data={DrugResponseData}
                    onSelectionChange={setSelectedDrugResponse}
                    rowSelectionModel={selectedDrugResponsesRowsid}
                    setrowSelectionModel={setSelectedDrugResponseRowsid}
                  />
                </TabPanel>

                {/* 如果要顯示 SV/CNV HTML，把這段打開（建議用 iframe sandbox） */}
                {/* <TabPanel value="7">
                  <Appendix_Data htmlContent={htmlContent} />
                </TabPanel> */}
              </TabContext>
            </Box>
          </Paper>
        </>
      )}
    </div>
  );
}

export default Job_results_detail_hg38;

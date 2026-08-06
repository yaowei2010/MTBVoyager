import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { config } from '../../../constant.js';

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


// 自行依照你的檔案結構引入以下組件
import Germline_Trio_table from './Germline_Trio_table.js';
// import Inheritance_Matching from './Inheritance_Matching.js';
import Drug_Response from './Drug_Response.js';
import Appendix_Data from './Appendix_Data.js';

// ========= UI 小工具 =========
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

function Job_results_detail() {
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

  const [InheritanceMatchingData, setInheritanceMatchingData] = useState({});


  const [DrugResponseData, setDrugResponseData] = useState([]);
  const [selectedDrugResponses, setSelectedDrugResponse] = useState([]);
  const [selectedDrugResponsesRowsid, setSelectedDrugResponseRowsid] = useState([]);


  const pathnameParts = window.location.pathname.split('/');
  const newJobID = pathnameParts[4];
  const currentJobType = pathnameParts[3].includes('trio')

    ? 'Germline Trio'
    : pathnameParts[3].includes('germline')
    ? 'Germline'
    : 'Somatic';


  // --------------------- SV/CNV HTML 相關 ---------------------
  // 父組件保留一份 htmlContent
  const [htmlContent, setHtmlContent] = useState('');
  // 用來紀錄勾選的 rowId => Boolean
  const [checkedSVRows, setCheckedSVRows] = useState({});

  // --------------------- 其他 ---------------------
  const [selectedTotal, setSelectedTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const [value, setValue] = useState('1');
  const [valueKnown, setValueKnown] = useState('1');
  const [valuePredict, setValuePredict] = useState('1');

  const handleChange = (event, newValue) => {
    setValue(newValue);
  };
  const handleChangeKnown = (event, newValue) => {
    setValueKnown(newValue);
};
  const handleChangePredict = (event, newValue) => {
      setValuePredict(newValue);
  };



  // --------------------- Summary 按鈕 ---------------------
  const handleSaveToReport = async () => {
    try {
      let allData = [];
      const processData = (data, tableName) => {
        return data.map(item => ({
          table_name: tableName,
          ...item
        }));
      };

      if (selectedKnownPathogenic.length > 0) {
        allData = [...allData, ...processData(selectedKnownPathogenic, 'Known Pathogenic Pheno')];
      }
      if (selectedKnownACMG.length > 0) {
        allData = [...allData, ...processData(selectedKnownACMG, 'Known Pathogenic ACMG')];
      }
      if (selectedKnownOther.length > 0) {
        allData = [...allData, ...processData(selectedKnownOther, 'Known Pathogenic Other')];
      }
      if (selectedPredictedSuspect.length > 0) {
        allData = [...allData, ...processData(selectedPredictedSuspect, 'Predicted Suspect Pheno')];
      }
      if (selectedPredictedACMG.length > 0) {
        allData = [...allData, ...processData(selectedPredictedACMG, 'Predicted Suspect ACMG')];
      }
      if (selectedPredictedOther.length > 0) {
        allData = [...allData, ...processData(selectedPredictedOther, 'Predicted Suspect Other')];
      }
      if (selectedOtherVariants.length > 0) {
        allData = [...allData, ...processData(selectedOtherVariants, 'Other Variants')];
      }
      if (selectedDrugResponses.length > 0) {
        allData = [...allData, ...processData(selectedDrugResponses, 'Drug Responses')];
      }
      if (allData.length === 0) {
        console.log('沒有資料需要保存');
        return;
      }

      console.log('all data',allData);
      const newJobID = window.location.pathname.split('/')[4];

      const response = await axios.post(`${config.rootApiIP}/get_summary_info`, {
        newJobID: newJobID,
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
      window.location.href = config.rootPathPrefix + `/Job_results/detail/${analysisIdFromUrl}/summary_report_germline_trio`;
    }
  };


  // =======================================================================================
  // ====================== 請求 & 解析後端傳回的 HTML (SV/CNV) ==============================
  // =======================================================================================
  useEffect(() => {
    axios
      .post(`${config.rootApiIP}/knotannotsv_url`, { newjobID: newJobID })
      .then((response) => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(response.data, 'text/html');

        // (a) 移除特定 style 的 <div>（可選）
        doc.querySelectorAll('div').forEach((div) => {
          if (
            div.getAttribute('style') ===
            'width: 98%; margin: 10px 10px 10px 10px; text-align:right;display: inline-block'
          ) {
            div.remove();
          }
        });

        // (b) 修改 script 裡 keyType / keyAnnotID 預設值 (或是插入其他必要代碼)
        doc.querySelectorAll('script').forEach((scriptEl) => {
          let text = scriptEl.textContent;
          // 改成你需要的預設
          text = text.replace(/var\s+keyType\s*=\s*"3";/g, 'var keyType = "4";');
          text = text.replace(/var\s+keyAnnotID\s*=\s*"0";/g, 'var keyAnnotID = "1";');
          scriptEl.textContent = text;
        });

        // (c) 在 thead 新增一個 "Select" <th> 欄位（若原本已加過就略過）
        const headRow = doc.querySelector('#tabFULLSPLIT thead tr');
        if (headRow && !headRow.innerText.includes('Select')) {
          const th = doc.createElement('th');
          th.innerText = 'Select';
          headRow.insertBefore(th, headRow.firstChild);
        }

        // (d) 在 tbody 的每個 <tr> 開頭插入 checkbox，並根據父層 state 來還原勾選
        const rows = doc.querySelectorAll('#tabFULLSPLIT tbody tr');
        rows.forEach((tr, index) => {
          // 嘗試用 tr.id 作為 rowId
          let rowId = tr.id;

          // 如果該列沒有 id，就用 <td data-search="xxx"> 裡的屬性當作替代
          if (!rowId) {
            // 假設在 <td data-search="xxxx">，可取得該屬性
            const tdWithDataSearch = tr.querySelector('[data-search]');
            if (tdWithDataSearch) {
              rowId = tdWithDataSearch.getAttribute('data-search');
            } else {
              // 若完全取不到，那就用一個 fallback
              rowId = 'row_' + index;
            }
          }

          // 檢查父層 state 是否紀錄過 (true=已勾選)
          const isChecked = !!checkedSVRows[rowId];

          // 建立新的 <td> 放入 checkbox
          const td = doc.createElement('td');
          td.innerHTML = `
            <input
              type="checkbox"
              ${isChecked ? 'checked' : ''}
              onchange="onCheckboxChange('${rowId}', this.checked)"
            />
          `;
          // 插入到每列開頭
          tr.insertBefore(td, tr.firstChild);
        });

        // (e) 確保 HTML 裡面有 onCheckboxChange()，把勾選狀態回傳給父層
        // 如果原本 HTML 已有，請合併，否則就 append
        const customScript = doc.createElement('script');
        customScript.textContent = `
          function onCheckboxChange(rowId, checked) {
            window.parent.postMessage(
              {
                type: 'ROW_CHECKED_CHANGE',
                rowId: rowId,
                checked: checked
              },
              '*'
            );
          }
        `;
        doc.body.appendChild(customScript);

        // (f) 設定到 state
        setHtmlContent(doc.documentElement.outerHTML);
      })
      .catch((error) => {
        console.error('Error downloading HTML file:', error);
      });
  }, [checkedSVRows]);
  // 注意：每當 checkedSVRows 改變，就會重新產生 HTML，確保下次 DataTables re-draw 或切換時可自動帶回勾選。
  // =======================================================================================
  // ====================== 請求 & 解析後端傳回的 HTML (SV/CNV)END ===========================
  // =======================================================================================

  


  // --------------------- 監聽 postMessage: row checkbox 改變 ---------------------
  useEffect(() => {
    const handleMessage = (event) => {
      if (event.data?.type === 'ROW_CHECKED_CHANGE') {
        const { rowId, checked } = event.data;
        if (!rowId) return; // 若 rowId = '' 就無法記錄
        // 更新到父層 state
        setCheckedSVRows((prev) => ({
          ...prev,
          [rowId]: checked
        }));
      }
    };
    window.addEventListener('message', handleMessage);
    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, []);





  // --------------------- 計算總勾選數量 (含 EXPANDED 狀態) ---------------------
  useEffect(() => {
    // 1) 各組件本身的勾選
    const selectedKnownPathogenicCount = selectedKnownPathogenic.length;
    const selectedKnownACMGCount = selectedKnownACMG.length;
    const selectedKnownOtherCount = selectedKnownOther.length;
    const selectedPredictedSuspectCount = selectedPredictedSuspect.length;
    const selectedPredictedACMGCount = selectedPredictedACMG.length;
    const selectedPredictedOtherCount = selectedPredictedOther.length;
    const selectedOtherVariantsCount = selectedOtherVariants.length;
    const selectedDrugResponsesCount = selectedDrugResponses.length;

    // 2) SV/CNV (HTML) 部分
    //   => Object.values(checkedSVRows) 是 [true, false, true, ...]
    //   => filter(Boolean).length 會得到被勾選的數量
    const selectedSVCount = Object.values(checkedSVRows).filter(Boolean).length;

    // 3) 加總
    const totalSelectedCount =
      selectedKnownPathogenicCount +
      selectedKnownACMGCount +
      selectedKnownOtherCount +
      selectedPredictedSuspectCount +
      selectedPredictedACMGCount +
      selectedPredictedOtherCount +
      selectedOtherVariantsCount +
      selectedDrugResponsesCount +
      selectedSVCount;

    setSelectedTotal(totalSelectedCount);
    console.log('Total Selected:', totalSelectedCount);
  }, [
    // 當任何勾選有變動時重新計算
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
    const fetchAllData = async () => {
      try {
        setLoading(true);

        // 範例：根據你實際的資料結構來處理
        const formatData = (data) =>
          data.map((item, index) => ({
            id: index + 1,
            Location: item.Location,
            Gene: item.Gene,
            INH: item.INH,
            RSID: item['RS ID'],
            MAF: Object.entries(item.MAF)
              .map(([key, value]) => `${key}: ${value}`)
              .join('\n'),
            GenotypeVAF: Object.entries(item['Genotype / VAF'])
              .map(([key, value]) => `${key}: ${value}`)
              .join('\n'),
            Evidence: Object.entries(item.Evidence)
              .map(([key, value]) => `${key}: ${value}`)
              .join('\n'),
            Domain: item.Domain,
            Pathogenicity: Object.entries(item.Pathogenicity)
              .map(([key, value]) => `${key}: ${value}`)
              .join('\n'),
            SplicingEffect: Object.entries(item['Splicing effect'])
              .map(([key, value]) => `${key}: ${value}`)
              .join('\n'),
            OMIM: (() => {
              const omim = item.OMIM_number;
              if (!omim || typeof omim !== 'object') return '-';

              const omimID = omim.OMIM_number || '-';
              const rawPheno = String(omim.Phenotype || '');
              const matchFlag = omim['符合條件'] || '-';

              let phenoName = '';
              let phenoID = '';
              let inheritance = '';

              // 格式1：{名稱}, 617540 (3)(AD)
              const matchFormat1 = rawPheno.match(/\{(.+?)\},?\s*(\d+)?(?:\s*\(\d+\))?\((\w+)\)?/);

              // 格式2：Auditory neuropathy, AR, 1, 601071 (3)(AR)
              const matchFormat2 = rawPheno.match(/^(.+?),.+?,.+?,\s*(\d+)\s*\(\d+\)\((\w+)\)/);

              // ✅ 格式3：Deafness, AR 42, 609646 (3)(AR)
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
            AmelieMaxScore: item['Amelie Max score'],
            AmelieMeanScore: item['Amelie Mean score'],
          }));

        const formatDrugResponseData = (data) =>
          data.map((item, index) => ({
            id: index + 1,
            Location: item.Location,
            Gene: item.Gene,
            RSID: item['RS ID'],
            Drugevidence: item['Drug evidence'],
            Chemical: item.Chemical.replace(/;/g, ';\n'),
            ClinVar: item.ClinVar,
          }));

        // 1) Known Pathogenic
        const knownPathogenicResponse = await axios.post(`${config.rootApiIP}/known_pathogenic_to_json_trio`, {});
        console.log('knownPathogenicResponse:',knownPathogenicResponse)
        setKnownPathogenicData(formatData(knownPathogenicResponse.data));

        const incidental_finding = await axios.post(`${config.rootApiIP}/incidental_finding_variant_trio`, {});
        console.log('incidental_finding:',incidental_finding)
        setKnownACMGData(formatData(incidental_finding.data.data1));

        setKnownOtherData(formatData(incidental_finding.data.data2));
        
        // 2) Predicted Suspect
        const predictedSuspectResponse = await axios.post(`${config.rootApiIP}/predicted_suspect_variant_trio`, {});
        console.log('predictedSuspectResponse:',predictedSuspectResponse)
        setPredictedSuspectData(formatData(predictedSuspectResponse.data));

        const predictedACMGResponse = await axios.post(`${config.rootApiIP}/predicted_ACMG_variant_trio`, {});
        console.log('predictedACMGResponse:',predictedACMGResponse)
        setPredictedACMGData(formatData(predictedACMGResponse.data));

        const predictedOtheresponse = await axios.post(`${config.rootApiIP}/predicted_other_variant_trio`, {});
        console.log('predictedOtheresponse:',predictedOtheresponse)
        setPredictedOtherData(formatData(predictedOtheresponse.data));
        
        // 3) Other Variants
        const otherVariantsResponse = await axios.post(`${config.rootApiIP}/other_variant_trio`, {});
        console.log(otherVariantsResponse)
        setOtherVariantsData(formatData(otherVariantsResponse.data));


        // 6) Drug Response
        const drugResponseResponse = await axios.post(`${config.rootApiIP}/drug_response_variant_trio`, {});
        console.log(drugResponseResponse)
        setDrugResponseData(formatDrugResponseData(drugResponseResponse.data.data));

        setLoading(false);
      } catch (error) {
        console.error('請求錯誤：', error);
        setLoading(false);
      }
    };
    fetchAllData();
  }, []);

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
                    <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>Current Job</Typography>
                    <Typography variant="body1">{currentJobType}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={6} md={3}>
                    <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>Sample ID</Typography>
                    <Typography variant="body1">{newJobID}</Typography>
                  </Grid>
                  <Grid item xs={6} sm={6} md={3}>
                    <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>Syndrome</Typography>
                    <Typography variant="body1">___________</Typography>
                  </Grid>
                  <Grid item xs={6} sm={6} md={3}>
                    <Typography variant="subtitle2" sx={{ color: '#1976d2' }}>Gene Panel</Typography>
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
                    {/* <Tab label="Inheritance Matching" value="4" /> */}
                    {/* <Tab label="Incidental Finding" value="5" /> */}
                    {/* <Tab label="Appendix Data" value="7" /> */}
                  </TabList>
                </Box>
                {/* ///////*/}
                {/* 外層 1 */}
                {/* ///////*/}
                <TabPanel value="1">
                  <TabContext value={valueKnown}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                        <TabList 
                            onChange={handleChangeKnown} 
                            centered
                            aria-label="secondary tabs example"
                            textColor="secondary"
                            indicatorColor="secondary"
                            >
                            <Tab label="pheno variants" value="1" />
                            <Tab label="acmg variants" value="2" />
                            <Tab label="other variants" value="3" />
                            
                        </TabList>
                    </Box>
                    <TabPanel value="1">
                      <Germline_Trio_table
                        data={knownPathogenicData}
                        onSelectionChange={setSelectedKnownPathogenic}
                        rowSelectionModel={selectedKnownPathogenicRowsid}
                        setrowSelectionModel={setSelectedKnownPathogenicRowsid}
                        />
                    </TabPanel>
                    <TabPanel value="2">
                      <Germline_Trio_table
                      data={knownACMGData}
                      onSelectionChange={setSelectedKnownACMG}
                      rowSelectionModel={selectedKnownACMGRowsid}
                      setrowSelectionModel={setSelectedKnownACMGRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="3">
                      <Germline_Trio_table
                      data={knownOtherData}
                      onSelectionChange={setSelectedKnownOther}
                      rowSelectionModel={selectedKnownOtherRowsid}
                      setrowSelectionModel={setSelectedKnownOtherRowsid}
                      />
                    </TabPanel>
                  </TabContext>
                </TabPanel>


                {/* ///////*/}
                {/* 外層 2 */}
                {/* ///////*/}
                <TabPanel value="2">
                  <TabContext value={valuePredict}>
                    <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
                        <TabList 
                            onChange={handleChangePredict} 
                            centered
                            aria-label="secondary tabs example"
                            textColor="secondary"
                            indicatorColor="secondary"
                            >
                            <Tab label="pheno variants" value="1" />
                            <Tab label="acmg variants" value="2" />
                            <Tab label="other variants" value="3" />
                            
                        </TabList>
                    </Box>
                    <TabPanel value="1">
                      <Germline_Trio_table
                      data={PredictedSuspectData}
                      onSelectionChange={setSelectedPredictedSuspect}
                      rowSelectionModel={selectedPredictedSuspectRowsid}
                      setrowSelectionModel={setselectedPredictedSuspectRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="2">
                      <Germline_Trio_table
                      data={PredictedACMGData}
                      onSelectionChange={setSelectedPredictedACMG}
                      rowSelectionModel={selectedPredictedACMGRowsid}
                      setrowSelectionModel={setselectedPredictedACMGRowsid}
                      />
                    </TabPanel>
                    <TabPanel value="3">
                      <Germline_Trio_table
                      data={PredictedOtherData}
                      onSelectionChange={setSelectedPredictedOther}
                      rowSelectionModel={selectedPredictedOtherRowsid}
                      setrowSelectionModel={setselectedPredictedOtherRowsid}
                      />
                    </TabPanel>
                  </TabContext>
                </TabPanel>

                {/* ///////*/}
                {/* 外層 3 */}
                {/* ///////*/}
                <TabPanel value="3">
                  <Germline_Trio_table
                      data={OtherVariantsData}
                      onSelectionChange={setSelectedOtherVariants}
                      rowSelectionModel={selectedOtherVariantsRowsid}
                      setrowSelectionModel={setSelectedOtherVariantsRowsid}
                      />
                  {/* <Other_Variants
                    data={OtherVariantsData}
                    onSelectionChange={setSelectedOtherVariants}
                    rowSelectionModel={selectedOtherVariantsRowsid}
                    setrowSelectionModel={setSelectedOtherVariantsRowsid}
                  /> */}
                </TabPanel>

                {/* <TabPanel value="4">
                  <Inheritance_Matching data={InheritanceMatchingData} />
                </TabPanel> */}

                <TabPanel value="6">
                  <Drug_Response
                    data={DrugResponseData}
                    onSelectionChange={setSelectedDrugResponse}
                    rowSelectionModel={selectedDrugResponsesRowsid}
                    setrowSelectionModel={setSelectedDrugResponseRowsid}
                  />
                </TabPanel>

                {/* <TabPanel value="7"> */}
                  {/* 這裡由Appendix_Data去渲染 htmlContent；可用iframe或dangerouslySetInnerHTML */}
                  {/* <Appendix_Data htmlContent={htmlContent} /> */}
                {/* </TabPanel> */}
              </TabContext>
            </Box>
          </Paper>
        </>
      )}
    </div>
  );
}

export default Job_results_detail;

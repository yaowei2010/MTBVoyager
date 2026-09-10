import React,{useEffect,useMemo,useRef,useState} from 'react';
import {Alert,Box,Button,Chip,CircularProgress,Divider,Grid,Link,Paper,Stack,Tab,Tabs,Table,TableBody,TableCell,TableContainer,TableHead,TableRow,TextField,Typography} from '@mui/material';
import {useParams} from 'react-router-dom';
import axios from 'axios';
import {config} from '../../../constant';
import WgsResultTable from '../WGS_Germline_Detail/WgsResultTable';
import Pathway from '../Somatic_TissueOnly_Detail/Pathway_viewer';
import {DataGrid} from '@mui/x-data-grid';
import {GlobalWorkerOptions,getDocument} from 'pdfjs-dist';

GlobalWorkerOptions.workerSrc=process.env.PUBLIC_URL+'/pdf.worker.mjs';

const baseSections=[
  ['high_risk','高風險位點','非 synonymous，且 ClinVar 為 Pathogenic/Likely Pathogenic 或 oncogenicity 為 Oncogenic/Likely Oncogenic 的位點。'],
  ['snv_actionable','具備用藥位點','僅從高風險位點進一步比對出的用藥證據。'],
  ['hereditary_high_risk','Hereditary high-risk variants','ClinVar pathogenic/likely pathogenic variants in ACMG hereditary-cancer genes; matched-normal confirmation is required.'],
  ['in_silico_candidates','In-silico candidates','Rare variants supported by at least two functional predictors; these are not clinically classified.'],
];
const optionalSections={sv:['sv','Structural variants','Displayed only because an optional SV callset was supplied.'],cnv:['cnv','Copy-number variants','Displayed only because an optional CNV callset was supplied.']};
const analysisSections=[['tmb_estimate','Estimated TMB','Exploratory WGS-derived coding TMB estimate.'],['mutation_signature','Mutation Signature','COSMIC SBS activities and signature profile.'],['cancer_type_prediction','Cancer Type Prediction','Legacy OncoNPC prediction summary and report.'],['pathway_analysis','Pathway Viewer','Network pathway analysis using the retained WGS candidates.'],['mtb_report','MTB Draft Report','Concise preliminary report for molecular tumor board review.']];
const analysisTabs=new Set(analysisSections.map(([key])=>key));
const oncogenicityCriteria={
  OVS1:['+8','Bona-fide tumor suppressor gene 中符合條件的預測 loss-of-function／特定 splice 變異。'],
  OS1:['+4','與已收錄的 oncogenic variant 具有完全相同的蛋白質變化。'],OS2:['+4','具可重現且支持 oncogenic effect 的功能性研究。'],OS3:['+4','符合高觀察數的 cancer hotspot 強證據。'],
  OM1:['+2','位於已建立的關鍵功能性蛋白區域。'],OM2:['+2','已知 oncogene／tumor suppressor gene 中符合條件的蛋白長度改變。'],OM3:['+2','同一胺基酸位置已有符合條件的不同 oncogenic substitution。'],OM4:['+2','符合中等強度的 cancer hotspot 證據。'],
  OP1:['+1','多個可用的 in-silico predictor 一致支持有功能影響。'],OP2:['+1','符合特定腫瘤型態／單一遺傳病因的支持條件。'],OP3:['+1','符合較低觀察數的 cancer hotspot 支持證據。'],OP4:['+1','在本流程使用的 gnomAD 註釋中缺失或族群頻率不高於 1%。'],
  SBVS1:['−8','任一評估族群中的 allele frequency 高於 5%，為非常強的 benign evidence。'],SBS1:['−4','任一評估族群中的 allele frequency 高於 1%，為強 benign evidence。'],SBS2:['−4','具可重現且顯示無 oncogenic effect 的功能性研究。'],
  SBP1:['−1','所有可用的 in-silico predictor 一致支持無功能影響。'],SBP2:['−1','Synonymous variant 同時具有 benign splice prediction 與低 conservation。'],
};

const isTherapyActionable=(row)=>String(row?.cancer_actionable||'').toLowerCase()==='true';
const isTumorMatched=(row)=>String(row?.cancer_type_match||'').toLowerCase()==='true';
const DRAFT_MIN_TUMOR_DP=60;
const draftDepthPass=(row)=>Number.isFinite(Number(row?.tumor_dp))&&Number(row.tumor_dp)>=DRAFT_MIN_TUMOR_DP;
const draftEvidencePass=(row)=>(row?.clinvar_current_verified===true&&/^(pathogenic|likely pathogenic|pathogenic\/likely pathogenic)$/i.test(String(row?.clinvar||'').replaceAll('_',' ').trim()))||/^(oncogenic|likely oncogenic)$/i.test(String(row?.oncogenicity||row?.oncogenicity_classification||'').trim());
const variantValue=(row={})=>row.variant_id||row.variant||'—';
const clinvarUrl=(row)=>{const match=variantValue(row).match(/^chr([^:]+):(\d+):([^:]+):([^:]+)$/);if(!match)return 'https://www.ncbi.nlm.nih.gov/clinvar/';const[,chrom,position,ref,alt]=match;return `https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(`${chrom}[chr] AND ${position}[chrpos38] AND ${ref}>${alt}`)}`;};
const ClinVarLink=({row})=>{const value=row.clinvar||row.CLIN_SIG||row.ClinVar_CLNSIG||'—';return value==='—'?value:<Link href={row.clinvar_url||clinvarUrl(row)} target="_blank" rel="noopener noreferrer" underline="hover" title="Verify this GRCh38 variant in NCBI ClinVar">{value}</Link>;};

function Metric({label,value,tone='primary'}){return <Paper variant="outlined" sx={{p:2.25,height:'100%',borderTop:4,borderTopColor:`${tone}.main`}}><Typography color="text.secondary" variant="body2" fontWeight={700}>{label}</Typography><Typography variant="h4" fontWeight={850} sx={{mt:.5}}>{value??'—'}</Typography></Paper>}

function ActionableEvidenceTable({rows,emptyMessage}){
  if(!rows.length)return <Alert severity="info">{emptyMessage}</Alert>;
  return <TableContainer component={Paper} variant="outlined" sx={{mt:1}}><Table size="small"><TableHead><TableRow>{['Variant (GRCh38)','Tumor AF','Tumor DP','gnomAD EAS AF','Gene / HGVS.p','Drug','AMP Tier','Evidence disease','Source','Response','ClinVar','Oncogenicity'].map(x=><TableCell key={x} sx={{fontWeight:800,bgcolor:'#edf5fb'}}>{x}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((r,i)=><TableRow key={`${r.gene}-${r.hgvsp}-${r.drug}-${i}`} hover><TableCell sx={{whiteSpace:'nowrap'}}>{variantValue(r)}</TableCell><TableCell>{r.tumor_af||'—'}</TableCell><TableCell>{r.tumor_dp||'—'}</TableCell><TableCell>{r.gnomad_eas_af||'—'}</TableCell><TableCell><Typography fontWeight={800}>{r.gene||'—'}</Typography><Typography variant="caption">{r.hgvsp||r.hgvsc||'—'}</Typography></TableCell><TableCell>{r.drug||'—'}</TableCell><TableCell><Chip size="small" label={r.amp_tier||'—'} color="primary" variant="outlined"/></TableCell><TableCell>{r.disease||'—'}</TableCell><TableCell>{r.source||'—'}</TableCell><TableCell>{r.significance||'—'}</TableCell><TableCell><ClinVarLink row={r}/></TableCell><TableCell>{r.oncogenicity||r.oncogenicity_classification||'—'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>;
}

function PdfCanvas({base64,title,scale=1.5}){
  const canvasRef=useRef(null);
  useEffect(()=>{
    let cancelled=false;
    const render=async()=>{
      if(!base64||!canvasRef.current)return;
      const bytes=Uint8Array.from(atob(base64),c=>c.charCodeAt(0));
      const pdf=await getDocument({data:bytes}).promise;
      const page=await pdf.getPage(1);
      if(cancelled||!canvasRef.current)return;
      const viewport=page.getViewport({scale});
      const canvas=canvasRef.current;canvas.width=viewport.width;canvas.height=viewport.height;
      await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
    };
    render().catch(error=>console.error(`Unable to render ${title}`,error));
    return()=>{cancelled=true;};
  },[base64,scale,title]);
  if(!base64)return null;
  return <Box sx={{width:'100%',overflowX:'auto',bgcolor:'#fff',p:1,border:'3px solid #ccc'}}><canvas ref={canvasRef} aria-label={title} style={{display:'block',maxWidth:'100%',height:'auto',margin:'0 auto',background:'#fff'}}/></Box>;
}

function MutationSignaturePanel({data}){
  const rows=(data?.signature_activities||[]).map((r,i)=>({id:i,field:r.signature,description:r.description,rate:Number(r.proportion).toFixed(2),sample:Number(r.activity).toLocaleString()}));
  const columns=[{field:'field',headerName:'SBS Type',width:200,renderCell:p=><a href={`https://cancer.sanger.ac.uk/signatures/sbs/${String(p.value).toLowerCase()}/`} target="_blank" rel="noreferrer">{p.value}</a>},{field:'description',headerName:'Description',minWidth:600,flex:1},{field:'rate',headerName:'SBS Rate',width:150},{field:'sample',headerName:'Sample',width:150}];
  if(!rows.length)return <Alert severity="info">Mutation signature result is not available.</Alert>;
  return <Box sx={{p:2}}><Alert severity="warning" sx={{mb:2}}>Exploratory tumor-only result. Germline tagging was disabled in the source callset, so this signature is not clinically validated.</Alert><Typography variant="h4" gutterBottom>Activities</Typography><Box sx={{height:400,width:'100%'}}><DataGrid rows={rows} columns={columns} initialState={{pagination:{paginationModel:{pageSize:10}}}} pageSizeOptions={[10]}/></Box>{data.signature_pie_pdf_base64&&<Box sx={{mt:3}}><Typography variant="h4" gutterBottom>Mutation Signature</Typography><PdfCanvas base64={data.signature_pie_pdf_base64} title="Mutation signature" scale={1.7}/></Box>}</Box>;
}

function CancerPredictionPanel({data}){
  const result=data?.cancer_type_prediction?.rows?.[0];
  if(!result)return <Alert severity="info">Cancer type prediction is not available.</Alert>;
  return <Box sx={{p:3}}><Alert severity="warning" sx={{mb:2}}>Exploratory tumor-only prediction; it must not replace pathology or clinical diagnosis.</Alert><Typography variant="h4" gutterBottom>Prediction Summary</Typography><Paper elevation={2} sx={{p:2,mb:3}}><Grid container spacing={2}><Grid item xs={4}><Typography fontWeight="bold">Prediction Cancer</Typography></Grid><Grid item xs={8}><Typography>{result.pred_cancer}</Typography></Grid><Grid item xs={4}><Typography fontWeight="bold">Prediction Probability</Typography></Grid><Grid item xs={8}><Typography>{result.pred_prob}</Typography></Grid></Grid></Paper>{data.cancer_prediction_pdf_base64&&<><Typography variant="h4" gutterBottom>Prediction Report</Typography><PdfCanvas base64={data.cancer_prediction_pdf_base64} title="Cancer type prediction report" scale={1.5}/></>}</Box>;
}

function TmbEstimatePanel({data}){
  const t=data?.tmb_estimate;
  if(!t?.tmb_proxy_mut_per_mb)return <Alert severity="info">Estimated TMB is not available.</Alert>;
  return <Box sx={{p:2}}><Alert severity="warning" sx={{mb:3}}>Estimated result only—not calibrated to an FDA-approved assay and not a clinical TMB-high classification. Rare/private germline variants may remain because this is tumor-only.</Alert><Stack direction={{xs:'column',md:'row'}} spacing={2} sx={{mb:3}}><Metric label="Estimated TMB" value={`${Number(t.tmb_proxy_mut_per_mb).toFixed(2)} mut/Mb`} tone="warning"/><Metric label="Counted variants" value={t.tmb_numerator_variants}/><Metric label="Callable coding territory" value={`${Number(t.callable_coding_mb).toFixed(3)} Mb`}/></Stack><Paper variant="outlined" sx={{p:2}}><Typography variant="h6" fontWeight={800}>Estimation method</Typography><Typography sx={{mt:1}}>{t.method}</Typography><Typography variant="body2" color="text.secondary" sx={{mt:1}}>GRCh38 · autosomal GENCODE v47 CDS ∩ uploaded callable BED · gnomAD AF ≤ {Number(t.population_af_max)*100}%.</Typography><Typography variant="body2" sx={{mt:2,fontWeight:700}}>Calculation: {t.tmb_numerator_variants} ÷ {Number(t.callable_coding_mb).toFixed(6)} Mb = {Number(t.tmb_proxy_mut_per_mb).toFixed(2)} mut/Mb</Typography></Paper></Box>;
}

function MtbReportPanel({report,downstream,loading,onGenerate,onSave}){
  const [draft,setDraft]=useState({case_summary:'',molecular_summary:'',treatment_discussion:'',limitations:[]});
  const [dirty,setDirty]=useState(false);
  const [editing,setEditing]=useState(false);
  useEffect(()=>{if(report?.narrative){setDraft(report.narrative);setDirty(false);setEditing(false)}},[report]);
  if(!report||report.status==='not_generated')return <Box sx={{textAlign:'center',py:8}}><Typography variant="h4" fontWeight={850}>MTB preliminary report</Typography><Typography color="text.secondary" sx={{my:2}}>Generate a concise draft from verified platform results. Gemma formats the narrative but cannot add findings or treatment evidence.</Typography><Button size="large" variant="contained" disabled={loading} onClick={()=>onGenerate(false)}>{loading?<><CircularProgress size={20} color="inherit" sx={{mr:1}}/>Generating…</>:'Generate MTB draft'}</Button></Box>;
  const d=report.data||{},n=report.narrative||{},included=row=>draftDepthPass(row)&&draftEvidencePass(row),matched=(d.actionable_matched||[]).filter(included),other=(d.actionable_other_cancers||[]).filter(included),highRisk=(d.high_risk_variants||[]).filter(included),hereditary=(d.hereditary_high_risk||[]).filter(included),signatures=d.top_mutational_signatures||[],tmb=d.estimated_tmb||{};
  const usedCriteria=new Set(highRisk.flatMap(r=>String(r.oncogenicity_criteria||'').split('|')).filter(Boolean));
  const Findings=({title,rows})=><Box sx={{mt:3}}><Typography variant="h6" fontWeight={850}>{title} ({rows.length})</Typography>{rows.length?<TableContainer component={Paper} variant="outlined" sx={{mt:1}}><Table size="small"><TableHead><TableRow>{['Gene / HGVS.p','Drug','AMP Tier','Cancer evidence','Source','ClinVar','Variant (GRCh38)','Tumor AF','Tumor DP','gnomAD EAS AF'].map(x=><TableCell key={x} sx={{fontWeight:800}}>{x}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((r,i)=><TableRow key={i}><TableCell>{r.gene||'—'}<br/><Typography variant="caption">{r.hgvsp||r.hgvsc||'—'}</Typography></TableCell><TableCell>{r.drug||'—'}</TableCell><TableCell>{r.amp_tier||'—'}</TableCell><TableCell>{r.disease||'—'}</TableCell><TableCell>{r.source||'—'}</TableCell><TableCell><ClinVarLink row={r}/></TableCell><TableCell sx={{whiteSpace:'nowrap'}}>{variantValue(r)}</TableCell><TableCell>{r.tumor_af||'—'}</TableCell><TableCell>{r.tumor_dp||'—'}</TableCell><TableCell>{r.gnomad_eas_af||'—'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>:<Typography color="text.secondary">No findings with Tumor DP ≥ {DRAFT_MIN_TUMOR_DP}.</Typography>}</Box>;
  const HighRiskEvidence=({rows})=><Box className="mtb-section" sx={{mt:3}}><Typography variant="h6" fontWeight={850}>高風險位點 ({rows.length})</Typography>{rows.length?<TableContainer component={Paper} variant="outlined" sx={{mt:1}}><Table size="small"><TableHead><TableRow>{['Gene / HGVS.p','Consequence','ClinVar','Oncogenicity','Score / criteria','Variant (GRCh38)','Tumor AF','Tumor DP','gnomAD EAS AF'].map(x=><TableCell key={x} sx={{fontWeight:800}}>{x}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((r,i)=><TableRow key={i}><TableCell><Typography fontWeight={800}>{r.gene||'—'}</Typography><Typography variant="caption">{r.hgvsp||r.hgvsc||'—'}</Typography></TableCell><TableCell>{r.consequence||'—'}</TableCell><TableCell><ClinVarLink row={r}/></TableCell><TableCell>{r.oncogenicity||'—'}</TableCell><TableCell>{r.oncogenicity_score||'—'}<br/><Typography variant="caption">{r.oncogenicity_criteria||'—'}</Typography></TableCell><TableCell sx={{whiteSpace:'nowrap'}}>{variantValue(r)}</TableCell><TableCell>{r.tumor_af||'—'}</TableCell><TableCell>{r.tumor_dp||'—'}</TableCell><TableCell>{r.gnomad_eas_af||'—'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>:<Typography color="text.secondary">No findings with Tumor DP ≥ {DRAFT_MIN_TUMOR_DP}.</Typography>}</Box>;
  const VariantFindings=({title,rows,hereditaryRisk=false})=><Box sx={{mt:3}}><Typography variant="h6" fontWeight={850}>{title} ({rows.length})</Typography>{hereditaryRisk&&<Typography variant="caption" color="warning.main">Tumor-only candidate; germline confirmation and genetic counseling review are required.</Typography>}{rows.length?<TableContainer component={Paper} variant="outlined" sx={{mt:1}}><Table size="small"><TableHead><TableRow>{['Gene / HGVS.p','Classification / evidence','ClinVar','Variant (GRCh38)','Tumor AF','Tumor DP','gnomAD EAS AF'].map(x=><TableCell key={x} sx={{fontWeight:800}}>{x}</TableCell>)}</TableRow></TableHead><TableBody>{rows.map((r,i)=><TableRow key={i}><TableCell>{r.gene||'—'}<br/><Typography variant="caption">{r.hgvsp||r.hgvsc||'—'}</Typography></TableCell><TableCell>{r.oncogenicity||r.significance||'—'}</TableCell><TableCell><ClinVarLink row={r}/></TableCell><TableCell sx={{whiteSpace:'nowrap'}}>{variantValue(r)}</TableCell><TableCell>{r.tumor_af||r.vaf||'—'}</TableCell><TableCell>{r.tumor_dp||'—'}</TableCell><TableCell>{r.gnomad_eas_af||'—'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>:<Typography color="text.secondary">No findings with Tumor DP ≥ {DRAFT_MIN_TUMOR_DP}.</Typography>}</Box>;
  const edit=(key,value)=>{setDraft({...draft,[key]:value});setDirty(true)};
  const regenerate=()=>{if(!dirty||window.confirm('Regenerating with Gemma will replace unsaved edits. Continue?'))onGenerate(true)};
  const cancelEdit=()=>{setDraft(report.narrative||{});setDirty(false);setEditing(false)};
  const narrativeFields=[['case_summary','病例摘要'],['molecular_summary','分子摘要']];
  return <Box>
    <style>{`
      @page{size:A4 landscape;margin:8mm}
      @media print{
        html,body{width:100%;margin:0!important;padding:0!important;background:#fff!important}
        body *{visibility:hidden}
        .mtb-print,.mtb-print *{visibility:visible}
        .mtb-print{position:absolute!important;left:0!important;top:0!important;width:100%!important;max-width:none!important;margin:0!important;padding:4mm!important;box-shadow:none!important;background:#fff!important}
        .mtb-no-print{display:none!important}
        .mtb-print .MuiTableContainer-root{width:100%!important;max-width:none!important;overflow:visible!important;box-shadow:none!important}
        .mtb-print table{width:100%!important;table-layout:fixed!important;border-collapse:collapse!important}
        .mtb-print thead{display:table-header-group}
        .mtb-print tr{break-inside:avoid!important;page-break-inside:avoid!important}
        .mtb-print th,.mtb-print td{font-size:6.5pt!important;line-height:1.2!important;padding:1.2mm .8mm!important;white-space:normal!important;overflow-wrap:anywhere!important;word-break:break-word!important}
        .mtb-print h3{font-size:18pt!important}
        .mtb-print h6{font-size:11pt!important}
        .mtb-print p,.mtb-print li{font-size:8.5pt!important}
        .mtb-print canvas,.mtb-print img{max-width:100%!important;height:auto!important}
        .mtb-section{break-inside:auto!important;page-break-inside:auto!important}
      }
    `}</style>
    <Stack className="mtb-no-print" direction="row" spacing={1} justifyContent="flex-end" sx={{mb:2}}>
      <Button variant="outlined" disabled={loading||editing} onClick={regenerate}>使用 Gemma 重新產生繁體中文內容</Button>
      {!editing&&<Button variant="outlined" disabled={loading} onClick={()=>setEditing(true)}>編輯</Button>}
      {editing&&<><Button color="inherit" disabled={loading} onClick={cancelEdit}>取消</Button><Button variant="contained" disabled={!dirty||loading} onClick={()=>onSave(draft)}>儲存修改</Button></>}
      <Button variant="contained" disabled={editing} onClick={()=>window.print()}>列印／儲存 PDF</Button>
    </Stack>
    <Paper className="mtb-print" sx={{p:{xs:2,md:5},bgcolor:'#fff'}}>
      <Stack direction="row" justifyContent="space-between"><Box><Typography variant="overline" color="primary">MOLECULAR TUMOR BOARD</Typography><Typography variant="h3" fontWeight={900}>分子腫瘤委員會初步報告</Typography></Box><Box sx={{textAlign:'right'}}><Chip color="warning" label="草稿－需專業審閱"/><Typography sx={{mt:1}}>{d.sample_id}</Typography><Typography variant="caption">{d.analysis_id}</Typography></Box></Stack>
      <Divider sx={{my:3}}/>{report.warning&&<Alert severity="warning" sx={{mb:2}}>{report.warning}</Alert>}
      <Grid container spacing={2}><Grid item xs={12} md={3}><Metric label="高風險位點" value={highRisk.length} tone="error"/></Grid><Grid item xs={12} md={3}><Metric label="Tumor-matched actionable" value={matched.length} tone="success"/></Grid><Grid item xs={12} md={3}><Metric label="Other cancer evidence" value={other.length} tone="warning"/></Grid><Grid item xs={12} md={3}><Metric label="Estimated TMB" value={tmb.tmb_proxy_mut_per_mb!=null?`${Number(tmb.tmb_proxy_mut_per_mb).toFixed(2)} mut/Mb`:'—'} tone="warning"/></Grid></Grid>
      <Alert severity="info" sx={{mt:2}}>Variant tables display Tumor DP ≥ {DRAFT_MIN_TUMOR_DP} findings classified as ClinVar P/LP or Oncogenic/Likely Oncogenic.</Alert>
      <Box sx={{mt:3}}>{narrativeFields.map(([key,label])=><Box key={key} sx={{mt:2}}><Typography variant="h6" fontWeight={850}>{label}</Typography>{editing?<TextField className="mtb-no-print" fullWidth multiline minRows={2} value={draft[key]||''} onChange={e=>edit(key,e.target.value)} sx={{mt:1}}/>:<Typography sx={{whiteSpace:'pre-wrap'}}>{draft[key]||'—'}</Typography>}</Box>)}</Box>
      <HighRiskEvidence rows={highRisk}/>
      <Findings title="具備用藥位點 — matched to current cancer type" rows={matched}/><Findings title="具備用藥位點 — evidence from other cancer types" rows={other}/>
      <VariantFindings title="Hereditary high-risk candidates" rows={hereditary} hereditaryRisk/>
      <Box className="mtb-section" sx={{mt:3}}><Typography variant="h6" fontWeight={850}>Mutational Signature (exploratory)</Typography>{editing?<TextField className="mtb-no-print" fullWidth multiline minRows={2} value={draft.signature_summary||''} onChange={e=>edit('signature_summary',e.target.value)} sx={{my:1}}/>:<Typography sx={{whiteSpace:'pre-wrap',my:1}}>{draft.signature_summary||'—'}</Typography>}{signatures.length?<TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell sx={{fontWeight:800}}>Signature</TableCell><TableCell sx={{fontWeight:800}}>Contribution</TableCell><TableCell sx={{fontWeight:800}}>Activity</TableCell></TableRow></TableHead><TableBody>{signatures.map((r,i)=><TableRow key={i}><TableCell>{r.signature}</TableCell><TableCell>{`${(Number(r.proportion||0)*100).toFixed(1)}%`}</TableCell><TableCell>{Number(r.activity||0).toLocaleString()}</TableCell></TableRow>)}</TableBody></Table></TableContainer>:<Typography color="text.secondary">No signature result available.</Typography>}{downstream?.signature_pie_pdf_base64&&<Box sx={{mt:2}}><PdfCanvas base64={downstream.signature_pie_pdf_base64} title="Mutational signature contribution chart" scale={1.35}/></Box>}</Box>
      <Box sx={{mt:3}}><Typography variant="h6" fontWeight={850}>Points for treatment discussion</Typography>{editing?<TextField className="mtb-no-print" fullWidth multiline minRows={2} value={draft.treatment_discussion||''} onChange={e=>edit('treatment_discussion',e.target.value)} sx={{mt:1}}/>:<Typography sx={{whiteSpace:'pre-wrap'}}>{draft.treatment_discussion||'—'}</Typography>}</Box>
      <Box sx={{mt:3}}><Typography variant="h6" fontWeight={850}>Limitations</Typography>{editing?<TextField className="mtb-no-print" fullWidth multiline minRows={4} helperText="One limitation per line" value={(draft.limitations||[]).join('\n')} onChange={e=>edit('limitations',e.target.value.split('\n'))}/>:<ul>{(draft.limitations||[]).filter(Boolean).map((x,i)=><li key={i}><Typography>{x}</Typography></li>)}</ul>}</Box>
      <Box className="mtb-section" sx={{mt:4,pt:2,borderTop:'2px solid #dbe6ee'}}><Typography variant="h6" fontWeight={850}>Appendix — Complete oncogenicity scoring reference</Typography><Typography variant="body2" sx={{mt:1}}>本報告採 ClinGen/CGC/VICC somatic oncogenicity 架構的本地確定性實作。計分分類：Oncogenic ≥10；Likely Oncogenic 6–9；VUS 0–5；Likely Benign −6 至 −1；Benign ≤−7。正分支持 oncogenicity，負分支持 benign interpretation。下表列出本流程全部 criteria；「Applied」表示該代碼出現在本病例的 oncogenic 位點。</Typography><TableContainer component={Paper} variant="outlined" sx={{mt:1}}><Table size="small"><TableHead><TableRow><TableCell sx={{fontWeight:800}}>Criterion</TableCell><TableCell sx={{fontWeight:800}}>Points</TableCell><TableCell sx={{fontWeight:800}}>Applied</TableCell><TableCell sx={{fontWeight:800}}>Operational definition used by this pipeline</TableCell></TableRow></TableHead><TableBody>{Object.entries(oncogenicityCriteria).map(([code,definition])=><TableRow key={code} sx={usedCriteria.has(code)?{bgcolor:'#fff8e1'}:{}}><TableCell sx={{fontWeight:800}}>{code}</TableCell><TableCell>{definition[0]}</TableCell><TableCell>{usedCriteria.has(code)?'Yes':'No'}</TableCell><TableCell>{definition[1]}</TableCell></TableRow>)}</TableBody></Table></TableContainer><Typography variant="caption" display="block" sx={{mt:1}}>Reference: Horak et al. Standards for the classification of pathogenicity of somatic variants in cancer (oncogenicity), ClinGen/CGC/VICC, Genetics in Medicine 2022. <a href="https://pmc.ncbi.nlm.nih.gov/articles/PMC9081216/" target="_blank" rel="noreferrer">PMCID: PMC9081216</a>. Criteria represent evidence codes, not treatment recommendations; tumor-only findings require clinical and, where relevant, germline confirmation.</Typography></Box>
      <Alert severity="warning" sx={{mt:3}}>{report.disclaimer}</Alert><Typography variant="caption" color="text.secondary">Generated {report.generated_at} · Narrative: {report.model||'deterministic template'}{report.edited_at?` · Edited ${report.edited_at}`:''}</Typography>
    </Paper>
  </Box>;
}

export default function WgsSomaticResult(){
  const {analysis_ID:id}=useParams();
  const [tab,setTab]=useState('high_risk');
  const [meta,setMeta]=useState(null);
  const [summary,setSummary]=useState(null);
  const [downstream,setDownstream]=useState(null);
  const [rows,setRows]=useState([]);
  const [matchedActionableCount,setMatchedActionableCount]=useState(null);
  const [offTumorEvidenceCount,setOffTumorEvidenceCount]=useState(null);
  const [hereditaryCount,setHereditaryCount]=useState(null);
  const [inSilicoCount,setInSilicoCount]=useState(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const [mtbReport,setMtbReport]=useState(null);
  const [reportLoading,setReportLoading]=useState(false);
  useEffect(()=>{
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}`).then(r=>setMeta(r.data)).catch(()=>setError('Unable to load analysis details.'));
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}/summary`).then(r=>setSummary(r.data)).catch(()=>{});
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}/downstream`).then(r=>setDownstream(r.data)).catch(()=>{});
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}/mtb-report`).then(r=>setMtbReport(r.data)).catch(()=>{});
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}/results`,{params:{section:'hereditary_high_risk'}}).then(r=>setHereditaryCount((r.data.results||[]).length)).catch(()=>{});
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}/results`,{params:{section:'in_silico_candidates'}}).then(r=>setInSilicoCount((r.data.results||[]).length)).catch(()=>{});
  },[id]);
  const sections=useMemo(()=>{
    const available=new Set(meta?.available_sections||[]);
    return [...baseSections,...['sv','cnv'].filter(k=>available.has(k)).map(k=>optionalSections[k]),...analysisSections];
  },[meta]);
  useEffect(()=>{
    setRows([]);setError('');setLoading(true);
    if(analysisTabs.has(tab)){setLoading(false);return;}
    axios.get(`${config.rootApiIP}/wgs-somatic/jobs/${id}/results`,{params:{section:tab}}).then(r=>{
      const results=r.data.results||[];
      if(tab==='snv_actionable'){
        const therapyRows=results.filter(isTherapyActionable);
        setRows(therapyRows);
        setMatchedActionableCount(therapyRows.filter(isTumorMatched).length);
        setOffTumorEvidenceCount(therapyRows.filter(row=>!isTumorMatched(row)).length);
      }else setRows(results);
    }).catch(e=>setError(e.response?.data?.detail||'Unable to load results.')).finally(()=>setLoading(false));
  },[id,tab,meta?.settings?.cancer_type]);
  const matchedActionable=rows.filter(isTumorMatched);
  const unmatchedActionable=rows.filter(row=>!isTumorMatched(row));
  const current=sections.find(([value])=>value===tab);
  const generateReport=(refresh)=>{setReportLoading(true);axios.post(`${config.rootApiIP}/wgs-somatic/jobs/${id}/mtb-report`,{refresh}).then(r=>setMtbReport(r.data)).catch(e=>setError(e.response?.data?.detail||'Unable to generate MTB report.')).finally(()=>setReportLoading(false));};
  const saveReport=(narrative)=>{setReportLoading(true);axios.put(`${config.rootApiIP}/wgs-somatic/jobs/${id}/mtb-report`,{narrative}).then(r=>setMtbReport(r.data)).catch(e=>setError(e.response?.data?.detail||'Unable to save MTB report edits.')).finally(()=>setReportLoading(false));};
  return <Box className="analysis-result-page" sx={{p:{xs:2,md:4},maxWidth:1600,mx:'auto',bgcolor:'#f5f8fb',minHeight:'100vh'}}>
    <Stack direction={{xs:'column',md:'row'}} justifyContent="space-between" spacing={2} alignItems={{md:'center'}}>
      <Box><Stack direction="row" spacing={1} sx={{mb:1}}><Chip label="TUMOR-ONLY" color="warning"/><Chip label="GRCh38" variant="outlined"/><Chip label="SNV/INDEL" color="primary" variant="outlined"/>{meta?.files?.sv&&<Chip label="SV INCLUDED" variant="outlined"/>}{meta?.files?.cnv&&<Chip label="CNV INCLUDED" variant="outlined"/>}</Stack><Typography variant="h3" fontWeight={850}>WGS tumor-only report</Typography><Typography color="text.secondary">Structured like the original tumor-only report, using the new oncogenicity algorithm.</Typography></Box>
      <Paper variant="outlined" sx={{p:2,minWidth:300}}><Typography fontWeight={800}>{meta?.subject?.subject_id||'Loading sample…'}</Typography><Typography variant="body2" color="text.secondary">Analysis {id}</Typography><Chip size="small" sx={{mt:1}} label={meta?.status||'loading'} color={meta?.status==='finished'?'success':'default'}/></Paper>
    </Stack>
    <Alert severity="warning" sx={{my:3}}>This is a tumor-only interpretation. Somatic origin and possible germline findings require confirmation with matched normal testing. Actionability and oncogenicity are separate assessments.</Alert>
    <Grid container spacing={2} sx={{mb:3}}><Grid item xs={6} md={2.4}><Metric label="Tumor-matched actionable" value={matchedActionableCount} tone="success"/></Grid><Grid item xs={6} md={2.4}><Metric label="Other cancer evidence" value={offTumorEvidenceCount} tone="warning"/></Grid><Grid item xs={6} md={2.4}><Metric label="Estimated TMB" value={downstream?.tmb_estimate?.tmb_proxy_mut_per_mb?`${Number(downstream.tmb_estimate.tmb_proxy_mut_per_mb).toFixed(2)} mut/Mb`:'—'} tone="warning"/></Grid><Grid item xs={6} md={2.4}><Metric label="Hereditary high-risk" value={hereditaryCount} tone="error"/></Grid><Grid item xs={6} md={2.4}><Metric label="In-silico candidates" value={inSilicoCount}/></Grid></Grid>
    <Paper sx={{overflow:'hidden',border:'1px solid #dbe6ee'}}><Tabs value={tab} onChange={(_,v)=>setTab(v)} variant="scrollable" scrollButtons="auto" sx={{px:1,borderBottom:'1px solid #dbe6ee',bgcolor:'#fff'}}>{sections.map(([v,l])=><Tab key={v} value={v} label={l} sx={v==='mtb_report'?{mx:.75,my:.75,minHeight:42,borderRadius:1.5,fontWeight:850,bgcolor:'#fff0c2',color:'#7a4b00','&:hover':{bgcolor:'#ffe49a'},'&.Mui-selected':{bgcolor:'#f59e0b',color:'#fff'}}:{}}/>)}</Tabs><Box sx={{p:{xs:2,md:3}}}>{!analysisTabs.has(tab)&&<><Typography variant="h5" fontWeight={800}>{current?.[1]}</Typography><Typography color="text.secondary" sx={{mb:2}}>{current?.[2]}</Typography></>}{tab==='snv_actionable'&&<Alert severity="info" sx={{mb:2}}>Drug evidence is separated by tumor-type relevance. AMP Tier and drug are shown for every candidate; off-tumor evidence is not a treatment recommendation for this patient.</Alert>}{tab==='snv_actionable'&&!meta?.settings?.cancer_type&&<Alert severity="warning" sx={{mb:2}}>Cancer type was not provided for this analysis. Evidence is shown as pan-cancer and tumor-type applicability requires clinical review.</Alert>}{tab==='snv_actionable'?<Stack spacing={3}><Box><Typography variant="h6" fontWeight={800} color="success.main">Matched to current cancer type ({matchedActionable.length})</Typography><ActionableEvidenceTable rows={matchedActionable} emptyMessage="No treatment evidence matched the current cancer type."/></Box><Box><Typography variant="h6" fontWeight={800} color="warning.main">Other cancer types / unmatched ({unmatchedActionable.length})</Typography><ActionableEvidenceTable rows={unmatchedActionable} emptyMessage="No off-tumor treatment evidence was found."/></Box></Stack>:tab==='mtb_report'?<MtbReportPanel report={mtbReport} downstream={downstream} loading={reportLoading} onGenerate={generateReport} onSave={saveReport}/>:tab==='tmb_estimate'?<TmbEstimatePanel data={downstream}/>:tab==='mutation_signature'?<MutationSignaturePanel data={downstream}/>:tab==='cancer_type_prediction'?<CancerPredictionPanel data={downstream}/>:tab==='pathway_analysis'?<Pathway/>:<WgsResultTable analysisId={id} somatic rows={rows} loading={loading} error={error} emptyMessage="No records in this section."/>}</Box></Paper>
  </Box>;
}

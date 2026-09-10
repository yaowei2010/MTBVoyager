import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Button, Chip, CircularProgress, Divider, Grid, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography } from '@mui/material';
import { config } from '../../../constant';
import WgsResultTable from '../WGS_Germline_Detail/WgsResultTable';

const Metric = ({ label, value, color = '#1976d2' }) => (
  <Paper variant="outlined" sx={{ p: 2.25, height: '100%', borderTop: 4, borderTopColor: color }}>
    <Typography variant="body2" color="text.secondary" fontWeight={700}>{label}</Typography>
    <Typography variant="h4" fontWeight={850} sx={{ mt: .5 }}>{value ?? '—'}</Typography>
  </Paper>
);

export default function LegacyMtbDraftReport({ analysisId }) {
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({});
  useEffect(() => {
    setError('');
    axios.get(`${config.rootApiIP}/wgs-somatic/legacy-jobs/${analysisId}/mtb-report`)
      .then(response => { setReport(response.data); setDraft(response.data.narrative || {}); })
      .catch(reason => setError(reason.response?.data?.detail || 'Unable to generate MTB draft report.'));
  }, [analysisId]);
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!report) return <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress /><Typography sx={{ mt: 2 }}>Preparing the complete tumor-only draft…</Typography></Box>;
  const generate = refresh => {
    setLoading(true); setError('');
    axios.post(`${config.rootApiIP}/wgs-somatic/legacy-jobs/${analysisId}/mtb-report`, { refresh })
      .then(response => { setReport(response.data); setDraft(response.data.narrative || {}); setEditing(false); })
      .catch(reason => setError(reason.response?.data?.detail || 'Gemma inference failed.'))
      .finally(() => setLoading(false));
  };
  const save = () => {
    setLoading(true); setError('');
    axios.put(`${config.rootApiIP}/wgs-somatic/legacy-jobs/${analysisId}/mtb-report`, { narrative: draft })
      .then(response => { setReport(response.data); setDraft(response.data.narrative || {}); setEditing(false); })
      .catch(reason => setError(reason.response?.data?.detail || 'Unable to save the draft.'))
      .finally(() => setLoading(false));
  };
  const base = report.data?.base_report || report;
  const tmb = base.tmb_estimate || {};
  const edit = (key, value) => setDraft(previous => ({ ...previous, [key]: value }));
  if (report.status === 'not_generated') return <Box sx={{ textAlign: 'center', py: 8 }}>
    <Typography variant="h4" fontWeight={850}>MTB 初步報告</Typography>
    <Typography color="text.secondary" sx={{ my: 2 }}>使用既有 tumor-only 結果產生繁體中文草稿；Gemma 只負責整理敘述，不得新增發現或治療證據。</Typography>
    <Button size="large" variant="contained" disabled={loading} onClick={() => generate(false)}>{loading ? <><CircularProgress size={20} color="inherit" sx={{ mr: 1 }} />產生中…</> : '產生 MTB 草稿'}</Button>
  </Box>;
  const narrativeFields = [['case_summary', '病例摘要'], ['molecular_summary', '分子摘要'], ['signature_summary', '突變特徵摘要'], ['treatment_discussion', '治療討論重點']];
  return <Box>
    <Stack direction="row" spacing={1} justifyContent="flex-end" sx={{ mb: 2 }}>
      <Button variant="outlined" disabled={loading || editing} onClick={() => generate(true)}>使用 Gemma 重新產生繁體中文內容</Button>
      {!editing && <Button variant="outlined" disabled={loading} onClick={() => setEditing(true)}>編輯</Button>}
      {editing && <><Button color="inherit" onClick={() => { setDraft(report.narrative || {}); setEditing(false); }}>取消</Button><Button variant="contained" disabled={loading} onClick={save}>儲存修改</Button></>}
      <Button variant="contained" disabled={editing} onClick={() => window.print()}>列印／儲存 PDF</Button>
    </Stack>
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
      <Box><Typography variant="overline" color="primary">MOLECULAR TUMOR BOARD</Typography><Typography variant="h4" fontWeight={900}>Tumor-only 分子腫瘤委員會初步報告</Typography><Typography color="text.secondary">Analysis {base.analysis_id} · {base.genome_build}</Typography></Box>
      <Chip color="warning" label="草稿－需專業審閱" />
    </Stack>
    {report.warning && <Alert severity="warning" sx={{ mb: 2 }}>{report.warning}</Alert>}
    {base.status === 'incomplete' && <Alert severity="error" sx={{ mb: 2 }}>分析結果不完整；缺少：{(base.missing_result_files || []).join(', ')}。缺失項目顯示為 unavailable，不解讀為零筆結果。</Alert>}
    <Alert severity="warning" sx={{ mb: 3}}>既有品質設定維持不變。高風險條件：{base.reporting_gate}。未進行 liftover。</Alert>
    <Grid container spacing={2} sx={{ mb: 3 }}>
      <Grid item xs={12} md={4}><Metric label="高風險變異" value={base.summary?.high_risk_count} color="#d32f2f" /></Grid>
      <Grid item xs={12} md={4}><Metric label="Oncogenicity candidates" value={base.summary?.oncogenicity_candidates} /></Grid>
      <Grid item xs={12} md={4}><Metric label="Estimated TMB proxy" value={`${Number(tmb.tmb_proxy_mut_per_mb || 0).toFixed(2)} mut/Mb`} color="#ed6c02" /></Grid>
    </Grid>
    <Paper variant="outlined" sx={{ p: 2.5, mb: 3 }}>
      <Typography variant="caption" color="text.secondary">AI-assisted narrative：{report.status === 'gemma_corrected' ? `${report.model}（部分欄位經規則模板校正）` : (report.model || 'deterministic template')}{report.edited_at ? ` · Edited ${report.edited_at}` : ''}</Typography>
      <Divider sx={{ my: 1.5 }} />
      {narrativeFields.map(([key, label]) => <Box key={key} sx={{ mt: 2 }}><Typography variant="h6" fontWeight={850}>{label}</Typography>{editing ? <TextField fullWidth multiline minRows={2} value={draft[key] || ''} onChange={event => edit(key, event.target.value)} sx={{ mt: 1 }} /> : <Typography sx={{ whiteSpace: 'pre-wrap' }}>{draft[key] || '—'}</Typography>}</Box>)}
      <Box sx={{ mt: 2 }}><Typography variant="h6" fontWeight={850}>限制</Typography>{editing ? <TextField fullWidth multiline minRows={4} value={(draft.limitations || []).join('\n')} onChange={event => edit('limitations', event.target.value.split('\n'))} helperText="每行一項" /> : <ul>{(draft.limitations || []).map((item, index) => <li key={index}><Typography>{item}</Typography></li>)}</ul>}</Box>
    </Paper>
    <Paper variant="outlined" sx={{ p: 2.5, mb: 3 }}>
      <Typography variant="h6" fontWeight={850}>TSO500 TMB proxy</Typography>
      <Typography sx={{ mt: 1 }}>{tmb.tmb_numerator_variants} unique coding variants ÷ {tmb.panel_size_mb} Mb = <strong>{Number(tmb.tmb_proxy_mut_per_mb || 0).toFixed(2)} mut/Mb</strong></Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{tmb.method}</Typography>
      {(tmb.limitations || []).map(item => <Typography key={item} variant="body2" color="warning.main" sx={{ mt: .75 }}>• {item}</Typography>)}
    </Paper>
    <Typography variant="h5" fontWeight={850} sx={{ mb: 1 }}>High Risk / Oncogenicity</Typography>
    <WgsResultTable analysisId={analysisId} somatic rows={base.high_risk || []} emptyMessage="No variants met the WGS-like high-risk gate." />
    <Typography variant="h5" fontWeight={850} sx={{ mt: 4, mb: 1 }}>Complete analysis inventory</Typography>
    <TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell sx={{ fontWeight: 800 }}>Analysis section</TableCell><TableCell sx={{ fontWeight: 800 }}>Available</TableCell><TableCell sx={{ fontWeight: 800 }}>Records</TableCell></TableRow></TableHead><TableBody>{Object.entries(base.sections || {}).map(([name, data]) => <TableRow key={name}><TableCell>{name.replaceAll('_', ' ')}</TableCell><TableCell><Chip size="small" color={data.available ? 'success' : 'default'} label={data.available ? 'Available' : 'Not available'} /></TableCell><TableCell>{data.count ?? '—'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>
    {(base.mutational_signatures || []).length > 0 && <Paper variant="outlined" sx={{ p: 2.5, mt: 3 }}><Typography variant="h6" fontWeight={850}>Top mutational signatures</Typography><Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1 }}>{base.mutational_signatures.map(item => <Chip key={item.signature} label={`${item.signature}: ${item.activity}`} />)}</Stack></Paper>}
    <Alert severity="warning" sx={{ mt: 3 }}>{report.disclaimer}</Alert>
  </Box>;
}

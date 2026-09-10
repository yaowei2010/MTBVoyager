import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Chip, CircularProgress, Grid, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
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
  useEffect(() => {
    setError('');
    axios.get(`${config.rootApiIP}/wgs-somatic/legacy-jobs/${analysisId}/mtb-report`)
      .then(response => setReport(response.data))
      .catch(reason => setError(reason.response?.data?.detail || 'Unable to generate MTB draft report.'));
  }, [analysisId]);
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!report) return <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress /><Typography sx={{ mt: 2 }}>Preparing the complete tumor-only draft…</Typography></Box>;
  const tmb = report.tmb_estimate || {};
  return <Box>
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
      <Box><Typography variant="overline" color="primary">MOLECULAR TUMOR BOARD</Typography><Typography variant="h4" fontWeight={900}>Legacy tumor-only draft report</Typography><Typography color="text.secondary">Analysis {report.analysis_id} · {report.genome_build}</Typography></Box>
      <Chip color="warning" label="DRAFT · PROFESSIONAL REVIEW REQUIRED" />
    </Stack>
    <Alert severity="warning" sx={{ mb: 3}}>Existing pipeline quality settings are unchanged. High risk: {report.reporting_gate}. No liftover is applied.</Alert>
    <Grid container spacing={2} sx={{ mb: 3 }}>
      <Grid item xs={12} md={4}><Metric label="High-risk variants" value={report.summary?.high_risk_count} color="#d32f2f" /></Grid>
      <Grid item xs={12} md={4}><Metric label="Oncogenicity candidates" value={report.summary?.oncogenicity_candidates} /></Grid>
      <Grid item xs={12} md={4}><Metric label="Estimated TMB proxy" value={`${Number(tmb.tmb_proxy_mut_per_mb || 0).toFixed(2)} mut/Mb`} color="#ed6c02" /></Grid>
    </Grid>
    <Paper variant="outlined" sx={{ p: 2.5, mb: 3 }}>
      <Typography variant="h6" fontWeight={850}>TSO500 TMB proxy</Typography>
      <Typography sx={{ mt: 1 }}>{tmb.tmb_numerator_variants} unique coding variants ÷ {tmb.panel_size_mb} Mb = <strong>{Number(tmb.tmb_proxy_mut_per_mb || 0).toFixed(2)} mut/Mb</strong></Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>{tmb.method}</Typography>
      {(tmb.limitations || []).map(item => <Typography key={item} variant="body2" color="warning.main" sx={{ mt: .75 }}>• {item}</Typography>)}
    </Paper>
    <Typography variant="h5" fontWeight={850} sx={{ mb: 1 }}>High Risk / Oncogenicity</Typography>
    <WgsResultTable analysisId={analysisId} somatic rows={report.high_risk || []} emptyMessage="No variants met the WGS-like high-risk gate." />
    <Typography variant="h5" fontWeight={850} sx={{ mt: 4, mb: 1 }}>Complete analysis inventory</Typography>
    <TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell sx={{ fontWeight: 800 }}>Analysis section</TableCell><TableCell sx={{ fontWeight: 800 }}>Available</TableCell><TableCell sx={{ fontWeight: 800 }}>Records</TableCell></TableRow></TableHead><TableBody>{Object.entries(report.sections || {}).map(([name, data]) => <TableRow key={name}><TableCell>{name.replaceAll('_', ' ')}</TableCell><TableCell><Chip size="small" color={data.available ? 'success' : 'default'} label={data.available ? 'Available' : 'Not available'} /></TableCell><TableCell>{data.count ?? '—'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>
    {(report.mutational_signatures || []).length > 0 && <Paper variant="outlined" sx={{ p: 2.5, mt: 3 }}><Typography variant="h6" fontWeight={850}>Top mutational signatures</Typography><Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1 }}>{report.mutational_signatures.map(item => <Chip key={item.signature} label={`${item.signature}: ${item.activity}`} />)}</Stack></Paper>}
    <Alert severity="warning" sx={{ mt: 3 }}>{report.disclaimer}</Alert>
  </Box>;
}

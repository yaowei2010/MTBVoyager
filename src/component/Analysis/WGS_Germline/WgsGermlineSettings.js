import React, { useState } from 'react';
import { Alert, Box, Button, Chip, Divider, FormControl, FormControlLabel, Grid, InputLabel, MenuItem, Paper, Radio, RadioGroup, Select, Stack, Switch, TextField, Typography } from '@mui/material';
import FilterAltOutlinedIcon from '@mui/icons-material/FilterAltOutlined';
import HubOutlinedIcon from '@mui/icons-material/HubOutlined';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { config } from '../../../constant';
import WgsAnalysisHeader from './WgsAnalysisHeader';
import PhenotypeAutocomplete from './PhenotypeAutocomplete';
import { cardSx, contentSx, pageSx, primaryButtonSx, secondaryButtonSx, sectionTitleSx } from './wgsUi';

const populations = ['gnomAD_EAS', 'gnomAD_AFR', 'gnomAD_AMR', 'gnomAD_ASJ', 'gnomAD_FIN', 'gnomAD_NFE', 'gnomAD_SAS', 'gnomAD_GLOBAL'];

export default function WgsGermlineSettings() {
  const navigate = useNavigate();
  const [settings, setSettings] = useState({ pass_only: true, min_dp_cutoff: 20, min_vaf: 0.2, maf_cutoff: 0.01, population: 'gnomAD_EAS', phenotypes: [], phenotype_include_descendants: true });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const set = (key, value) => setSettings((old) => ({ ...old, [key]: value }));

  const submit = async () => {
    const draft = JSON.parse(sessionStorage.getItem('wgsGermlineDraft') || '{}');
    if (!draft.upload_id) return setError('The WGS upload session is missing. Please upload the three VCF files again.');
    setSubmitting(true); setError('');
    try {
      await axios.post(`${config.rootApiIP}/wgs-germline/jobs`, {
        draft_id: draft.draft_id, upload_id: draft.upload_id, analysis_type: 'wgs_germline', genome_build: 'hg38',
        ...settings,
        phenotypes: settings.phenotypes.map(({ id, label, name }) => ({ mondo_id: id, label: label || name })),
      });
      sessionStorage.removeItem('wgsGermlineDraft');
      navigate(`${config.rootPathPrefix}/Job_results`);
    } catch (e) { setError(e.response?.data?.detail || 'Unable to start the WGS germline analysis.'); }
    finally { setSubmitting(false); }
  };

  return (
    <Box sx={pageSx}><Box sx={contentSx}>
      <WgsAnalysisHeader activeStep={2} />
      {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} sx={{ mb: 3 }}><Chip label="GRCh38" color="primary" variant="outlined" /><Chip label={settings.population} sx={{ bgcolor: '#e8f7f2', color: '#087f5b', fontWeight: 700 }} /><Chip label={`${settings.phenotypes.length} MONDO phenotypes`} variant="outlined" /></Stack>
      <Paper sx={{ ...cardSx, mb: 3 }}>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mb: 3 }}><Box sx={{ p: 1.1, display: 'flex', borderRadius: 2, bgcolor: '#e7f4ff', color: '#0b67b2' }}><FilterAltOutlinedIcon /></Box><Box><Typography variant="h5" sx={sectionTitleSx}>Variant filtering</Typography><Typography color="text.secondary">Quality and population-frequency thresholds applied to candidate variants.</Typography></Box></Stack>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}><TextField fullWidth disabled label="Genome build" value="hg38" /></Grid>
          <Grid item xs={12} md={6}><FormControl fullWidth><InputLabel>Population frequency</InputLabel><Select label="Population frequency" value={settings.population} onChange={(e) => set('population', e.target.value)}>{populations.map((p) => <MenuItem key={p} value={p}>{p}</MenuItem>)}</Select></FormControl></Grid>
          <Grid item xs={12}><RadioGroup row value={settings.pass_only ? 'pass' : 'all'} onChange={(e) => set('pass_only', e.target.value === 'pass')}><FormControlLabel value="all" control={<Radio />} label="Use all variants" /><FormControlLabel value="pass" control={<Radio />} label="Use only PASS variants" /></RadioGroup></Grid>
          <Grid item xs={12} md={4}><TextField fullWidth type="number" label="Minimum depth" value={settings.min_dp_cutoff} onChange={(e) => set('min_dp_cutoff', Number(e.target.value))} /></Grid>
          <Grid item xs={12} md={4}><TextField fullWidth type="number" label="Minimum VAF" inputProps={{ step: 0.01, min: 0, max: 1 }} value={settings.min_vaf} onChange={(e) => set('min_vaf', Number(e.target.value))} /></Grid>
          <Grid item xs={12} md={4}><TextField fullWidth type="number" label="Maximum population AF" inputProps={{ step: 0.001, min: 0, max: 1 }} value={settings.maf_cutoff} onChange={(e) => set('maf_cutoff', Number(e.target.value))} /></Grid>
        </Grid>
      </Paper>
      <Paper sx={cardSx}>
        <Stack direction="row" spacing={1.5} alignItems="center"><Box sx={{ p: 1.1, display: 'flex', borderRadius: 2, bgcolor: '#e8f7f2', color: '#087f5b' }}><HubOutlinedIcon /></Box><Box><Typography variant="h5" sx={sectionTitleSx}>Phenotype-guided prioritization</Typography><Typography color="text.secondary">Connect clinical disease concepts to their associated human gene sets.</Typography></Box></Stack>
        <Divider sx={{ my: 3 }} />
        <Alert severity="info" variant="outlined" sx={{ mb: 3, borderRadius: 2 }}>Phenotype Variant includes non-conflicting, reviewed/valid P or LP variants in genes associated with the selected MONDO diseases.</Alert>
        <PhenotypeAutocomplete value={settings.phenotypes} onChange={(items) => set('phenotypes', items)} />
        <FormControlLabel sx={{ mt: 2 }} control={<Switch checked={settings.phenotype_include_descendants} onChange={(e) => set('phenotype_include_descendants', e.target.checked)} />} label="Include descendant MONDO diseases when resolving the gene set" />
      </Paper>
      <Stack direction={{ xs: 'column-reverse', sm: 'row' }} spacing={2} justifyContent="center" sx={{ mt: 5 }}><Button variant="outlined" onClick={() => navigate(`${config.rootPathPrefix}/Analysis/WGS_Germline/Sample`)} sx={secondaryButtonSx}>Previous</Button><Button variant="contained" disabled={submitting} onClick={submit} sx={primaryButtonSx}>{submitting ? 'Starting…' : 'Start WGS analysis'}</Button></Stack>
    </Box></Box>
  );
}

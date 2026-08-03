import React, { useContext, useState } from 'react';
import { Alert, Box, Button, Chip, FormControl, FormControlLabel, FormLabel, Grid, Paper, Radio, RadioGroup, Stack, TextField, Typography } from '@mui/material';
import BiotechOutlinedIcon from '@mui/icons-material/BiotechOutlined';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { config } from '../../../constant';
import { AuthContext } from '../../Auth/AuthContext';
import WgsAnalysisHeader from './WgsAnalysisHeader';
import { cardSx, contentSx, pageSx, primaryButtonSx, secondaryButtonSx, sectionTitleSx } from './wgsUi';

export default function WgsGermlineSubject() {
  const navigate = useNavigate();
  const { userId } = useContext(AuthContext);
  const [form, setForm] = useState({ subject_id: '', dob: '', gender: 'male', history: '' });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const change = (key) => (event) => setForm((value) => ({ ...value, [key]: event.target.value }));

  const next = async () => {
    if (!form.subject_id.trim()) return setError('Subject ID is required.');
    setSaving(true);
    setError('');
    try {
      const { data } = await axios.post(`${config.rootApiIP}/wgs-germline/subject`, {
        ...form, protocol: 'WGS Germline', genome_build: 'hg38', user_id: userId,
      });
      sessionStorage.setItem('wgsGermlineDraft', JSON.stringify({ subject: form, draft_id: data?.draft_id || data?.id || null }));
      navigate(`${config.rootPathPrefix}/Analysis/WGS_Germline/Sample`);
    } catch (e) {
      setError(e.response?.data?.detail || 'Unable to save the WGS germline subject. The WGS backend endpoint may not be available yet.');
    } finally { setSaving(false); }
  };

  return (
    <Box sx={pageSx}><Box sx={contentSx}>
      <WgsAnalysisHeader activeStep={0} />
      {error && <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>{error}</Alert>}
      <Paper sx={cardSx}>
        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 3 }}>
          <Box sx={{ p: 1.25, display: 'flex', borderRadius: 2, bgcolor: '#e7f4ff', color: '#0b67b2' }}><BiotechOutlinedIcon /></Box>
          <Box><Typography variant="h5" sx={sectionTitleSx}>Patient & specimen context</Typography><Typography color="text.secondary">Clinical metadata associated with this germline analysis.</Typography></Box>
          <Chip label="GRCh38" color="primary" variant="outlined" sx={{ ml: 'auto !important', fontWeight: 700 }} />
        </Stack>
        <Grid container spacing={3}>
        <Grid item xs={12} md={6}><TextField fullWidth required variant="filled" label="Subject ID" value={form.subject_id} onChange={change('subject_id')} /></Grid>
        <Grid item xs={12} md={6}><TextField fullWidth disabled variant="filled" label="Protocol" value="WGS Germline (hg38)" /></Grid>
        <Grid item xs={12} md={6}><TextField fullWidth type="date" variant="filled" label="Date of Birth" InputLabelProps={{ shrink: true }} value={form.dob} onChange={change('dob')} /></Grid>
        <Grid item xs={12} md={6}><FormControl><FormLabel>Gender</FormLabel><RadioGroup row value={form.gender} onChange={change('gender')}><FormControlLabel value="male" control={<Radio />} label="Male" /><FormControlLabel value="female" control={<Radio />} label="Female" /></RadioGroup></FormControl></Grid>
        <Grid item xs={12}><TextField fullWidth multiline rows={3} variant="filled" label="History / Description" value={form.history} onChange={change('history')} /></Grid>
        </Grid>
      </Paper>
      <Stack direction={{ xs: 'column-reverse', sm: 'row' }} spacing={2} justifyContent="center" sx={{ mt: 5 }}>
        <Button variant="outlined" onClick={() => navigate(`${config.rootPathPrefix}/Analysis/Protocol`)} sx={secondaryButtonSx}>Previous</Button>
        <Button variant="contained" disabled={saving} onClick={next} sx={primaryButtonSx}>{saving ? 'Saving…' : 'Continue to inputs'}</Button>
      </Stack>
    </Box></Box>
  );
}

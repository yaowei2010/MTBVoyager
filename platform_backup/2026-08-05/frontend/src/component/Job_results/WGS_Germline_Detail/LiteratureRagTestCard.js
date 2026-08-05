import React, { useState } from 'react';
import { Alert, Box, Button, Chip, CircularProgress, Paper, Stack, TextField, Typography } from '@mui/material';
import AutoStoriesOutlinedIcon from '@mui/icons-material/AutoStoriesOutlined';
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined';
import axios from 'axios';
import { config } from '../../../constant';
import GeneLiteratureDrawer from './GeneLiteratureDrawer';

const genePattern = /^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$/;

export default function LiteratureRagTestCard({ analysisId }) {
  const [gene, setGene] = useState('TSC2');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);

  const normalizedGene = gene.trim().toUpperCase();
  const valid = genePattern.test(normalizedGene);

  const run = async () => {
    if (!valid || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    setOpen(true);
    try {
      const { data } = await axios.post(
        `${config.rootApiIP}/wgs-germline/jobs/${analysisId}/literature`,
        { gene: normalizedGene, variant: '', refresh: false },
      );
      setResult(data);
    } catch (requestError) {
      const timedOut = requestError.response?.status === 504;
      setError(requestError.response?.data?.detail || (timedOut ? 'The local model is still generating. Please retry in a moment; the completed result will be cached.' : 'Unable to retrieve or generate the literature summary.'));
    } finally {
      setLoading(false);
    }
  };

  return <>
    <Paper sx={{ p: { xs: 2, md: 2.5 }, mb: 3, borderRadius: 3, border: '1px solid #cfe3ee', background: 'linear-gradient(135deg,#f7fcff 0%,#eef9f6 100%)', boxShadow: '0 10px 28px rgba(26,72,112,.06)' }}>
      <Stack direction={{ xs: 'column', lg: 'row' }} spacing={2.5} alignItems={{ lg: 'center' }} justifyContent="space-between">
        <Stack direction="row" spacing={1.5} alignItems="flex-start">
          <Box sx={{ p: 1.1, display: 'flex', borderRadius: 2, bgcolor: '#dff5ef', color: '#087f5b' }}><ScienceOutlinedIcon /></Box>
          <Box>
            <Typography variant="h6" fontWeight={850} color="#16324f">Literature RAG test</Typography>
            <Typography color="text.secondary">Test a gene against this report. A cache miss runs the local model and stores the response automatically.</Typography>
          </Box>
        </Stack>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.25} sx={{ minWidth: { lg: 470 } }}>
          <TextField
            fullWidth size="small" label="Gene symbol" value={gene}
            onChange={(event) => setGene(event.target.value.toUpperCase())}
            onKeyDown={(event) => { if (event.key === 'Enter') run(); }}
            error={Boolean(gene) && !valid} helperText={Boolean(gene) && !valid ? 'Enter a valid gene symbol.' : 'Try TSC2, BRCA1 or CALM1'}
          />
          <Button variant="contained" disabled={!valid || loading} onClick={run} startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <AutoStoriesOutlinedIcon />} sx={{ minWidth: 170, height: 40 }}>
            {loading ? 'Generating…' : 'Run inference'}
          </Button>
        </Stack>
      </Stack>
      {result && <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
        <Chip size="small" color={result.cache?.hit ? 'success' : 'primary'} label={result.cache?.hit ? 'Cache hit' : 'Cache miss'} />
        <Chip size="small" variant="outlined" label={result.inference_performed ? 'Inference performed' : 'Inference skipped'} />
        <Chip size="small" variant="outlined" label={`${result.articles?.length || 0} publications`} />
        <Chip size="small" variant="outlined" label={result.status || 'unknown'} />
        <Button size="small" onClick={() => setOpen(true)}>View result</Button>
      </Stack>}
      {error && !open && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    </Paper>
    <GeneLiteratureDrawer open={open} onClose={() => setOpen(false)} gene={normalizedGene} data={result} loading={loading} error={error} />
  </>;
}

import React, { useRef, useState } from 'react';
import { Alert, Box, Button, Chip, LinearProgress, Paper, Stack, TextField, Typography } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { config } from '../../../constant';
import WgsAnalysisHeader from './WgsAnalysisHeader';
import { cardSx, contentSx, pageSx, primaryButtonSx, secondaryButtonSx, sectionTitleSx } from './wgsUi';

const inputs = [
  { key: 'snv', label: 'SNV hard-filtered VCF', suffix: '.hard-filtered.vcf.gz' },
  { key: 'sv', label: 'Structural Variant VCF', suffix: '.sv.vcf.gz' },
  { key: 'cnv', label: 'Copy Number Variant VCF', suffix: '.cnv.vcf.gz' },
];

function FileField({ spec, file, onChange }) {
  const ref = useRef();
  const valid = !file || file.name.toLowerCase().endsWith(spec.suffix);
  return (
    <Paper sx={{ ...cardSx, transition: 'transform .18s ease, border-color .18s ease', '&:hover': { transform: 'translateY(-2px)', borderColor: '#79b8e8' } }}>
      <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
        <Box sx={{ width: 42, height: 42, display: 'grid', placeItems: 'center', borderRadius: 2, bgcolor: file && valid ? '#e8f7f2' : '#edf5fc', color: file && valid ? '#087f5b' : '#1769aa' }}><UploadFileIcon /></Box>
        <Box><Typography variant="h6" sx={sectionTitleSx}>{spec.label}</Typography><Typography variant="body2" color="text.secondary">Required filename: *{spec.suffix}</Typography></Box>
        {file && valid && <Chip label="Ready" size="small" color="success" sx={{ ml: 'auto !important', fontWeight: 700 }} />}
      </Stack>
      <input hidden ref={ref} type="file" accept=".vcf.gz,.gz" onChange={(e) => onChange(e.target.files?.[0] || null)} />
      <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="center">
        <TextField fullWidth disabled value={file?.name || ''} error={!valid} helperText={!valid ? `File must end with ${spec.suffix}` : file ? `${(file.size / 1048576).toFixed(1)} MB` : ' '} />
        <Button variant="contained" startIcon={<UploadFileIcon />} onClick={() => ref.current.click()}>Browse</Button>
        {file && <Button color="error" startIcon={<DeleteOutlineIcon />} onClick={() => onChange(null)}>Remove</Button>}
      </Stack>
    </Paper>
  );
}

export default function WgsGermlineSample() {
  const navigate = useNavigate();
  const [files, setFiles] = useState({ snv: null, sv: null, cnv: null });
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const isValid = inputs.every(({ key, suffix }) => files[key] && files[key].name.toLowerCase().endsWith(suffix) && files[key].size > 0);

  const upload = async () => {
    if (!isValid) return setError('All three VCF inputs are required and must match the expected filenames.');
    const draft = JSON.parse(sessionStorage.getItem('wgsGermlineDraft') || '{}');
    const body = new FormData();
    body.append('snv', files.snv); body.append('sv', files.sv); body.append('cnv', files.cnv);
    if (draft.draft_id) body.append('draft_id', draft.draft_id);
    setUploading(true); setError('');
    try {
      const { data } = await axios.post(`${config.rootApiIP}/wgs-germline/upload`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => setProgress(e.total ? Math.round((e.loaded * 100) / e.total) : 0),
      });
      sessionStorage.setItem('wgsGermlineDraft', JSON.stringify({ ...draft, upload_id: data?.upload_id || data?.id, files: Object.fromEntries(inputs.map(({ key }) => [key, files[key].name])) }));
      navigate(`${config.rootPathPrefix}/Analysis/WGS_Germline/Settings`);
    } catch (e) { setError(e.response?.data?.detail || 'Unable to upload WGS input files.'); }
    finally { setUploading(false); }
  };

  return (
    <Box sx={pageSx}><Box sx={contentSx}>
      <WgsAnalysisHeader activeStep={1} />
      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}
      <Box sx={{ mb: 2 }}><Typography variant="h5" sx={sectionTitleSx}>Genomic callsets</Typography><Typography color="text.secondary">Provide the normalized callsets produced by the WGS secondary analysis pipeline.</Typography></Box>
      <Stack spacing={2.5}>{inputs.map((spec) => <FileField key={spec.key} spec={spec} file={files[spec.key]} onChange={(file) => setFiles((old) => ({ ...old, [spec.key]: file }))} />)}</Stack>
      {uploading && <Paper sx={{ ...cardSx, mt: 3 }}><Stack direction="row" justifyContent="space-between"><Typography fontWeight={700}>Secure upload</Typography><Typography color="primary">{progress}%</Typography></Stack><LinearProgress variant="determinate" value={progress} sx={{ mt: 1.5, height: 8, borderRadius: 4 }} /></Paper>}
      <Stack direction={{ xs: 'column-reverse', sm: 'row' }} spacing={2} justifyContent="center" sx={{ mt: 5 }}><Button variant="outlined" onClick={() => navigate(`${config.rootPathPrefix}/Analysis/WGS_Germline/Subject`)} sx={secondaryButtonSx}>Previous</Button><Button variant="contained" disabled={!isValid || uploading} onClick={upload} sx={primaryButtonSx}>{uploading ? 'Uploading…' : 'Continue to settings'}</Button></Stack>
    </Box></Box>
  );
}

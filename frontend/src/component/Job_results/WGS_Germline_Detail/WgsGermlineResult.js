import React, { useEffect, useState } from 'react';
import { Alert, Box, Chip, CircularProgress, Divider, Paper, Stack, Tab, Tabs, Typography } from '@mui/material';
import BiotechOutlinedIcon from '@mui/icons-material/BiotechOutlined';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { config } from '../../../constant';
import WgsResultTable from './WgsResultTable';

const snvTabs = [
  { value: 'phenotype', label: 'Phenotype Variant' },
  { value: 'known_pathogenic', label: 'Known Pathogenic Variant' },
  {
    value: 'acmg_sf', label: 'ACMG-SF Candidates', severity: 'info',
    description: 'P/LP protein-altering or essential splice variants in ACMG-SF v3.3 genes that passed quality and population-frequency filters. Inheritance Status explains whether each genotype satisfies its gene-specific reporting rule.',
    emptyMessage: 'No variants met the ACMG-SF v3.3 candidate criteria.',
  },
  {
    value: 'acmg_sf_inheritance', label: 'Inheritance-matched ACMG-SF', severity: 'success',
    description: 'Only candidates whose zygosity and variant type satisfy the ACMG-SF v3.3 gene-specific reporting rule are shown. Unphased possible compound heterozygotes remain in ACMG-SF Candidates.',
    emptyMessage: 'No ACMG-SF candidate had a confirmed inheritance-rule match. Review carrier, unphased and unable-to-assess records in ACMG-SF Candidates.',
  },
  { value: 'in_silico', label: 'In-silico Prediction Variant' },
];
const svTabs = [{ value: 'known_pathogenic', label: 'Known Pathogenic SV' }, { value: 'acmg_sf', label: 'ACMG SF SV' }];

function NestedResults({ tabs, data, loading, errors, analysisId }) {
  const [tab, setTab] = useState(tabs[0].value);
  const selected = tabs.find(({ value }) => value === tab) || tabs[0];
  const count = Array.isArray(data[tab]) ? data[tab].length : 0;
  return <>
    <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable" sx={{ mb: 2, minHeight: 44, '& .MuiTab-root': { minHeight: 44, textTransform: 'none', fontWeight: 700, borderRadius: 2, mr: 1 }, '& .Mui-selected': { bgcolor: '#eaf4fc' } }}>
      {tabs.map(({ value, label }) => <Tab key={value} value={value} label={label} />)}
    </Tabs>
    {selected.description && <Alert severity={selected.severity} variant="outlined" sx={{ mb: 2.5, borderRadius: 2 }} action={<Chip size="small" label={`${count} result${count === 1 ? '' : 's'}`} sx={{ fontWeight: 800 }} />}>{selected.description}</Alert>}
    <WgsResultTable analysisId={analysisId} rows={data[tab]} loading={loading[tab]} error={errors[tab]} emptyMessage={selected.emptyMessage} />
  </>;
}

export default function WgsGermlineResult() {
  const { analysis_ID: analysisId } = useParams();
  const [section, setSection] = useState('snv');
  const [meta, setMeta] = useState(null);
  const [data, setData] = useState({ snv: {}, sv: {}, pharmcat: [] });
  const [loading, setLoading] = useState({ meta: true, snv: {}, sv: {}, pharmcat: false });
  const [errors, setErrors] = useState({ snv: {}, sv: {}, pharmcat: '' });

  useEffect(() => {
    let active = true;
    axios.get(`${config.rootApiIP}/wgs-germline/jobs/${analysisId}`).then(({ data }) => active && setMeta(data)).catch(() => {}).finally(() => active && setLoading((old) => ({ ...old, meta: false })));
    return () => { active = false; };
  }, [analysisId]);

  useEffect(() => {
    let active = true;
    const loadCategory = async (kind, category) => {
      setLoading((old) => ({ ...old, [kind]: { ...old[kind], [category]: true } }));
      try {
        const { data: response } = await axios.get(`${config.rootApiIP}/wgs-germline/jobs/${analysisId}/${kind}`, { params: { category } });
        if (active) setData((old) => ({ ...old, [kind]: { ...old[kind], [category]: Array.isArray(response) ? response : response?.results || response?.rows || [] } }));
      } catch (e) {
        if (active) setErrors((old) => ({ ...old, [kind]: { ...old[kind], [category]: e.response?.data?.detail || `Unable to load ${kind.toUpperCase()} results.` } }));
      } finally { if (active) setLoading((old) => ({ ...old, [kind]: { ...old[kind], [category]: false } })); }
    };
    if (section === 'snv') snvTabs.forEach(({ value: category }) => { if (!data.snv[category] && !loading.snv[category]) loadCategory('snv', category); });
    if (section === 'sv') svTabs.forEach(({ value: category }) => { if (!data.sv[category] && !loading.sv[category]) loadCategory('sv', category); });
    if (section === 'pharmcat' && !loading.pharmcat && data.pharmcat.length === 0 && !errors.pharmcat) {
      setLoading((old) => ({ ...old, pharmcat: true }));
      axios.get(`${config.rootApiIP}/wgs-germline/jobs/${analysisId}/pharmcat`).then(({ data: response }) => active && setData((old) => ({ ...old, pharmcat: Array.isArray(response) ? response : response?.results || response?.rows || [] }))).catch((e) => active && setErrors((old) => ({ ...old, pharmcat: e.response?.data?.detail || 'Unable to load PharmCAT results.' }))).finally(() => active && setLoading((old) => ({ ...old, pharmcat: false })));
    }
    return () => { active = false; };
    // Category state intentionally controls lazy loading.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, analysisId]);

  return (
    <Box sx={{ minHeight: '100vh', px: { xs: 2, md: 4 }, py: 4, mr: { md: 8 }, mb: 10, background: 'linear-gradient(180deg,#f5faff 0%,#fff 45%)' }}>
      <Box sx={{ maxWidth: 1500, mx: 'auto' }}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ md: 'center' }} spacing={2}>
        <Box><Chip label="GERMLINE INTERPRETATION" size="small" sx={{ mb: 1.5, bgcolor: '#e8f7f2', color: '#087f5b', fontWeight: 800, letterSpacing: '.06em' }} /><Typography variant="h3" sx={{ fontSize: { xs: 34, md: 48 }, fontWeight: 800, letterSpacing: '-.035em', color: '#102a43' }}>WGS clinical findings</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Phenotype-aware SNV, SV and pharmacogenomic interpretation</Typography></Box>
        <Box sx={{ width: 58, height: 58, borderRadius: 3, display: 'grid', placeItems: 'center', bgcolor: '#e7f4ff', color: '#0b67b2' }}><BiotechOutlinedIcon fontSize="large" /></Box>
      </Stack>
      <Paper sx={{ p: { xs: 2, md: 2.5 }, my: 3, borderRadius: 3, border: '1px solid #dce8f1', boxShadow: '0 10px 30px rgba(26,72,112,.07)' }}>
        {meta?.is_demo && <Alert severity="warning" variant="filled" sx={{ mb: 2, borderRadius: 2, fontWeight: 700 }}>{meta.demo_notice || 'Demo data only — not for clinical use.'}</Alert>}
        {loading.meta ? <CircularProgress size={24} /> : meta ? <Stack spacing={2}><Box sx={{ display: 'flex', gap: 1.25, flexWrap: 'wrap' }}><Chip label={`Analysis ${analysisId}`} sx={{ fontWeight: 700 }} /><Chip label={`Subject ${meta.subject_id || meta.subject || '-'}`} /><Chip label={meta.population || 'gnomAD_EAS'} color="success" variant="outlined" /><Chip label="GRCh38" color="primary" variant="outlined" /></Box>{(meta.phenotypes || []).length > 0 && <><Divider /><Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>{(meta.phenotypes || []).map((p) => <Chip key={p.mondo_id || p.id} color="primary" variant="outlined" label={`${p.mondo_id || p.id} ${p.label || ''}`} />)}</Box></>}</Stack> : <Alert severity="warning">Analysis metadata is not available.</Alert>}
      </Paper>
      <Paper sx={{ borderRadius: 3, border: '1px solid #dce8f1', overflow: 'hidden', boxShadow: '0 14px 38px rgba(26,72,112,.08)' }}><Tabs value={section} onChange={(_, value) => setSection(value)} variant="fullWidth" sx={{ bgcolor: '#102f4f', '& .MuiTab-root': { minHeight: 62, color: 'rgba(255,255,255,.72)', textTransform: 'none', fontSize: 16, fontWeight: 750 }, '& .Mui-selected': { color: '#fff !important', bgcolor: 'rgba(37,160,184,.2)' }, '& .MuiTabs-indicator': { height: 4, bgcolor: '#38c6b2' } }}><Tab value="snv" label="SNV" /><Tab value="sv" label="SV" /><Tab value="cnv" label="CNV · Coming soon" disabled /><Tab value="pharmcat" label="PharmCat" /></Tabs><Box sx={{ p: { xs: 2, md: 3 } }}>{section === 'snv' && <NestedResults analysisId={analysisId} tabs={snvTabs} data={data.snv} loading={loading.snv} errors={errors.snv} />}{section === 'sv' && <NestedResults analysisId={analysisId} tabs={svTabs} data={data.sv} loading={loading.sv} errors={errors.sv} />}{section === 'pharmcat' && <WgsResultTable analysisId={analysisId} rows={data.pharmcat} loading={loading.pharmcat} error={errors.pharmcat} emptyMessage="No PharmCAT drug and star-allele relationships were reported." />}</Box></Paper>
      </Box>
    </Box>
  );
}

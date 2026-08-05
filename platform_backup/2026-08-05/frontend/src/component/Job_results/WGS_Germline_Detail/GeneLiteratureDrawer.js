import React from 'react';
import { Alert, Box, Button, Chip, CircularProgress, Divider, Drawer, Link, Stack, Typography } from '@mui/material';
import AutoStoriesOutlinedIcon from '@mui/icons-material/AutoStoriesOutlined';

const Narrative = ({ title, children }) => children ? <Box><Typography variant="overline" sx={{ color: '#52738f', fontWeight: 800 }}>{title}</Typography><Typography sx={{ color: '#1e3448', lineHeight: 1.7 }}>{children}</Typography></Box> : null;

export default function GeneLiteratureDrawer({ open, onClose, gene, data, loading, error }) {
  return <Drawer anchor="right" open={open} onClose={onClose} PaperProps={{ sx: { width: { xs: '100%', sm: 620 }, p: { xs: 2.5, sm: 4 }, bgcolor: '#f8fbfd' } }}>
    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
      <Box><Chip icon={<AutoStoriesOutlinedIcon />} label="LOCAL LITERATURE RAG" size="small" sx={{ mb: 1.5, bgcolor: '#e8f3ff', color: '#075a9c', fontWeight: 800 }} /><Typography variant="h4" fontWeight={850} color="#102f4f">{gene || 'Gene'} evidence</Typography><Typography color="text.secondary">PubMed retrieval · local database · locally hosted model</Typography></Box>
      <Button onClick={onClose}>Close</Button>
    </Stack>
    <Alert severity="info" sx={{ my: 3 }}>AI-generated literature summary. It does not determine ACMG classification and must be reviewed against the cited publications.</Alert>
    {loading && <Box sx={{ py: 8, textAlign: 'center' }}><CircularProgress /><Typography sx={{ mt: 2 }} color="text.secondary">Retrieving local evidence and generating summary…</Typography></Box>}
    {error && <Alert severity="error">{error}</Alert>}
    {!loading && data && <Stack spacing={2.5}>
      <Stack direction="row" spacing={1} flexWrap="wrap"><Chip label={`${data.articles?.length || 0} retrieved records`} /><Chip label={data.retrieval_source === 'local' ? 'Local cache' : 'PubMed refreshed'} color="success" variant="outlined" />{data.status === 'model_unavailable' && <Chip label="Model unavailable" color="warning" />}</Stack>
      <Narrative title="Gene–disease relationship">{data.summary}</Narrative>
      <Narrative title="Phenotype relevance">{data.phenotype_relevance}</Narrative>
      <Narrative title="Inheritance">{data.inheritance}</Narrative>
      <Narrative title="Variant-specific evidence">{data.variant_evidence}</Narrative>
      {data.limitations?.length > 0 && <Box><Typography variant="overline" sx={{ color: '#52738f', fontWeight: 800 }}>Limitations</Typography>{data.limitations.map((item, index) => <Typography key={index} component="li" sx={{ ml: 2.5, color: '#475f73' }}>{item}</Typography>)}</Box>}
      {data.citations?.length > 0 && <Box><Typography variant="overline" sx={{ color: '#52738f', fontWeight: 800 }}>Validated citations</Typography><Stack spacing={1}>{data.citations.map((citation) => <Box key={citation.pmid} sx={{ pl: 1.5, borderLeft: '3px solid #38a3a5' }}><Link href={`https://pubmed.ncbi.nlm.nih.gov/${citation.pmid}/`} target="_blank" rel="noreferrer" fontWeight={750}>PMID {citation.pmid}</Link><Typography variant="body2" color="text.secondary">{(citation.claims || []).join(' · ')}</Typography></Box>)}</Stack></Box>}
      <Divider />
      <Box><Typography variant="h6" fontWeight={800} color="#16324f" mb={1.5}>Retrieved publications</Typography><Stack spacing={1.5}>{(data.articles || []).map((article) => <Box key={article.pmid} sx={{ p: 2, border: '1px solid #dce8f1', borderRadius: 2, bgcolor: '#fff' }}><Link href={article.url} target="_blank" rel="noreferrer" underline="hover" fontWeight={750}>{article.title}</Link><Typography variant="body2" color="text.secondary" mt={.5}>PMID {article.pmid} · {article.journal || 'Journal unavailable'} · {article.year || 'Year unavailable'}</Typography></Box>)}</Stack></Box>
    </Stack>}
  </Drawer>;
}

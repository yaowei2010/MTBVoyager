import React, { useState } from 'react';
import { Alert, Box, Button, Chip, Link } from '@mui/material';
import AutoStoriesOutlinedIcon from '@mui/icons-material/AutoStoriesOutlined';
import axios from 'axios';
import { DataGrid, GridToolbar } from '@mui/x-data-grid';
import { config } from '../../../constant';
import GeneLiteratureDrawer from './GeneLiteratureDrawer';

const preferredFields = [
  ['SYMBOL', 'Gene'], ['Consequence', 'Consequence'], ['HGVSc', 'HGVS.c'], ['HGVSp', 'HGVS.p'],
  ['chromosome', 'Chromosome'], ['position', 'Position'], ['start', 'Start'], ['end', 'End'],
  ['ref', 'Ref'], ['alt', 'Alt'], ['sv_type', 'SV Type'], ['length', 'Length'], ['gene', 'Gene'],
  ['transcript', 'Transcript'], ['consequence', 'Consequence'], ['hgvsc', 'HGVS.c'], ['hgvsp', 'HGVS.p'],
  ['genotype', 'Genotype'], ['depth', 'Depth'], ['vaf', 'VAF'], ['population_af', 'Population AF'],
  ['classification', 'Classification'], ['review_status', 'Review status'], ['review_stars', 'Review stars'],
  ['normalized_pathogenicity', 'Pathogenicity'], ['clinvar_review_status', 'ClinVar Review'],
  ['clinvar_review_stars', 'ClinVar Stars'], ['clinvar_conflict', 'ClinVar Conflict'],
  ['has_conflict', 'Conflict'], ['matched_phenotypes', 'Matched phenotype'], ['mondo_ids', 'MONDO ID'],
  ['clinvar_id', 'ClinVar ID'], ['disease', 'Disease'], ['evidence', 'Evidence'],
  ['acmg_sf_disease', 'ACMG-SF Disease'], ['acmg_sf_inheritance', 'Inheritance'],
  ['zygosity', 'Zygosity'], ['inheritance_status', 'Inheritance Status'],
  ['variant', 'Variant'], ['clinvar', 'ClinVar'], ['max_population_af', 'Max population AF'],
  ['hereditary_condition', 'Hereditary condition'], ['prediction_support_count', 'Predictor support'],
  ['prediction_support', 'In-silico evidence'], ['tumor_only_status', 'Confirmation status'],
  ['inheritance_reason', 'Inheritance Assessment'], ['acmg_sf_variant_rule', 'ACMG-SF Rule'],
  ['gene_symbol', 'Gene'], ['diplotype', 'Star allele / Diplotype'], ['phenotype', 'Phenotype'],
  ['drug', 'Drug'], ['recommendation', 'Recommendation'], ['guideline', 'Guideline'], ['evidence_level', 'Evidence level'],
  ['amp_tier', 'AMP Tier'], ['source', 'Evidence source'], ['significance', 'Response / significance'],
  ['sample_genotype', 'Sample genotype'], ['clinpgx_allele', 'ClinPGx allele'], ['comparison', 'Comparator'],
  ['phenotype_category', 'Phenotype category'], ['association', 'Association'], ['annotation_id', 'ClinPGx annotation ID'],
  ['match_status', 'Match status'], ['clinpgx_release', 'ClinPGx release'], ['source_url', 'Source'],
  ['cancer_evidence_sources', 'Cancer evidence sources'], ['cancer_actionable', 'Actionable evidence'],
  ['cancer_type_match', 'Tumor type match'], ['annotsv_gene_count', 'Overlapping genes'],
  ['somatic_status', 'Somatic status'],
  ['cancer_evidence', 'Cancer evidence detail'],
  ['CLIN_SIG', 'ClinVar'], ['ClinVar_CLNSIG', 'ClinVar'],
  ['oncogenicity_classification', 'Oncogenicity'], ['oncogenicity_score', 'Oncogenicity score'],
  ['oncogenicity_criteria', 'Oncogenicity criteria'], ['oncogenicity_review_required', 'Oncogenicity review'],
  ['oncogenicity_evidence', 'Oncogenicity audit detail'],
  ['oncovi_2026_classification', 'OncoVI 2026 reference'], ['oncovi_2026_score', 'OncoVI 2026 score'],
  ['oncovi_2026_criteria', 'OncoVI 2026 criteria'], ['oncogenicity_profile_difference', 'Profile differences'],
  ['oncovi_2026_validation_status', 'OncoVI validation status'], ['oncovi_2026_evidence', 'OncoVI 2026 audit detail'],
  ['oncogenicity_input_scope', 'Oncogenicity input scope'], ['oncogenicity_coordinate_build', 'Input genome build'],
  ['oncogenicity_limitations', 'Oncogenicity limitations'],
];

const displayValue = (value) => {
  if (Array.isArray(value)) return value.join(', ');
  if (value && typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return value ?? '';
};

const variantValue = (row = {}) => {
  if (row.variant_id) return row.variant_id;
  const match = String(row['#Uploaded_variation'] || '').match(/^(.+?)_(\d+)_([^_/]+)\/(.+)$/);
  if (match) return `${match[1].startsWith('chr') ? match[1] : `chr${match[1]}`}:${match[2]}:${match[3]}:${match[4]}`;
  return row.variant || '';
};

const clinvarUrl = (row) => {
  const match = variantValue(row).match(/^chr([^:]+):(\d+):([^:]+):([^:]+)$/);
  if (!match) return 'https://www.ncbi.nlm.nih.gov/clinvar/';
  const [, chrom, position, ref, alt] = match;
  return `https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(`${chrom}[chr] AND ${position}[chrpos38] AND ${ref}>${alt}`)}`;
};

export default function WgsResultTable({ rows, loading, error, analysisId, somatic = false, emptyMessage = 'No variants matched this category.' }) {
  const [literature, setLiterature] = useState({ open: false, gene: '', data: null, loading: false, error: '' });
  const openLiterature = async (row) => {
    const gene = row.gene || row.gene_symbol || row.SYMBOL;
    const variant = [row.chromosome, row.position || row.start, row.ref, row.alt].filter(Boolean).join(':');
    setLiterature({ open: true, gene, data: null, loading: true, error: '' });
    try {
      const { data } = await axios.post(`${config.rootApiIP}/wgs-germline/jobs/${analysisId}/literature`, { gene, variant });
      setLiterature({ open: true, gene, data, loading: false, error: '' });
    } catch (requestError) {
      const timedOut = requestError.response?.status === 504;
      setLiterature({ open: true, gene, data: null, loading: false, error: requestError.response?.data?.detail || (timedOut ? 'The local model is still generating. Please retry in a moment; the completed result will be cached.' : 'Unable to generate literature summary.') });
    }
  };
  if (error) return <Alert severity="error">{error}</Alert>;
  const safeRows = Array.isArray(rows) ? rows : [];
  const keys = new Set(safeRows.flatMap((row) => Object.keys(row || {})));
  const hiddenSomaticFields = new Set(['tumor_only_status', 'somatic_status']);
  const configured = preferredFields.filter(([field]) => keys.has(field) && !(somatic && hiddenSomaticFields.has(field)));
  const syntheticFields = new Set(['variant_id', 'tumor_af', 'tumor_dp', 'gnomad_eas_af']);
  const remaining = [...keys].filter((key) => key !== 'id' && !(somatic && (hiddenSomaticFields.has(key) || syntheticFields.has(key))) && !configured.some(([field]) => field === key));
  const columns = [...configured, ...remaining.map((key) => [key, key])].map(([field, headerName]) => ({
    field, headerName, minWidth: ['recommendation', 'evidence', 'inheritance_reason', 'acmg_sf_disease', 'cancer_evidence', 'oncogenicity_evidence', 'oncovi_2026_evidence'].includes(field) ? 320 : 150, flex: 1,
    valueGetter: (value) => displayValue(value),
    renderCell: field === 'classification' ? (params) => {
      const label = displayValue(params.value);
      const pathogenic = /pathogenic|^p$|^lp$/i.test(label);
      return <Chip size="small" label={label || '—'} color={pathogenic ? 'error' : 'default'} variant={pathogenic ? 'filled' : 'outlined'} sx={{ fontWeight: 700 }} />;
    } : ['clinvar', 'CLIN_SIG', 'ClinVar_CLNSIG'].includes(field) ? (params) => {
      const label = displayValue(params.value) || '—';
      return label === '—' ? label : <Link href={clinvarUrl(params.row)} target="_blank" rel="noopener noreferrer" underline="hover" title="Verify this GRCh38 variant in NCBI ClinVar">{label}</Link>;
    } : field === 'has_conflict' || field === 'clinvar_conflict' ? (params) => {
      const conflicted = params.value === true || String(params.value).toLowerCase() === 'yes';
      return <Chip size="small" label={conflicted ? 'Conflict' : 'No conflict'} color={conflicted ? 'warning' : 'success'} variant="outlined" />;
    } : field === 'inheritance_status' ? (params) => {
      const status = String(params.value || 'unable_to_assess');
      const styles = {
        matched: { label: 'Matched', color: 'success' },
        possible_unphased: { label: 'Possible · unphased', color: 'warning' },
        carrier: { label: 'Carrier', color: 'info' },
        not_matched: { label: 'Not matched', color: 'default' },
        unable_to_assess: { label: 'Unable to assess', color: 'warning' },
      };
      const item = styles[status] || { label: status, color: 'default' };
      return <Chip size="small" label={item.label} color={item.color} variant={status === 'matched' ? 'filled' : 'outlined'} sx={{ fontWeight: 750 }} />;
    } : field === 'zygosity' ? (params) => {
      const zyg = displayValue(params.value) || 'UNKNOWN';
      return <Chip size="small" label={zyg} variant="outlined" color={zyg === 'UNKNOWN' ? 'warning' : 'primary'} />;
    } : undefined,
  }));
  if (analysisId && (keys.has('gene') || keys.has('gene_symbol') || keys.has('SYMBOL'))) columns.unshift({
    field: '__literature', headerName: 'Literature', width: 132, sortable: false, filterable: false,
    renderCell: (params) => <Button size="small" variant="outlined" startIcon={<AutoStoriesOutlinedIcon />} onClick={() => openLiterature(params.row)}>Insight</Button>,
  });
  if (somatic) columns.unshift(
    { field: '__variant', headerName: 'Variant (GRCh38)', minWidth: 230, flex: 1.2, valueGetter: (_value, row) => variantValue(row) || '—' },
    { field: 'tumor_af', headerName: 'Tumor AF', width: 110, valueGetter: (value) => displayValue(value) || '—' },
    { field: 'tumor_dp', headerName: 'Tumor DP', width: 110, valueGetter: (value) => displayValue(value) || '—' },
    { field: 'gnomad_eas_af', headerName: 'gnomAD EAS AF', width: 140, valueGetter: (value) => displayValue(value) || '—' },
  );

  return (
    <Box sx={{ width: '100%', minHeight: 480 }}>
      <GeneLiteratureDrawer {...literature} onClose={() => setLiterature((old) => ({ ...old, open: false }))} />
      {!loading && safeRows.length === 0 ? <Alert severity="info">{emptyMessage}</Alert> : (
        <DataGrid
          autoHeight loading={loading} disableRowSelectionOnClick
          rows={safeRows.map((row, index) => ({ ...row, id: row.id ?? row.variant_id ?? `${index + 1}` }))}
          columns={columns} slots={{ toolbar: GridToolbar }}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }} pageSizeOptions={[10, 25, 50, 100]}
          sx={{
            border: '1px solid #dce7f0', borderRadius: 2.5, overflow: 'hidden', bgcolor: '#fff',
            '& .MuiDataGrid-columnHeaders': { bgcolor: '#edf5fb', color: '#16324f', fontWeight: 800, borderBottom: '1px solid #cbdce9' },
            '& .MuiDataGrid-columnHeaderTitle': { fontWeight: 800 },
            '& .MuiDataGrid-toolbarContainer': { px: 2, py: 1.25, borderBottom: '1px solid #e6eef5', bgcolor: '#fbfdff' },
            '& .MuiDataGrid-cell': { whiteSpace: 'normal', lineHeight: 1.35, py: 1, borderColor: '#edf2f6' },
            '& .MuiDataGrid-row': { maxHeight: 'none !important', '&:nth-of-type(even)': { bgcolor: '#fbfdff' }, '&:hover': { bgcolor: '#eef7ff' } },
            '& .MuiDataGrid-footerContainer': { borderTop: '1px solid #dce7f0', bgcolor: '#fbfdff' },
          }}
        />
      )}
    </Box>
  );
}

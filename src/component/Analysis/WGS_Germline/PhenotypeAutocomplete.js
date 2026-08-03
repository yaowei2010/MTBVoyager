import React, { useEffect, useMemo, useState } from 'react';
import { Autocomplete, Box, Chip, CircularProgress, TextField, Typography } from '@mui/material';
import axios from 'axios';
import { config } from '../../../constant';

export default function PhenotypeAutocomplete({ value, onChange }) {
  const [query, setQuery] = useState('');
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);
  const normalizedQuery = useMemo(() => query.trim(), [query]);

  useEffect(() => {
    if (normalizedQuery.length < 2) { setOptions([]); return undefined; }
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const { data } = await axios.get(`${config.rootApiIP}/wgs-germline/mondo/search`, { params: { q: normalizedQuery, limit: 20 } });
        if (active) setOptions(Array.isArray(data) ? data : data?.results || []);
      } catch (_) { if (active) setOptions([]); }
      finally { if (active) setLoading(false); }
    }, 300);
    return () => { active = false; clearTimeout(timer); };
  }, [normalizedQuery]);

  return (
    <Box sx={{ p: { xs: 2, md: 2.5 }, borderRadius: 2.5, bgcolor: '#f8fbfd', border: '1px solid #d9e7f2' }}>
      <Autocomplete
        multiple filterOptions={(items) => items} options={options} value={value} loading={loading}
        onChange={(_, selected) => onChange(selected)} onInputChange={(_, text) => setQuery(text)}
        getOptionLabel={(option) => option.label || option.name || option.id || ''}
        isOptionEqualToValue={(option, selected) => option.id === selected.id}
        renderTags={(items, getTagProps) => items.map((item, index) => <Chip {...getTagProps({ index })} key={item.id} color={item.is_rare_disease ? 'secondary' : 'default'} variant="outlined" label={`${item.id} ${item.label || item.name}${item.is_rare_disease ? ' · Rare' : ''}`} />)}
        renderOption={(props, option) => <li {...props} key={option.id}><Box sx={{ py: .5, width: '100%' }}><Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}><Typography fontWeight={700} color="#16324f">{option.label || option.name}</Typography>{option.is_rare_disease && <Chip label="Rare disease" size="small" sx={{ height: 22, bgcolor: '#f3e8ff', color: '#7e22ce', fontWeight: 800, border: '1px solid #d8b4fe' }} />}</Box><Typography variant="body2" color="text.secondary">{option.id}{Number.isFinite(option.gene_count) ? ` · ${option.gene_count} associated genes` : ''}</Typography></Box></li>}
        renderInput={(params) => <TextField {...params} label="Phenotype / Disease (MONDO)" placeholder="Search disease name, synonym, or MONDO ID" helperText="Rare diseases are marked from the official MONDO Rare Disease subset. Associated human genes are used for phenotype filtering." InputProps={{ ...params.InputProps, endAdornment: <>{loading && <CircularProgress size={20} />}{params.InputProps.endAdornment}</> }} />}
      />
    </Box>
  );
}

import React, { useCallback, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Button, Chip, Paper, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import { Link } from 'react-router-dom';
import { AuthContext } from '../Auth/AuthContext';
import { config } from '../../constant';

export default function ApprovalInbox() {
  const { authHeaders } = useContext(AuthContext);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState('');
  const load = useCallback(() => axios.get(`${config.rootApiIP}/accounts/approvals/inbox/`, { headers: authHeaders() })
    .then(({ data }) => { setRows(data); setError(''); })
    .catch((err) => setError(err.response?.data?.detail || '無法讀取待簽核報告。')), [authHeaders]);
  useEffect(() => { load(); }, [load]);
  return <Box sx={{ p: 2 }}>
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}><Box><Typography variant="h4" fontWeight={800}>待我簽核</Typography><Typography color="text.secondary">目前指派給您的 WGS tumor-only 最終報告。</Typography></Box><Chip color={rows.length ? 'warning' : 'default'} label={`${rows.length} 件待辦`} /></Stack>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    {!rows.length ? <Alert severity="info">目前沒有等待您簽核的報告。</Alert> : <TableContainer component={Paper} variant="outlined"><Table><TableHead><TableRow><TableCell>Analysis ID</TableCell><TableCell>版本</TableCell><TableCell>送簽人</TableCell><TableCell>送簽時間</TableCell><TableCell>備註</TableCell><TableCell /></TableRow></TableHead><TableBody>{rows.map(row => <TableRow key={row.id}><TableCell><b>{row.analysis_id}</b></TableCell><TableCell>v{row.version}</TableCell><TableCell>{row.submitted_by?.username || '—'}</TableCell><TableCell>{new Date(row.submitted_at).toLocaleString()}</TableCell><TableCell>{row.submit_comment || '—'}</TableCell><TableCell><Button component={Link} to={`${config.rootPathPrefix}/Job_results/detail_wgs_somatic/${row.analysis_id}?tab=mtb_report`} variant="contained">開啟簽核</Button></TableCell></TableRow>)}</TableBody></Table></TableContainer>}
  </Box>;
}

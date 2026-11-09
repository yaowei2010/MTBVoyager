import React, { useCallback, useContext, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Alert, Box, Button, Checkbox, Chip, FormControl, InputLabel, ListItemText,
  MenuItem, Paper, Select, Stack, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, TextField, Typography
} from '@mui/material';
import { AuthContext } from '../Auth/AuthContext';
import { config } from '../../constant';


export default function CaseAccessManagement() {
  const { authHeaders } = useContext(AuthContext);
  const [cases, setCases] = useState([]);
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const [caseResponse, userResponse] = await Promise.all([
        axios.get(`${config.rootApiIP}/accounts/cases/`, { headers: authHeaders() }),
        axios.get(`${config.rootApiIP}/accounts/users/`, { headers: authHeaders() }),
      ]);
      setCases(caseResponse.data);
      setUsers(userResponse.data.filter((user) => user.is_active));
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || '無法讀取案件權限');
    }
  }, [authHeaders]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => cases.filter((item) =>
    !query || item.analysis_id.toLowerCase().includes(query.toLowerCase()) ||
    item.owner?.username?.toLowerCase().includes(query.toLowerCase())
  ), [cases, query]);

  const assign = async (item, assignedIds) => {
    try {
      const { data } = await axios.patch(
        `${config.rootApiIP}/accounts/cases/${encodeURIComponent(item.analysis_id)}/access/`,
        { assigned_user_ids: assignedIds },
        { headers: authHeaders() }
      );
      setCases((current) => current.map((row) => row.analysis_id === data.analysis_id ? data : row));
    } catch (err) {
      setError(err.response?.data?.detail || '案件指派失敗');
    }
  };

  return <Box sx={{ p: 2 }}>
    <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
      <Box><Typography variant="h4" fontWeight={800}>案件存取管理</Typography><Typography color="text.secondary">指定 user 或 viewer 可查看的分析結果。</Typography></Box>
      <Stack direction="row" spacing={1}><TextField size="small" label="搜尋 Analysis ID / Owner" value={query} onChange={(e) => setQuery(e.target.value)}/><Button variant="outlined" onClick={load}>重新整理</Button></Stack>
    </Stack>
    {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}
    <TableContainer component={Paper} variant="outlined">
      <Table><TableHead><TableRow><TableCell>Analysis ID</TableCell><TableCell>Owner</TableCell><TableCell>已授權帳號</TableCell></TableRow></TableHead>
      <TableBody>{filtered.map((item) => {
        const selected = item.assigned_users.map((user) => user.id);
        return <TableRow key={item.analysis_id}>
          <TableCell><b>{item.analysis_id}</b></TableCell>
          <TableCell>{item.owner?.username || <Chip size="small" color="warning" label="未辨識 owner" />}</TableCell>
          <TableCell sx={{ minWidth: 360 }}><FormControl fullWidth size="small"><InputLabel>可查看結果的帳號</InputLabel><Select multiple label="可查看結果的帳號" value={selected} onChange={(e) => assign(item, e.target.value)} renderValue={(values) => values.map((id) => users.find((user) => user.id === id)?.username || id).join(', ')}>{users.map((user) => <MenuItem key={user.id} value={user.id}><Checkbox checked={selected.includes(user.id)}/><ListItemText primary={user.username} secondary={user.role}/></MenuItem>)}</Select></FormControl></TableCell>
        </TableRow>;
      })}</TableBody></Table>
    </TableContainer>
  </Box>;
}

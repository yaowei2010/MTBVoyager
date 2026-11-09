import React, { useCallback, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import { Alert, Box, Button, FormControl, InputLabel, MenuItem, Paper, Select, Stack, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from '@mui/material';
import { AuthContext } from '../Auth/AuthContext';
import { config } from '../../constant';

export default function ApprovalRuleManagement() {
  const { authHeaders } = useContext(AuthContext);
  const [users, setUsers] = useState([]);
  const [rules, setRules] = useState([]);
  const [form, setForm] = useState({ submitter_id: '', approver_id: '' });
  const [error, setError] = useState('');
  const load = useCallback(() => Promise.all([
    axios.get(`${config.rootApiIP}/accounts/users/`, { headers: authHeaders() }),
    axios.get(`${config.rootApiIP}/accounts/approval-rules/`, { headers: authHeaders() }),
  ]).then(([userResponse, ruleResponse]) => { setUsers(userResponse.data.filter(item => item.is_active)); setRules(ruleResponse.data); setError(''); })
    .catch(err => setError(err.response?.data?.detail || '無法讀取簽核關係。')), [authHeaders]);
  useEffect(() => { load(); }, [load]);
  const save = () => axios.post(`${config.rootApiIP}/accounts/approval-rules/`, form, { headers: authHeaders() }).then(() => { setForm({ submitter_id: '', approver_id: '' }); return load(); }).catch(err => setError(err.response?.data?.detail || '無法儲存簽核關係。'));
  const remove = id => axios.delete(`${config.rootApiIP}/accounts/approval-rules/${id}/`, { headers: authHeaders() }).then(load).catch(err => setError(err.response?.data?.detail || '無法刪除簽核關係。'));
  return <Box sx={{ p: 2 }}>
    <Typography variant="h4" fontWeight={800}>簽核關係設定</Typography><Typography color="text.secondary" sx={{ mb: 3 }}>設定每位報告修改者的直屬簽核人；系統會阻止自己簽自己及循環關係。</Typography>
    {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
    <Paper variant="outlined" sx={{ p: 2, mb: 3 }}><Stack direction={{ xs: 'column', md: 'row' }} spacing={2}><FormControl fullWidth><InputLabel>報告修改者</InputLabel><Select label="報告修改者" value={form.submitter_id} onChange={e => setForm({ ...form, submitter_id: e.target.value })}>{users.map(user => <MenuItem key={user.id} value={user.id}>{user.username} ({user.role})</MenuItem>)}</Select></FormControl><FormControl fullWidth><InputLabel>直屬簽核人</InputLabel><Select label="直屬簽核人" value={form.approver_id} onChange={e => setForm({ ...form, approver_id: e.target.value })}>{users.filter(user => user.id !== form.submitter_id).map(user => <MenuItem key={user.id} value={user.id}>{user.username} ({user.role})</MenuItem>)}</Select></FormControl><Button variant="contained" disabled={!form.submitter_id || !form.approver_id} onClick={save} sx={{ minWidth: 150 }}>儲存關係</Button></Stack></Paper>
    <TableContainer component={Paper} variant="outlined"><Table><TableHead><TableRow><TableCell>修改者</TableCell><TableCell>簽核人</TableCell><TableCell>狀態</TableCell><TableCell>更新時間</TableCell><TableCell /></TableRow></TableHead><TableBody>{rules.map(rule => <TableRow key={rule.id}><TableCell><b>{rule.submitter.username}</b></TableCell><TableCell>{rule.approver.username}</TableCell><TableCell>{rule.is_active ? '啟用' : '停用'}</TableCell><TableCell>{new Date(rule.updated_at).toLocaleString()}</TableCell><TableCell><Button color="error" onClick={() => remove(rule.id)}>刪除</Button></TableCell></TableRow>)}</TableBody></Table></TableContainer>
  </Box>;
}

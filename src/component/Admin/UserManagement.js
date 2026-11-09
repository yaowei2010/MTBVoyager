import React, { useCallback, useContext, useEffect, useState } from 'react';
import axios from 'axios';
import {
  Alert, Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, InputLabel, MenuItem, Paper, Select, Stack, Switch, Table,
  TableBody, TableCell, TableContainer, TableHead, TableRow, TextField, Typography
} from '@mui/material';
import { AuthContext } from '../Auth/AuthContext';
import { config } from '../../constant';


const emptyForm = { username: '', password: '', email: '', role: 'user' };

export default function UserManagement() {
  const { authHeaders, user: currentUser } = useContext(AuthContext);
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(emptyForm);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await axios.get(`${config.rootApiIP}/accounts/users/`, { headers: authHeaders() });
      setUsers(data);
      setError('');
    } catch (err) {
      setError(err.response?.data?.detail || '無法讀取使用者清單');
    }
  }, [authHeaders]);

  useEffect(() => { load(); }, [load]);

  const createUser = async () => {
    try {
      await axios.post(`${config.rootApiIP}/accounts/users/`, form, { headers: authHeaders() });
      setOpen(false);
      setForm(emptyForm);
      await load();
    } catch (err) {
      const data = err.response?.data;
      setError(typeof data === 'string' ? data : JSON.stringify(data || '建立帳號失敗'));
    }
  };

  const updateUser = async (target, changes) => {
    try {
      await axios.patch(`${config.rootApiIP}/accounts/users/${target.id}/`, changes, { headers: authHeaders() });
      await load();
    } catch (err) {
      setError(err.response?.data?.detail || '更新帳號失敗');
    }
  };

  return <Box sx={{ p: 2 }}>
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
      <Box><Typography variant="h4" fontWeight={800}>使用者與權限管理</Typography><Typography color="text.secondary">管理 admin、user、viewer 三種角色。</Typography></Box>
      <Button variant="contained" onClick={() => setOpen(true)}>新增使用者</Button>
    </Stack>
    {error && <Alert severity="error" onClose={() => setError('')} sx={{ mb: 2 }}>{error}</Alert>}
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead><TableRow><TableCell>帳號</TableCell><TableCell>Email</TableCell><TableCell>角色</TableCell><TableCell>狀態</TableCell><TableCell>最後登入</TableCell></TableRow></TableHead>
        <TableBody>{users.map((item) => <TableRow key={item.id}>
          <TableCell><Stack direction="row" spacing={1} alignItems="center"><b>{item.username}</b>{item.id === currentUser?.id && <Chip size="small" label="目前帳號" />}</Stack></TableCell>
          <TableCell>{item.email || '—'}</TableCell>
          <TableCell><Select size="small" value={item.role} disabled={item.id === currentUser?.id} onChange={(e) => updateUser(item, { role: e.target.value })}><MenuItem value="admin">admin</MenuItem><MenuItem value="user">user</MenuItem><MenuItem value="viewer">viewer</MenuItem></Select></TableCell>
          <TableCell><Stack direction="row" alignItems="center"><Switch checked={item.is_active} disabled={item.id === currentUser?.id} onChange={(e) => updateUser(item, { is_active: e.target.checked })}/>{item.is_active ? '啟用' : '停用'}</Stack></TableCell>
          <TableCell>{item.last_login ? new Date(item.last_login).toLocaleString() : '尚未登入'}</TableCell>
        </TableRow>)}</TableBody>
      </Table>
    </TableContainer>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
      <DialogTitle>新增使用者</DialogTitle>
      <DialogContent><Stack spacing={2} sx={{ mt: 1 }}>
        <TextField label="帳號" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}/>
        <TextField label="初始密碼" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}/>
        <TextField label="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}/>
        <FormControl><InputLabel>角色</InputLabel><Select label="角色" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}><MenuItem value="admin">admin</MenuItem><MenuItem value="user">user</MenuItem><MenuItem value="viewer">viewer</MenuItem></Select></FormControl>
      </Stack></DialogContent>
      <DialogActions><Button onClick={() => setOpen(false)}>取消</Button><Button variant="contained" onClick={createUser}>建立</Button></DialogActions>
    </Dialog>
  </Box>;
}

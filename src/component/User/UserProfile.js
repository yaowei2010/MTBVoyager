import React, { useContext, useState } from 'react';
import axios from 'axios';
import {
  Alert, Box, Button, Chip, Divider, Paper, Stack, TextField, Typography
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../Auth/AuthContext';
import { config } from '../../constant';


export default function UserProfile() {
  const { user, authHeaders, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [message, setMessage] = useState({ type: '', text: '' });
  const [busy, setBusy] = useState(false);

  const changePassword = async (event) => {
    event.preventDefault();
    if (form.new_password !== form.confirm_password) {
      setMessage({ type: 'error', text: '新密碼與確認密碼不一致。' });
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${config.rootApiIP}/accounts/me/password/`, {
        current_password: form.current_password,
        new_password: form.new_password,
      }, { headers: authHeaders() });
      setMessage({ type: 'success', text: '密碼已更新，請重新登入。' });
      setTimeout(() => {
        logout();
        navigate(`${config.rootPathPrefix}/login`);
      }, 1200);
    } catch (err) {
      const data = err.response?.data;
      const detail = data?.current_password || data?.new_password?.join?.(' ') || data?.detail;
      setMessage({ type: 'error', text: detail || '密碼更新失敗。' });
    } finally {
      setBusy(false);
    }
  };

  return <Box sx={{ p: 2, maxWidth: 900 }}>
    <Typography variant="h4" fontWeight={800}>User</Typography>
    <Typography color="text.secondary" sx={{ mb: 3 }}>查看目前登入身分與帳號安全設定。</Typography>
    <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box><Typography variant="overline" color="text.secondary">目前帳號</Typography><Typography variant="h5" fontWeight={800}>{user?.username}</Typography></Box>
        <Chip label={user?.role || '—'} color={user?.role === 'admin' ? 'primary' : 'default'} />
      </Stack>
      <Divider sx={{ my: 2 }} />
      <Stack spacing={1}>
        <Typography><b>User ID：</b>{user?.id}</Typography>
        <Typography><b>Email：</b>{user?.email || '未設定'}</Typography>
        <Typography><b>帳號狀態：</b>{user?.is_active ? '啟用' : '停用'}</Typography>
        <Typography><b>最後登入：</b>{user?.last_login ? new Date(user.last_login).toLocaleString() : '尚無紀錄'}</Typography>
      </Stack>
      <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>{user?.permissions?.map((permission) => <Chip key={permission} size="small" variant="outlined" label={permission} />)}</Stack>
    </Paper>
    <Paper component="form" onSubmit={changePassword} variant="outlined" sx={{ p: 3 }}>
      <Typography variant="h6" fontWeight={800}>修改密碼</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>更新後目前登入狀態會登出，請使用新密碼重新登入。</Typography>
      {message.text && <Alert severity={message.type} sx={{ mb: 2 }}>{message.text}</Alert>}
      <Stack spacing={2}>
        <TextField required type="password" label="目前密碼" value={form.current_password} onChange={(e) => setForm({ ...form, current_password: e.target.value })}/>
        <TextField required type="password" label="新密碼" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })}/>
        <TextField required type="password" label="確認新密碼" value={form.confirm_password} onChange={(e) => setForm({ ...form, confirm_password: e.target.value })}/>
        <Button type="submit" variant="contained" disabled={busy}>{busy ? '更新中…' : '更新密碼'}</Button>
      </Stack>
    </Paper>
  </Box>;
}

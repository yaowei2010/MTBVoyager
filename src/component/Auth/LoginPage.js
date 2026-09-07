// component/Auth/LoginPage.js
import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from './AuthContext';
import { Box, Button, Chip, Divider, TextField, Typography, Paper, Snackbar, Alert } from '@mui/material';
import BiotechOutlinedIcon from '@mui/icons-material/BiotechOutlined';
import { config } from '../../constant';

function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const [alert, setAlert] = useState({ open: false, type: 'success', message: '' });

  const handleLogin = async () => {
    try {
      const res = await axios.post(`${config.rootApiIP}/accounts/token/`, {
        username,
        password
      });

      const token = res.data.access;
      if (token) {
        const userInfoRes = await axios.get(`${config.rootApiIP}/accounts/user-info`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        const userId = userInfoRes.data.id;
        login(token, userId);

        setAlert({ open: true, type: 'success', message: '登入成功！即將導向主頁' });
        setTimeout(() => navigate(config.rootPathPrefix + '/home'), 1000);
      } else {
        setAlert({ open: true, type: 'error', message: '登入失敗：未收到 Token' });
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || '登入失敗，請稍後再試';
      setAlert({ open: true, type: 'error', message: errorMsg });
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault(); // 防止表單預設刷新
    handleLogin();
  };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh" sx={{ p: 2, background: 'radial-gradient(circle at 15% 15%,rgba(34,178,167,.22),transparent 28rem),linear-gradient(135deg,#0c2945 0%,#124d70 58%,#08766f 100%)' }}>
      <Paper elevation={0} sx={{ p: { xs: 3, sm: 5 }, width: '100%', maxWidth: 440, borderRadius: 4, border: '1px solid rgba(255,255,255,.45)', boxShadow: '0 28px 70px rgba(2,20,38,.32)' }}>
        <Box sx={{ width: 58, height: 58, display: 'grid', placeItems: 'center', borderRadius: 3, bgcolor: '#e7f4ff', color: '#0b67b2', mb: 3 }}><BiotechOutlinedIcon fontSize="large" /></Box>
        <Chip label="CLINICAL GENOMICS" size="small" sx={{ mb: 1.5, bgcolor: '#e8f7f2', color: '#087f5b', fontWeight: 800, letterSpacing: '.06em' }} />
        <Typography variant="h4" sx={{ fontWeight: 800 }}>Welcome back</Typography>
        <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>Sign in to the germline and somatic interpretation workspace.</Typography>
        <Divider sx={{ mb: 2 }} />

        {/* ✅ Enter 送出 */}
        <Box component="form" onSubmit={handleSubmit}>
          <TextField
            label="帳號"
            variant="outlined"
            fullWidth
            margin="normal"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <TextField
            label="密碼"
            type="password"
            variant="outlined"
            fullWidth
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          <Button
            type="submit"          // ✅ 讓按鈕也走 form submit
            variant="contained"
            fullWidth
            sx={{ mt: 2, height: 50, fontSize: 16 }}
          >
            登入
          </Button>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2.5, textAlign: 'center' }}>
          還沒有帳號？<Link to={config.rootPathPrefix + "/register"}>前往註冊</Link>
        </Typography>
      </Paper>

      <Snackbar
        open={alert.open}
        autoHideDuration={3000}
        onClose={() => setAlert({ ...alert, open: false })}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert severity={alert.type} onClose={() => setAlert({ ...alert, open: false })} sx={{ width: '100%' }}>
          {alert.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default LoginPage;

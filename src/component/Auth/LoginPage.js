// component/Auth/LoginPage.js
import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { AuthContext } from './AuthContext';
import {
  Box, Button, TextField, Typography, Paper, Snackbar, Alert
} from '@mui/material';
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
    <Box display="flex" justifyContent="center" alignItems="center" height="100vh" bgcolor="#f5f5f5">
      <Paper elevation={6} sx={{ p: 4, width: 350 }}>
        <Typography variant="h5" gutterBottom>登入系統</Typography>

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
            sx={{ mt: 2 }}
          >
            登入
          </Button>
        </Box>

        <Typography variant="body2" sx={{ mt: 2 }}>
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

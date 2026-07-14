// component/Auth/RegisterPage.js
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import {
  Box, Button, TextField, Typography, Paper, Snackbar, Alert
} from '@mui/material';
import { config } from '../../constant';

function RegisterPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [alert, setAlert] = useState({ open: false, type: 'success', message: '' });
  const navigate = useNavigate();

  const handleRegister = async () => {
    try {
      const res = await axios.post(`${config.rootApiIP}/accounts/register/`, {
        username,
        password
      });

      setAlert({ open: true, type: 'success', message: res.data.message || '註冊成功！即將前往登入頁' });

      // ✅ 註冊成功後 1 秒後跳轉
      setTimeout(() => navigate(config.rootPathPrefix + '/login'), 1000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || '註冊失敗，請稍後再試';
      setAlert({ open: true, type: 'error', message: errorMsg });
    }
  };

  return (
    <Box display="flex" justifyContent="center" alignItems="center" height="100vh" bgcolor="#f5f5f5">
      <Paper elevation={6} sx={{ p: 4, width: 350 }}>
        <Typography variant="h5" gutterBottom>註冊帳號</Typography>
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
          variant="contained"
          fullWidth
          sx={{ mt: 2 }}
          onClick={handleRegister}
        >
          註冊
        </Button>
        <Typography variant="body2" sx={{ mt: 2 }}>
          已有帳號？<Link to={config.rootPathPrefix +"/login"}>前往登入</Link>
        </Typography>
      </Paper>

      {/* Snackbar 提示 */}
      <Snackbar
        open={alert.open}
        autoHideDuration={3000}
        onClose={() => setAlert({ ...alert, open: false })}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          severity={alert.type}
          onClose={() => setAlert({ ...alert, open: false })}
          sx={{ width: '100%' }}
        >
          {alert.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default RegisterPage;

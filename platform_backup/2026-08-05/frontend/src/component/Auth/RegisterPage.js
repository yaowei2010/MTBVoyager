// component/Auth/RegisterPage.js
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import {
  Box, Button, TextField, Typography, Paper, Snackbar, Alert, Chip, Divider, Stack
} from '@mui/material';
import BiotechRoundedIcon from '@mui/icons-material/BiotechRounded';
import PersonAddAltRoundedIcon from '@mui/icons-material/PersonAddAltRounded';
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
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', p: 3, background: 'radial-gradient(circle at 15% 15%, rgba(32,178,170,.23), transparent 34%), linear-gradient(135deg, #071a33 0%, #0b3d68 54%, #0a716d 100%)' }}>
      <Paper elevation={18} sx={{ p: { xs: 3, sm: 5 }, width: '100%', maxWidth: 460, border: '1px solid rgba(255,255,255,.65)', borderRadius: 4 }}>
        <Stack spacing={1.25} alignItems="flex-start" sx={{ mb: 3 }}>
          <Box sx={{ width: 52, height: 52, borderRadius: 2.5, display: 'grid', placeItems: 'center', color: 'white', background: 'linear-gradient(135deg, #0b67b2, #0d8f80)', boxShadow: '0 10px 24px rgba(11,103,178,.24)' }}>
            <BiotechRoundedIcon fontSize="large" />
          </Box>
          <Chip label="CLINICAL GENOMICS PLATFORM" size="small" color="primary" variant="outlined" />
          <Typography variant="h4" sx={{ fontWeight: 800, letterSpacing: '-.025em' }}>建立帳號</Typography>
          <Typography color="text.secondary">註冊後即可使用整合式基因體分析工作流程。</Typography>
        </Stack>
        <Divider sx={{ mb: 2 }} />
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
          size="large"
          startIcon={<PersonAddAltRoundedIcon />}
          sx={{ mt: 2.5 }}
          onClick={handleRegister}
        >
          註冊
        </Button>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2.5, textAlign: 'center' }}>
          已有帳號？ <Link to={config.rootPathPrefix +"/login"}>前往登入</Link>
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

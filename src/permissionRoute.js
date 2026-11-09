import React, { useContext } from 'react';
import { Alert, Box } from '@mui/material';
import { Outlet } from 'react-router-dom';
import { AuthContext } from './component/Auth/AuthContext';


export default function PermissionRoute({ permission }) {
  const { hasPermission, isLoading } = useContext(AuthContext);
  if (isLoading) return null;
  if (!hasPermission(permission)) {
    return <Box sx={{ p: 4 }}><Alert severity="error">您沒有使用此功能的權限。</Alert></Box>;
  }
  return <Outlet />;
}

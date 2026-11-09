import React, { createContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { config } from '../../constant';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [userId, setUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // 初始化從 localStorage 讀取 token & userId
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (!storedToken) {
      setIsLoading(false);
      return;
    }
    setToken(storedToken);
    axios.get(`${config.rootApiIP}/accounts/me/`, {
      headers: { Authorization: `Bearer ${storedToken}` }
    }).then(({ data }) => {
      setUser(data);
      setUserId(data.id);
      localStorage.setItem('userId', data.id);
    }).catch(() => {
      localStorage.removeItem('token');
      localStorage.removeItem('userId');
      setToken(null);
    }).finally(() => setIsLoading(false));
  }, []);

  // ✅ login: 同時存 token + userId（會在 LoginPage 裡個別設定）
  const login = (newToken, userInfo) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    if (userInfo?.id) {
      localStorage.setItem('userId', userInfo.id);
      setUserId(userInfo.id);
      setUser(userInfo);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    setToken(null);
    setUserId(null);
    setUser(null);
  };

  const hasPermission = useCallback(
    (permission) => Boolean(user?.permissions?.includes(permission)),
    [user]
  );

  const authHeaders = useCallback(() => (
    token ? { Authorization: `Bearer ${token}` } : {}
  ), [token]);

  return (
    <AuthContext.Provider value={{ token, userId, user, role: user?.role, login, logout, isLoading, hasPermission, authHeaders }}>
      {children}
    </AuthContext.Provider>
  );
};

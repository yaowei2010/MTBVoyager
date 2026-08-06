import React, { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [userId, setUserId] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // 初始化從 localStorage 讀取 token & userId
  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    const storedUserId = localStorage.getItem('userId');
    if (storedToken) setToken(storedToken);
    if (storedUserId) setUserId(storedUserId);
    setIsLoading(false);
  }, []);

  // ✅ login: 同時存 token + userId（會在 LoginPage 裡個別設定）
  const login = (newToken, newUserId) => {
    localStorage.setItem('token', newToken);
    setToken(newToken);
    if (newUserId) {
      localStorage.setItem('userId', newUserId);
      setUserId(newUserId);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('userId');
    setToken(null);
    setUserId(null);
  };

  return (
    <AuthContext.Provider value={{ token, userId, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
};

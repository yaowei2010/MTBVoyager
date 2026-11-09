import React, { useContext, useEffect, useState } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { AuthContext } from './component/Auth/AuthContext';
import Left_navigation from './component/Navbar/Left_navigation';
import { config } from './constant';

function PrivateRoute() {
  const { token, isLoading } = useContext(AuthContext);
  const navigate = useNavigate();
  const [navigationOpen, setNavigationOpen] = useState(false);

  useEffect(() => {
    if (!isLoading && !token) {
      navigate(config.rootPathPrefix +'/login');
      
    }
  }, [token, isLoading, navigate]);

  // ✅ 若還在初始化，就先不 render
  if (isLoading) return null;

  // ✅ 若已經檢查過了且沒有 token，也不 render
  if (!token) return null;

  return (
    <>
      <Left_navigation
        open={navigationOpen}
        onOpen={() => setNavigationOpen(true)}
        onClose={() => setNavigationOpen(false)}
      />
      <div
        className="clinical-app-content"
        style={{
          boxSizing: 'border-box',
          marginLeft: navigationOpen ? '240px' : '80px',
          width: navigationOpen ? 'calc(100% - 240px)' : 'calc(100% - 80px)',
          padding: '0 24px 32px',
          transition: 'margin-left 225ms cubic-bezier(0.4, 0, 0.6, 1), width 225ms cubic-bezier(0.4, 0, 0.6, 1)',
        }}
      >
        <Outlet />
      </div>
    </>
  );
}

export default PrivateRoute;

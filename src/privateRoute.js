import React, { useContext, useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';
import { AuthContext } from './component/Auth/AuthContext';
import Left_navigation from './component/Navbar/Left_navigation';
import { config } from './constant';

function PrivateRoute() {
  const { token, isLoading } = useContext(AuthContext);
  const navigate = useNavigate();

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
      <Left_navigation />
      <div className="clinical-app-content" style={{ marginTop: "-10px", paddingLeft: "150px" }}>
        <Outlet />
      </div>
    </>
  );
}

export default PrivateRoute;

import React, { useEffect, useState } from 'react';
import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import { Layout } from 'antd';
import Navigation from '../components/Navigation';
import { isTokenValid, getToken, clearToken } from '../utils/auth';
import 'antd/dist/antd.css';

const { Content } = Layout;

function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // 不需要认证的页面
  const publicPages = ['/login', '/register'];
  const isPublicPage = publicPages.includes(router.pathname);

  useEffect(() => {
    const checkAuth = () => {
      const token = getToken();
      
      if (!token || !isTokenValid(token)) {
        clearToken();
        setIsAuthenticated(false);
        setIsChecking(false);
        if (!isPublicPage) {
          router.replace('/login');
        }
        return;
      }

      setIsAuthenticated(true);
      setIsChecking(false);
    };

    checkAuth();

    // 监听自定义事件，用于认证状态变化
    const handleTokenChange = () => {
      checkAuth();
    };

    window.addEventListener('tokenChanged', handleTokenChange);

    return () => {
      window.removeEventListener('tokenChanged', handleTokenChange);
    };
  }, [router.pathname, isPublicPage]);

  // 正在检查认证状态时显示加载
  if (isChecking) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        加载中...
      </div>
    );
  }

  // 公共页面（登录、注册）不显示导航栏
  if (isPublicPage) {
    return <Component {...pageProps} />;
  }

  // 需要认证的页面
  if (!isAuthenticated) {
    return null; // 这种情况下应该已经重定向到登录页
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Navigation />
      <Content style={{ padding: '24px' }}>
        <Component {...pageProps} />
      </Content>
    </Layout>
  );
}

export default MyApp; 
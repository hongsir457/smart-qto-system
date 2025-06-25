import React, { useEffect, useState } from 'react';
import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import { Layout } from 'antd';
import Navigation from '../components/Navigation';
import ErrorBoundary from '../components/ErrorBoundary';
import { isTokenValid, getToken, clearToken } from '../utils/auth';
import { safeRouterReplace, isRouterReady } from '../utils/routeUtils';
import 'antd/dist/antd.css';

const { Content } = Layout;

function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  // 不需要认证的页面
  const publicPages = ['/login', '/register'];
  const isPublicPage = publicPages.includes(router.pathname);
  
    // 创建稳定的认证检查函数
  const checkAuth = React.useCallback(async () => {
    try {
      // 等待路由准备就绪
      if (!isRouterReady(router)) {
        return;
      }

      const token = getToken();
      const currentPath = router.pathname;
      const isCurrentPublic = publicPages.includes(currentPath);
      
      if (!token || !isTokenValid(token)) {
        clearToken();
        setIsAuthenticated(false);
        setIsChecking(false);
        
        if (!isCurrentPublic) {
          // 使用安全的路由替换
          await safeRouterReplace(router, '/login');
        }
        return;
      }

      setIsAuthenticated(true);
      setIsChecking(false);
    } catch (error) {
      console.error('Authentication check error:', error);
      setIsAuthenticated(false);
      setIsChecking(false);
    }
  }, [router.pathname, router.isReady]); // 只依赖路径和路由状态

  useEffect(() => {
    let isMounted = true;
    let isCheckingAuth = false;
    
    const runCheckAuth = async () => {
      if (isMounted && !isCheckingAuth) {
        isCheckingAuth = true;
        await checkAuth();
        isCheckingAuth = false;
      }
    };

    runCheckAuth();

    // 监听自定义事件，用于认证状态变化
    const handleTokenChange = () => {
      if (isMounted && !isCheckingAuth) {
        isCheckingAuth = true;
        setTimeout(() => {
          if (isMounted) {
            checkAuth().finally(() => {
              isCheckingAuth = false;
            });
          }
        }, 100); // 防抖处理
      }
    };

    window.addEventListener('tokenChanged', handleTokenChange);

    return () => {
      isMounted = false;
      window.removeEventListener('tokenChanged', handleTokenChange);
    };
  }, [checkAuth]);

  // 正在检查认证状态时显示加载
  if (isChecking || !isRouterReady(router)) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '16px',
        color: '#666'
      }}>
        正在验证身份...
      </div>
    );
  }

  // 公共页面（登录、注册）不显示导航栏
  if (isPublicPage) {
    return (
      <ErrorBoundary>
        <Component {...pageProps} />
      </ErrorBoundary>
    );
  }

  // 需要认证的页面
  if (!isAuthenticated) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        fontSize: '16px',
        color: '#666'
      }}>
        正在跳转到登录页...
      </div>
    );
  }

  return (
    <ErrorBoundary>
      <Layout style={{ minHeight: '100vh' }}>
        <Navigation />
        <Content style={{ padding: '24px' }}>
          <Component {...pageProps} />
        </Content>
      </Layout>
    </ErrorBoundary>
  );
}

export default MyApp; 
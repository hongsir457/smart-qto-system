import React, { useEffect } from 'react';
import { useRouter } from 'next/router';
import { isTokenValid, getToken } from '../utils/auth';

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const token = getToken();
    
    if (!token || !isTokenValid(token)) {
      // 未登录，重定向到登录页
      router.replace('/login');
    } else {
      // 已登录，重定向到图纸管理页
      router.replace('/drawings');
    }
  }, [router]);

  // 显示加载状态，因为页面会立即重定向
  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      height: '100vh',
      fontSize: '16px',
      color: '#666'
    }}>
      正在跳转...
    </div>
  );
} 
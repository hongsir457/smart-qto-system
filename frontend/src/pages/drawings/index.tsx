import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import ProjectUploadPage from '../DrawingUpload';
import { isTokenValid, getToken } from '../../utils/auth';
import { safeRouterReplace, isRouterReady } from '../../utils/routeUtils';

export default function DrawingsPage() {
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    let isMounted = true;
    
    const checkAuth = async () => {
      try {
        // 等待路由准备就绪
        if (!isRouterReady(router)) {
          return;
        }

        const token = getToken();
        
        if (!token || !isTokenValid(token)) {
          if (isMounted) {
            await safeRouterReplace(router, '/login');
          }
          return;
        }
        
        if (isMounted) {
          setIsReady(true);
        }
      } catch (error) {
        console.error('Page auth check error:', error);
        if (isMounted) {
          await safeRouterReplace(router, '/login');
        }
      }
    };

    checkAuth();

    return () => {
      isMounted = false;
    };
  }, [router]);

  // 在认证检查完成前显示加载状态
  if (!isReady || !isRouterReady(router)) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '200px',
        fontSize: '16px',
        color: '#666'
      }}>
        正在加载图纸管理页面...
      </div>
    );
  }

  return <ProjectUploadPage />;
} 
import { NextRouter } from 'next/router';

// 安全的路由跳转，避免中止错误
export const safeRouterPush = async (router: NextRouter, url: string): Promise<boolean> => {
  try {
    await router.push(url);
    return true;
  } catch (error: any) {
    // 忽略路由中止错误
    if (error.cancelled) {
      console.log('Route change cancelled:', url);
      return false;
    }
    console.error('Route change error:', error);
    return false;
  }
};

// 安全的路由替换，避免中止错误
export const safeRouterReplace = async (router: NextRouter, url: string): Promise<boolean> => {
  try {
    await router.replace(url);
    return true;
  } catch (error: any) {
    // 忽略路由中止错误
    if (error.cancelled) {
      console.log('Route replace cancelled:', url);
      return false;
    }
    console.error('Route replace error:', error);
    return false;
  }
};

// 检查路由是否已准备好
export const isRouterReady = (router: NextRouter): boolean => {
  return router.isReady && !router.isFallback;
}; 
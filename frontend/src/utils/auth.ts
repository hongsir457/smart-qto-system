const { jwtDecode } = require('jwt-decode');

interface JWTPayload {
  sub: string;
  exp: number;
}

export const isTokenValid = (token: string | null): boolean => {
  if (!token) return false;
  
  try {
    const decoded = jwtDecode(token) as JWTPayload;
    const currentTime = Date.now() / 1000;
    
    // 检查token是否过期（添加5分钟缓冲）
    return decoded.exp > currentTime - 300;
  } catch (error) {
    console.error('Token validation error:', error);
    return false;
  }
};

export const getToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('token');
  }
  return null;
};

export const clearToken = (): void => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('token');
    // 触发自定义事件以通知其他组件
    window.dispatchEvent(new CustomEvent('tokenChanged'));
  }
};

export const setToken = (token: string): void => {
  if (typeof window !== 'undefined') {
    localStorage.setItem('token', token);
    // 触发自定义事件以通知其他组件
    window.dispatchEvent(new CustomEvent('tokenChanged'));
  }
}; 
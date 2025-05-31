import axios from 'axios';
import { message } from 'antd';

// 创建axios实例
const request = axios.create({
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
    timeout: 300000,  // 设置超时时间为5分钟
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器
request.interceptors.request.use(
    (config) => {
        // 从localStorage获取token
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// 响应拦截器
request.interceptors.response.use(
    (response) => {
        return response;
    },
    (error) => {
        if (error.response) {
            // 处理响应错误
            if (error.response.status === 401) {
                // 未授权，清除token并跳转到登录页
                localStorage.removeItem('token');
                window.location.href = '/login';
            } else {
                // 显示错误信息
                message.error(error.response.data.detail || '请求失败');
            }
        } else if (error.request) {
            // 请求超时
            message.error('请求超时，请稍后重试');
        } else {
            // 其他错误
            message.error('发生错误，请稍后重试');
        }
        return Promise.reject(error);
    }
);

export default request; 
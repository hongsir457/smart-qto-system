import axios from 'axios';
import { LoginForm, Drawing } from '../types';

const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// 请求拦截器：添加token
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const login = async (data: LoginForm) => {
    const response = await api.post('/api/v1/auth/login', data);
    return response.data;
};

// 封装fetch，自动加token
export async function authFetch(input: RequestInfo, init: RequestInit = {}) {
    const token = localStorage.getItem('token');
    const headers = new Headers(init.headers || {});
    if (token) {
        headers.set('Authorization', 'Bearer ' + token);
    }
    let url = input;
    if (typeof input === 'string' && input.startsWith('/')) {
        url = API_URL + input;
    }
    return fetch(url, { ...init, headers });
}

// 上传图纸
export async function uploadDrawing(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await authFetch('/api/v1/drawings/upload', {
        method: 'POST',
        body: formData,
    });
    if (!res.ok) throw new Error('上传失败');
    return res.json();
}

// 分页获取图纸
export async function getDrawings(page = 1, size = 10) {
    const url = `/api/v1/drawings?page=${page}&size=${size}`;
    const res = await authFetch(url);
    if (!res.ok) throw new Error('获取图纸失败');
    // 兼容后端直接返回数组
    const data = await res.json();
    if (Array.isArray(data)) {
        return { items: data, total: data.length };
    }
    return data;
}

export const getDrawing = async (id: number) => {
    const res = await authFetch(`/api/v1/drawings/${id}`);
    if (!res.ok) throw new Error('获取图纸详情失败');
    return res.json();
};

export const exportQuantities = async (id: number) => {
    const response = await api.get(`/drawings/${id}/export`, {
        responseType: 'blob',
    });
    return response.data;
};

export const deleteDrawing = async (id: number) => {
    const res = await authFetch(`/api/v1/drawings/${id}`, {
        method: 'DELETE',
    });
    if (!res.ok) throw new Error('删除失败');
    return res.json();
};

export const recognizeDrawing = async (id: number) => {
    const res = await authFetch(`/api/v1/drawings/${id}/detect`, {
        method: 'POST',
    });
    if (!res.ok) throw new Error('重新识别失败');
    return res.json();
};

export const updateDrawingLabel = async (id: number, label: string) => {
    const res = await authFetch(`/api/v1/drawings/${id}/label`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label }),
    });
    if (!res.ok) throw new Error('标注更新失败');
    return res.json();
};

export const verifyDrawing = async (id: number) => {
    const res = await fetch(`/api/v1/drawings/${id}/verify`, {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('token'),
            'Content-Type': 'application/json'
        }
    });
    if (!res.ok) throw new Error('二次校验失败');
    return res.json();
};

export const aiAssistDrawing = async (id: number) => {
    const res = await fetch(`/api/v1/drawings/${id}/ai-assist`, {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('token'),
            'Content-Type': 'application/json'
        }
    });
    if (!res.ok) throw new Error('AI辅助失败');
    return res.json();
};

// Playground API
export const playgroundApi = {
    // 发送聊天消息
    chat: async (data: {
        messages: Array<{ role: string; content: string }>;
        model: string;
        temperature: number;
        max_tokens: number;
        top_p: number;
        frequency_penalty: number;
        presence_penalty: number;
    }) => {
        const response = await api.post('/api/v1/playground/chat', data);
        return response.data;
    },

    // 获取可用模型列表
    getModels: async () => {
        const response = await api.get('/api/v1/playground/models');
        return response.data;
    },

    // 获取预设模板
    getPresets: async () => {
        const response = await api.get('/api/v1/playground/presets');
        return response.data;
    },

    // 验证API密钥
    validateApiKey: async () => {
        const response = await api.post('/api/v1/playground/validate');
        return response.data;
    },

    // 获取使用统计
    getUsage: async () => {
        const response = await api.get('/api/v1/playground/usage');
        return response.data;
    },

    // 流式聊天
    streamChat: async (
        data: {
            messages: Array<{ role: string; content: string }>;
            model: string;
            temperature: number;
            max_tokens: number;
        },
        abortController?: AbortController
    ) => {
        const token = localStorage.getItem('token');
        
        const response = await fetch(`${API_URL}/api/v1/playground/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': token ? `Bearer ${token}` : '',
                'Accept': 'text/stream',
            },
            body: JSON.stringify({
                ...data,
                stream: true,
            }),
            signal: abortController?.signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            let errorMessage = '流式请求失败';
            
            try {
                const errorData = JSON.parse(errorText);
                errorMessage = errorData.detail || errorMessage;
            } catch {
                errorMessage = errorText || errorMessage;
            }
            
            throw new Error(errorMessage);
        }

        return response;
    }
}; 
// pages/login.tsx
import React from 'react';
import { Form, Input, Button, message } from 'antd';
import { useRouter } from 'next/router';
import axios from 'axios';
import { setToken } from '../utils/auth';

export default function LoginPage() {
  const router = useRouter();

  const onFinish = async (values: any) => {
    try {
      // FastAPI OAuth2PasswordRequestForm 需要 x-www-form-urlencoded
      const params = new URLSearchParams();
      params.append('username', values.username);
      params.append('password', values.password);
      
      console.log('发送登录请求...', values.username); // 调试日志
      
      const response = await axios.post(
        'http://localhost:8000/api/v1/auth/login',
        params,
        { 
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          timeout: 10000 // 10秒超时
        }
      );
      
      console.log('登录响应:', response.data); // 调试日志
      
      // 兼容 token 和 access_token 字段
      const token = response.data.access_token;
      if (token) {
        setToken(token); // 使用新的认证工具
        message.success('登录成功！');
        
        // 使用 replace 而不是 push，并添加短暂延迟确保 token 存储完成
        setTimeout(() => {
          router.replace('/drawings');
        }, 100);
      } else {
        message.error('登录失败：未返回 token');
      }
    } catch (error: any) {
      console.error('登录错误:', error); // 调试日志
      
      if (error.response) {
        // 服务器返回错误响应
        const errorMsg = error.response.data?.detail || '登录失败，请检查用户名和密码';
        message.error(errorMsg);
      } else if (error.request) {
        // 请求发送失败
        message.error('无法连接到服务器，请检查网络连接');
      } else {
        // 其他错误
        message.error('登录失败，请稍后重试');
      }
    }
  };

  return (
    <div style={{ maxWidth: 320, margin: '100px auto' }}>
      <h2>登录</h2>
      <Form name="login" onFinish={onFinish}>
        <Form.Item name="username" rules={[{ required: true, message: '请输入注册邮箱' }]}>
          <Input placeholder="注册邮箱" />
        </Form.Item>
        <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
          <Input.Password placeholder="密码" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" block>
            登录
          </Button>
        </Form.Item>
      </Form>
      <div style={{ color: '#888', fontSize: 13, marginTop: 8 }}>
        请填写注册时的邮箱作为用户名登录
      </div>
      <div style={{ textAlign: 'right', marginTop: 8 }}>
        <Button type="link" onClick={() => router.push('/register')}>
          没有账号？注册
        </Button>
      </div>
    </div>
  );
}

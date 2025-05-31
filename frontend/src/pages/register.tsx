import React, { useState } from 'react';
import { Form, Input, Button, message } from 'antd';
import { useRouter } from 'next/router';
import axios from 'axios';

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // 假设后端注册接口为 /api/v1/auth/register
      await axios.post('http://localhost:8000/api/v1/auth/register', {
        email: values.email,
        username: values.username,
        password: values.password,
      });
      message.success('注册成功，请登录');
      router.push('/login');
    } catch (error: any) {
      message.error(error.response?.data?.detail || '注册失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 320, margin: '100px auto' }}>
      <h2>注册新用户</h2>
      <Form name="register" onFinish={onFinish}>
        <Form.Item name="email" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}> 
          <Input placeholder="邮箱" />
        </Form.Item>
        <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}> 
          <Input placeholder="用户名" />
        </Form.Item>
        <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}> 
          <Input.Password placeholder="密码" />
        </Form.Item>
        <Form.Item name="confirm" dependencies={['password']} hasFeedback
          rules={[
            { required: true, message: '请确认密码' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('password') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error('两次输入的密码不一致!'));
              },
            }),
          ]}
        >
          <Input.Password placeholder="确认密码" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" block loading={loading}>
            注册
          </Button>
        </Form.Item>
      </Form>
      <div style={{ textAlign: 'right', marginTop: 8 }}>
        <Button type="link" onClick={() => router.push('/login')}>
          返回登录
        </Button>
      </div>
    </div>
  );
} 
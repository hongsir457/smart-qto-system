import React from 'react';
import { Menu, Layout } from 'antd';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  FileTextOutlined, 
  ApiOutlined, 
  UploadOutlined,
  LogoutOutlined 
} from '@ant-design/icons';
import { clearToken } from '../utils/auth';

const { Header } = Layout;

const Navigation: React.FC = () => {
  const router = useRouter();
  
  const handleLogout = () => {
    clearToken();
    router.push('/login');
  };

  const menuItems = [
    {
      key: '/',
      icon: <UploadOutlined />,
      label: <Link href="/" style={{ textDecoration: 'none' }}>图纸管理</Link>,
    },
    {
      key: '/playground',
      icon: <ApiOutlined />,
      label: <Link href="/playground" style={{ textDecoration: 'none' }}>AI Playground</Link>,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
      style: { marginLeft: 'auto' }
    }
  ];

  return (
    <Header style={{ padding: 0, background: '#fff', borderBottom: '1px solid #f0f0f0' }}>
      <div style={{ display: 'flex', alignItems: 'center', height: '100%' }}>
        <div style={{ 
          padding: '0 24px', 
          fontSize: '18px', 
          fontWeight: 'bold',
          color: '#1890ff'
        }}>
          <FileTextOutlined style={{ marginRight: '8px' }} />
          智能工程量计算系统
        </div>
        <Menu
          mode="horizontal"
          selectedKeys={[router.pathname]}
          items={menuItems}
          style={{ 
            flex: 1, 
            border: 'none',
            justifyContent: 'flex-end',
            paddingRight: '24px'
          }}
        />
      </div>
    </Header>
  );
};

export default Navigation; 
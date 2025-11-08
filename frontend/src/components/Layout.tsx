import React, { useState } from 'react';
import { Layout as AntLayout, Menu, theme, Button, Space } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  ProjectOutlined,
  FileTextOutlined,
  BugOutlined,
  PlayCircleOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  MoonOutlined,
  SunOutlined,
} from '@ant-design/icons';
import { useTheme } from '../contexts/ThemeContext';

const { Header, Sider, Content } = AntLayout;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { theme: themeMode, toggleTheme } = useTheme();
  const {
    token: { colorBgContainer, borderRadiusLG, colorBorderSecondary, colorBgLayout },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: '项目管理',
    },
    {
      key: '/requirements',
      icon: <FileTextOutlined />,
      label: '需求管理',
    },
    {
      key: '/test-cases',
      icon: <BugOutlined />,
      label: '测试用例',
    },
    {
      key: '/test-runs',
      icon: <PlayCircleOutlined />,
      label: '测试执行',
    },
    {
      key: '/performance-tests',
      icon: <ThunderboltOutlined />,
      label: '性能测试',
    },
    {
      key: '/ai-engine',
      icon: <RobotOutlined />,
      label: 'AI引擎',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <AntLayout style={{ 
      minHeight: '100vh', 
      height: '100vh', 
      overflow: 'hidden',
      background: colorBgLayout,
    }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        width={200}
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          height: '100vh',
          overflow: 'auto',
          zIndex: 100,
        }}
      >
        <div style={{ 
          height: 32, 
          margin: 16, 
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: 6,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: collapsed ? 12 : 16,
          fontWeight: 'bold'
        }}>
          {collapsed ? 'AI' : 'AI测试平台'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ height: 'calc(100vh - 64px)', overflow: 'auto' }}
        />
      </Sider>
      <AntLayout style={{ 
        marginLeft: collapsed ? 80 : 200, 
        transition: 'margin-left 0.2s',
        background: colorBgLayout,
      }}>
        <Header 
          style={{ 
            padding: '0 24px', 
            background: colorBgContainer,
            position: 'sticky',
            top: 0,
            zIndex: 1,
            boxShadow: themeMode === 'dark' 
              ? '0 2px 8px rgba(0,0,0,0.3)' 
              : '0 2px 8px rgba(0,0,0,0.1)',
            borderBottom: `1px solid ${colorBorderSecondary}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ 
            fontSize: 18,
            fontWeight: 'bold',
            color: '#1890ff'
          }}>
            AI智能自动化测试平台
          </div>
          <Space>
            <Button
              type="text"
              icon={themeMode === 'dark' ? <SunOutlined /> : <MoonOutlined />}
              onClick={toggleTheme}
              style={{
                fontSize: 18,
                width: 40,
                height: 40,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              title={themeMode === 'dark' ? '切换到亮色模式' : '切换到暗色模式'}
            />
          </Space>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: 'auto',
            height: 'calc(100vh - 112px)',
          }}
        >
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
};

export default Layout; 
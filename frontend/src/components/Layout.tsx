import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  CssBaseline,
} from '@mui/material';
import {
  CloudUpload,
  List as ListIcon,
  Psychology,
  Architecture,
  Timeline,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

const drawerWidth = 240;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      text: '图纸上传',
      icon: <CloudUpload />,
      path: '/upload',
    },
    {
      text: '图纸列表',
      icon: <ListIcon />,
      path: '/list',
    },
    {
      text: '增强分析',
      icon: <Psychology />,
      path: '/enhanced',
    },
    {
      text: '任务监控',
      icon: <Timeline />,
      path: '/task-monitor',
    },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      
      {/* 顶部应用栏 */}
      <AppBar
        position="fixed"
        sx={{ width: `calc(100% - ${drawerWidth}px)`, ml: `${drawerWidth}px` }}
      >
        <Toolbar>
          <Architecture sx={{ mr: 2 }} />
          <Typography variant="h6" noWrap component="div">
            智能工程量清单系统
          </Typography>
        </Toolbar>
      </AppBar>

      {/* 侧边导航栏 */}
      <Drawer
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
          },
        }}
        variant="permanent"
        anchor="left"
      >
        <Toolbar>
          <Typography variant="h6" component="div">
            QTO系统
          </Typography>
        </Toolbar>
        
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  '&.Mui-selected': {
                    backgroundColor: 'primary.light',
                    color: 'primary.contrastText',
                    '& .MuiListItemIcon-root': {
                      color: 'primary.contrastText',
                    },
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* 主内容区域 */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          bgcolor: 'background.default',
          p: 3,
          mt: 8, // 为AppBar留出空间
        }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default Layout; 
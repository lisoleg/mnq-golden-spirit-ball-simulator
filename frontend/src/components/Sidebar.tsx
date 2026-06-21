import React from 'react';
import { List, ListItemButton, ListItemIcon, ListItemText, IconButton, Box } from '@mui/material';
import {
  Science, AcUnit, BarChart, Waves, Link,
  GpsFixed, Psychology, PhotoCamera, Assignment,
  ChevronLeft, ChevronRight,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUIStore } from '../store/uiStore';
import { NAV_ITEMS } from '../utils/constants';

const ICON_MAP: Record<string, React.ReactElement> = {
  science: <Science />,
  ac_unit: <AcUnit />,
  bar_chart: <BarChart />,
  waves: <Waves />,
  link: <Link />,
  gps_fixed: <GpsFixed />,
  psychology: <Psychology />,
  photo_camera: <PhotoCamera />,
  assignment: <Assignment />,
};

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUIStore((s) => s.toggleSidebar);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <List sx={{ pt: 0 }}>
        {NAV_ITEMS.map((item) => (
          <ListItemButton
            key={item.path}
            selected={location.pathname === item.path}
            onClick={() => navigate(item.path)}
            sx={{
              '&.Mui-selected': {
                backgroundColor: '#1890ff20',
                borderRight: '3px solid #1890ff',
              },
              '&.Mui-selected:hover': {
                backgroundColor: '#1890ff30',
              },
              py: collapsed ? 1 : 1.5,
              justifyContent: collapsed ? 'center' : 'flex-start',
            }}
          >
            <ListItemIcon
              sx={{
                minWidth: collapsed ? 0 : 40,
                color: location.pathname === item.path ? '#1890ff' : '#888',
              }}
            >
              {ICON_MAP[item.icon]}
            </ListItemIcon>
            {!collapsed && <ListItemText primary={item.label} sx={{ color: '#e0e0e0' }} />}
          </ListItemButton>
        ))}
      </List>

      <Box sx={{ flexGrow: 1 }} />

      <IconButton
        onClick={toggleSidebar}
        sx={{
          mx: 'auto',
          mb: 2,
          color: '#888',
          '&:hover': { color: '#1890ff' },
        }}
      >
        {collapsed ? <ChevronRight /> : <ChevronLeft />}
      </IconButton>
    </Box>
  );
}

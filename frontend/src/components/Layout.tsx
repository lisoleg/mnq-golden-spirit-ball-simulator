import { Box, AppBar, Drawer, Toolbar, Typography } from '@mui/material';
import Sidebar from './Sidebar';
import TopBar from './TopBar';
import { useUIStore } from '../store/uiStore';
import { Outlet } from 'react-router-dom';

const DRAWER_WIDTH = 240;
const DRAWER_COLLAPSED = 64;
const APPBAR_HEIGHT = 64;

export default function Layout() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const drawerWidth = collapsed ? DRAWER_COLLAPSED : DRAWER_WIDTH;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          ml: `${drawerWidth}px`,
          width: `calc(100% - ${drawerWidth}px)`,
          backgroundColor: '#16213e',
        }}
      >
        <Toolbar sx={{ height: APPBAR_HEIGHT }}>
          <TopBar />
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            backgroundColor: '#0f3460',
            borderRight: '1px solid #1a1a2e',
            overflowX: 'hidden',
          },
        }}
      >
        <Toolbar sx={{ height: APPBAR_HEIGHT }}>
          <Typography variant="h6" sx={{ color: '#1890ff', fontWeight: 'bold' }}>
            {collapsed ? 'M' : 'MNQ Dashboard'}
          </Typography>
        </Toolbar>
        <Sidebar />
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          ml: `${drawerWidth}px`,
          mt: `${APPBAR_HEIGHT}px`,
          p: 3,
          backgroundColor: '#1a1a2e',
          minHeight: `calc(100vh - ${APPBAR_HEIGHT}px)`,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

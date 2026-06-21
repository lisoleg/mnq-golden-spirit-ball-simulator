import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1890ff' },
    secondary: { main: '#e94560' },
    background: { default: '#1a1a2e', paper: '#16213e' },
  },
  typography: {
    fontFamily: '"Microsoft YaHei", "Roboto", sans-serif',
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#0f3460',
          borderRadius: 12,
        },
      },
    },
  },
});

export default theme;

export const CHART_COLORS = {
  cyan: '#00d4ff',
  gold: '#ffd700',
  green: '#00ff88',
  card: '#0f3460',
  primary: '#1890ff',
  secondary: '#e94560',
};

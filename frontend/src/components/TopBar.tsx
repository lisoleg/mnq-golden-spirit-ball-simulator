import { useState, useEffect } from 'react';
import { Box, Typography, IconButton } from '@mui/material';
import { Settings } from '@mui/icons-material';
import axios from 'axios';
import { API_BASE_URL } from '../utils/constants';

export default function TopBar() {
  const [apiOnline, setApiOnline] = useState(false);
  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    const checkApi = async () => {
      try {
        await axios.get(`${API_BASE_URL}/health`, { timeout: 5000 });
        setApiOnline(true);
      } catch {
        setApiOnline(false);
      }
    };
    checkApi();
    const id = setInterval(checkApi, 10000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const update = () => {
      setCurrentTime(
        new Date().toLocaleString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        }),
      );
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', gap: 2 }}>
      <Typography variant="h6" sx={{ flexGrow: 1, color: '#e0e0e0' }}>
        MNQ Dashboard
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box
          sx={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: apiOnline ? '#00ff88' : '#e94560',
            boxShadow: apiOnline ? '0 0 6px #00ff88' : '0 0 6px #e94560',
          }}
        />
        <Typography variant="body2" sx={{ color: '#888' }}>
          {apiOnline ? 'API 在线' : 'API 离线'}
        </Typography>
      </Box>

      <Typography variant="body2" sx={{ color: '#888' }}>
        {currentTime}
      </Typography>

      <IconButton sx={{ color: '#888' }}>
        <Settings />
      </IconButton>
    </Box>
  );
}

import { useState } from 'react';
import { Box, Grid, Card, CardContent, Typography, Button, Chip } from '@mui/material';
import { PlayArrow, FastForward } from '@mui/icons-material';
import { CHART_COLORS } from '../theme';
import { formatNumber } from '../utils/formatters';
import * as scfApi from '../api/scf';
import type { SCFSnapshot } from '../api/types';
import { usePolling } from '../hooks/usePolling';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

export default function SCFPanel() {
  const [current, setCurrent] = useState<SCFSnapshot | null>(null);
  const [history, setHistory] = useState<SCFSnapshot[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const status = await scfApi.fetchSCFStatus();
      setCurrent(status);
      setHistory((prev) => [...prev.slice(-99), status]);
    } catch (e) {
      console.error('Failed to fetch SCF status:', e);
    }
  };

  usePolling(fetchStatus, 5000);

  const handleStep = async () => {
    setLoading(true);
    try {
      const result = await scfApi.scfStep();
      setCurrent(result);
      setHistory((prev) => [...prev.slice(-99), result]);
    } catch (e: any) {
      console.error('SCF step error:', e);
    }
    setLoading(false);
  };

  const handleRunToConvergence = async () => {
    setLoading(true);
    try {
      const results = await scfApi.scfRunToConvergence();
      if (results.length > 0) {
        setCurrent(results[results.length - 1]);
        setHistory((prev) => [...prev.slice(-99), ...results]);
      }
    } catch (e: any) {
      console.error('SCF run error:', e);
    }
    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 3 }}>
        三层信息波 (SCF)
      </Typography>

      {/* Info Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>核心波</Typography>
              <Typography variant="h4" sx={{ color: CHART_COLORS.primary, fontWeight: 'bold' }}>
                {formatNumber(current?.core ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>八卦波</Typography>
              <Typography variant="h4" sx={{ color: CHART_COLORS.cyan, fontWeight: 'bold' }}>
                {formatNumber(current?.bagua_mean ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>64卦波</Typography>
              <Typography variant="h4" sx={{ color: CHART_COLORS.gold, fontWeight: 'bold' }}>
                {formatNumber(current?.hex64_mean ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>收敛状态</Typography>
              <Chip
                label={current?.converged ? '已收敛' : '未收敛'}
                sx={{
                  backgroundColor: current?.converged ? '#00ff88' : '#e94560',
                  color: '#fff',
                  fontWeight: 'bold',
                  mt: 1,
                }}
              />
              <Typography variant="body2" sx={{ color: '#888', mt: 1 }}>
                最大变化: {formatNumber(current?.max_change ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Controls */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Button
          variant="contained"
          startIcon={<PlayArrow />}
          onClick={handleStep}
          disabled={loading}
          sx={{ backgroundColor: '#1890ff' }}
        >
          单步
        </Button>
        <Button
          variant="contained"
          startIcon={<FastForward />}
          onClick={handleRunToConvergence}
          disabled={loading}
          sx={{ backgroundColor: '#00ff8820', color: '#00ff88', '&:hover': { backgroundColor: '#00ff8830' } }}
        >
          运行至收敛
        </Button>
      </Box>

      {/* Area Chart */}
      <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
        波值历史趋势
      </Typography>
      <ResponsiveContainer width="100%" height={350}>
        <AreaChart data={history}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
          <XAxis dataKey="timestamp" tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
          <YAxis tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
          <Tooltip contentStyle={{ backgroundColor: '#16213e', border: '1px solid #0f3460' }} />
          <Legend />
          <Area type="monotone" dataKey="core" stroke={CHART_COLORS.primary} fill={CHART_COLORS.primary} fillOpacity={0.15} />
          <Area type="monotone" dataKey="bagua_mean" stroke={CHART_COLORS.cyan} fill={CHART_COLORS.cyan} fillOpacity={0.15} />
          <Area type="monotone" dataKey="hex64_mean" stroke={CHART_COLORS.gold} fill={CHART_COLORS.gold} fillOpacity={0.15} />
        </AreaChart>
      </ResponsiveContainer>
    </Box>
  );
}

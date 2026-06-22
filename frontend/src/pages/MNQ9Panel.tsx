import { useState } from 'react';
import { Box, Grid, Card, CardContent, Typography, Button, MenuItem, Select } from '@mui/material';
import { PlayArrow, TrendingUp, TrendingDown, Warning, Shield } from '@mui/icons-material';
import GaugeChart from '../components/GaugeChart';
import * as mnq9Api from '../api/mnq9';
import type { MNQ9Status } from '../api/types';
import { usePolling } from '../hooks/usePolling';
import { CHART_COLORS } from '../theme';
import { formatNumber, formatPercent } from '../utils/formatters';

const STRATEGIES = [
  { key: 'bull', label: '多头', icon: <TrendingUp />, color: CHART_COLORS.green },
  { key: 'bear', label: '空头', icon: <TrendingDown />, color: CHART_COLORS.secondary },
  { key: 'crisis', label: '危机', icon: <Warning />, color: '#ff6600' },
  { key: 'hedge', label: '对冲', icon: <Shield />, color: CHART_COLORS.gold },
];

const SCENARIOS = [
  'default', 'bull_market', 'bear_market', 'crisis', 'recovery',
  'high_volatility', 'low_volatility', 'black_swan',
];

export default function MNQ9Panel() {
  const [status, setStatus] = useState<MNQ9Status | null>(null);
  const [loading, setLoading] = useState(false);
  const [scenario, setScenario] = useState('default');
  const [strategyValues, setStrategyValues] = useState<Record<string, number>>({
    bull: 0, bear: 0, crisis: 0, hedge: 0,
  });

  const fetchStatus = async () => {
    try {
      const data = await mnq9Api.fetchMNQ9Status();
      setStatus(data);
      // Mock strategy values based on omega
      setStrategyValues({
        bull: data.omega * 0.8,
        bear: data.omega * 0.3,
        crisis: (1 - data.B_conf) * 0.6,
        hedge: data.B_conf * 0.7,
      });
    } catch (e) {
      console.error('Failed to fetch MNQ9 status:', e);
    }
  };

  usePolling(fetchStatus, 5000);

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const data = await mnq9Api.mnq9RunSimulation(scenario, {});
      setStatus(data);
      setStrategyValues({
        bull: data.omega * 0.8,
        bear: data.omega * 0.3,
        crisis: (1 - data.B_conf) * 0.6,
        hedge: data.B_conf * 0.7,
      });
    } catch (e) {
      console.error('MNQ9 simulation error:', e);
    }
    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 1 }}>
        MNQ9 信心核
      </Typography>
      <Card sx={{ backgroundColor: '#16213e', p: 2, mb: 3, borderLeft: '4px solid #faad14' }}>
        <Typography variant="body1" sx={{ color: '#e0e0e0', mb: 0.5 }}>
          四策略预测器 — 多头（bull）、空头（bear）、危机预警（crisis）、对冲（hedge）。
        </Typography>
        <Typography variant="body2" sx={{ color: '#888' }}>
          基于 Omega 参数和 B_conf 信心度计算各策略强度。切换场景可模拟不同市场条件下的策略表现。
        </Typography>
      </Card>

      {/* Confidence Gauge */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
        <GaugeChart
          value={status?.B_conf ?? 0}
          min={0}
          max={1}
          label="信心度"
          color={CHART_COLORS.primary}
        />
      </Box>

      {/* Strategy Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {STRATEGIES.map((s) => (
          <Grid item xs={3} key={s.key}>
            <Card sx={{ backgroundColor: '#0f3460' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, mb: 1 }}>
                  <Box sx={{ color: s.color }}>{s.icon}</Box>
                  <Typography variant="body1" sx={{ color: s.color, fontWeight: 'bold' }}>
                    {s.label}
                  </Typography>
                </Box>
                <Typography variant="h4" sx={{ color: s.color, fontWeight: 'bold' }}>
                  {formatNumber(strategyValues[s.key])}
                </Typography>
                <Typography variant="caption" sx={{ color: '#888' }}>
                  强度: {formatPercent(strategyValues[s.key])}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Scenario Selector + Run Button */}
      <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', mb: 3 }}>
        <Typography variant="body2" sx={{ color: '#888' }}>场景:</Typography>
        <Select
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          size="small"
          sx={{ color: '#e0e0e0', minWidth: 200 }}
        >
          {SCENARIOS.map((s) => (
            <MenuItem key={s} value={s}>{s}</MenuItem>
          ))}
        </Select>
        <Button
          variant="contained"
          startIcon={<PlayArrow />}
          onClick={handleRunSimulation}
          disabled={loading}
          sx={{ backgroundColor: '#1890ff' }}
        >
          运行模拟
        </Button>
      </Box>

      {/* Status Info */}
      <Grid container spacing={2}>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>Omega</Typography>
              <Typography variant="h5" sx={{ color: CHART_COLORS.cyan, fontWeight: 'bold' }}>
                {formatNumber(status?.omega ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>内核</Typography>
              <Typography variant="h5" sx={{ color: CHART_COLORS.gold, fontWeight: 'bold' }}>
                {formatNumber(status?.kernel ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={3}>
          <Card sx={{ backgroundColor: '#0f3460' }}>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="body2" sx={{ color: '#888' }}>历史长度</Typography>
              <Typography variant="h5" sx={{ color: CHART_COLORS.green, fontWeight: 'bold' }}>
                {status?.history_length ?? 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

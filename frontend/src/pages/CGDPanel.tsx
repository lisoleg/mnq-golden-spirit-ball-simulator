import { useState } from 'react';
import { Box, Grid, Card, Typography, List, ListItem, ListItemIcon, ListItemText, Button } from '@mui/material';
import { CheckCircle, Cancel, PlayArrow } from '@mui/icons-material';
import GaugeChart from '../components/GaugeChart';
import { CHART_COLORS } from '../theme';
import { formatNumber } from '../utils/formatters';
import * as cgdApi from '../api/cgd';
import type { CGDStatus } from '../api/types';
import { usePolling } from '../hooks/usePolling';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

export default function CGDPanel() {
  const [status, setStatus] = useState<CGDStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const data = await cgdApi.fetchCGDStatus();
      setStatus(data);
    } catch (e) {
      console.error('Failed to fetch CGD status:', e);
    }
  };

  usePolling(fetchStatus, 5000);

  const handleStep = async () => {
    setLoading(true);
    try {
      const data = await cgdApi.cgdStep();
      setStatus(data);
    } catch (e) {
      console.error('CGD step error:', e);
    }
    setLoading(false);
  };

  const violationRatio = status
    ? status.violation_count / (status.total_constraints || 1)
    : 0;

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 3 }}>
        约束动力学 (CGD)
      </Typography>

      {/* Violation Gauge */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
        <GaugeChart
          value={violationRatio}
          min={0}
          max={1}
          label="违反率"
          color={CHART_COLORS.secondary}
        />
      </Box>

      {/* Constraint List */}
      <Grid container spacing={3}>
        <Grid item xs={6}>
          <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
            约束状态列表
          </Typography>
          <Card sx={{ backgroundColor: '#0f3460', maxHeight: 400, overflow: 'auto' }}>
            <List>
              {status?.constraints.map((c, i) => (
                <ListItem key={i} sx={{ borderBottom: '1px solid #16213e' }}>
                  <ListItemIcon>
                    {c.satisfied ? (
                      <CheckCircle sx={{ color: '#00ff88' }} />
                    ) : (
                      <Cancel sx={{ color: '#e94560' }} />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={c.name}
                    secondary={`值: ${formatNumber(c.value)} | 阈值: ${formatNumber(c.threshold)}`}
                    sx={{ color: '#e0e0e0' }}
                  />
                </ListItem>
              )) || (
                <ListItem>
                  <ListItemText primary="等待数据..." sx={{ color: '#555' }} />
                </ListItem>
              )}
            </List>
          </Card>
        </Grid>

        <Grid item xs={6}>
          <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
            违反历史
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={status?.history || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
              <XAxis dataKey="timestamp" tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
              <YAxis tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
              <Tooltip contentStyle={{ backgroundColor: '#16213e', border: '1px solid #0f3460' }} />
              <Bar dataKey="violations" fill={CHART_COLORS.secondary} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          <Box sx={{ mt: 2 }}>
            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleStep}
              disabled={loading}
              sx={{ backgroundColor: '#1890ff' }}
            >
              推进一步
            </Button>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}

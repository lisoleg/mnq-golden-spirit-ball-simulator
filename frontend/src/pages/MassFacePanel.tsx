import { useEffect } from 'react';
import { Box, Grid, Card, CardContent, Typography } from '@mui/material';
import GaugeChart from '../components/GaugeChart';
import { useMassfaceStore } from '../store/massfaceStore';
import { usePolling } from '../hooks/usePolling';
import { CHART_COLORS } from '../theme';
import { formatNumber } from '../utils/formatters';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const METRICS = [
  { key: 'MASS_FACE', label: 'MASS_FACE', color: CHART_COLORS.primary },
  { key: 'LOCAL_COMP_LOOP', label: 'LOCAL_COMP_LOOP', color: CHART_COLORS.cyan },
  { key: 'LOOP_HOLD_13', label: 'LOOP_HOLD_13', color: CHART_COLORS.gold },
  { key: 'BOUNDARY_LEAK', label: 'BOUNDARY_LEAK', color: CHART_COLORS.green },
  { key: 'DIAG_MINUS_AXIS_LOOP', label: 'DIAG_MINUS_AXIS_LOOP', color: CHART_COLORS.secondary },
];

export default function MassFacePanel() {
  const { readings, history } = useMassfaceStore();
  const fetchReadings = useMassfaceStore((s) => s.fetchReadings);
  const fetchHistory = useMassfaceStore((s) => s.fetchHistory);

  usePolling(fetchReadings, 3000);

  useEffect(() => {
    fetchHistory(100);
  }, [fetchHistory]);

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 3 }}>
        MASS_FACE 面板
      </Typography>

      {/* Gauge */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
        <GaugeChart
          value={readings?.MASS_FACE ?? 0}
          min={0}
          max={1}
          label="MASS_FACE"
          color={CHART_COLORS.primary}
        />
      </Box>

      {/* Metric Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {METRICS.map((m) => (
          <Grid item xs={2.4} key={m.key}>
            <Card sx={{ backgroundColor: '#0f3460' }}>
              <CardContent sx={{ textAlign: 'center', py: 1.5 }}>
                <Typography variant="body2" sx={{ color: '#888' }}>
                  {m.label}
                </Typography>
                <Typography
                  variant="h5"
                  sx={{ color: m.color, fontWeight: 'bold', fontFamily: '"Roboto Mono", monospace' }}
                >
                  {formatNumber(Number(readings?.[m.key as keyof typeof readings] ?? 0))}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* History Chart */}
      <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
        读数历史趋势
      </Typography>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={history}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
          <XAxis dataKey="timestamp" tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
          <YAxis tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
          <Tooltip contentStyle={{ backgroundColor: '#16213e', border: '1px solid #0f3460' }} />
          <Legend />
          {METRICS.map((m) => (
            <Line
              key={m.key}
              type="monotone"
              dataKey={m.key}
              stroke={m.color}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );
}

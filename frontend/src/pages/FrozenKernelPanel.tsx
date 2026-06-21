import { useState } from 'react';
import { Box, Grid, Button, Card, TextField, MenuItem, Select, Typography, Chip } from '@mui/material';
import { PlayArrow, RestartAlt, Security } from '@mui/icons-material';
import StatusCard from '../components/StatusCard';
import ParamSlider from '../components/ParamSlider';
import { useKernelStore } from '../store/kernelStore';
import { usePolling } from '../hooks/usePolling';
import { CHART_COLORS } from '../theme';
import { formatNumber, gateBadge } from '../utils/formatters';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

export default function FrozenKernelPanel() {
  const { status, readingsHistory, loading } = useKernelStore();
  const fetchStatus = useKernelStore((s) => s.fetchStatus);
  const doStep = useKernelStore((s) => s.doStep);
  const reset = useKernelStore((s) => s.reset);
  const doD4Audit = useKernelStore((s) => s.doD4Audit);

  const [steps, setSteps] = useState(1);
  const [seed, setSeed] = useState('');
  const [condition, setCondition] = useState('default');

  usePolling(fetchStatus, 5000);

  // Heatmap rendering
  const field = status?.field || [];
  const heatmapMin = field.length > 0 ? Math.min(...field.flat()) : 0;
  const heatmapMax = field.length > 0 ? Math.max(...field.flat()) : 1;

  const getHeatmapColor = (val: number) => {
    const normalized = (val - heatmapMin) / (heatmapMax - heatmapMin || 1);
    const r = Math.round(normalized * 255);
    const g = Math.round((1 - normalized) * 128);
    const b = Math.round(normalized * 200);
    return `rgb(${r},${g},${b})`;
  };

  const strictGate = status ? gateBadge(status.strict_gate) : null;
  const dynamicGate = status ? gateBadge(status.dynamic_gate) : null;

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 3 }}>
        FrozenKernel 演化面板
      </Typography>

      {/* Top: Status Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item>
          <StatusCard title="步数" value={status?.step_count ?? '-'} unit="步" />
        </Grid>
        <Grid item>
          <Card sx={{ minWidth: 160, backgroundColor: '#0f3460', p: 2 }}>
            <Typography variant="body2" sx={{ color: '#888' }}>严格门控</Typography>
            <Chip
              label={strictGate?.label ?? '-'}
              sx={{
                backgroundColor: strictGate?.color ?? '#888',
                color: '#fff',
                fontWeight: 'bold',
                mt: 1,
              }}
            />
          </Card>
        </Grid>
        <Grid item>
          <Card sx={{ minWidth: 160, backgroundColor: '#0f3460', p: 2 }}>
            <Typography variant="body2" sx={{ color: '#888' }}>动态门控</Typography>
            <Chip
              label={dynamicGate?.label ?? '-'}
              sx={{
                backgroundColor: dynamicGate?.color ?? '#888',
                color: '#fff',
                fontWeight: 'bold',
                mt: 1,
              }}
            />
          </Card>
        </Grid>
      </Grid>

      {/* Middle: Heatmap + Readings Chart */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={5}>
          <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
            8×8 场热图
          </Typography>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: 'repeat(8, 1fr)',
              gap: 1,
              backgroundColor: '#1a1a2e',
              p: 2,
              borderRadius: 2,
            }}
          >
            {field.flat().map((val, i) => (
              <Box
                key={i}
                sx={{
                  width: 40,
                  height: 40,
                  backgroundColor: getHeatmapColor(val),
                  borderRadius: 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 10,
                  color: '#fff',
                }}
              >
                {formatNumber(val, 2)}
              </Box>
            ))}
            {field.length === 0 &&
              Array.from({ length: 64 }).map((_, i) => (
                <Box
                  key={i}
                  sx={{
                    width: 40,
                    height: 40,
                    backgroundColor: '#16213e',
                    borderRadius: 1,
                  }}
                />
              ))}
          </Box>
        </Grid>

        <Grid item xs={7}>
          <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
            MASS_FACE 读数趋势
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={readingsHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
              <XAxis
                dataKey="timestamp"
                tick={{ fill: '#888', fontSize: 11 }}
                stroke="#0f3460"
              />
              <YAxis tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
              <Tooltip contentStyle={{ backgroundColor: '#16213e', border: '1px solid #0f3460' }} />
              <Legend />
              <Line type="monotone" dataKey="MASS_FACE" stroke={CHART_COLORS.primary} dot={false} />
              <Line type="monotone" dataKey="LOCAL_COMP_LOOP" stroke={CHART_COLORS.cyan} dot={false} />
              <Line type="monotone" dataKey="LOOP_HOLD_13" stroke={CHART_COLORS.gold} dot={false} />
              <Line type="monotone" dataKey="BOUNDARY_LEAK" stroke={CHART_COLORS.green} dot={false} />
              <Line type="monotone" dataKey="DIAG_MINUS_AXIS_LOOP" stroke={CHART_COLORS.secondary} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Grid>
      </Grid>

      {/* Controls */}
      <Box sx={{ backgroundColor: '#16213e', borderRadius: 2, p: 3 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={3}>
            <TextField
              label="种子值"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              size="small"
              fullWidth
              sx={{
                '& .MuiInputBase-input': { color: '#e0e0e0' },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: '#0f3460' },
              }}
            />
          </Grid>
          <Grid item xs={3}>
            <Select
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              size="small"
              fullWidth
              sx={{ color: '#e0e0e0' }}
            >
              <MenuItem value="default">默认</MenuItem>
              <MenuItem value="strict">严格</MenuItem>
              <MenuItem value="relaxed">宽松</MenuItem>
            </Select>
          </Grid>
          <Grid item xs={3}>
            <ParamSlider label="演化步数" value={steps} min={1} max={100} step={1} onChange={setSteps} />
          </Grid>
          <Grid item xs={3}>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" startIcon={<PlayArrow />} onClick={() => doStep(steps)} disabled={loading} sx={{ backgroundColor: '#1890ff' }}>
                单步演化
              </Button>
              <Button variant="outlined" startIcon={<RestartAlt />} onClick={() => reset(seed ? Number(seed) : undefined, condition)} disabled={loading} sx={{ color: '#1890ff', borderColor: '#1890ff' }}>
                重置
              </Button>
              <Button variant="outlined" startIcon={<Security />} onClick={doD4Audit} disabled={loading} sx={{ color: '#ffd700', borderColor: '#ffd700' }}>
                D4审计
              </Button>
            </Box>
          </Grid>
        </Grid>
      </Box>
    </Box>
  );
}


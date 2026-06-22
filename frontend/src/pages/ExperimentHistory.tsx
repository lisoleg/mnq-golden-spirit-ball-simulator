import { useState, useEffect } from 'react';
import { Box, Typography, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Button, Dialog, DialogTitle, DialogContent, DialogActions, Chip, Card } from '@mui/material';
import { useExperimentStore } from '../store/experimentStore';
import { CHART_COLORS } from '../theme';
import { formatTimestamp, statusColor } from '../utils/formatters';
import * as experimentApi from '../api/experiment';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

export default function ExperimentHistory() {
  const { history, loading } = useExperimentStore();
  const fetchHistory = useExperimentStore((s) => s.fetchHistory);
  const [selectedResult, setSelectedResult] = useState<any>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [comparisonData, setComparisonData] = useState<any[]>([]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleView = async (id: string) => {
    try {
      const entry = await experimentApi.fetchHistoryDetail(id);
      setSelectedResult(entry.result);
      setDialogOpen(true);
    } catch (e) {
      console.error('Failed to fetch history detail:', e);
    }
  };

  // Build comparison chart data from completed experiments
  useEffect(() => {
    const completed = history.filter((h) => h.status === 'completed' && h.result);
    if (completed.length > 0) {
      const data = completed.map((h) => ({
        name: h.name,
        timestamp: formatTimestamp(h.timestamp),
        value: h.result?.score ?? h.result?.value ?? 0,
      }));
      setComparisonData(data);
    }
  }, [history]);

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 1 }}>
        实验历史
      </Typography>
      <Card sx={{ backgroundColor: '#16213e', p: 2, mb: 3, borderLeft: '4px solid #13c2c2' }}>
        <Typography variant="body1" sx={{ color: '#e0e0e0', mb: 0.5 }}>
          已运行实验的完整历史记录。
        </Typography>
        <Typography variant="body2" sx={{ color: '#888' }}>
          包含实验名称、参数配置、运行时长、最终状态。点击「详情」查看实验输出数据，底部图表展示已完成实验的得分对比。
        </Typography>
      </Card>

      {/* History Table */}
      <TableContainer component={Paper} sx={{ backgroundColor: '#0f3460', mb: 3 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: '#888' }}>ID</TableCell>
              <TableCell sx={{ color: '#888' }}>名称</TableCell>
              <TableCell sx={{ color: '#888' }}>时间</TableCell>
              <TableCell sx={{ color: '#888' }}>状态</TableCell>
              <TableCell sx={{ color: '#888' }}>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {history.map((h) => (
              <TableRow key={h.id}>
                <TableCell sx={{ color: '#e0e0e0' }}>{h.id}</TableCell>
                <TableCell sx={{ color: '#1890ff' }}>{h.name}</TableCell>
                <TableCell sx={{ color: '#e0e0e0' }}>{formatTimestamp(h.timestamp)}</TableCell>
                <TableCell>
                  <Chip
                    label={h.status}
                    sx={{
                      backgroundColor: statusColor(h.status),
                      color: '#fff',
                      fontWeight: 'bold',
                    }}
                  />
                </TableCell>
                <TableCell>
                  <Button
                    size="small"
                    onClick={() => handleView(h.id)}
                    sx={{ color: '#1890ff' }}
                  >
                    查看结果
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {history.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} sx={{ color: '#555', textAlign: 'center' }}>
                  {loading ? '加载中...' : '无历史记录'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Comparison Chart */}
      {comparisonData.length > 0 && (
        <Box>
          <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
            实验对比图
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
              <XAxis dataKey="name" tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
              <YAxis tick={{ fill: '#888', fontSize: 11 }} stroke="#0f3460" />
              <Tooltip contentStyle={{ backgroundColor: '#16213e', border: '1px solid #0f3460' }} />
              <Legend />
              <Line type="monotone" dataKey="value" stroke={CHART_COLORS.primary} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* Result Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ color: '#1890ff' }}>实验结果</DialogTitle>
        <DialogContent>
          <Box sx={{ backgroundColor: '#0a0a0a', p: 2, borderRadius: 1, maxHeight: 400, overflow: 'auto' }}>
            <pre style={{ color: '#00ff88', fontFamily: '"Roboto Mono", monospace', fontSize: 13 }}>
              {selectedResult ? JSON.stringify(selectedResult, null, 2) : ''}
            </pre>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} sx={{ color: '#888' }}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

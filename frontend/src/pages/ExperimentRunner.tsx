import { useState, useEffect, useRef } from 'react';
import { Box, Card, CardContent, Typography, Button, LinearProgress, Grid, TextField } from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import OutputTerminal from '../components/OutputTerminal';
import { useExperimentStore } from '../store/experimentStore';
import { SSE_BASE_URL } from '../utils/constants';

export default function ExperimentRunner() {
  const { experiments, loading } = useExperimentStore();
  const fetchExperiments = useExperimentStore((s) => s.fetchExperiments);
  const runExperiment = useExperimentStore((s) => s.runExperiment);
  const updateTaskStatus = useExperimentStore((s) => s.updateTaskStatus);

  const [selectedExp, setSelectedExp] = useState<string | null>(null);
  const [params, setParams] = useState<Record<string, any>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [sseConnected, setSseConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    fetchExperiments();
  }, [fetchExperiments]);

  const handleRun = async () => {
    if (!selectedExp) return;
    setLogs([]);
    setProgress(0);
    try {
      const taskId = await runExperiment(selectedExp, params);
      // Open SSE connection for live progress
      const es = new EventSource(`${SSE_BASE_URL}/${taskId}`);
      esRef.current = es;

      es.onopen = () => setSseConnected(true);

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.log) {
            setLogs((prev) => [...prev, data.log]);
          }
          if (data.progress) {
            setProgress(data.progress);
          }
          if (data.status === 'completed' || data.status === 'failed') {
            es.close();
            setSseConnected(false);
            updateTaskStatus(taskId);
          }
        } catch {
          setLogs((prev) => [...prev, event.data]);
        }
      };

      es.onerror = () => {
        setSseConnected(false);
        es.close();
        // Fallback: poll for status
        const pollId = setInterval(async () => {
          await updateTaskStatus(taskId);
          const task = useExperimentStore.getState().currentTask;
          if (task) {
            setProgress(task.progress * 100);
            if (task.log) setLogs(task.log);
            if (task.status === 'completed' || task.status === 'failed') {
              clearInterval(pollId);
            }
          }
        }, 2000);
      };
    } catch (e: any) {
      setLogs((prev) => [...prev, `错误: ${e.message}`]);
    }
  };

  const selectedExperiment = experiments.find((e) => e.id === selectedExp);

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 3 }}>
        实验运行器
      </Typography>

      <Grid container spacing={3}>
        {/* Left: Experiment List */}
        <Grid item xs={5}>
          <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
            可用实验
          </Typography>
          {experiments.map((exp) => (
            <Card
              key={exp.id}
              onClick={() => {
                setSelectedExp(exp.id);
                setParams({});
              }}
              sx={{
                mb: 1,
                cursor: 'pointer',
                backgroundColor: selectedExp === exp.id ? '#1890ff20' : '#0f3460',
                border: selectedExp === exp.id ? '2px solid #1890ff' : '1px solid #16213e',
                '&:hover': { backgroundColor: '#1890ff15' },
              }}
            >
              <CardContent sx={{ py: 1.5 }}>
                <Typography variant="body1" sx={{ color: '#e0e0e0', fontWeight: 'bold' }}>
                  {exp.name}
                </Typography>
                <Typography variant="body2" sx={{ color: '#888' }}>
                  {exp.description}
                </Typography>
              </CardContent>
            </Card>
          ))}
          {experiments.length === 0 && !loading && (
            <Typography variant="body2" sx={{ color: '#555' }}>
              无可用实验，请检查API连接
            </Typography>
          )}
        </Grid>

        {/* Right: Parameters + Output */}
        <Grid item xs={7}>
          {selectedExperiment ? (
            <>
              <Typography variant="subtitle2" sx={{ color: '#888', mb: 1 }}>
                参数配置 — {selectedExperiment.name}
              </Typography>
              <Box sx={{ mb: 2 }}>
                <TextField
                  label="参数 JSON"
                  placeholder='{ "key": "value" }'
                  value={JSON.stringify(params)}
                  onChange={(e) => {
                    try {
                      setParams(JSON.parse(e.target.value));
                    } catch {
                      // allow raw text editing
                    }
                  }}
                  multiline
                  rows={3}
                  fullWidth
                  sx={{
                    '& .MuiInputBase-input': { color: '#e0e0e0' },
                    '& .MuiOutlinedInput-notchedOutline': { borderColor: '#0f3460' },
                  }}
                />
              </Box>

              <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleRun}
                  disabled={loading}
                  sx={{ backgroundColor: '#1890ff', '&:hover': { backgroundColor: '#40a9ff' } }}
                >
                  运行实验
                </Button>
                {sseConnected && (
                  <Typography variant="caption" sx={{ color: '#00ff88' }}>
                    SSE 已连接
                  </Typography>
                )}
              </Box>

              {progress > 0 && (
                <Box sx={{ mb: 2 }}>
                  <LinearProgress
                    variant="determinate"
                    value={progress}
                    sx={{
                      backgroundColor: '#0f3460',
                      '& .MuiLinearProgress-bar': { backgroundColor: '#1890ff' },
                    }}
                  />
                  <Typography variant="caption" sx={{ color: '#888' }}>
                    进度: {progress.toFixed(1)}%
                  </Typography>
                </Box>
              )}

              <OutputTerminal lines={logs} />
            </>
          ) : (
            <Typography variant="body1" sx={{ color: '#555' }}>
              请从左侧选择一个实验
            </Typography>
          )}
        </Grid>
      </Grid>
    </Box>
  );
}

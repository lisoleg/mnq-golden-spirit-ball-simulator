import { useState } from 'react';
import { Box, Card, Typography, TextField, Button, Switch, FormControlLabel, Chip, Grid } from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import ParamSlider from '../components/ParamSlider';
import OutputTerminal from '../components/OutputTerminal';
import * as deepApi from '../api/deep';
import { CHART_COLORS } from '../theme';
import { formatNumber } from '../utils/formatters';

export default function DeepPanel() {
  const [seedText, setSeedText] = useState('');
  const [length, setLength] = useState(128);
  const [temperature, setTemperature] = useState(0.7);
  const [syntaxConstraint, setSyntaxConstraint] = useState(true);
  const [loading, setLoading] = useState(false);
  const [output, setOutput] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setOutput([]);
    try {
      const data = await deepApi.deepGenerate({
        seed_text: seedText,
        length,
        temperature,
        syntax_constraint: syntaxConstraint,
      });
      setResult(data);
      setOutput([
        '=== 生成结果 ===',
        data.text,
        '',
        `语法有效: ${data.syntax_valid ? '是' : '否'}`,
        `熵值: ${formatNumber(data.entropy)}`,
        `κ签名: ${data.kappa_signature}`,
      ]);
    } catch (e: any) {
      setOutput([`生成失败: ${e.message}`]);
    }
    setLoading(false);
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ color: '#1890ff', mb: 1 }}>
        MNQ-Deep 深度生成
      </Typography>
      <Card sx={{ backgroundColor: '#16213e', p: 2, mb: 3, borderLeft: '4px solid #eb2f96' }}>
        <Typography variant="body1" sx={{ color: '#e0e0e0', mb: 0.5 }}>
          接入 DeepSeek API 的文本生成模块 — 基于 MNQ 理论框架生成回答。
        </Typography>
        <Typography variant="body2" sx={{ color: '#888' }}>
          输入种子文本 → 调整长度和温度 → 点击生成。DeepSeek 会基于金符学、阴龙积、八卦算子、冻结核等 MNQ 理论生成回答。语法有效性、熵值、κ 签名同步计算。
        </Typography>
      </Card>

      <Grid container spacing={3}>
        <Grid item xs={5}>
          <Card sx={{ backgroundColor: '#0f3460', p: 3 }}>
            <Typography variant="subtitle2" sx={{ color: '#888', mb: 2 }}>
              参数配置
            </Typography>

            <TextField
              label="种子文本"
              value={seedText}
              onChange={(e) => setSeedText(e.target.value)}
              multiline
              rows={4}
              fullWidth
              placeholder="输入种子文本..."
              sx={{
                mb: 2,
                '& .MuiInputBase-input': { color: '#e0e0e0' },
                '& .MuiOutlinedInput-notchedOutline': { borderColor: '#16213e' },
              }}
            />

            <ParamSlider
              label="生成长度"
              value={length}
              min={32}
              max={1024}
              step={32}
              onChange={setLength}
            />

            <ParamSlider
              label="温度"
              value={temperature}
              min={0.1}
              max={2.0}
              step={0.1}
              onChange={setTemperature}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={syntaxConstraint}
                  onChange={(e) => setSyntaxConstraint(e.target.checked)}
                  sx={{ '& .MuiSwitch-thumb': { backgroundColor: syntaxConstraint ? '#1890ff' : '#888' } }}
                />
              }
              label="语法约束"
              sx={{ color: '#e0e0e0', mb: 2 }}
            />

            <Button
              variant="contained"
              startIcon={<PlayArrow />}
              onClick={handleGenerate}
              disabled={loading || !seedText}
              fullWidth
              sx={{ backgroundColor: '#1890ff' }}
            >
              生成
            </Button>
          </Card>

          {result && (
            <Box sx={{ mt: 2 }}>
              <Chip
                label={result.syntax_valid ? '语法有效' : '语法无效'}
                sx={{
                  backgroundColor: result.syntax_valid ? '#00ff88' : '#e94560',
                  color: '#fff',
                  mr: 1,
                }}
              />
              <Chip
                label={`熵: ${formatNumber(result.entropy)}`}
                sx={{ backgroundColor: '#0f3460', color: CHART_COLORS.gold }}
              />
            </Box>
          )}
        </Grid>

        <Grid item xs={7}>
          <OutputTerminal lines={output} />
        </Grid>
      </Grid>
    </Box>
  );
}


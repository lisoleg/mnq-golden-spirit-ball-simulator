import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Typography, Card, CardContent, Divider, Chip, Table,
  TableBody, TableRow, TableCell, Paper,
} from '@mui/material';
import {
  Science, AcUnit, BarChart, Waves, Link,
  GpsFixed, Psychology, PhotoCamera, Assignment, School,
} from '@mui/icons-material';

const moduleCards = [
  {
    icon: <Science sx={{ fontSize: 32, color: '#1890ff' }} />,
    title: '实验运行器',
    path: '/experiment',
    desc: '运行18个预定义仿真实验（零场测试、PG拓扑囚禁、六角环隙等），通过SSE实时查看日志输出和进度。从左侧选择实验→配置JSON参数→点击运行即可。',
  },
  {
    icon: <AcUnit sx={{ fontSize: 32, color: '#00d4ff' }} />,
    title: 'FrozenKernel 冷冻核',
    path: '/kernel',
    desc: '冻结核演化引擎，MNQ核心模块。严格门控（StrictGate）判定金符学质量面+多余环路+对消轴环三个条件是否同时满足；动态门控（DynamicGate）根据约束违反度动态调整阈值。D4审计执行8种D4变换检测协变性。',
  },
  {
    icon: <BarChart sx={{ fontSize: 32, color: '#52c41a' }} />,
    title: 'MASS_FACE 质量面',
    path: '/massface',
    desc: '显示五个核心指标：MASS_FACE（质量面读数）、LOCAL_COMP_LOOP（局部完备回路）、LOOP_HOLD_13（环路保持13）、BOUNDARY_LEAK（边界泄漏）、DIAG_MINUS_AXIS_LOOP（对角减轴环）。这些指标构成了MNQ场质量的完整画像。',
  },
  {
    icon: <Waves sx={{ fontSize: 32, color: '#ff7a45' }} />,
    title: '三层信息波 (SCF)',
    path: '/scf',
    desc: '自洽场迭代。三层分别为：核波（原子尺度信息传递）、八卦波（中尺度信息编码）、64卦波（宏观尺度信息涌现）。点击"运行至收敛"观察三层波如何逐步自洽。',
  },
  {
    icon: <Link sx={{ fontSize: 32, color: '#ff4d4f' }} />,
    title: '约束动力学 (CGD)',
    path: '/cgd',
    desc: '约束驱动动力学。监控多条约束（质量面守恒、相干度、能量上限等）的满足状态。红色表示违反、绿色表示满足。违反度越大说明系统越不稳定。',
  },
  {
    icon: <GpsFixed sx={{ fontSize: 32, color: '#faad14' }} />,
    title: 'MNQ9 信心核',
    path: '/mnq9',
    desc: '四策略预测器：多头（bull）、空头（bear）、危机预警（crisis）、对冲（hedge）。基于Omega参数和B_conf信心度计算各策略强度，可用于趋势分析和风险评估。',
  },
  {
    icon: <Psychology sx={{ fontSize: 32, color: '#eb2f96' }} />,
    title: 'MNQ-Deep 深度生成',
    path: '/deep',
    desc: '接入DeepSeek API的文本生成模块。输入种子文本，DeepSeek会基于MNQ理论框架（金符学、阴龙积、八卦算子、冻结核）生成回答。语法有效性、熵值、κ签名同步计算。',
  },
  {
    icon: <PhotoCamera sx={{ fontSize: 32, color: '#9254de' }} />,
    title: 'κ-Snap 快照',
    path: '/kappa',
    desc: 'TOMAS协议的快照管理。查看/下载/删除历次实验的κ快照，每个快照包含SHA256指纹用于可验证性。支持JSON格式导出。',
  },
  {
    icon: <Assignment sx={{ fontSize: 32, color: '#13c2c2' }} />,
    title: '实验历史',
    path: '/history',
    desc: '所有已运行实验的历史记录。包括实验名称、参数、运行时长、最终状态。支持翻页浏览和详细查看。',
  },
];

const terms = [
  { term: '金符学', def: 'MNQ的理论基础，融合中国传统八卦算子与现代数学（八元数、D4群、非结合代数）' },
  { term: '阴龙积', def: '3D复广数空间中的耦合运算 ⊙，非结合性是其核心特征，由Associator [i,i,j]≠0证明' },
  { term: '3D复广数', def: 'z = a+bi+cj, i²=j²=-1, ij=ji。金符学基础代数结构' },
  { term: '八卦算子', def: '8个算子（䷀䷁䷂䷃䷄䷅䷆䷇）与八元数基底一一同构映射' },
  { term: 'D4 协变', def: 'D4二面体群下的变换协变性，8种变换L1_diff全零=完美协变' },
  { term: '冻结核', def: 'MNQ8更新律：本征振荡→N₈邻域耦合→阈值判定，5层递进具现' },
  { term: 'SCF', def: '自洽场迭代（Self-Consistent Field），三层信息波逐步收敛的过程' },
  { term: 'CGD', def: '约束驱动动力学（Constraint-Guided Dynamics），用于维持系统稳定' },
  { term: 'MNQ9', def: '信心评估模块，含4策略预测器，用于多情景分析和风险评估' },
  { term: 'TOMAS', def: '可验证输出协议（Tamper-proof Observable Machine Arbitration System）' },
  { term: 'κ 快照', def: 'TOMAS的完整性快照，含Merkle链和SHA256指纹，用于输出不可篡改性' },
  { term: 'PG拓扑囚禁', def: 'Oloid差分+持续超阈值判定，鲁珀特之泪孤子流贯囚禁' },
];

export default function Documentation() {
  const navigate = useNavigate();

  return (
    <Box>
      <Typography variant="h4" sx={{ color: '#1890ff', mb: 1 }}>
        使用文档
      </Typography>
      <Typography variant="body2" sx={{ color: '#888', mb: 4 }}>
        MNQ 金灵球网络仿真器 — 完整操作指南与理论速览
      </Typography>

      {/* 第一章：项目概述 */}
      <Card sx={{ backgroundColor: '#16213e', mb: 4, borderLeft: '4px solid #1890ff' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            <School sx={{ color: '#1890ff' }} />
            <Typography variant="h6" sx={{ color: '#1890ff' }}>第一章 · 项目概述</Typography>
          </Box>
          <Typography variant="body1" sx={{ color: '#e0e0e0', lineHeight: 1.8 }}>
            MNQ（金灵球网络，JinLing Mesh Network）是一个基于<strong>金符学理论</strong>的复杂系统仿真框架。
            它将中国传统八卦理论与现代数学（八元数非结合代数、D4协变群、冷冻核动力学）相结合，
            构建了一个多层级信息处理模型，覆盖从微观核波到宏观64卦波的全尺度信息涌现。
          </Typography>
          <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {['Python 3.10+', 'Flask', 'React 18', 'MUI v5', 'NumPy', 'Recharts', 'DeepSeek API'].map((t) => (
              <Chip key={t} label={t} size="small" sx={{ backgroundColor: '#0f3460', color: '#888' }} />
            ))}
          </Box>
        </CardContent>
      </Card>

      {/* 第二章：模块说明 */}
      <Typography variant="h6" sx={{ color: '#1890ff', mb: 2 }}>第二章 · 模块说明</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mb: 4 }}>
        {moduleCards.map((mod) => (
          <Card
            key={mod.path}
            sx={{
              backgroundColor: '#16213e',
              cursor: 'pointer',
              transition: 'all 0.2s',
              '&:hover': { backgroundColor: '#1a2a4e', transform: 'translateY(-2px)' },
            }}
            onClick={() => navigate(mod.path)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                {mod.icon}
                <Typography variant="subtitle1" sx={{ color: '#e0e0e0', fontWeight: 600 }}>
                  {mod.title}
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ color: '#aaa', lineHeight: 1.6 }}>
                {mod.desc}
              </Typography>
            </CardContent>
          </Card>
        ))}
      </Box>

      <Divider sx={{ borderColor: '#0f3460', mb: 4 }} />

      {/* 第三章：快速上手 */}
      <Typography variant="h6" sx={{ color: '#1890ff', mb: 2 }}>第三章 · 快速上手</Typography>
      <Card sx={{ backgroundColor: '#16213e', mb: 4 }}>
        <CardContent>
          <Box component="ol" sx={{ color: '#e0e0e0', lineHeight: 2.2, pl: 2 }}>
            <li>从左侧导航选择模块页面</li>
            <li>在实验运行器中先跑一个实验（如 <Chip label="ZERO_FIELD" size="small" sx={{ backgroundColor: '#0f3460', color: '#52c41a' }} />）验证系统正常</li>
            <li>各面板每 3~5 秒自动轮询刷新状态数据</li>
            <li>FrozenKernel 和 SCF 面板可手动推进一步，观察单步变化</li>
            <li>MNQ-Deep 面板需要 DeepSeek API 可用（已配置），输入文本即可生成</li>
          </Box>
        </CardContent>
      </Card>

      {/* 第四章：关键术语 */}
      <Typography variant="h6" sx={{ color: '#1890ff', mb: 2 }}>第四章 · 关键术语</Typography>
      <Paper sx={{ backgroundColor: '#16213e', mb: 4 }}>
        <Table size="small">
          <TableBody>
            {terms.map((t) => (
              <TableRow key={t.term} sx={{ '&:last-child td': { borderBottom: 0 } }}>
                <TableCell sx={{ color: '#e0e0e0', fontWeight: 600, whiteSpace: 'nowrap', width: 140, borderColor: '#0f3460' }}>
                  {t.term}
                </TableCell>
                <TableCell sx={{ color: '#aaa', lineHeight: 1.6, borderColor: '#0f3460' }}>
                  {t.def}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Paper>

      <Divider sx={{ borderColor: '#0f3460', mb: 4 }} />

      {/* 第五章：技术架构 */}
      <Typography variant="h6" sx={{ color: '#1890ff', mb: 2 }}>第五章 · 技术架构</Typography>
      <Card sx={{ backgroundColor: '#16213e', mb: 4 }}>
        <CardContent>
          <Typography component="pre" sx={{ color: '#aaa', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.8, overflowX: 'auto' }}>
{`mnq_windows/
├── mnq_core.py          # 核心算法 (~2000行): 金符学全模块
├── mnq_dashboard.py     # tkinter GUI (桌面版)
├── mnq_deep.py          # MNQ-Deep Combo Transformer
├── mnq9_core.py         # MNQ9 信心评估独立模块
├── PAPER.md             # 顶刊级论文 (v3.2)
├── backend/             # Flask REST API (44路由, 11蓝图)
│   ├── app.py           # 入口, 生产模式静态文件服务
│   ├── config.py        # 端口/CORS/SSE 配置
│   └── api/             # 11个 Blueprint 模块
└── frontend/            # React 18 SPA
    ├── src/pages/       # 9个页面组件
    ├── src/api/         # 11个 API 代理模块
    ├── src/store/       # 5个 Zustand 状态管理
    └── dist/            # 构建产物 (Flask直接托管)`}
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
}

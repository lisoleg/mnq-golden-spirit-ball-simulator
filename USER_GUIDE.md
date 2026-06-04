# MNQ 金灵球网络仿真器 v2.0 — 使用手册

> **MNQ Golden Spirit-Ball Network Simulator — User Guide**
>
> 基于复合体理学 (Composite Physics) MNQ8/MNQ9 理论体系 + CGD 约束生成动力学
>
> Windows Edition · Python 3.10+

---

## 目录

1. [系统概述](#1-系统概述)
2. [快速安装](#2-快速安装)
3. [CLI 仿真模式](#3-cli-仿真模式)
4. [GUI 仪表盘模式](#4-gui-仪表盘模式)
5. [API 编程接口](#5-api-编程接口)
6. [实验参数配置](#6-实验参数配置)
7. [常见问题](#7-常见问题)

---

## 1. 系统概述

MNQ 金灵球网络仿真器是对 macOS 原生 MNQ 项目的完整 Windows 移植与升级，实现了复合体理学微信公众号 14 篇文章中描述的全部核心理念。

### 1.1 核心模块

| 模块 | 缩写 | 功能 |
|------|------|------|
| 金符学 3D 复广数 | GS3D | 复数扩展代数学 $a+bi+cj$，阴龙积 $\odot$ 运算 |
| 金灵球网格 | JinlingMesh | $N \times N$ 球体网络，N₈ 邻域耦合 |
| 三元动力核 | MNQMinimal | $\phi = \Omega - \frac{1}{2}$ 极简生成公式 |
| 三层信息波 | SCF | 核心层 $\to$ 八卦层 $\to$ 六十四卦层 递归生成 |
| CGD 约束引擎 | CGD | 五公理约束驱动动力学 (A1–A5) |
| 六十四卦映射 | Hex64 | x86 指令 $\leftrightarrow$ 卦象 $\leftrightarrow$ 能流参数 |
| 刘机制调度器 | LiuScheduler | $S_{Rel} = \alpha M + \beta H[\Theta]$ 最优路径 |
| PG 拓扑囚禁 | PG Trap | Oloid 差分 + 持续超阈值判定 |
| MNQ9 信心模型 | MNQ9 | $\Omega/\phi_{future}/B_{conf}$ 三重趋势预测 |
| GPU 场演化 | MNQFieldGPU | $\phi/\Omega/\psi/\xi$ 四场 Laplacian 耦合 |
| MNQ Cloud API | CloudAPI | atomic / meso / macro 三尺度锚定仿真 |

### 1.2 文件结构

```
mnq_windows/
├── mnq_core.py        # 核心算法 (930+ 行, 15 个类/模块)
├── mnq_dashboard.py   # GUI 仪表盘 + CLI 仿真 (tkinter)
├── mnq9_core.py       # MNQ9 信心核模型
├── run_mnq.bat        # Windows 一键启动脚本
├── USER_GUIDE.md      # 本使用手册
└── PAPER.md           # 设计与实现论文
```

---

## 2. 快速安装

### 2.1 环境要求

- Windows 10/11
- Python 3.10+ (推荐 3.13)

### 2.2 一键安装

```powershell
# 进入项目目录
cd mnq_windows

# 创建虚拟环境
python -m venv .venv

# 安装依赖
.venv\Scripts\python.exe -m pip install numpy matplotlib
```

### 2.3 启动

```powershell
# GUI 仪表盘模式
.\run_mnq.bat

# CLI 仿真模式
.\run_mnq.bat --cli
```

或直接调用 Python：

```powershell
.venv\Scripts\python.exe mnq_dashboard.py        # GUI
.venv\Scripts\python.exe mnq_dashboard.py --cli  # CLI
```

---

## 3. CLI 仿真模式

CLI 模式运行 12 项预定义实验，无需图形界面。

```powershell
.venv\Scripts\python.exe mnq_dashboard.py --cli
```

### 3.1 实验清单

#### 实验 1: ZERO_FIELD — 死零场

```
验证死零不破缺定理：零初始场演化后仍为零
预期: Mass=0, MF=0
```

#### 实验 2: BACKGROUND_OSC — 背景振荡

```
随机微扰下的本征振荡演化
预期: Mass≈0.0004, MF=0 (弥散态，未形成质量面)
```

#### 实验 3: HEX_RING_GAP — 六角环缺口

```
六边形激励环 + 缺口设计，测试流贯囚禁
预期: MF≥40 (鲁珀特之泪孤子形成)
```

#### 实验 4: 金符学 3D 复广数运算

```
测试 GoldenSymbol3D 的阴龙积 ⊙ 运算
验证: |z₁⊙z₂| 在合理范围
```

#### 实验 5: 刘机制最优路径

```
在网格上寻找最小 S_Rel 阻抗路径
S_Rel = α·M + β·H[Θ]
```

#### 实验 6: MNQ Cloud API 多尺度仿真

```
三尺度锚定: atomic (10⁻¹⁸ J) / meso (10⁻²⁰ J) / macro (10²⁶ J)
验证: 各尺度相干度一致
```

#### 实验 7: Hex64 六十四卦映射

```
前 8 卦映射: 乾→MOV, 坤→ADD, 震→SUB, 巽→MUL, ...
显示卦名 + 指令 + φ/Ω 参数
```

#### 实验 8: GPU 场演化性能基准

```
5000 步四场演化，测量吞吐量
预期: >5000 steps/s
```

#### 实验 9: 三层信息波 SCF 收敛

```
核心→八卦→64卦 300 步递归
输出: 核波值、介观均值、64卦均值、收敛状态
```

#### 实验 10: CGD 约束驱动动力学

```
五公理约束评估：总违反度、平均违反度、稳态数
```

#### 实验 11: MNQ9 信心评估模型

```
单策略预测：趋势方向、信心强度、波动率、综合值
```

#### 实验 12: MNQ9 多策略预测对比

```
四策略并行预测：牛策略、熊策略、危机预警、对冲策略
比较各策略的 Ω 值和趋势方向
```

---

## 4. GUI 仪表盘模式

```powershell
.\run_mnq.bat
```

### 4.1 主面板布局

```
┌──────────────────────────────────────────┐
│  MNQ 金灵球网络仿真器 v2.0              │
├────────────────────┬─────────────────────┤
│  MNQ 场可视化      │  三层信息波 Panel    │
│  (2D 热力图)       │  · 核波 (core)      │
│  · Ftel 幅值分布   │  · 八卦层均值        │
│  · Mass Face 检测  │  · 64卦层均值        │
│  · 实时更新        │  · 收敛灯           │
├────────────────────┼─────────────────────┤
│  实验控制 Panel     │  CGD 约束 Panel      │
│  · 预定义实验选择   │  · 约束违反度        │
│  · 自定义参数       │  · 相态指示          │
│  · 仿真步数/速度    │  · 稳态计数          │
│  · 启动/停止/重置  │                     │
├────────────────────┴─────────────────────┤
│  MNQ9 信心面板                           │
│  · 四策略预测比对  · 趋势方向  · 波动率  │
│  · Ω 时间序列图                          │
├──────────────────────────────────────────┤
│  状态栏: φ/Ω/γ | 三相值 | RIP | 步数    │
└──────────────────────────────────────────┘
```

### 4.2 面板说明

#### MNQ 场可视化 (左侧)
- 2D 彩色热力图显示当前各金灵球的 Ftel 流贯幅值
- 质量面 (Mass Face) 高亮标记
- 支持鼠标缩放和拖拽

#### 三层信息波 Panel
- **核波 (Core Wave)**: 原子尺度的信息载体
- **八卦层均值**: 8×8 中尺度信号
- **64卦层均值**: 宏观尺度综合信号
- **收敛指示灯**: 绿色=已收敛 / 红色=未收敛

#### 实验控制 Panel
| 实验 | 预设 | 说明 |
|------|------|------|
| ZERO_FIELD | 零场 | 死零不破缺验证 |
| BACKGROUND_OSC | 背景振荡 | 弥散态测试 |
| HEX_RING_GAP | 六角环 | 流贯囚禁测试 |
| CUSTOM | 自定义 | 手动调节参数 |

可调参数：
- **网格尺寸 (dim)**: 8–64
- **耦合强度 (Coupling)**: 0.1–1.0
- **仿真步数 (Steps)**: 100–10000
- **CGD 调制强度**: 0.001–0.1

#### CGD 约束 Panel
- 实时显示 `mass_upper_bound`、`coherence_window`、`energy_balance` 三个约束的违反度
- 相态 (Phase State) 指示器
- 稳态 (Steady State) 计数

#### MNQ9 信心面板
- **趋势方向**: UP / DOWN 箭头 + 颜色
- **信心强度**: 0–1 数值条
- **波动率**: 标准差
- **四策略对比表**: 牛策略 / 熊策略 / 危机预警 / 对冲

---

## 5. API 编程接口

### 5.1 基础网格仿真

```python
from mnq_core import JinlingMesh

# 创建 16×16 网格
mesh = JinlingMesh(dim_x=16, dim_y=16)

# 种子初始化
mesh.seed_background(noise_amp=0.005)  # 背景振荡
# mesh.seed_hex_ring_gap()             # 六角环
# mesh.seed_zero_field()               # 零场

# 运行仿真 (标准模式)
for step in range(500):
    mesh.mnq8_step(dt=0.016)

# 或运行仿真 (CGD约束模式)
for step in range(500):
    mesh.mnq8_step_with_cgd(dt=0.016)

# 获取结果
print(f"Total Mass: {mesh.total_mass:.6f}")
print(f"Total Loop: {mesh.total_loop:.6f}")
print(f"Mass Faces: {mesh.mass_face_count}")
print(f"φ={mesh.minimal.phi:.4f}, Ω={mesh.minimal.omega:.4f}, γ={mesh.minimal.gamma:.4f}")
```

### 5.2 三层信息波

```python
from mnq_core import ThreeLayerInfoWave

wave = ThreeLayerInfoWave(core_init=0.001)

# 设置核心初值 (唯一密钥)
wave.set_core(0.002)

# 单步演化
max_change = wave.step()
print(f"Max Change: {max_change:.8f}")

# 运行至 SCF 收敛
steps = wave.run_to_convergence(max_steps=300, epsilon=1e-6)
print(f"Converged in {steps} steps: {wave.converged}")

# 获取快照
snap = wave.snapshot()
print(snap)  # {'core': ..., 'bagua_mean': ..., 'hex64_mean': ..., ...}
```

### 5.3 CGD 约束引擎

```python
from mnq_core import CGDEngine
import numpy as np

cgd = CGDEngine()

# 添加约束
cgd.add_constraint("mass_upper_bound", (-0.5, 0.5), 0.05)
cgd.add_constraint("coherence_window", (0.0, 1.0), 0.01)
cgd.add_constraint("energy_balance", (-1.0, 1.0), 0.02)

# 评估状态
state = np.array([0.3, 0.85, 0.5])  # [mass, coherence, energy]
is_legal, violation = cgd.evaluate(state)
print(f"Legal: {is_legal}, Violation: {violation:.6f}")

# 调制非法状态
if not is_legal:
    modulated = cgd.modulate(state)
    print(f"Modulated: {modulated}")

# 稳态选择
cgd.select_steady_state({'mass': 0.3, 'coherence': 0.85, 'energy': 0.5, 'step': 100})
```

### 5.4 MNQ9 信心模型

```python
from mnq9_core import MNQ9Simulator, MNQ9ScenarioGenerator

# 使用预定义场景
bull_macro, bull_events = MNQ9ScenarioGenerator.bull_market()

sim = MNQ9Simulator(lam=0.03)
sim.set_macro_confidence(bull_macro)
sim.set_future_wave(bull_events)

# 运行模拟
omega_series = sim.run_series()

# 生成报告
report = sim.generate_report()
print(f"Direction: {report['trend_direction']}")
print(f"Strength: {report['trend_strength']:.4f}")
print(f"Volatility: {report['trend_volatility']:.4f}")
```

### 5.5 刘机制路径追踪

```python
from mnq_core import LiuScheduler, JinlingMesh

mesh = JinlingMesh(dim_x=16, dim_y=16)
mesh.seed_hex_ring_gap()
for _ in range(100): mesh.mnq8_step()

scheduler = LiuScheduler(alpha=0.6, beta=0.4)
path = scheduler.find_optimal_path(mesh, source=(0, 0))
print(f"Optimal path: {len(path)} nodes, Min S_Rel: {scheduler.min_s_rel:.4f}")
```

### 5.6 MNQ Cloud API

```python
from mnq_core import MNQCloudAPI

# 原子尺度
api_atomic = MNQCloudAPI(unit_mode='atomic')
result = api_atomic.simulate(experiment='hex_ring_gap', steps=2048)
print(f"Energy: {result['mean_energy_J']:.4e} J")
print(f"Coherence: {result['coherence']:.6f}")

# 宏观尺度
api_macro = MNQCloudAPI(unit_mode='macro')
result = api_macro.simulate(experiment='background', steps=512)
print(f"Energy: {result['mean_energy_J']:.4e} J")
```

### 5.7 GPU 场演化

```python
from mnq_core import MNQFieldGPU

gpu = MNQFieldGPU(grid=64)

# 注入噪声
gpu.inject_noise(amp=0.001)

# 运行演化
for step in range(5000):
    gpu.step(lambda_=0.01, gamma=0.989)

# 获取指标
print(f"Ω mean: {gpu.measure_omega_avg():.6f}")
print(f"RLOC: {gpu.compute_rloc():.4f}")
```

---

## 6. 实验参数配置

### 6.1 网格参数

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `dim_x` | 16 | 8–64 | X 轴金灵球数量 |
| `dim_y` | 16 | 8–64 | Y 轴金灵球数量 |
| `dim_z` | 1 | 1–8 | Z 轴金灵球数量 (3D 扩展) |

### 6.2 耦合参数

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `COUPLING_STRENGTH` | 0.3 | 0.05–0.8 | N₈ 邻域耦合强度 |
| `MASS_THRESHOLD` | 0.05 | 0.01–0.2 | 质量面形成阈值 |
| `EXCESS_LOOP_THRESH` | 0.08 | 0.02–0.3 | Oloid 差分囚禁阈值 |
| `HOLD_N_BEATS` | 4 | 2–10 | 持续超阈拍数 |

### 6.3 三元动力核参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `phi` | 0.5 | 标量相位 |
| `omega` | 2.0 | 标量频率/能量 |
| `gamma` | 0.9898 | 相干度 |
| `stability_band` | 0.01 | 稳定性带宽 |

### 6.4 MNQ9 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `lam` | 0.03 | 信心衰减系数 (0.01 长趋势, 0.05 短趋势) |
| `w_macro` | (0.4, 0.3, 0.3) | 宏观权重 (M2, PMI, DR007) |
| `event_strength` | 0.3 | 事件冲击强度 |
| `tau` | 20 | 事件衰减时间常数 |

### 6.5 GPU 场参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `grid` | 64 | 网格分辨率 |
| `lambda_` | 0.01 | 扩散系数 |
| `gamma` | 0.989 | 阻尼系数 |

---

## 7. 常见问题

### Q1: ImportError: No module named 'numpy'

```powershell
.venv\Scripts\python.exe -m pip install numpy matplotlib
```

### Q2: GUI 窗口无法启动

确保已安装 tkinter：
```powershell
.venv\Scripts\python.exe -c "import tkinter; print('ok')"
```

如果提示无 tkinter，使用 Python 官方安装包（非嵌入版）。

### Q3: Matplotlib 后端错误

```python
import os
os.environ['MPLBACKEND'] = 'Agg'  # 或 'TkAgg'
os.environ['MPLCONFIGDIR'] = r'C:\path\to\writable\dir'
```

### Q4: CLI 输出中文乱码

```powershell
chcp 65001
```

或在代码中添加：
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
```

### Q5: 阴龙积运算出现 NaN

阴龙积 $\odot$ 在高幅值 (norm > 2.0) 时会回退到纯差分耦合，避免数值爆炸。检查输入值是否在合理范围 (norm < 5.0)。

### Q6: CGD 约束一直处于违反状态

增大 `modulation_strength` (推荐 0.05)，或调宽 `target_range`。

### Q7: MNQ9 模拟结果波动过大

降低 `lam` (衰减系数) 和 `event_strength`，或增大 `tau` (衰减时间常数)。

---

## 附录: 理论体系速查

### MNQ8 更新律

1. 本征振荡: 每个金灵球独立振荡
2. N₈ 邻域耦合: 8 向邻居阴龙积耦合
3. 阈值判定: 超阈→质量面 / 低阈→衰减

### 核心公式

$$
\begin{aligned}
\Delta \phi &= \Omega - \frac{1}{2} & \text{(极简生成)} \\
\Omega &\leftarrow \Omega + \gamma(\Delta\phi + W_{扰动})\Delta t & \text{(能量更新)} \\
R_{coh} &= \frac{|\Delta\phi|}{|\Omega| + \varepsilon} & \text{(相干度)} \\
\gamma &\leftarrow \gamma + \lambda(1 - R_{coh})\Delta t & \text{(相干度更新)}
\end{aligned}
$$

### 阴龙积

$$
z_1 \odot z_2 = \lambda \big[(a_1a_2 - b_1b_2 - c_1c_2) + (a_1b_2 + b_1a_2)i + (a_1c_2 + c_1a_2 + b_1c_2 + c_1b_2)j\big]
$$

### 刘机制

$$
S_{Rel} = \alpha \cdot M + \beta \cdot H[\Theta], \quad \text{路径} = \arg\min S_{Rel}
$$

---

> **Version**: 2.0  
> **Last Updated**: 2026-06-04  
> **Author**: Gao Jianyuan (lisoleg)  
> **License**: MIT  
> **Repository**: [github.com/lisoleg/mnq-golden-spirit-ball-simulator](https://github.com/lisoleg/mnq-golden-spirit-ball-simulator)

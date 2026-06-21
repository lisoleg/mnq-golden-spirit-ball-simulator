# MNQ 金灵球网络仿真器 v3.0 — Windows Edition

> **MNQ Golden Spirit-Ball Network Simulator**
>
> 基于复合体理学 (Composite Physics) MNQ8 冻结核/MNQ9 理论体系 + CGD 约束生成动力学 + D4 协变观察者
>
> Windows Edition · Python 3.10+ · ~2500 行纯 Python

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-3.0-green.svg)](CHANGELOG.md)

---

## 概述

MNQ 金灵球网络仿真器是对 macOS 原生 MNQ 项目 (Swift/C/Metal) 的完整 Windows 移植与升级，实现了复合体理学微信公众号 14 篇文章中描述的全部核心理念。v3.0 新增 MNQ8 冻结核 (5层冻结演化核心)、MASS_FACE 复合解读器 (6维质量面)、D4 协变观察者 (8种对称变换)、动态稳定性门与严格双门质量判别系统，提供 18 项预定义实验的 CLI/GUI 双模式操作。

## 理论基础

### MNQ 系统 (Minimum Nonlinear Quantum Information Field Theory)

MNQ 是基于 IWPU（信息点波动场宇宙）模型的离散数值仿真计算框架。其核心是**刘机制**（关系作用量极小化 δS_Rel=0）在离散 IWPU 网格上的数值实现。

### 核心概念

| 概念 | 符号 | 说明 |
|------|------|------|
| 金灵球 | 𝔊 | 信息本体最小离散单元，不可再分的关系节点 |
| 3D 复广数 | z = a + bi + cj | 金符学状态空间，i²=j²=-1, ij=ji (对易) |
| 阴龙积 | ⊙ | 核心邻域耦合法则，非对易乘法 |
| 流贯 | Ftel | 信息势差驱动的有向信息流 |
| N₈ 邻域 | — | 每个金灵球与 8 个邻域节点耦合 |
| 三元动力核 | φ-Ω-γ | 极简生成公式 |
| 三层信息波 | SCF | 核波(原子) → 介观波 → 64卦波(宏观) |
| CGD 约束 | A1-A5 | 约束生成动力学五公理 |
| MNQ9 信心核 | — | 四策略预测器 (牛/熊/危机/对冲) |
| MNQ8 冻结核 | FK | 5层冻结演化核心 (core→bagua→hex64→wuxing→commit) |
| MASS_FACE | — | 6维后验复合质量面解读 |
| D4 协变观察者 | — | 8种 D4 对称变换 + 协变性审计 |
| 稳定性门 | — | 动态稳定性门 + 严格双门质量判别 |

### PG 拓扑囚禁

- **流贯囚禁**: 流贯被锁定于特定拓扑结构 (L2代数壳)
- **鲁珀特之泪同构**: HEX_RING_GAP 缺口六边形壳层
- **Oloid 差分**: 动态背景差分对照，提取纯结构信号
- **质量面 (Mass Face)**: 拓扑囚禁的孤子结构

## 实现模块

### 核心引擎 (`mnq_core.py` v3.0, ~1600+行)

| 模块 | 类/函数 | 功能 |
|------|---------|------|
| 金符学 3D 复广数 | `GoldenSymbol3D` | 加法/共轭/模/阴龙积⊙/逆元 |
| 三元动力核 | `MNQMinimalState` | φ-Ω-γ 极简生成公式 |
| 金灵球网格 | `JinlingMesh` | MNQ8 更新律 + PG 拓扑囚禁检测 |
| Hex64 六十四卦 | `HEX64_TABLE` / `MNQCore` | 64卦 → x86 指令映射 |
| 刘机制调度器 | `LiuScheduler` | S_Rel = α·M + β·H[Θ], ArgMin 路径 |
| GPU 四场仿真 | `MNQFieldGPU` | φ/Ω/ψ/ξ 四场并行演化 (NumPy) |
| Cloud API 兼容 | `MNQCloudAPI` | 三尺度锚定: atomic/meso/macro |
| 三层信息波 (SCF) | `ThreeLayerSCF` | 核波→介观波→64卦波 信息传递 |
| CGD 约束驱动 | `CGDConstraintEngine` | A1-A5 公理 + 约束违反度监控 |
| 反馈回路 | `FeedbackLoop` | CGD 约束 → MNQ 场状态修正 |
| **MNQ8 冻结核** | `MNQ8FrozenKernel` | 5层冻结演化 (core→bagua→hex64→wuxing→commit) |
| **MASS_FACE 解读器** | `MassFaceReader` | 6维后验复合质量面 + 闭环/AXIS/DIAG 反馈 |
| **动态稳定性门** | `DynamicStabilityGate` | 多条件阈值质量判别 |
| **严格双门** | `StrictDualGate` | DELTA_MASS + DELTA_LOOP 双条件判别 |
| **D4 协变观察者** | `D4CovariantObserver` | 8种对称变换 + 协变性审计 |
| **冻结核网格** | `FrozenKernelMesh` | 整合全部冻结核组件 |

### MNQ9 信心核 (`mnq9_core.py`, ~300行)

| 策略 | 说明 |
|------|------|
| 牛策略 (Bull) | 上升趋势预测 |
| 熊策略 (Bear) | 下降趋势预测 |
| 危机预警 (Crisis) | 极端事件检测 |
| 对冲策略 (Hedge) | 风险中性综合评估 |

### 仪表盘 (`mnq_dashboard.py` v3.0, ~850+行)

- **GUI 模式**: tkinter 多面板仪表盘 (冻结核/SCF/CGD/MNQ9/金灵球/Hex64)
- **CLI 模式**: 18 项预定义实验，一键批量运行

## 快速开始

### 安装

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 安装依赖
.venv\Scripts\python.exe -m pip install numpy matplotlib

# 3. 运行
run_mnq.bat          # GUI 模式
run_mnq.bat --cli    # CLI 模式 (12项实验)
```

### CLI 18 项实验

```bash
.venv\Scripts\python.exe mnq_dashboard.py --cli
```

| # | 实验 | 验证内容 |
|---|------|---------|
| 1 | ZERO_FIELD | 死零不破缺定理 |
| 2 | BACKGROUND_OSC | 弥散态无囚禁 |
| 3 | HEX_RING_GAP | 流贯囚禁 (鲁珀特之泪) |
| 4 | 金符学3D复广数运算 | 阴龙积⊙耦合 |
| 5 | Hex64 六十四卦映射 | 64卦→x86指令 |
| 6 | 刘机制路径选择 | S_Rel 极小化 |
| 7 | GPU 四场演化 | φ/Ω/ψ/ξ 性能基准 |
| 8 | MNQ Cloud API | 三尺度锚定 |
| 9 | **三层信息波 SCF** | 核波→介观→64卦波 |
| 10 | **CGD 约束驱动** | A1-A5 违反度监控 |
| 11 | **MNQ9 信心评估** | 四策略对比 |
| 12 | **MNQ9 多策略对比** | 一致性判定 |
| 13 | **SHA256 核指纹验证** | 冻结核代码完整性 |
| 14 | **背景场演化** | 64步 MASS_FACE 基线 |
| 15 | **HEX_RING_GAP 条件** | 384步峰态追踪 |
| 16 | **D4 协变性审计** | 8种对称变换协变验证 |
| 17 | **严格双门判别** | DELTA_MASS + DELTA_LOOP |
| 18 | **MASS_FACE 复合解读** | 6维质量面组分全测 |

## 测试结果 (v3.0 全部通过)

| 实验 | 关键指标 | 结果 |
|------|---------|------|
| 死零场 | Mass=0, MF=0 | ✅ 死零不破缺 |
| 流贯囚禁 | MF=40 | ✅ 鲁珀特之泪孤子 |
| 三层信息波 | 64卦波=0.9946 | ✅ 信号传递正常 |
| CGD 约束 | 总违反度=17.11 | ✅ 约束可追踪 |
| MNQ9 信心 | 方向=DOWN, 强度=1.36 | ✅ 四策略一致 |
| GPU 演化 | 8009 steps/s | ✅ 性能达标 |
| SHA256 核指纹 | 验证通过 | ✅ 代码完整性 |
| 背景演化 64 步 | MASS_FACE=0.118 | ✅ 基线稳定 |
| HEX_RING_GAP 384 步 | peak=0.313 | ✅ 峰态追踪 |
| D4 协变审计 | L1_diff=0.0 | ✅ 协变性成立 |
| 严格双门 | DELTA_MASS=0.640 | ✅ 双门通过 |
| MASS_FACE 复合 | 6维全测 | ✅ 组分完整 |

## 文件结构

```
mnq_windows/
├── mnq_core.py           # 核心引擎 v3.0 (~1600+行)
├── mnq9_core.py          # MNQ9 信心核 (~300行)
├── mnq_dashboard.py      # GUI仪表盘 + CLI v3.0 (~850+行)
├── run_mnq.bat           # Windows 启动脚本
├── README.md             # 本文件
├── USER_GUIDE.md         # 完整使用手册 (7章)
├── PAPER.md              # 设计与实现论文 (7章+附录)
├── CHANGELOG.md          # 版本变更日志
├── LICENSE               # MIT 许可证
├── CONTRIBUTING.md       # 贡献指南
├── .gitignore
├── _ref_*.docx.txt       # 理论参考文档 (4篇)
└── .venv/                # 虚拟环境 (不入库)
```

## 文档索引

| 文档 | 内容 | 适合读者 |
|------|------|---------|
| [README.md](README.md) | 项目概览与快速开始 | 所有用户 |
| [USER_GUIDE.md](USER_GUIDE.md) | 完整使用手册 (安装/CLI/GUI/API/参数/FAQ) | 使用者 |
| [PAPER.md](PAPER.md) | 学术论文 (理论/架构/算法/实验/术语表) | 研究者 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更历史 | 开发者 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 | 开发者 |

## 与原版 mnqvm 的对应关系

| 原版 (Swift/C/Metal) | Windows版 (Python) |
|----------------------|-------------------|
| MNQRunner.swift | mnq_dashboard.py (MNQDashboard) |
| MNQ_GPU.swift (Metal) | mnq_core.py (MNQFieldGPU + NumPy) |
| MNQ_CPU.swift | mnq_core.py (JinlingMesh) |
| MNQ_Hex64.swift | mnq_core.py (HEX64_TABLE) |
| MNQ_Perf.swift | mnq_core.py (mnq_minimal_step) |
| core/mnq_minimal.c | mnq_core.py (MNQMinimalState) |
| core/mnq_hex64_core.c | mnq_core.py (MNQCore) |
| core/hex64_map.c | mnq_core.py (HEX64_TABLE) |
| core/operators_bagua.c | mnq_core.py (bagua_apply) |
| SwiftUI ContentView | tkinter MNQDashboard (v3.0 冻结核面板) |
| — (v2.0 新增) | mnq_core.py (ThreeLayerSCF) |
| — (v2.0 新增) | mnq_core.py (CGDConstraintEngine) |
| — (v2.0 新增) | mnq9_core.py (MNQ9 四策略) |
| — (v3.0 新增) | mnq_core.py (MNQ8FrozenKernel + 5 模块) |
| — (v3.0 新增) | mnq_dashboard.py (冻结核面板 + 6 项实验) |

## 依赖

- Python 3.10+
- NumPy
- Matplotlib (仅 GUI 模式需要)
- tkinter (Python 自带)

## 许可证

[MIT License](LICENSE) — 自由使用、修改、分发。

## 致谢

- 复合体理学微信公众号 — 理论基础
- 太乙AGI团队 — 原始 macOS Swift/C/Metal 实现

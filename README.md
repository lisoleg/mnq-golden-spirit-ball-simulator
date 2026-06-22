# MNQ 金灵球网络仿真器 v3.2 — Windows Edition + Web 仪表盘

> **MNQ Golden Spirit-Ball Network Simulator**
>
> 基于复合体理学 (Composite Physics) MNQ8 冻结核/MNQ9 理论体系 + CGD 约束生成动力学 + D4 协变观察者 + DeepSeek LLM 集成
>
> Windows Edition · Python 3.10+ · Flask + React Web 仪表盘 · ~4000+ 行代码

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-3.2-green.svg)](CHANGELOG.md)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000.svg)](https://flask.palletsprojects.com/)

---

## 概述

MNQ 金灵球网络仿真器是对 macOS 原生 MNQ 项目 (Swift/C/Metal) 的完整 Windows 移植与升级，实现了复合体理学微信公众号 14 篇文章中描述的全部核心理念。v3.2 在原有 tkinter GUI + CLI 基础上新增 **Flask + React Web 仪表盘**，集成 **DeepSeek Chat API** 驱动 MNQ-Deep 文本生成，提供 18 项预定义实验的 CLI/GUI/Web 三种操作模式。核心论文已覆盖八元数非结合根基证明（阴龙积非结合性定理 + GS³↪𝕆 嵌入 + 八卦-八元数同构）。

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

### 仪表盘 (`mnq_dashboard.py` v3.1, ~850+行)

- **GUI 模式**: tkinter 多面板仪表盘 (冻结核/SCF/CGD/MNQ9/金灵球/Hex64)
- **CLI 模式**: 18 项预定义实验，一键批量运行

### Web 仪表盘 (`backend/` + `frontend/`, v4.0)

- **后端**: Flask Blueprint 架构, 11 个 Blueprint, 44 条 REST API 路由 + SSE 实时推送
- **前端**: Vite + React 18 + MUI + Tailwind CSS + Recharts + Zustand
- **10 个功能面板**: FrozenKernel / MASS_FACE / SCF / CGD / MNQ9 / MNQ-Deep / κ-Snap / 实验运行器 / 实验历史 / 使用文档
- **DeepSeek 集成**: `backend/api/deep.py` 调用 DeepSeek Chat API (deepseek-chat) 驱动 MNQ-Deep 文本生成
- **Web UI 使用文档**: 内置 Documentation.tsx 面向所有用户提供完整的模块说明和术语表

## 快速开始

### 方式一：Web 仪表盘（推荐）

```powershell
# 1. 安装后端依赖
cd mnq_windows/backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. 启动后端 (自动托管前端静态文件)
..\.venv\Scripts\python.exe app.py

# 3. 浏览器打开
# http://localhost:5000
```

### 方式二：tkinter GUI + CLI

```bash
# 1. 创建虚拟环境
python -m venv .venv

# 2. 安装依赖
.venv\Scripts\python.exe -m pip install numpy matplotlib

# 3. 运行
run_mnq.bat          # GUI 模式
run_mnq.bat --cli    # CLI 模式 (18项实验)
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
├── mnq_core.py              # 核心引擎 v3.2 (~2000+行)
├── mnq9_core.py             # MNQ9 信心核 (~300行)
├── mnq_dashboard.py         # tkinter GUI仪表盘 + CLI v3.1 (~850+行)
├── mnq_deep.py              # MNQ-Deep Transformer (~500行)
├── run_mnq.bat              # Windows tkinter 启动脚本
├── backend/                 # Flask Web 后端
│   ├── app.py              # Flask 入口 (含静态文件托管)
│   ├── config.py           # CORS/端口配置
│   ├── requirements.txt    # Python 依赖 (Flask/Numpy/Requests)
│   └── api/                # 11个 Blueprint, 44条路由
│       ├── experiment.py   # 实验管理 API (list/run/status/history)
│       ├── kernel.py       # FrozenKernel API
│       ├── massface.py     # MASS_FACE 读数 API
│       ├── scf.py          # 三层信息波 API
│       ├── cgd.py          # CGD 约束动力学 API
│       ├── mnq9.py         # MNQ9 信心核 API
│       ├── deep.py         # MNQ-Deep + DeepSeek API 集成
│       ├── kappa.py        # κ-Snap 快照管理 API
│       ├── mesh.py         # 金灵球网格 API
│       ├── liu.py          # 刘机制调度器 API
│       └── cloud.py        # MNQ Cloud API
├── frontend/                # React SPA 前端
│   ├── vite.config.ts      # Vite 构建配置
│   ├── package.json        # Node.js 依赖
│   └── src/
│       ├── api/            # 9个 API 调用模块 (axios)
│       ├── components/     # 通用组件 (Layout/Sidebar/GaugeChart)
│       ├── pages/          # 10个页面 (含 Documentation.tsx)
│       ├── store/          # Zustand 状态管理
│       └── utils/          # 工具函数 (formatters/constants)
├── README.md                # 本文件
├── USER_GUIDE.md            # 完整使用手册 (含Web使用)
├── PAPER.md                 # 学术论文 v3.2 (八元数非结合根基证明 + Web/DeepSeek)
├── ARCHITECTURE_WEB.md      # Web 仪表盘架构设计
├── PRD_WEB_DASHBOARD.md     # Web 仪表盘产品需求文档
├── CHANGELOG.md             # 版本变更日志
├── CGD_TOMAS_MAPPING.md     # CGD↔TOMAS 公理映射
├── TOMAS_VERDICT.md         # TOMAS 裁决文档
├── LICENSE                  # MIT 许可证
├── CONTRIBUTING.md          # 贡献指南
├── _ref_*.docx.txt          # 理论参考文档 (4篇)
├── snaps/                   # κ-Snap JSON 快照
├── mus/                     # MUS 双存记录
└── .venv/                   # 虚拟环境 (不入库)
```

## 文档索引

| 文档 | 内容 | 适合读者 |
|------|------|---------|
| [README.md](README.md) | 项目概览与快速开始 | 所有用户 |
| [USER_GUIDE.md](USER_GUIDE.md) | 完整使用手册 (Web/GUI/CLI/API/参数/FAQ) | 使用者 |
| [PAPER.md](PAPER.md) | 学术论文 v3.2 (八元数非结合根基证明 + Web仪表盘 + DeepSeek) | 研究者 |
| [ARCHITECTURE_WEB.md](ARCHITECTURE_WEB.md) | Web 仪表盘系统架构设计 (Flask + React) | 开发者 |
| [PRD_WEB_DASHBOARD.md](PRD_WEB_DASHBOARD.md) | Web 仪表盘产品需求文档 | 产品/开发者 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更历史 | 开发者 |
| [CGD_TOMAS_MAPPING.md](CGD_TOMAS_MAPPING.md) | CGD↔TOMAS 公理映射文档 | 研究者 |
| [TOMAS_VERDICT.md](TOMAS_VERDICT.md) | TOMAS 裁决文档 | 研究者 |
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
| — (v3.2 新增) | backend/api/* (Flask API, 11 Blueprint) |
| — (v3.2 新增) | frontend/src/* (React SPA, 10 页面) |
| — (v3.2 新增) | backend/api/deep.py (DeepSeek Chat API 集成) |

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 核心算法 | Python 3.10+ / NumPy | 金符学复广数、冻结核、SCF、CGD 等 |
| Web 后端 | Flask 3.0 + Flask-CORS | REST API + SSE 实时推送 + 静态文件托管 |
| Web 前端 | Vite + React 18 + MUI + Tailwind CSS | SPA 仪表盘, 10 面板 |
| 图表 | Recharts | Gauge/Line/Heatmap 实时可视化 |
| 状态管理 | Zustand | 前端全局状态 |
| LLM 集成 | DeepSeek Chat API | MNQ-Deep 金符学文本生成 |
| GUI | tkinter (Python 标准库) | 传统桌面仪表盘 |
| 科学计算 | NumPy + Matplotlib | 场演化 / 数据可视化 |

## 依赖

### 核心引擎 (Python)
- Python 3.10+
- NumPy
- Matplotlib (仅 GUI 模式需要)
- tkinter (Python 自带)

### Web 后端 (Python)
- Flask 3.0+
- Flask-CORS 4.0+
- Requests (DeepSeek API 调用)

### Web 前端 (Node.js)
- React 18 + TypeScript
- Vite 5
- MUI 5 (Material UI)
- Tailwind CSS 3
- Recharts 2
- Zustand 4

## 许可证

[MIT License](LICENSE) — 自由使用、修改、分发。

## 致谢

- 复合体理学微信公众号 — 理论基础
- 太乙AGI团队 — 原始 macOS Swift/C/Metal 实现

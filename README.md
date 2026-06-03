# MNQ 金灵球网络仿真器 - Windows Edition

## 概述

基于复合体理学微信公众号的MNQ理论体系和 `mnqvm` 目录下的 Swift/C 源码，完整实现了可在 Windows 下运行的 MNQ 金灵球网络分布式拓扑计算仿真器。

## 理论基础

### MNQ 系统 (Minimum Nonlinear Quantum Information Field Theory)

MNQ 是基于 IWPU（信息点波动场宇宙）模型的离散数值仿真计算框架。其核心是刘机制（关系作用量极小化 δS_Rel=0）在离散 IWPU 网格上的数值实现。

### 金灵球网络 (Jinling Sphere Network)

- **金灵球 (𝔊)**: 信息本体最小离散单元，不可再分的关系节点
- **N₈ 邻域耦合**: 每个金灵球与8个邻域节点耦合
- **3D 复广数 (金符学)**: 状态 z = a + bi + cj，其中 i²=j²=-1, ij=ji
- **阴龙积 ⊙**: 核心邻域耦合法则
- **流贯 (Ftel)**: 信息势差驱动的有向信息流

### PG 拓扑囚禁

- **流贯囚禁**: 流贯被锁定于特定拓扑结构（L2代数壳）
- **鲁珀特之泪同构**: HEX_RING_GAP 缺口六边形壳层
- **Oloid 差分**: 动态背景差分对照，提取纯结构信号
- **质量面 (Mass Face)**: 拓扑囚禁的孤子结构

### 刘机制 (Liu Mechanism)

流贯在所有可能路径中选择 S_Rel 取极小值的路径（最小阻抗路径）。

## 实现模块

### 1. 金符学 3D 复广数 (`GoldenSymbol3D`)

| 运算 | 公式 | 物理意义 |
|------|------|---------|
| 加法 | z₁+z₂ | 流贯强度叠加 |
| 共轭 | z̄ = a-bi+cj | 反转波性相位 |
| 模 | \|z\|² = a²+b²+c² | 总流贯能量密度 |
| 阴龙积 ⊙ | 乘法法则 | 核心邻域耦合 |
| 逆元 | z⁻¹ = z̄/\|z\|² | 反向传播流贯 |

### 2. 三元动力核 (`MNQMinimalState`)

极简公式:
```
① Δφ = Ω − 0.5·Ω
② Ω ← Ω + γ·(Δφ + W扰动)·dt
③ Rcoh = |Δφ| / (|Ω| + ε)
④ γ ← γ + λ·(1 − Rcoh)·dt
```

### 3. 金灵球网格 (`JinlingMesh`)

- MNQ8 更新律: 本征振荡 → N₈耦合 → 阈值判定
- 实验模式: ZERO_FIELD / BACKGROUND_OSC / HEX_RING_GAP
- PG 拓扑囚禁检测: Oloid差分 + 锁定持续判定

### 4. Hex64 六十四卦映射

完整 64 卦 → x86 指令映射表，8 个基础卦:
- 乾(MOV) → 坤(ADD) → 震(SUB) → 巽(MUL) → 坎(DIV) → 离(CMP) → 艮(JMP) → 兑(CALL)

### 5. 刘机制调度器 (`LiuScheduler`)

S_Rel = α·M + β·H[Θ]，寻找 ArgMin S_Rel 路径

### 6. GPU 四场仿真 (`MNQFieldGPU`)

φ/Ω/ψ/ξ 四场并行演化（NumPy实现，替代 Metal）

### 7. MNQ Cloud API 兼容层

三尺度锚定系统: atomic / meso / macro

## 运行方式

### GUI 模式 (推荐)

```bash
# 双击运行
run_mnq.bat

# 或命令行
python mnq_dashboard.py
```

### CLI 模式

```bash
python mnq_dashboard.py --cli
```

## 测试结果

| 实验 | Mass | MF | 验证 |
|------|------|----|------|
| ZERO_FIELD (死零场) | 0.000000 | 0 | ✓ 死零不破缺 |
| BACKGROUND_OSC (背景) | 0.0004 | 0 | ✓ 弥散态无囚禁 |
| HEX_RING_GAP (缺口六角壳) | 0.0031 | 41 | ✓ 流贯囚禁成功 |

## 依赖

- Python 3.8+
- NumPy
- Matplotlib (仅GUI模式需要)
- tkinter (Python自带)

## 文件结构

```
mnq_windows/
├── mnq_core.py          # 核心引擎 (全部算法实现)
├── mnq_dashboard.py     # GUI仪表盘 + CLI模式
├── run_mnq.bat           # Windows启动脚本
└── README.md             # 本文件
```

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
| SwiftUI ContentView | tkinter MNQDashboard |

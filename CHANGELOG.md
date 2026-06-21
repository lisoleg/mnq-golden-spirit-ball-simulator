# 变更日志

> 所有重要变更均记录于此文件。
> 格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
> 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [2.0.0] — 2026-06-04

### 新增

#### 核心引擎 (mnq_core.py)

- **三层信息波自洽场 (ThreeLayerSCF)**: 核波(原子尺度) → 介观波(中尺度) → 64卦波(宏观尺度) 三层级信息传递与收敛
- **CGD 约束生成动力学 (CGDConstraintEngine)**: 基于 A1-A5 五公理的约束违反度实时监控与弱调制语义
- **反馈回路 (FeedbackLoop)**: CGD 约束违反 → MNQ 场状态修正闭环
- **高级八卦算子**: 扩展 bagua_apply 运算
- **MNQ8 更新律增强**: 本征振荡 → N₈邻域耦合 → 阈值判定 完整实现

#### MNQ9 信心核 (mnq9_core.py) — 全新模块

- **牛策略预测器 (Bull)**: 上升趋势信号检测
- **熊策略预测器 (Bear)**: 下降趋势信号检测
- **危机预警策略 (Crisis)**: 极端事件预警
- **对冲策略 (Hedge)**: 风险中性综合评估
- **多策略一致性判定**: 四策略方向投票

#### 仪表盘 (mnq_dashboard.py)

- **SCF 面板**: 三层信息波实时可视化
- **CGD 面板**: 约束违反度监控仪表
- **MNQ9 面板**: 四策略信心指数对比
- **CLI 扩展至 12 项实验**: 新增 #9-#12 (SCF/CGD/MNQ9/多策略对比)

#### 启动脚本 (run_mnq.bat)

- 指向项目级 `.venv/` 隔离环境
- 新增模块说明面板

#### 文档

- **USER_GUIDE.md**: 完整使用手册 (7章, ~15KB)
- **PAPER.md**: 设计与实现论文 (7章+2附录, ~23KB, 含 LaTeX 公式/Mermaid 图/术语表)
- **CHANGELOG.md**: 本文件
- **LICENSE**: MIT 许可证
- **CONTRIBUTING.md**: 贡献指南

### 变更

- README.md 全面升级至 v2.0
- .gitignore 增加 `.venv/` 排除
- 文件结构更新: 新增 mnq9_core.py

### 测试结果

| 实验 | 关键指标 | 状态 |
|------|---------|------|
| 死零场 | Mass=0, MF=0 | ✅ |
| 流贯囚禁 | MF=40 | ✅ |
| 三层信息波 | 64卦波=0.9946 | ✅ |
| CGD 约束 | 总违反度=17.11 | ✅ |
| MNQ9 信心 | 方向=DOWN, 强度=1.36 | ✅ |
| MNQ9 多策略 | 4策略一致 | ✅ |
| GPU 演化 | 8009 steps/s | ✅ |
| 全部 12 项 | — | ✅ 全通过 |

---

## [1.0.0] — 2026-06-04 (同日初版)

### 新增

#### 核心引擎 (mnq_core.py)

- **金符学 3D 复广数 (GoldenSymbol3D)**: z = a + bi + cj, i²=j²=-1, ij=ji
  - 加法 / 共轭 / 模 / 阴龙积⊙ / 逆元
- **三元动力核 (MNQMinimalState)**: φ-Ω-γ 极简生成公式
  - ① Δφ = Ω − 0.5·Ω
  - ② Ω ← Ω + γ·(Δφ + W扰动)·dt
  - ③ Rcoh = |Δφ| / (|Ω| + ε)
  - ④ γ ← γ + λ·(1 − Rcoh)·dt
- **金灵球网格 (JinlingMesh)**: MNQ8 更新律 + PG 拓扑囚禁检测
  - 实验模式: ZERO_FIELD / BACKGROUND_OSC / HEX_RING_GAP
  - Oloid 差分 + 锁定持续判定
- **Hex64 六十四卦映射**: 64卦 → x86 指令映射表
  - 8基础卦: 乾(MOV)/坤(ADD)/震(SUB)/巽(MUL)/坎(DIV)/离(CMP)/艮(JMP)/兑(CALL)
- **刘机制调度器 (LiuScheduler)**: S_Rel = α·M + β·H[Θ], ArgMin 路径
- **GPU 四场仿真 (MNQFieldGPU)**: φ/Ω/ψ/ξ 四场并行演化 (NumPy 实现, 替代 Metal)
- **MNQ Cloud API 兼容层**: 三尺度锚定 (atomic/meso/macro)

#### 仪表盘 (mnq_dashboard.py)

- tkinter GUI 仪表盘 (金灵球/Hex64/GPU 面板)
- CLI 模式 (8 项实验)

#### 启动脚本 (run_mnq.bat)

- Windows 一键启动

#### 文档

- README.md v1.0

### 测试结果

| 实验 | Mass | MF | 状态 |
|------|------|----|------|
| ZERO_FIELD | 0.000000 | 0 | ✅ 死零不破缺 |
| BACKGROUND_OSC | 0.0004 | 0 | ✅ 弥散态 |
| HEX_RING_GAP | 0.0031 | 41 | ✅ 流贯囚禁 |

### 已知问题 (v1.0)

- 阴龙积⊙纯乘法耦合在高幅值时数值爆炸 → v2.0 已修复 (混合耦合策略)
- 需 clamp 状态值到 [-5,5] 防止发散 → v2.0 已修复
- Minimal 核心 omega 持续增长到上限 10.0 → v2.0 已修复
- NumPy/matplotlib 需安装到 isolated env → v2.0 使用项目级 .venv/

---

## 版本对照

| 维度 | v1.0 | v2.0 |
|------|------|------|
| 核心引擎行数 | ~600 | ~1050 |
| 仪表盘行数 | ~400 | ~650 |
| 模块数 | 7 | 11 (+SCF/CGD/Feedback/MNQ9) |
| CLI 实验数 | 8 | 12 |
| 文档数 | 1 (README) | 6 (全套) |
| 测试通过率 | 3/3 | 12/12 |

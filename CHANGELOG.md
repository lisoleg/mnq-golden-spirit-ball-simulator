# 变更日志

> 所有重要变更均记录于此文件。
> 格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
> 版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [3.2.0] — 2026-06-22

### 新增

#### Web 仪表盘 v4.0 (backend/ + frontend/)

- **Flask 后端 API**: 11 个 Blueprint, 44 条 REST 路由
  - 实验管理、FrozenKernel、MASS_FACE、SCF、CGD、MNQ9、MNQ-Deep、κ-Snap、金灵球网格、刘机制、MNQ Cloud
  - SSE (Server-Sent Events) 实时进度推送
  - 静态文件托管 (生产模式下托管 Vite 构建产物)
- **React 前端 SPA**: Vite + React 18 + MUI + Tailwind CSS + Recharts + Zustand
  - 10 个功能面板: FrozenKernel / MASS_FACE / SCF / CGD / MNQ9 / MNQ-Deep / κ-Snap / 实验运行器 / 实验历史 / 使用文档
  - 暗色科技主题 (深紫黑背景 + 科技蓝强调)
  - GaugeChart 仪表盘组件、实时图表、SSE 进度条

#### DeepSeek Chat API 集成

- `backend/api/deep.py` 重构：从 mock/本地 PyTorch 改为调用 DeepSeek Chat API
  - API 端点: `https://api.deepseek.com/v1/chat/completions`
  - 模型: `deepseek-chat`
  - System prompt 设定 MNQ 金符学理论上下文
  - 保留 MNQ 后处理管线（语法检查、香农熵、κ签名）
  - 新增依赖: `requests>=2.31`

#### UI 使用文档

- **Documentation.tsx**: 完整 Web UI 使用文档页面
  - 项目概述、10 个模块说明、快速上手指南、术语表
- **9 个面板页**: 各增加解释说明 Card/Alert，降低使用门槛
- **导航优化**: 侧边栏新增"首页"和"使用文档"入口

### 修复

#### 前后端 API 契约修复 (9 个模块)

- `frontend/src/api/experiment.ts`: `fetchExperiments` 解包逻辑 (`res.data.experiments ?? res.data`)；`runExperiment` URL 修正为 `POST /experiment/run`
- `frontend/src/api/kappa.ts`: 全部 URL 修正 (`/snapshots`→`/list`等)
- `frontend/src/api/massface.ts`: `/readings`→`/read`，history 数据展开
- `frontend/src/api/scf.ts`: `run_to_convergence`→`run-to-convergence`
- `frontend/src/api/cgd.ts`: `/step`→`/violation`
- `frontend/src/api/kernel.ts`: `d4_audit`→`d4-audit`
- `frontend/src/api/mnq9.ts`: `/simulate`→`/run-series`
- `frontend/src/api/mesh.ts`: 端点 URL 全面修正
- `frontend/src/api/deep.ts`: `seed_text`→`start_text`

#### 前端运行时错误修复

- `frontend/src/utils/formatters.ts`: `formatNumber`/`formatPercent` 添加 `null`/`NaN` 守卫，返回 `"N/A"` 而非崩溃
- `frontend/src/components/GaugeChart.tsx`: `value` 兜底为 0 防止 `toFixed` 报错
- `frontend/src/pages/CGDPanel.tsx`: `constraints.map` 添加可选链 `?.` 防止空数组崩溃
- `frontend/src/pages/ExperimentRunner.tsx`: progress 进度非空检查

#### 后端 500 错误修复

- `backend/api/scf.py`: `/step` 和 `/run-to-convergence` 处理空 POST body
- `backend/api/cgd.py`: 响应字段名对齐前端期望 (`violation_count`→`violation`，添加 constraints 数组字段)
- `backend/api/deep.py`: 修复中文引号导致的语法错误

### 文档更新

- **README.md**: 版本升至 v3.2，新增 Web 仪表盘、DeepSeek、技术栈章节
- **USER_GUIDE.md**: 新增 Web 仪表盘使用章节
- **PAPER.md**: 新增 Web 仪表盘架构 + DeepSeek 集成章节
- **ARCHITECTURE_WEB.md**: 更新 DeepSeek 集成说明
- **CHANGELOG.md**: 本条目

### 变更

- `backend/api/deep.py`: 行数 ~80 → ~230+ (DeepSeek API 集成)
- `backend/requirements.txt`: 新增 `requests>=2.31`
- 前端 API 模块: 9 个文件全面修正 URL 和解包逻辑
- 10 个前端页面: 各增加解释说明组件

---

### 新增

#### TOMAS 封装层 (mnq_core.py + mnq_dashboard.py)

- **建议1: κ-Snap Export**: `kappa_snap_export()` 函数
  - 每次 `FrozenKernelMesh.run()` 结束后自动写 JSON 快照
  - 快照格式遵循 TOMAS 裁决文档定义（`snap_id`, `prev_snap_id`, `cited_ref`, `e_obs_mf`）
  - 保存至 `./snaps/` 目录
- **建议2: ℐ-Semantic Feedback Hook**: `FrozenKernelMesh.semantic_feedback()` 方法
  - 占位接口，标注未来接 TOMAS KB 的调用方式
  - 在 `run()` 结束后自动调用（可通过参数关闭）
- **建议3: MUS 双存 UI Hint**: `mnq_dashboard.py` GUI 提示
  - 当严格双门 FAIL 但动态门 PASS 时（暂态闭合）
  - 弹出 `messagebox.askyesno()` 提示，用户选择后写入 `./mus/` 目录（JSON）
- **建议4: ψ-锚 CLI flag**: （计划中实现）
  - CLI 模式新增 `--comply-psi-anchor` flag
  - 启用时：强制输出所有情况（含 collapse case、negative 结果），不 suppress
- **建议5: CGD ⇔ TOMAS Axiom 映射文档**: 新增 `CGD_TOMAS_MAPPING.md`
  - CGD_A1→TOMAS A1(ℐ-守恒)，CGD_A2→TOMAS A2(κ-Snap)
  - CGD_A3→刘机制 ArgMin S_Rel，CGD_A4/A5 对应关系分析

#### MNQ-Deep Transformer (mnq_deep.py — 新文件)

- **MNQComboAttention**: 三驱动力注意力（保护头/服务头/稳定头）
- **MNQComboLayer**: 层间衰减残差 + Ω-φ 动力学
- **MNQComboTransformer**: 完整的 Combo Transformer（6层）
- **MNQCrossLayer**: 跨层 Ω 传递
- **MNQCrossTransformer**: 跨层 Ω Transformer（6层）
- **语法约束解码**: `generate()` 函数支持 `syntax_constraint=True`（括号匹配、缩进一致性、禁止连续换行）
- **基线对比**: `StandardTransformer` 实现

### 变更

- `mnq_core.py` 版本头: v2.0 → v3.1
- `mnq_core.py` 新增导入: `json`, `uuid`, `os`
- `mnq_core.py` 新增函数: `kappa_snap_export()`
- `mnq_core.py` 修改类: `FrozenKernelMesh` 新增 `semantic_feedback()` 方法，`run()` 修改为调用新函数
- `mnq_core.py` `__all__` 更新: 新增 `kappa_snap_export`
- `mnq_dashboard.py` 版本头: v3.0 → v3.1
- `mnq_dashboard.py` 新增导入: `json`, `uuid`, `os`
- `mnq_dashboard.py` 修改方法: `_fk_step()` 新增 MUS UI 提示
- 新增文件: `mnq_deep.py` (~500行), `CGD_TOMAS_MAPPING.md`

---

## [3.0.0] — 2026-06-04

### 新增

#### 核心引擎 (mnq_core.py)

- **MNQ8 冻结核 (MNQ8FrozenKernel)**: 五层冻结核演化核心
  - `_fk_law_core()` → `_fk_law_bagua()` → `_fk_law_hex64()` → `_fk_law_wuxing()` → `_fk_law_commit()`
  - 严格五 NO 原则: NO_EXTRA_DYNAMICS, NO_OBSERVER_WRITE_BACK, NO_FITTING, NO_PROTON
  - 背景与条件场初始化 + 差分场 ΔF(t) = F_condition(t) − F_background(t)
  - SHA256 核指纹完整性验证
- **MASS_FACE 复合解读器 (MassFaceReader)**: 后验复合解读
  - 6 维质量面组分: 有限载流子数(0.09) + 局域/背景比(0.10) + 补偿回路(0.23) + 保持持久度(0.17) + 边界泄漏阻力(0.09) + 漂移阻抗(0.07) + 旋涡(0.04)
  - MASS_CLOSURE 闭环度、AXIS/DIAG 回路反馈
- **动态稳定性门 (DynamicStabilityGate)**: 多条件阈值系统
  - EXCESS_MASS_FACE > 0.70, EXCESS_LOCAL_COMP_LOOP > 0.50
  - EXCESS_LOOP_HOLD_13 > 0.80, EXCESS_BOUNDARY_LEAK < 0.15
  - FINAL_TO_PEAK_EXCESS_MASS_RATIO > 0.85
- **严格双门 (StrictDualGate)**: 更保守的双条件门
  - DELTA_MASS_FACE > 0.20 & DELTA_LOCAL_COMP_LOOP > 0.20
- **D4 协变共轭极大观察者 (D4CovariantObserver)**: 8 种 D4 对称变换
  - ID, ROT90, ROT180, ROT270, MIRROR_LR, MIRROR_UD, MIRROR_MAIN_DIAG, MIRROR_ANTI_DIAG
  - 协变性审计 (co_max_windows, 坐标重写不修改通道语义)
- **冻结核网格集成器 (FrozenKernelMesh)**: 整合所有冻结核组件

#### 仪表盘 (mnq_dashboard.py)

- **冻结核面板**: 7 个实时读数标签 + 3 个控制按钮 (步进/重置/D4审计)
- **CLI 扩展至 18 项实验**: 新增 #13-#18 (SHA256验证/背景演化/HEX_RING_GAP条件/D4审计/双门/MASS_FACE复合)

#### 启动脚本 (run_mnq.bat)

- 版本号升至 v3.0
- 模块描述更新至 v3.0 (11 模块)

### 测试结果

| 实验 | 关键指标 | 状态 |
|------|---------|------|
| SHA256 核指纹 | 验证通过 | ✅ |
| 背景演化 64 步 | MASS_FACE=0.118 | ✅ |
| HEX_RING_GAP 384 步 | peak=0.313 | ✅ |
| D4 协变审计 | 5 变换 L1_diff=0.0 | ✅ |
| 严格双门 | DELTA_MASS=0.640, DELTA_LOOP=1.000 | ✅ |
| MASS_FACE 复合 | 6 维全测量 | ✅ |
| 全部 18 项 | — | ✅ 全通过 |

### 变更

- mnq_core.py 行数: ~1050 → ~1600+ (新增冻结核 5 模块)
- mnq_dashboard.py 行数: ~650 → ~850+ (新增冻结核面板 + 6 项实验)
- `__all__` 导出列表更新 (新增 FrozenKernelMesh 等 6 个类)

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

| 维度 | v1.0 | v2.0 | v3.0 | v3.2 |
|------|------|------|------|------|
| 核心引擎行数 | ~600 | ~1050 | ~1600+ | ~2000+ |
| 仪表盘行数 | ~400 | ~650 | ~850+ | ~850+ (tkinter) + ~2000+ (Flask API) + ~3000+ (React) |
| 模块数 | 7 | 11 (+SCF/CGD/Feedback/MNQ9) | 16 (+冻结核5模块) | 27 (+Web 前后端 11 模块) |
| CLI 实验数 | 8 | 12 | 18 | 18 |
| 文档数 | 1 (README) | 6 (全套) | 6 (全套) | 10 (全套 + Web) |
| 操作模式 | CLI | CLI + GUI | CLI + tkinter GUI | CLI + tkinter GUI + Web 仪表盘 |
| LLM 集成 | — | — | — | DeepSeek Chat API |
| 测试通过率 | 3/3 | 12/12 | 18/18 | 47/47 (Web 后端) |

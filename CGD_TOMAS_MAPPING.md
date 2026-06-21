# CGD ⇔ TOMAS 公理映射文档

> 本文档映射 MNQ 金灵球网络仿真器中 CGD 约束生成动力学的五条公理（A1-A5）到 TOMAS（太一互搏公理体系）的公理体系，帮助跨社群理解。

---

## 1. CGD_A1（信息不灭/质量面守恒）⇔ TOMAS A1（ℐ-守恒）

| 条目 | CGD A1 | TOMAS A1 |
|------|--------|-----------|
| 内容 | 信息不灭公理：质量面total_mass随时间守恒，信息不会凭空消失或创生 | ℐ-守恒公理：知识核 ℐ 中的概念节点和信息超边不灭——只能被确认、证伪、修正，不能被删除 |
| 精神 | 信息总量守恒，变换形式但不灭 | 知识不灭，修正形式但保留痕迹 |
| 数值实现 | `total_mass` 在 CGD 演化中偏差超过阈值则触发惩罚 | `ℐ-update` 在 TOMAS KB 中更新节点置信度，不删除旧值 |
| 对应性 | ✅ 高度对应——均强调"不灭性" | ✅ 高度对应 |

**TOMAS 封装建议**：在 `kappa_snap_export()` 中，将 `total_mass` 变化写入快照，供 TOMAS KB 做 ℐ-守恒检查。

---

## 2. CGD_A2（因果箭）⇔ TOMAS A2（κ-Snap 血缘链）

| 条目 | CGD A2 | TOMAS A2 |
|------|--------|-----------|
| 内容 | 因果箭公理：MNQ场演化路径不可回溯，因果箭单向 | κ-Snap 公理：每次知识更新生成快照（SnapEvent），含 prev_snap_id 指针，形成不可篡改血缘链 |
| 精神 | 时间箭头 / 因果不对称性 | 知识演化箭头 / 快照不对称性 |
| 数值实现 | `field_history` 记录每一步场状态，不可回溯修改 | `SnapEvent.prev_snap_id` 形成链表，新快照引用旧快照 |
| 对应性 | ✅ 高度对应——均强调"单向不可回溯" | ✅ 高度对应 |

**TOMAS 封装建议**：`kappa_snap_export()` 已实现 `prev_snap_id` 指针，直接对应 CGD 的因果箭。

---

## 3. CGD_A3（最小作用量关系）⇔ 刘机制 ArgMin S_Rel）

| 条目 | CGD A3 | 刘机制 / TOMAS |
|------|--------|--------------|
| 内容 | 最小作用量公理：MNQ场演化沿着作用量极小的路径 | 刘机制：S_Rel = α·M + β·H[Θ], ArgMin 路径选择 |
| 精神 | 自然选择"最省力"的演化路径 | 信息结构选择"关系阻抗最小"的路径 |
| 数值实现 | CGD 约束违反度极小时对应作用量极小 | `LiuScheduler.ArgMin_S_Rel()` 选择极小路径 |
| 对应性 | ✅ 同一数学结构的不同表述 | ✅ 同一精神 |

**TOMAS 封装建议**：在 `semantic_feedback()` 中，将刘机制的 ArgMin 结果反馈给 TOMAS KB，作为概念节点选择的依据。

---

## 4. CGD_A4（相干性阈值）⇔ TOMAS "稳定对象＝能长期保持闭合关系的状态结构"

| 条目 | CGD A4 | TOMAS |
|------|--------|-------|
| 内容 | 相干性阈值公理：γ（相干度）低于阈值时触发去相干惩罚 | 稳定对象 = 能长期保持闭合差分补偿关系的状态结构（GPCT 判据） |
| 精神 | 相干性保持是信息不灭的前提 | 闭合关系保持是对象稳定的前提 |
| 数值实现 | `gamma > gamma_min` 检查，违反则惩罚 | `DynamicStabilityGate` + `StrictDualGate` 评估闭合保持能力 |
| 对应性 | ✅ 精神对应——均强调"保持能力" | ✅ 精神对应 |

**TOMAS 封装建议**：将 `DynamicStabilityGate` 的评估结果映射为 TOMAS GPCT 的 `need_new_node` 触发条件。

---

## 5. CGD_A5（约束违反可追踪）⇔ TOMAS 知识可追溯性

| 条目 | CGD A5 | TOMAS |
|------|--------|-------|
| 内容 | 约束违反可追踪公理：所有约束违反度可精确追踪到具体场点 | 知识更新的每一步可追溯（κ-Snap 血缘链 +cited_ref） |
| 精神 | 可解释性 / 可追溯性 | 可追溯性 / 可解释性 |
| 数值实现 | `CGDEngine.violations` 列表记录每次违反 | `SnapEvent.cited_ref` 记录快照来源 |
| 对应性 | ✅ 高度对应 | ✅ 高度对应 |

**TOMAS 封装建议**：在 `kappa_snap_export()` 中，增加 `cgd_violations` 字段，记录当时的 CGD 约束违反情况。

---

## 6. 总结对照表

| CGD 公理 | TOMAS 对应 | 对应强度 | 封装优先级 |
|----------|------------|----------|------------|
| A1 信息不灭 | A1 ℐ-守恒 | ✅ 高度 | P0（已实现） |
| A2 因果箭 | A2 κ-Snap 血缘链 | ✅ 高度 | P0（已实现） |
| A3 最小作用量 | 刘机制 ArgMin S_Rel | ✅ 同一结构 | P1 |
| A4 相干性阈值 | GPCT 稳定对象判据 | ✅ 精神对应 | P1 |
| A5 违反可追踪 | 知识可追溯性 | ✅ 高度 | P0（已实现） |

---

## 7. 待实施项

- [ ] `kappa_snap_export()` 增加 `cgd_violations` 字段
- [ ] `semantic_feedback()` 对接 TOMAS KB 的 `ℐ-update` 接口
- [ ] `DynamicStabilityGate` 结果映射为 GPCT `need_new_node` 触发
- [ ] 在 GUI 中增加 "TOMAS 映射视图" 面板，实时显示 CGD⇔TOMAS 状态

---

*文档版本*: v1.0 (2026-06-21)  
*对应代码*: `mnq_core.py` v3.1 + `mnq_dashboard.py` v3.1  
*参考文献*: TOMAS v2.0 (TR-TOMAS-v2.0-202606), MNQ8 质量生成实验报告 (V19-V25)

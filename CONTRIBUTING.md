# 贡献指南

> 欢迎为 MNQ 金灵球网络仿真器贡献代码、文档或想法！

---

## 如何贡献

### 报告问题

1. 在 [GitHub Issues](https://github.com/lisoleg/mnq-golden-spirit-ball-simulator/issues) 搜索是否已有相同问题
2. 如果没有，创建新 Issue，包含：
   - 问题描述（发生了什么 vs 期望什么）
   - 重现步骤
   - 环境信息（Python 版本、操作系统）
   - 错误日志（如有）

### 提交代码

1. **Fork** 本仓库
2. 创建分支：`git checkout -b feature/your-feature-name`
3. 编写代码，确保：
   - 遵循现有代码风格 (PEP 8)
   - 新功能需有对应实验/测试
   - 不引入新的外部依赖（核心引擎保持纯 Python + NumPy）
4. 运行测试：
   ```bash
   .venv\Scripts\python.exe mnq_dashboard.py --cli
   ```
   确保 12 项实验全部通过
5. 提交：`git commit -m "feat: 简要描述"`
6. 推送并创建 Pull Request

### 提交信息规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 新增 MNQ10 宏观周期模块` |
| `fix:` | 修复 Bug | `fix: 阴龙积高幅值数值爆炸` |
| `docs:` | 文档变更 | `docs: 更新 API 参考` |
| `refactor:` | 重构 | `refactor: 提取 SCF 公共接口` |
| `test:` | 测试相关 | `test: 增加 CGD 边界用例` |
| `chore:` | 杂项 | `chore: 更新依赖版本` |

## 代码规范

### 核心引擎 (mnq_core.py / mnq9_core.py)

- **纯 Python + NumPy**：不引入 SciPy/Torch 等重依赖
- **类设计**：每个物理概念对应一个类，构造函数参数有默认值
- **数值安全**：所有状态值 clamp 到合理范围，防止发散
- **注释**：关键算法标注公式来源（论文公式编号或公众号文章引用）

### 仪表盘 (mnq_dashboard.py)

- GUI 和 CLI 共享同一套实验接口
- 新增实验需同时在 `run_cli_simulation()` 和 GUI 面板中注册
- matplotlib 图表使用 `Agg` 后端兼容（`MPLBACKEND=Agg`）

### 文档

- Markdown 文件使用中文为主、英文术语括注
- 数学公式使用 LaTeX 语法（`$...$` 行内，`$$...$$` 独立）
- 架构图使用 Mermaid 语法

## 项目结构

```
mnq_windows/
├── mnq_core.py           # 核心引擎 — 所有算法实现
├── mnq9_core.py          # MNQ9 信心核 — 四策略预测器
├── mnq_dashboard.py      # 仪表盘 — GUI + CLI
├── run_mnq.bat           # Windows 启动脚本
├── _ref_*.docx.txt       # 理论参考文档（只读，勿修改）
└── docs/                 # (未来) 补充文档
```

## 开发环境

```bash
# 克隆
git clone git@github.com:lisoleg/mnq-golden-spirit-ball-simulator.git
cd mnq-golden-spirit-ball-simulator

# 虚拟环境
python -m venv .venv
.venv\Scripts\python.exe -m pip install numpy matplotlib

# 验证
.venv\Scripts\python.exe mnq_dashboard.py --cli
```

## 理论背景

贡献者建议阅读：

1. `PAPER.md` — 完整的设计与实现论文
2. `_ref_*.docx.txt` — 复合体理学原始参考文档
3. `USER_GUIDE.md` — 使用手册（含模块说明）

## License

提交的代码将遵循 [MIT License](LICENSE)。

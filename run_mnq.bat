@echo off
chcp 65001 >nul
title MNQ 金灵球网络仿真器 v3.0
echo ══════════════════════════════════════════════════
echo   MNQ 金灵球网络仿真器 v3.0 - Windows Edition
echo   基于复合体理学 质量生成实验V13-V25冻结核
echo ══════════════════════════════════════════════════
echo.

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

:: 检查 venv Python
if not exist "%VENV_PYTHON%" (
    echo [错误] 未找到虚拟环境，请先运行安装
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install numpy matplotlib
    pause
    exit /b 1
)

echo [启动] MNQ 金灵球网络仿真器 v3.0
echo.
echo   参数说明:
echo     无参数     - 启动GUI仪表盘模式（冻结核/D4协变/MASS_FACE/MNQ9/CGD面板）
echo     --cli      - 启动命令行仿真模式（18项实验）
echo.
echo   v3.0 新增模块:
echo     1. MNQ8冻结核 (V13-V16) - 五层法则: core-bagua-hex64-wuxing-commit
echo     2. MASS_FACE复合读数    - 六维质量面后验观测
echo     3. D4协变共极大观察器   - 8种D4对称变换审计
echo     4. 动态稳定门+严格双门  - 多条件阈值判定系统
echo     5. 冻结核SHA256指纹验证  - 冻结核完整性保证
echo.
echo   v2.0 保留模块:
echo     6. 三层信息波 (SCF)     - 原子/介观/宏观尺度
echo     7. CGD约束驱动动力学    - 约束违反度实时监控
echo     8. MNQ9信心评估         - 四策略预测对比
echo     9. 金符学3D复广数+阴龙积
echo    10. Hex64六十四卦+刘机制
echo    11. GPU四场演化+Cloud API
echo.

"%VENV_PYTHON%" "%~dp0mnq_dashboard.py" %*

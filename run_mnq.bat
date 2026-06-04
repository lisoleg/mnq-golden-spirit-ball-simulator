@echo off
chcp 65001 >nul
title MNQ 金灵球网络仿真器 v2.0
echo ══════════════════════════════════════════════════
echo   MNQ 金灵球网络仿真器 v2.0 - Windows Edition
echo   基于复合体理学 MNQ/IWPU/CGD/MNQ9 理论体系
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

echo [启动] MNQ 金灵球网络仿真器 v2.0
echo.
echo   参数说明:
echo     无参数     - 启动GUI仪表盘模式（含MNQ9/CGD/三层信息波面板）
echo     --cli      - 启动命令行仿真模式（12项实验）
echo.
echo   新增模块:
echo     1. 三层信息波 (SCF)  - 原子/介观/宏观尺度信息传递
echo     2. CGD约束驱动动力学 - 约束违反度实时监控
echo     3. MNQ9信心评估       - 四策略预测对比
echo     4. 金符学3D复广数     - 阴龙积⊙耦合运算
echo     5. Hex64六十四卦      - 映射计算指令
echo     6. 刘机制路径追踪     - 最优S_Rel路径
echo     7. GPU四场演化        - 性能基准
echo.

"%VENV_PYTHON%" "%~dp0mnq_dashboard.py" %*

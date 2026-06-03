@echo off
chcp 65001 >nul
title MNQ 金灵球网络仿真器
echo ══════════════════════════════════════════════════
echo   MNQ 金灵球网络仿真器 - Windows Edition
echo   基于复合体理学 MNQ/IWPU 理论体系
echo ══════════════════════════════════════════════════
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请安装 Python 3.8+
    echo 下载: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 检查依赖
python -c "import numpy" >nul 2>&1
if %errorlevel% neq 0 (
    echo [安装] 正在安装依赖: numpy matplotlib
    pip install numpy matplotlib
)

echo [启动] MNQ 金灵球网络仿真器
echo.
echo   参数说明:
echo     无参数     - 启动GUI仪表盘模式
echo     --cli      - 启动命令行仿真模式
echo.
echo   快捷操作:
echo     1. 选择实验模式 (背景振荡/缺口六角壳/死零场)
echo     2. 点击 ▶ 启动 开始仿真
echo     3. 观察流贯场/质量面/Oloid差分实时变化
echo     4. 使用 刘机制路径追踪 查看最优路径
echo     5. 使用 MNQ Cloud API 运行三尺度仿真
echo.

python "%~dp0mnq_dashboard.py" %*

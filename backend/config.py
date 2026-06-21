"""
MNQ Web Dashboard 后端配置文件

控制 Flask 应用的 CORS、端口、目录等全局配置。
"""

import os

# Flask 服务端口
PORT = 5000

# 调试模式 (生产环境设为 False)
DEBUG = True

# CORS 允许的来源 (前端开发服务器地址)
CORS_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]

# 快照文件目录 (相对于 backend/ 的上级目录)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPS_DIR = os.path.join(BASE_DIR, '..', 'snaps')

# MUS 记录目录
MUS_DIR = os.path.join(BASE_DIR, '..', 'mus')

# 实验历史存储文件 (JSON 文件)
HISTORY_FILE = os.path.join(BASE_DIR, 'experiment_history.json')

# 前端构建输出目录 (生产环境静态文件)
FRONTEND_DIST = os.path.join(BASE_DIR, '..', 'frontend', 'dist')

# 日志级别
LOG_LEVEL = 'INFO'

# 确保必要目录存在
os.makedirs(SNAPS_DIR, exist_ok=True)
os.makedirs(MUS_DIR, exist_ok=True)

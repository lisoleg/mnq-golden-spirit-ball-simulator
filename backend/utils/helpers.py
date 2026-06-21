"""
MNQ Web Dashboard 辅助函数

通用工具函数，供各 API 模块使用。
"""

import sys
import os
import time
import uuid
import logging

logger = logging.getLogger(__name__)


def setup_mnq_imports():
    """
    将 mnq_windows 根目录加入 sys.path，
    以便 backend/ 下的模块可以 import mnq_core, mnq_deep, mnq9_core。
    """
    base = os.path.join(os.path.dirname(__file__), '..', '..')
    if base not in sys.path:
        sys.path.insert(0, base)


def generate_task_id() -> str:
    """
    生成唯一的任务 ID，格式: task_YYYYMMDDHHmmss_uuid6

    Returns:
        str: 唯一任务标识符
    """
    timestamp = time.strftime('%Y%m%d%H%M%S')
    short_uuid = uuid.uuid4().hex[:6]
    return f"task_{timestamp}_{short_uuid}"


def safe_json_default(obj):
    """
    自定义 JSON 编码器，处理 numpy 类型。

    Args:
        obj: 待序列化对象

    Returns:
        可 JSON 序列化的值
    """
    import numpy as np
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, complex):
        return {'real': obj.real, 'imag': obj.imag}
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

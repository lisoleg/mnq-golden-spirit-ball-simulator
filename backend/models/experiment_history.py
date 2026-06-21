"""
实验历史模型 (JSON 文件存储)

管理实验运行历史的增删查操作。
使用 JSON 文件存储，简单轻量。
"""

import os
import json
import time
import logging
import threading
from typing import List, Dict, Optional
from config import HISTORY_FILE

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _load_history() -> List[Dict]:
    """从 JSON 文件加载历史记录列表。"""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load history: {e}")
        return []


def _save_history(history: List[Dict]):
    """将历史记录列表写入 JSON 文件。"""
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, default=str)
    except IOError as e:
        logger.error(f"Failed to save history: {e}")


def add_history_entry(entry: dict) -> dict:
    """
    添加一条实验历史记录。

    Args:
        entry: 历史记录字典，需包含 experiment_id, params, result 等

    Returns:
        dict: 带有 id 和 timestamp 的完整记录
    """
    with _lock:
        history = _load_history()
        record = {
            'id': f"hist_{int(time.time() * 1000)}",
            'timestamp': time.time(),
            **entry,
        }
        history.insert(0, record)  # 最新在前

        # 限制历史记录数量 (保留最多 200 条)
        if len(history) > 200:
            history = history[:200]

        _save_history(history)
        return record


def get_history_list(limit: int = 50) -> List[Dict]:
    """
    获取实验历史列表。

    Args:
        limit: 最大返回数量

    Returns:
        List[Dict]: 历史记录摘要列表
    """
    history = _load_history()
    return history[:limit]


def get_history_entry(entry_id: str) -> Optional[Dict]:
    """
    获取指定历史记录详情。

    Args:
        entry_id: 历史记录 ID

    Returns:
        Optional[Dict]: 历史记录，不存在则返回 None
    """
    history = _load_history()
    for entry in history:
        if entry.get('id') == entry_id:
            return entry
    return None


def delete_history_entry(entry_id: str) -> bool:
    """
    删除指定历史记录。

    Args:
        entry_id: 历史记录 ID

    Returns:
        bool: 是否成功删除
    """
    with _lock:
        history = _load_history()
        new_history = [e for e in history if e.get('id') != entry_id]
        if len(new_history) == len(history):
            return False  # 未找到记录
        _save_history(new_history)
        return True

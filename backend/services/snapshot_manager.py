"""
κ-Snap 快照管理器

管理 snaps/ 目录下的 JSON 快照文件：
- 列出所有快照
- 读取指定快照
- 导出当前状态为快照
- 删除快照
"""

import os
import json
import logging
from typing import List, Dict, Optional
from config import SNAPS_DIR

logger = logging.getLogger(__name__)


def list_snapshots(limit: int = 50) -> List[Dict]:
    """
    列出 snaps/ 目录下的所有快照文件。

    Args:
        limit: 最大返回数量

    Returns:
        List[Dict]: 快照摘要列表 (id, filename, timestamp, size)
    """
    snapshots = []
    if not os.path.exists(SNAPS_DIR):
        return snapshots

    for filename in sorted(os.listdir(SNAPS_DIR), reverse=True):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(SNAPS_DIR, filename)
        try:
            stat = os.stat(filepath)
            snap_id = filename.replace('.json', '')
            snapshots.append({
                'id': snap_id,
                'filename': filename,
                'timestamp': stat.st_mtime,
                'size': stat.st_size,
            })
        except OSError as e:
            logger.warning(f"Failed to stat snapshot {filename}: {e}")

        if len(snapshots) >= limit:
            break

    return snapshots


def get_snapshot(snap_id: str) -> Optional[Dict]:
    """
    读取指定快照的完整内容。

    Args:
        snap_id: 快照 ID (不含 .json 后缀)

    Returns:
        Optional[Dict]: 快照内容，不存在则返回 None
    """
    filepath = _resolve_snapshot_path(snap_id)
    if filepath is None:
        return None

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read snapshot {snap_id}: {e}")
        return None


def export_snapshot(snap_id: str, data: dict, experiment_id: str = None) -> dict:
    """
    导出当前状态为快照文件。

    Args:
        snap_id: 快照 ID
        data: 快照数据
        experiment_id: 关联的实验 ID (可选)

    Returns:
        dict: {snap_id, file_path}
    """
    import time
    os.makedirs(SNAPS_DIR, exist_ok=True)

    filepath = os.path.join(SNAPS_DIR, f"{snap_id}.json")
    metadata = {
        'snap_id': snap_id,
        'timestamp': time.time(),
        'experiment_id': experiment_id,
    }
    payload = {**metadata, **data}

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, default=str)

    logger.info(f"Snapshot exported: {filepath}")
    return {'snap_id': snap_id, 'file_path': filepath}


def delete_snapshot(snap_id: str) -> bool:
    """
    删除指定快照文件。

    Args:
        snap_id: 快照 ID

    Returns:
        bool: 是否成功删除
    """
    filepath = _resolve_snapshot_path(snap_id)
    if filepath is None:
        return False

    try:
        os.remove(filepath)
        logger.info(f"Snapshot deleted: {filepath}")
        return True
    except OSError as e:
        logger.error(f"Failed to delete snapshot {snap_id}: {e}")
        return False


def _resolve_snapshot_path(snap_id: str) -> Optional[str]:
    """
    解析快照文件路径，防止路径遍历攻击。

    Args:
        snap_id: 快照 ID

    Returns:
        Optional[str]: 安全的文件路径，不存在或危险则返回 None
    """
    # 安全检查：禁止包含路径分隔符
    if '/' in snap_id or '\\' in snap_id or '..' in snap_id:
        logger.warning(f"Rejected suspicious snap_id: {snap_id}")
        return None

    filepath = os.path.join(SNAPS_DIR, f"{snap_id}.json")
    if not os.path.isfile(filepath):
        return None

    return filepath

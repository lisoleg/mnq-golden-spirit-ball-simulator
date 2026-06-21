"""
κ-Snap 快照浏览器 API

路由:
- GET    /api/kappa/list           列出所有快照
- GET    /api/kappa/<id>           获取快照内容
- GET    /api/kappa/<id>/download  下载快照 JSON
- DELETE /api/kappa/<id>           删除快照
- POST   /api/kappa/export         导出当前状态
"""

import sys
import os
import json
import logging
from flask import Blueprint, jsonify, request, send_file, Response

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from services.snapshot_manager import (
    list_snapshots, get_snapshot, export_snapshot, delete_snapshot,
)
from api.kernel import _get_or_create_kernel

logger = logging.getLogger(__name__)

kappa_bp = Blueprint('kappa', __name__)


@kappa_bp.route('/list', methods=['GET'])
def kappa_list():
    """列出所有快照。"""
    try:
        limit = request.args.get('limit', 50, type=int)
        snapshots = list_snapshots(limit=limit)
        return jsonify({'snapshots': snapshots})
    except Exception as e:
        logger.error(f"kappa/list error: {e}")
        return jsonify({'error': str(e)}), 500


@kappa_bp.route('/<snap_id>', methods=['GET'])
def kappa_get(snap_id: str):
    """获取指定快照内容。"""
    try:
        snapshot = get_snapshot(snap_id)
        if snapshot is None:
            return jsonify({'error': 'Snapshot not found'}), 404
        return jsonify({'snapshot': snapshot})
    except Exception as e:
        logger.error(f"kappa/get error: {e}")
        return jsonify({'error': str(e)}), 500


@kappa_bp.route('/<snap_id>/download', methods=['GET'])
def kappa_download(snap_id: str):
    """下载快照 JSON 文件。"""
    try:
        snapshot = get_snapshot(snap_id)
        if snapshot is None:
            return jsonify({'error': 'Snapshot not found'}), 404

        return Response(
            json.dumps(snapshot, indent=2, default=str),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename="{snap_id}.json"',
            },
        )
    except Exception as e:
        logger.error(f"kappa/download error: {e}")
        return jsonify({'error': str(e)}), 500


@kappa_bp.route('/<snap_id>', methods=['DELETE'])
def kappa_delete(snap_id: str):
    """删除指定快照。"""
    try:
        success = delete_snapshot(snap_id)
        if not success:
            return jsonify({'error': 'Snapshot not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"kappa/delete error: {e}")
        return jsonify({'error': str(e)}), 500


@kappa_bp.route('/export', methods=['POST'])
def kappa_export():
    """
    导出当前冻结核状态为快照。

    请求体: {experiment_id: str (可选)}
    响应: {snap_id, file_path}
    """
    try:
        data = request.get_json(force=True) or {}
        experiment_id = data.get('experiment_id')

        fkm = _get_or_create_kernel()
        snap = fkm.snapshot()
        r = fkm.reader.read()

        payload = {
            'field_snapshot': snap,
            'readings': r,
        }

        import time
        snap_id = f"kappa_{int(time.time() * 1000)}"
        result = export_snapshot(snap_id, payload, experiment_id=experiment_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"kappa/export error: {e}")
        return jsonify({'error': str(e)}), 500

"""
Liu Scheduler (刘机制) API

路由:
- POST /api/liu/find-path 追踪最优路径
"""

import sys
import os
import logging
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq_core import JinlingMesh, LiuScheduler

logger = logging.getLogger(__name__)

liu_bp = Blueprint('liu', __name__)

# 全局 LiuScheduler 实例
_liu_scheduler = LiuScheduler()


@liu_bp.route('/find-path', methods=['POST'])
def liu_find_path():
    """
    追踪从源点到各目标的最优路径。

    请求体: {source: [x, y]}
    响应:
        {path: [[x1,y1], ...], min_s_rel: float}
    """
    try:
        data = request.get_json(force=True) or {}
        source = data.get('source')

        if source is None:
            return jsonify({'error': 'Missing source coordinates'}), 400
        if len(source) != 2:
            return jsonify({'error': 'source must be [x, y]'}), 400

        x, y = int(source[0]), int(source[1])

        # 使用已有网格或创建新网格
        mesh = JinlingMesh(dim_x=32, dim_y=32)
        mesh.seed_hex_ring_gap()
        for _ in range(500):
            mesh.mnq8_step(dt=0.016)

        path = _liu_scheduler.find_optimal_path(mesh, (x, y))

        return jsonify({
            'path': path,
            'min_s_rel': float(_liu_scheduler.min_s_rel),
            'path_length': len(path),
        })
    except Exception as e:
        logger.error(f"liu/find-path error: {e}")
        return jsonify({'error': str(e)}), 500

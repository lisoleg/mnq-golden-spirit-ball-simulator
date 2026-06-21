"""
MASS_FACE 质量面读数 API

路由:
- GET /api/massface/read    获取质量面复合读数
- GET /api/massface/history 获取历史读数 (带 ?limit=N)
"""

import sys
import os
import logging
from collections import deque
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.kernel import _get_or_create_kernel

logger = logging.getLogger(__name__)

massface_bp = Blueprint('massface', __name__)

# 内存中的读数历史 (最近 200 条)
_readings_history = deque(maxlen=200)


@massface_bp.route('/read', methods=['GET'])
def massface_read():
    """获取当前质量面复合读数。"""
    try:
        fkm = _get_or_create_kernel()
        r = fkm.reader.read()

        # 保存到历史
        import time
        entry = {'timestamp': time.time(), 'readings': r}
        _readings_history.append(entry)

        return jsonify(r)
    except Exception as e:
        logger.error(f"massface/read error: {e}")
        return jsonify({'error': str(e)}), 500


@massface_bp.route('/history', methods=['GET'])
def massface_history():
    """
    获取质量面历史读数。

    Query params:
        limit: 最大返回数量 (默认 200)
    """
    try:
        limit = request.args.get('limit', 200, type=int)
        history = list(_readings_history)[-limit:]
        return jsonify({'history': history})
    except Exception as e:
        logger.error(f"massface/history error: {e}")
        return jsonify({'error': str(e)}), 500

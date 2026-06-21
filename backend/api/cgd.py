"""
CGD (约束生成动力学) API

路由:
- GET  /api/cgd/status         获取约束状态
- GET  /api/cgd/violation      获取违反度
- POST /api/cgd/add-constraint 添加约束
- POST /api/cgd/modulate       弱调制
"""

import sys
import os
import logging
import numpy as np
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq_core import CGDEngine

logger = logging.getLogger(__name__)

cgd_bp = Blueprint('cgd', __name__)

# 全局 CGD 引擎实例 (单例)
_cgd_engine = CGDEngine()
_cgd_engine.add_constraint("质量面守恒", (0.0, 0.5), modulation=0.005)
_cgd_engine.add_constraint("相干度", (0.98, 1.0), modulation=0.002)
_cgd_engine.add_constraint("能量上限", (0.0, 2.0), modulation=0.01)


@cgd_bp.route('/status', methods=['GET'])
def cgd_status():
    """获取 CGD 约束状态。"""
    try:
        constraints = []
        for c in _cgd_engine.constraints:
            constraints.append({
                'name': c.name,
                'target_range': list(c.target_range),
                'modulation': c.modulation_strength,
            })
        return jsonify({
            'constraints': constraints,
            'steady_states_count': len(_cgd_engine.steady_states),
        })
    except Exception as e:
        logger.error(f"cgd/status error: {e}")
        return jsonify({'error': str(e)}), 500


@cgd_bp.route('/violation', methods=['GET'])
def cgd_violation():
    """获取约束违反度。"""
    try:
        # 使用默认状态向量评估
        sv = np.array([0.25, 0.99, 0.5])
        is_legal, violation = _cgd_engine.evaluate(sv)

        return jsonify({
            'violation': float(violation),
            'is_legal': bool(is_legal),
            'steady_states_count': len(_cgd_engine.steady_states),
        })
    except Exception as e:
        logger.error(f"cgd/violation error: {e}")
        return jsonify({'error': str(e)}), 500


@cgd_bp.route('/add-constraint', methods=['POST'])
def cgd_add_constraint():
    """
    添加约束。

    请求体: {name: str, target_range: [min, max], modulation: float}
    响应: {success: bool}
    """
    try:
        data = request.get_json(force=True)
        if not data or 'name' not in data:
            return jsonify({'error': 'Missing name'}), 400

        name = data['name']
        target_range = tuple(data.get('target_range', [0.0, 1.0]))
        modulation = data.get('modulation', 0.005)

        _cgd_engine.add_constraint(name, target_range, modulation=modulation)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"cgd/add-constraint error: {e}")
        return jsonify({'error': str(e)}), 500


@cgd_bp.route('/modulate', methods=['POST'])
def cgd_modulate():
    """
    弱调制。

    请求体: {state_vector: [float, ...]}
    响应: {modulated_vector: [float, ...]}
    """
    try:
        data = request.get_json(force=True)
        if not data or 'state_vector' not in data:
            return jsonify({'error': 'Missing state_vector'}), 400

        sv = np.array(data['state_vector'], dtype=np.float64)
        # 评估约束
        is_legal, violation = _cgd_engine.evaluate(sv)

        # 简单调制: 向合法区间中心移动
        if not is_legal:
            modulated = sv.copy()
            for c in _cgd_engine.constraints:
                low, high = c.target_range
                center = (low + high) / 2
                # 对每个维度进行弱调制
                if modulated.any():
                    modulated = modulated + c.modulation_strength * (center - modulated.mean())
                    modulated = np.clip(modulated, low, high)
        else:
            modulated = sv

        return jsonify({
            'input_vector': sv.tolist(),
            'modulated_vector': modulated.tolist(),
            'violation': float(violation),
            'is_legal': bool(is_legal),
        })
    except Exception as e:
        logger.error(f"cgd/modulate error: {e}")
        return jsonify({'error': str(e)}), 500

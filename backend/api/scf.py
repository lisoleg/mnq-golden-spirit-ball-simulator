"""
SCF (三层信息波) API

路由:
- GET  /api/scf/status             获取 SCF 状态
- POST /api/scf/step               执行 SCF 迭代
- POST /api/scf/run-to-convergence 运行至收敛
"""

import sys
import os
import logging
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq_core import ThreeLayerInfoWave

logger = logging.getLogger(__name__)

scf_bp = Blueprint('scf', __name__)

# 全局 SCF 实例 (单例)
_scf_wave = ThreeLayerInfoWave(core_init=0.001)


@scf_bp.route('/status', methods=['GET'])
def scf_status():
    """获取 SCF 当前状态。"""
    try:
        snap = _scf_wave.snapshot()
        return jsonify({
            'core': snap['core'],
            'bagua_mean': snap['bagua_mean'],
            'hex64_mean': snap['hex64_mean'],
            'converged': snap['converged'],
            'max_change': snap.get('max_change', 0.0),
        })
    except Exception as e:
        logger.error(f"scf/status error: {e}")
        return jsonify({'error': str(e)}), 500


@scf_bp.route('/step', methods=['POST'])
def scf_step():
    """
    执行 SCF 迭代。

    请求体: {steps: int}
    响应: {snapshot, max_change}
    """
    try:
        data = request.get_json(force=True) or {}
        steps = data.get('steps', 1)

        max_change = 0.0
        for _ in range(steps):
            change = _scf_wave.step()
            max_change = max(max_change, change)

        snap = _scf_wave.snapshot()
        return jsonify({
            'snapshot': snap,
            'max_change': max_change,
        })
    except Exception as e:
        logger.error(f"scf/step error: {e}")
        return jsonify({'error': str(e)}), 500


@scf_bp.route('/run-to-convergence', methods=['POST'])
def scf_run_to_convergence():
    """
    运行 SCF 到收敛。

    请求体: {max_steps: int, epsilon: float}
    响应: {steps, converged, snapshot}
    """
    try:
        global _scf_wave
        data = request.get_json(force=True) or {}
        max_steps = data.get('max_steps', 300)
        epsilon = data.get('epsilon', 1e-6)

        core_init = data.get('core_init', 0.001)
        _scf_wave = ThreeLayerInfoWave(core_init=core_init)

        steps = _scf_wave.run_to_convergence(max_steps=max_steps, epsilon=epsilon)
        snap = _scf_wave.snapshot()

        return jsonify({
            'steps': steps,
            'converged': snap['converged'],
            'snapshot': snap,
        })
    except Exception as e:
        logger.error(f"scf/run-to-convergence error: {e}")
        return jsonify({'error': str(e)}), 500

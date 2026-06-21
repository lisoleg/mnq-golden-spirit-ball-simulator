"""
JinlingMesh (金灵球网格) API

路由:
- GET  /api/mesh/status      网格状态
- GET  /api/mesh/field       流贯场数组
- GET  /api/mesh/mass-face   质量面数组
- GET  /api/mesh/excess-loop Oloid 差分数组
- POST /api/mesh/seed        初始化种子
- POST /api/mesh/step        步进演化
"""

import sys
import os
import logging
import numpy as np
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq_core import JinlingMesh

logger = logging.getLogger(__name__)

mesh_bp = Blueprint('mesh', __name__)

# 全局 JinlingMesh 实例 (单例)
_jinling_mesh = JinlingMesh(dim_x=32, dim_y=32)
_jinling_mesh.seed_background()


def _mesh_to_list(array):
    """将 numpy 数组转换为可 JSON 序列化的列表。"""
    if array is None:
        return []
    return array.tolist()


@mesh_bp.route('/status', methods=['GET'])
def mesh_status():
    """获取网格当前状态。"""
    try:
        return jsonify({
            'dim_x': _jinling_mesh.dim_x,
            'dim_y': _jinling_mesh.dim_y,
            'total_mass': float(_jinling_mesh.total_mass),
            'total_loop': float(_jinling_mesh.total_loop),
            'mass_face_count': int(_jinling_mesh.mass_face_count),
            'step_count': getattr(_jinling_mesh, 'step_count', 0),
        })
    except Exception as e:
        logger.error(f"mesh/status error: {e}")
        return jsonify({'error': str(e)}), 500


@mesh_bp.route('/field', methods=['GET'])
def mesh_field():
    """获取流贯场数组 (Ftel/能量场)。"""
    try:
        # 获取 phi (流贯势) 场
        phi = getattr(_jinling_mesh, 'phi', None)
        if phi is not None:
            return jsonify({'field': _mesh_to_list(phi)})

        # 从 spheres 列表构建场数组
        dim = _jinling_mesh.dim_x
        result = np.zeros((dim, dim))
        for y in range(dim):
            for x in range(dim):
                sphere = _jinling_mesh.get_sphere(x, y)
                if sphere:
                    result[y, x] = float(sphere.ftel_magnitude if sphere.ftel_magnitude else sphere.state.norm())
        return jsonify({'field': _mesh_to_list(result)})
    except Exception as e:
        logger.error(f"mesh/field error: {e}")
        return jsonify({'error': str(e)}), 500


@mesh_bp.route('/mass-face', methods=['GET'])
def mesh_mass_face():
    """获取质量面数组。"""
    try:
        dim = _jinling_mesh.dim_x
        result = np.zeros((dim, dim))
        for y in range(dim):
            for x in range(dim):
                sphere = _jinling_mesh.get_sphere(x, y)
                if sphere:
                    val = float(sphere.state.a)
                    # 阈值判定质量面
                    result[y, x] = 1.0 if abs(val) > 0.05 else 0.0
        return jsonify({'mass_faces': _mesh_to_list(result)})
    except Exception as e:
        logger.error(f"mesh/mass-face error: {e}")
        return jsonify({'error': str(e)}), 500


@mesh_bp.route('/excess-loop', methods=['GET'])
def mesh_excess_loop():
    """获取 Oloid 差分数组 (过盈回路)。"""
    try:
        dim = _jinling_mesh.dim_x
        result = np.zeros((dim, dim))
        for y in range(1, dim - 1):
            for x in range(1, dim - 1):
                c = _jinling_mesh.get_sphere(x, y)
                n = _jinling_mesh.get_sphere(x, y - 1)
                s = _jinling_mesh.get_sphere(x, y + 1)
                e = _jinling_mesh.get_sphere(x + 1, y)
                w = _jinling_mesh.get_sphere(x - 1, y)
                center = float(c.state.norm()) if c else 0.0
                neighbors = float(
                    (n.state.norm() + s.state.norm() + e.state.norm() + w.state.norm())
                ) / 4.0 if (n and s and e and w) else 0.0
                result[y, x] = max(0, neighbors - center)
        return jsonify({'excess_loop': _mesh_to_list(result)})
    except Exception as e:
        logger.error(f"mesh/excess-loop error: {e}")
        return jsonify({'error': str(e)}), 500


@mesh_bp.route('/seed', methods=['POST'])
def mesh_seed():
    """
    初始化网格种子。

    请求体: {mode: str}
    支持的模式: background, zero_field, hex_ring_gap
    响应: {success: bool, mode: str}
    """
    try:
        data = request.get_json(force=True) or {}
        mode = data.get('mode', 'background')

        global _jinling_mesh
        dim = data.get('dim', 32)
        _jinling_mesh = JinlingMesh(dim_x=dim, dim_y=dim)

        seed_methods = {
            'background': _jinling_mesh.seed_background,
            'zero_field': _jinling_mesh.seed_zero_field,
            'hex_ring_gap': _jinling_mesh.seed_hex_ring_gap,
        }

        seeder = seed_methods.get(mode)
        if seeder is None:
            available = list(seed_methods.keys())
            return jsonify({
                'error': f'Unknown seed mode: {mode}',
                'available_modes': available,
            }), 400

        seeder()
        return jsonify({'success': True, 'mode': mode})
    except Exception as e:
        logger.error(f"mesh/seed error: {e}")
        return jsonify({'error': str(e)}), 500


@mesh_bp.route('/step', methods=['POST'])
def mesh_step():
    """
    执行网格演化步进。

    请求体: {dt: float, steps: int}
    响应: {stats: dict}
    """
    try:
        data = request.get_json(force=True) or {}
        dt = data.get('dt', 0.016)
        steps = data.get('steps', 1)

        for _ in range(steps):
            _jinling_mesh.mnq8_step(dt=dt)

        return jsonify({
            'stats': {
                'mass': float(_jinling_mesh.total_mass),
                'loop': float(_jinling_mesh.total_loop),
                'mass_face_count': int(_jinling_mesh.mass_face_count),
            }
        })
    except Exception as e:
        logger.error(f"mesh/step error: {e}")
        return jsonify({'error': str(e)}), 500

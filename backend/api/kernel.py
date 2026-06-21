"""
FrozenKernel (冻结核) API

路由:
- GET  /api/kernel/status      获取冻结核状态
- POST /api/kernel/step        单步/多步演化
- POST /api/kernel/reset       重置冻结核
- GET  /api/kernel/readings    获取 MASS_FACE 读数
- GET  /api/kernel/fingerprint 获取 SHA256 指纹
- POST /api/kernel/d4-audit    执行 D4 协变审计
"""

import sys
import os
import logging
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq_core import (
    FrozenKernelMesh, D4CovariantObserver,
    mnq8_frozen_kernel_verify, FROZEN_KERNEL_FINGERPRINT,
)

logger = logging.getLogger(__name__)

kernel_bp = Blueprint('kernel', __name__)

# 全局冻结核实例 (单例)
_fk_mesh = None


def _get_or_create_kernel() -> FrozenKernelMesh:
    """获取或懒创建 FrozenKernelMesh 单例。"""
    global _fk_mesh
    if _fk_mesh is None:
        _fk_mesh = FrozenKernelMesh(seed=42)
        _fk_mesh.init_background()
        keep_hex = [0, 1, 5, 6, 7, 8, 10, 11, 12, 13, 15]
        _fk_mesh.init_condition(keep_hex, seed=42, phi_polarity=1,
                                omega_mode="MASK", comp_mode="MASK",
                                phi_gain=1, center_anchor=1)
    return _fk_mesh


@kernel_bp.route('/status', methods=['GET'])
def kernel_status():
    """获取冻结核当前状态。"""
    try:
        fkm = _get_or_create_kernel()
        snap = fkm.snapshot()
        return jsonify({
            'step_count': fkm.kernel.step_count,
            'active_points': fkm.kernel.active_points(),
            'l1_by_channel': fkm.kernel.l1_by_channel(),
            'mass_face': snap.get('mass_face'),
            'carrier': snap.get('carrier'),
            'fingerprint': snap.get('fingerprint', '')[:16],
        })
    except Exception as e:
        logger.error(f"kernel/status error: {e}")
        return jsonify({'error': str(e)}), 500


@kernel_bp.route('/step', methods=['POST'])
def kernel_step():
    """
    执行指定步数的冻结核演化。

    请求体: {steps: int}
    响应: {field_snapshot, readings}
    """
    try:
        data = request.get_json(force=True) or {}
        steps = data.get('steps', 1)

        fkm = _get_or_create_kernel()
        for _ in range(steps):
            fkm.step()

        r = fkm.reader.read()
        snap = fkm.snapshot()
        return jsonify({
            'step_count': fkm.kernel.step_count,
            'readings': r,
            'mass_face': snap.get('mass_face'),
            'active': snap.get('active'),
        })
    except Exception as e:
        logger.error(f"kernel/step error: {e}")
        return jsonify({'error': str(e)}), 500


@kernel_bp.route('/reset', methods=['POST'])
def kernel_reset():
    """
    重置冻结核。

    请求体: {seed: int, condition: str (可选)}
    响应: {success: bool}
    """
    try:
        data = request.get_json(force=True) or {}
        seed = data.get('seed', 42)
        condition = data.get('condition', 'default')

        global _fk_mesh
        _fk_mesh = FrozenKernelMesh(seed=seed)
        _fk_mesh.init_background()
        keep_hex = [0, 1, 5, 6, 7, 8, 10, 11, 12, 13, 15]
        _fk_mesh.init_condition(keep_hex, seed=seed, phi_polarity=1,
                                omega_mode="MASK", comp_mode="MASK",
                                phi_gain=1, center_anchor=1)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"kernel/reset error: {e}")
        return jsonify({'error': str(e)}), 500


@kernel_bp.route('/readings', methods=['GET'])
def kernel_readings():
    """获取 MASS_FACE 复合读数。"""
    try:
        fkm = _get_or_create_kernel()
        r = fkm.reader.read()
        return jsonify(r)
    except Exception as e:
        logger.error(f"kernel/readings error: {e}")
        return jsonify({'error': str(e)}), 500


@kernel_bp.route('/fingerprint', methods=['GET'])
def kernel_fingerprint():
    """获取冻结核 SHA256 完整性指纹验证。"""
    try:
        verified = mnq8_frozen_kernel_verify()
        return jsonify({
            'fingerprint': FROZEN_KERNEL_FINGERPRINT,
            'verified': verified,
        })
    except Exception as e:
        logger.error(f"kernel/fingerprint error: {e}")
        return jsonify({'error': str(e)}), 500


@kernel_bp.route('/d4-audit', methods=['POST'])
def kernel_d4_audit():
    """执行 D4 协变审计。"""
    try:
        fkm = _get_or_create_kernel()
        d4r = D4CovariantObserver.audit_covariance(fkm.kernel, fkm.kernel)
        results = []
        for name in ['ID', 'ROT90', 'ROT180', 'ROT270', 'MIRROR_LR',
                     'MIRROR_TB', 'TRANSPOSE', 'ANTI_TRANSPOSE']:
            r = d4r.get(name, {})
            results.append({
                'transform': name,
                'covariant': r.get('covariant', False),
                'details': r,
            })
        return jsonify({'results': results})
    except Exception as e:
        logger.error(f"kernel/d4-audit error: {e}")
        return jsonify({'error': str(e)}), 500

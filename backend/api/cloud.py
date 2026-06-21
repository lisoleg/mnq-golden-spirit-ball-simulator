"""
MNQ Cloud API

路由:
- POST /api/cloud/simulate 运行 Cloud 仿真
"""

import sys
import os
import logging
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq_core import MNQCloudAPI

logger = logging.getLogger(__name__)

cloud_bp = Blueprint('cloud', __name__)


@cloud_bp.route('/simulate', methods=['POST'])
def cloud_simulate():
    """
    运行 MNQ Cloud 仿真。

    请求体:
        {unit_mode: str, experiment: str, steps: int, epsilon: float, seed: int}
    可选 unit_mode: atomic, meso, macro
    可选 experiment: hex_ring_gap, background, zero_field

    响应:
        {mean_energy_J, coherence, coherence_std, ...}
    """
    try:
        data = request.get_json(force=True) or {}

        unit_mode = data.get('unit_mode', 'atomic')
        experiment = data.get('experiment', 'hex_ring_gap')
        steps = data.get('steps', 512)
        epsilon = data.get('epsilon', 1e-6)
        seed = data.get('seed', 42)

        valid_modes = ['atomic', 'meso', 'macro']
        if unit_mode not in valid_modes:
            return jsonify({
                'error': f'Invalid unit_mode: {unit_mode}',
                'valid_modes': valid_modes,
            }), 400

        api = MNQCloudAPI(unit_mode=unit_mode)
        result = api.simulate(experiment=experiment, steps=steps, seed=seed)

        return jsonify({
            'mean_energy_J': result.get('mean_energy_J', 0.0),
            'coherence': result.get('coherence', 0.0),
            'coherence_std': result.get('coherence_std', 0.0),
            'unit_mode': unit_mode,
            'experiment': experiment,
            'steps': steps,
        })
    except Exception as e:
        logger.error(f"cloud/simulate error: {e}")
        return jsonify({'error': str(e)}), 500

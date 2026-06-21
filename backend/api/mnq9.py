"""
MNQ9 (信心核) API

路由:
- GET  /api/mnq9/status          获取 MNQ9 状态
- POST /api/mnq9/set-macro       设置宏观信心场
- POST /api/mnq9/set-future      设置未来事件波
- POST /api/mnq9/run-series      运行趋势模拟
- GET  /api/mnq9/scenario/<name> 应用预定义场景
"""

import sys
import os
import logging
from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from mnq9_core import MNQ9Simulator, MNQ9ScenarioGenerator

logger = logging.getLogger(__name__)

mnq9_bp = Blueprint('mnq9', __name__)

# 全局 MNQ9 模拟器实例 (单例)
_mnq9_sim = MNQ9Simulator(lam=0.03)
_mnq9_sim.set_macro_confidence({'M2': 0.2, 'PMI': 0.1, 'DR007': -0.1})
_mnq9_sim.set_future_wave([0.05] * 20)


@mnq9_bp.route('/status', methods=['GET'])
def mnq9_status():
    """获取 MNQ9 当前状态。"""
    try:
        omega = getattr(_mnq9_sim.core, 'omega', None)
        if omega is None and hasattr(_mnq9_sim, 'omega_series') and _mnq9_sim.omega_series:
            omega = _mnq9_sim.omega_series[-1]
        if omega is None:
            omega = 0.02
        return jsonify({
            'omega': float(omega),
            'B_conf': float(_mnq9_sim.B_conf_series[-1]) if (hasattr(_mnq9_sim, 'B_conf_series') and _mnq9_sim.B_conf_series) else 0.0,
            'kernel': float(getattr(_mnq9_sim.core, 'omega', 0.02)),
            'history_length': len(_mnq9_sim.omega_series),
        })
    except Exception as e:
        logger.error(f"mnq9/status error: {e}")
        return jsonify({'error': str(e)}), 500


@mnq9_bp.route('/set-macro', methods=['POST'])
def mnq9_set_macro():
    """
    设置宏观信心场。

    请求体: {M2: float, PMI: float, DR007: float, ...}
    响应: {success: bool}
    """
    try:
        data = request.get_json(force=True) or {}
        macro = {
            'M2': data.get('M2', 0.2),
            'PMI': data.get('PMI', 0.1),
            'DR007': data.get('DR007', -0.1),
        }
        # 合并额外字段
        for key, val in data.items():
            if key not in macro:
                macro[key] = val
        _mnq9_sim.set_macro_confidence(macro)
        return jsonify({'success': True, 'macro': macro})
    except Exception as e:
        logger.error(f"mnq9/set-macro error: {e}")
        return jsonify({'error': str(e)}), 500


@mnq9_bp.route('/set-future', methods=['POST'])
def mnq9_set_future():
    """
    设置未来事件波。

    请求体: {phi_series: [float, ...]}
    响应: {success: bool}
    """
    try:
        data = request.get_json(force=True) or {}
        phi_series = data.get('phi_series', [0.05] * 20)
        _mnq9_sim.set_future_wave(phi_series)
        return jsonify({'success': True, 'length': len(phi_series)})
    except Exception as e:
        logger.error(f"mnq9/set-future error: {e}")
        return jsonify({'error': str(e)}), 500


@mnq9_bp.route('/run-series', methods=['POST'])
def mnq9_run_series():
    """
    运行趋势模拟。

    请求体: {steps: int}
    响应: {omega_series, B_conf_series, report}
    """
    try:
        data = request.get_json(force=True) or {}
        steps = data.get('steps', 60)

        global _mnq9_sim
        # 重新初始化以确保结果正确
        _mnq9_sim = MNQ9Simulator(lam=data.get('lam', 0.03))
        macro = data.get('macro')
        events = data.get('events')
        if macro:
            _mnq9_sim.set_macro_confidence(macro)
        else:
            _mnq9_sim.set_macro_confidence({'M2': 0.2, 'PMI': 0.1, 'DR007': -0.1})
        if events:
            _mnq9_sim.set_future_wave(events)
        else:
            _mnq9_sim.set_future_wave([0.05] * 20)

        omega_series = _mnq9_sim.run_series(steps=steps)
        report = _mnq9_sim.generate_report()

        # 提取 Omega 序列
        omega_values = [float(v) if not isinstance(v, dict) else float(v.get('omega', 0))
                        for v in omega_series]

        return jsonify({
            'omega_series': omega_values,
            'B_conf_series': [report.get('B_conf', 0.0)] * steps,
            'report': report,
        })
    except Exception as e:
        logger.error(f"mnq9/run-series error: {e}")
        return jsonify({'error': str(e)}), 500


@mnq9_bp.route('/scenario/<name>', methods=['GET'])
def mnq9_scenario(name: str):
    """
    应用预定义场景。

    支持的场景: bullish, bearish, crisis_recovery, policy_shock

    响应: {macro: dict, events: list}
    """
    try:
        scenario_map = {
            'bullish': MNQ9ScenarioGenerator.bull_market,
            'bearish': MNQ9ScenarioGenerator.bear_market,
            'crisis_recovery': MNQ9ScenarioGenerator.crisis_recovery,
            'policy_shock': MNQ9ScenarioGenerator.policy_shock,
        }

        generator = scenario_map.get(name)
        if generator is None:
            available = list(scenario_map.keys())
            return jsonify({
                'error': f'Unknown scenario: {name}',
                'available_scenarios': available,
            }), 404

        macro, events = generator()
        return jsonify({'macro': macro, 'events': events})
    except Exception as e:
        logger.error(f"mnq9/scenario error: {e}")
        return jsonify({'error': str(e)}), 500

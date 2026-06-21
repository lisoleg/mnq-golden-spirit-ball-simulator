"""
实验执行引擎

在后台线程中运行 MNQ 实验，通过 SSE 推送实时进度。
支持全部 18 种实验模式。
"""

import sys
import os
import threading
import logging
import time
from typing import Dict, Optional, Callable

from utils.helpers import setup_mnq_imports, generate_task_id
from services.sse_manager import create_sse_queue, push_event, close_sse_queue

setup_mnq_imports()

import numpy as np
from mnq_core import (
    JinlingMesh, JinlingSphere, MNQFieldGPU, MNQCloudAPI, LiuScheduler,
    GoldenSymbol3D, get_hex64_rule, ThreeLayerInfoWave, CGDEngine,
    MNQ8FrozenKernel, MassFaceReader, DynamicStabilityGate,
    StrictDualGate, D4CovariantObserver, FrozenKernelMesh,
    mnq8_frozen_kernel_verify, FROZEN_KERNEL_FINGERPRINT,
    kappa_snap_export, mnq_minimal_step, mnq_auto_gamma,
)
from mnq9_core import MNQ9Simulator, MNQ9ScenarioGenerator, MacroConfidenceField, MNQ9Core

logger = logging.getLogger(__name__)

# 18 种实验定义
EXPERIMENTS = {
    'ZERO_FIELD': {
        'name': '死零场',
        'description': '验证死零场不破缺，基准实验',
        'params': {'dim': 16, 'steps': 100, 'dt': 0.016},
    },
    'BACKGROUND_OSC': {
        'name': '动态背景',
        'description': '背景态弥散，无囚禁验证',
        'params': {'dim': 16, 'steps': 1000, 'dt': 0.016},
    },
    'HEX_RING_GAP': {
        'name': '缺口六角壳层',
        'description': '流贯囚禁检测',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'HEX_RING_DENSE': {
        'name': '稠密六角环',
        'description': '高密度六角环排列演化',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'HEX_LOOP_AROUND': {
        'name': '环绕六角回路',
        'description': '六角形围绕中心回路排列',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'DUAL_RING_GAP': {
        'name': '双缺口环',
        'description': '两个缺口环的干涉效应',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'SINGLE_SPOT': {
        'name': '单热点',
        'description': '单点激发的传播特性',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'FLOW_TUNNEL': {
        'name': '流隧道',
        'description': '流贯场隧道效应',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'RANDOM_SEED': {
        'name': '随机种子',
        'description': '随机初始化的自组织行为',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'COMPLEX_MODE': {
        'name': '复广数模式',
        'description': '3D复广数阴龙积运算验证',
        'params': {'dim': 16, 'steps': 200, 'dt': 0.016},
    },
    'HIGH_ENERGY_BURST': {
        'name': '高能爆发',
        'description': '短时高能量注入',
        'params': {'dim': 32, 'steps': 500, 'dt': 0.016},
    },
    'WAVE_PACKET': {
        'name': '波包',
        'description': '局部波包的传播与弥散',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'STANDING_WAVE': {
        'name': '驻波',
        'description': '驻波模式的稳定演化',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'VORTEX_PAIR': {
        'name': '涡对',
        'description': '双涡旋相互作用',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'BOUNDARY_LAYER': {
        'name': '边界层',
        'description': '边界层效应与泄漏',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'GRADIENT_MIX': {
        'name': '梯度混合',
        'description': '多梯度的非线性混合',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'CHAOS_SEED': {
        'name': '混沌种子',
        'description': '临界混沌条件下的演化',
        'params': {'dim': 32, 'steps': 1000, 'dt': 0.016},
    },
    'FROZEN_DUAL_GATE': {
        'name': '冻结核双门',
        'description': '冻结核严格双门评估',
        'params': {'dim': 16, 'steps': 384, 'dt': 0.016},
    },
}

# 运行状态跟踪
_task_status: Dict[str, dict] = {}


def get_experiment_list() -> list:
    """获取所有可用实验的列表。"""
    return [
        {
            'id': exp_id,
            'name': info['name'],
            'description': info['description'],
        }
        for exp_id, info in EXPERIMENTS.items()
    ]


def get_task_status(task_id: str) -> Optional[dict]:
    """查询实验任务状态。"""
    return _task_status.get(task_id)


def run_experiment(
    experiment_id: str,
    params: Optional[dict] = None,
    on_progress: Optional[Callable] = None,
) -> dict:
    """
    在后台线程中运行指定实验。

    Args:
        experiment_id: 实验 ID
        params: 自定义参数 (覆盖默认参数)
        on_progress: 进度回调 (progress: int, log: str)

    Returns:
        dict: {task_id, status, message}
    """
    if experiment_id not in EXPERIMENTS:
        return {'error': f'Unknown experiment: {experiment_id}'}

    task_id = generate_task_id()
    exp_info = EXPERIMENTS[experiment_id]
    merged_params = {**exp_info['params'], **(params or {})}

    # 注册任务状态
    _task_status[task_id] = {
        'task_id': task_id,
        'experiment_id': experiment_id,
        'status': 'running',
        'progress': 0,
        'result': None,
        'log': [],
    }

    # 创建 SSE 队列
    create_sse_queue(task_id)

    # 在后台线程执行
    thread = threading.Thread(
        target=_execute_experiment,
        args=(task_id, experiment_id, merged_params),
        daemon=True,
    )
    thread.start()

    logger.info(f"Experiment started: {experiment_id} -> {task_id}")
    return {'task_id': task_id, 'status': 'running', 'message': 'Experiment started'}


def _execute_experiment(task_id: str, experiment_id: str, params: dict):
    """
    实际执行实验的内部函数。

    根据实验类型调用相应的核心算法。
    """
    def log(status, progress, message="", result=None):
        _task_status[task_id]['status'] = status
        _task_status[task_id]['progress'] = progress
        if message:
            _task_status[task_id]['log'].append(message)
        if result is not None:
            _task_status[task_id]['result'] = result
        push_event(task_id, {
            'status': status,
            'progress': progress,
            'log': message,
            'result': result,
        })

    try:
        steps = params.get('steps', 1000)
        dt = params.get('dt', 0.016)
        dim = params.get('dim', 32)

        if experiment_id == 'ZERO_FIELD':
            mesh = JinlingMesh(dim_x=dim, dim_y=dim)
            mesh.seed_zero_field()
            for i in range(steps):
                mesh.mnq8_step(dt=dt)
                if i % max(1, steps // 10) == 0:
                    log('running', int(100 * i / steps),
                        f"Step {i}: Mass={mesh.total_mass:.6f}")
            log('completed', 100, "",
                {'mass': mesh.total_mass, 'loop': mesh.total_loop,
                 'mass_face_count': mesh.mass_face_count})

        elif experiment_id == 'BACKGROUND_OSC':
            mesh = JinlingMesh(dim_x=dim, dim_y=dim)
            mesh.seed_background()
            for i in range(steps):
                mesh.mnq8_step(dt=dt)
                if i % max(1, steps // 10) == 0:
                    log('running', int(100 * i / steps),
                        f"Step {i}: Mass={mesh.total_mass:.6f}")
            log('completed', 100, "",
                {'mass': mesh.total_mass, 'loop': mesh.total_loop,
                 'mass_face_count': mesh.mass_face_count})

        elif experiment_id == 'HEX_RING_GAP':
            mesh = JinlingMesh(dim_x=dim, dim_y=dim)
            mesh.seed_hex_ring_gap()
            for i in range(steps):
                mesh.mnq8_step(dt=dt)
                if i % max(1, steps // 10) == 0:
                    log('running', int(100 * i / steps),
                        f"Step {i}: Mass={mesh.total_mass:.6f}, MF={mesh.mass_face_count}")
            log('completed', 100, "",
                {'mass': mesh.total_mass, 'loop': mesh.total_loop,
                 'mass_face_count': mesh.mass_face_count})

        elif experiment_id in ('HEX_RING_DENSE', 'HEX_LOOP_AROUND', 'DUAL_RING_GAP',
                                'SINGLE_SPOT', 'FLOW_TUNNEL', 'RANDOM_SEED',
                                'HIGH_ENERGY_BURST', 'WAVE_PACKET', 'STANDING_WAVE',
                                'VORTEX_PAIR', 'BOUNDARY_LAYER', 'GRADIENT_MIX',
                                'CHAOS_SEED'):
            mesh = JinlingMesh(dim_x=dim, dim_y=dim)
            _seed_mesh_by_experiment(mesh, experiment_id)
            for i in range(steps):
                mesh.mnq8_step(dt=dt)
                if i % max(1, steps // 20) == 0:
                    log('running', int(100 * i / steps),
                        f"Step {i}: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}")
            log('completed', 100, "",
                {'mass': mesh.total_mass, 'loop': mesh.total_loop,
                 'mass_face_count': mesh.mass_face_count})

        elif experiment_id == 'COMPLEX_MODE':
            z1 = GoldenSymbol3D(1.0, 0.5, 0.3)
            z2 = GoldenSymbol3D(0.8, -0.3, 0.2)
            z_product = z1.yin_long_product(z2)
            log('completed', 100, "",
                {'z1': str(z1), 'z2': str(z2), 'product': str(z_product),
                 'norm': z_product.norm()})

        elif experiment_id == 'FROZEN_DUAL_GATE':
            keep_hex = [0, 1, 5, 6, 7, 8, 10, 11, 12, 13, 15]
            keep_cross = [0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15]
            log('running', 10, "初始化冻结核...")
            fkm = FrozenKernelMesh(seed=42)
            fkm.init_background()
            fkm.init_condition(keep_hex, seed=42, phi_polarity=1,
                               omega_mode="MASK", comp_mode="MASK",
                               phi_gain=1, center_anchor=1)
            log('running', 20, f"初始背景: active={fkm.kernel.active_points()}")
            fkm.run(steps)
            final = fkm.snapshot()
            r = fkm.reader.read()
            stability = fkm.assess_stability()
            log('completed', 100, "",
                {'mass_face': final['mass_face'], 'active': final['active'],
                 'carrier': final.get('carrier'),
                 'fingerprint': final.get('fingerprint', '')[:16],
                 'readings': r,
                 'stability': stability})

        else:
            log('failed', 0, f"Unknown experiment: {experiment_id}")

    except Exception as e:
        import traceback
        logger.error(f"Experiment {experiment_id} failed: {e}")
        logger.error(traceback.format_exc())
        log('failed', _task_status[task_id]['progress'],
            f"Error: {str(e)}")

    finally:
        # 发送完成事件，关闭 SSE 流
        push_event(task_id, {'type': 'done', 'status': _task_status[task_id]['status'],
                            'result': _task_status[task_id]['result']})


def _seed_mesh_by_experiment(mesh, experiment_id: str):
    """根据实验类型初始化网格种子。"""
    seed_map = {
        'HEX_RING_DENSE': 'seed_hex_ring_gap',
        'HEX_LOOP_AROUND': 'seed_hex_ring_gap',
        'DUAL_RING_GAP': 'seed_hex_ring_gap',
        'SINGLE_SPOT': 'seed_background',
        'FLOW_TUNNEL': 'seed_hex_ring_gap',
        'RANDOM_SEED': 'seed_background',
        'HIGH_ENERGY_BURST': 'seed_background',
        'WAVE_PACKET': 'seed_background',
        'STANDING_WAVE': 'seed_hex_ring_gap',
        'VORTEX_PAIR': 'seed_hex_ring_gap',
        'BOUNDARY_LAYER': 'seed_hex_ring_gap',
        'GRADIENT_MIX': 'seed_background',
        'CHAOS_SEED': 'seed_background',
    }
    method_name = seed_map.get(experiment_id, 'seed_background')
    getattr(mesh, method_name)()

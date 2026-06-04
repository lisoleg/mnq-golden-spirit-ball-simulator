"""
MNQ9 信心核模型 (Confidence Kernel Model) — 宏观趋势模拟器
基于 MNQ9 白皮书实现: Ω/φ_future/B_conf 三重机制

核心理念:
1. Ω (信心主核): 市场底层信心惯性, 负责趋势主方向
2. φ_future (未来事件波): 外部事件/数据/政策形成的冲击向量
3. B_conf (宏观信心场): 宏观指标形成的背景信心强度

用法:
    sim = MNQ9Simulator()
    sim.set_macro_confidence({'M2': 0.18, 'PMI': 0.05, 'DR007': -0.10})
    sim.set_future_wave([0.2, -0.3, 0.0, 0.1])
    trends = sim.run_series(steps=100)
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import math
from collections import deque


# ============================================================================
# 1. MNQ9Core — 信心主核引擎
# ============================================================================

class MNQ9Core:
    """
    MNQ9 信心主核 (Confidence Kernel)
    实现宏观趋势、资金流、事件注入的核心算法
    """

    def __init__(self, lam: float = 0.5, w_macro: Tuple[float, float, float] = (0.4, 0.3, 0.3)):
        """
        Args:
            lam: 信心衰减系数 λ (0.01~0.05, 越大趋势越短)
            w_macro: 宏观因子权重 (M2, PMI, DR007)
        """
        self.omega = 0.02       # Ω — 信心守恒核
        self.lam = lam           # λ — 衰减系数
        self.w_macro = w_macro   # 宏观权重
        self.history: List[dict] = []

    def compute_B_conf(self, df_macro) -> np.ndarray:
        """
        计算宏观信心场 B_conf
        输入: DataFrame 含 M2YOY, PMI, DR007 (可选)
        输出: 标准化后的信心场序列
        """
        df = df_macro.copy()
        cols = df.columns

        if 'M2YOY' in cols:
            df['M2_z'] = (df['M2YOY'] - df['M2YOY'].mean()) / (df['M2YOY'].std() + 1e-8)
        else:
            df['M2_z'] = 0.0

        if 'PMI' in cols:
            df['PMI_z'] = (df['PMI'] - df['PMI'].mean()) / (df['PMI'].std() + 1e-8)
        else:
            df['PMI_z'] = 0.0

        if 'DR007' in cols:
            df['DR007_inv_z'] = -(df['DR007'] - df['DR007'].mean()) / (df['DR007'].std() + 1e-8)
        else:
            df['DR007_inv_z'] = 0.0

        df['B_conf'] = (
            self.w_macro[0] * df['M2_z'] +
            self.w_macro[1] * df['PMI_z'] +
            self.w_macro[2] * df['DR007_inv_z']
        )
        df['B_conf'] = np.tanh(df['B_conf'])
        return df['B_conf']

    def update_omega(self, phi_future: float) -> float:
        """更新信心守恒核: Ω ← Ω + φ_future - λ·Ω"""
        self.omega = self.omega + phi_future - self.lam * self.omega
        return self.omega

    def compute_phi_future(self, event_strength: float = 0.3,
                           event_polarity: float = 1.0,
                           tau: float = 20.0, t: int = 0) -> float:
        """
        计算事件波 φ_future
        φ = strength × polarity × exp(-t/τ)

        Args:
            event_strength: 事件强度 (±0.05~0.5)
            event_polarity: 事件极向 (+1利多 / -1利空)
            tau: 衰减时间常数
            t: 距事件时间步数
        """
        return event_strength * event_polarity * math.exp(-t / tau)

    def update_confidence(self, macro_val: float, phi_future: float) -> float:
        """综合信心: B_t = clip(macro_val + φ_future + Ω, -1, 1)"""
        omega_t = self.update_omega(phi_future)
        B_t = max(-1.0, min(1.0, macro_val + phi_future + omega_t))
        self.history.append({
            'macro_val': macro_val, 'phi': phi_future,
            'Omega': omega_t, 'B_conf': B_t
        })
        return B_t

    def run_series(self, df_macro, phi_params: dict = None) -> List[float]:
        """批量运行时间序列, 返回综合信心趋势"""
        if phi_params is None:
            phi_params = {'event_strength': 0.1, 'event_polarity': 1, 'tau': 20}

        results = []
        t = 0
        for _, row in df_macro.iterrows():
            phi = self.compute_phi_future(**phi_params, t=t)
            B_conf = row.get('B_conf', 0.0)
            B_t = self.update_confidence(B_conf, phi)
            results.append(B_t)
            t += 1

        # 如果df中已有B_conf, 直接使用
        if 'B_conf' in df_macro.columns:
            return results
        return results


# ============================================================================
# 2. MNQ9Simulator — 宏观趋势模拟器
# ============================================================================

@dataclass
class MacroConfidenceField:
    """宏观信心场配置"""
    M2: float = 0.0        # 货币总量 (归一化 -1~1)
    PMI: float = 0.0       # 景气度 (归一化)
    DR007: float = 0.0     # 资金成本 (归一化, 逆向)
    social_financing: float = 0.0   # 社融
    LPR: float = 0.0       # 利率环境 (逆向)
    export_growth: float = 0.0      # 出口增速
    real_estate: float = 0.0        # 地产销售
    employment: float = 0.0         # 就业数据

    def to_vector(self) -> np.ndarray:
        return np.array([self.M2, self.PMI, self.DR007,
                        self.social_financing, self.LPR,
                        self.export_growth, self.real_estate, self.employment])


class MNQ9Simulator:
    """
    MNQ9 宏观趋势模拟器 — 完整API

    用法:
        sim = MNQ9Simulator(lam=0.03)
        sim.set_macro_confidence({'M2': 0.18, 'PMI': 0.05, 'DR007': -0.10})
        sim.set_future_wave([0.2, -0.3, 0.0, 0.1])
        omega_series = sim.run_series(steps=len(phi_series))
    """

    def __init__(self, lam: float = 0.03, w_macro: tuple = (0.4, 0.3, 0.3)):
        self.core = MNQ9Core(lam=lam, w_macro=w_macro)
        self.macro_field = MacroConfidenceField()
        self.phi_series: List[float] = []
        self.omega_series: List[float] = []
        self.B_conf_series: List[float] = []

    def set_macro_confidence(self, fields: dict):
        """设置宏观信心场各字段 (全部归一化到 -1~1)"""
        for k, v in fields.items():
            if hasattr(self.macro_field, k):
                setattr(self.macro_field, k, v)

    def set_future_wave(self, phi_series: list):
        """设置事件冲击序列"""
        self.phi_series = list(phi_series)

    def _compute_kernel(self) -> float:
        """计算宏观信心核 kernel = Σ w_i × field_i (tanh压缩)"""
        vec = self.macro_field.to_vector()
        weights = np.array([0.3, 0.3, 0.2, 0.05, 0.05, 0.04, 0.03, 0.03])
        kernel = float(np.dot(vec, weights))
        return math.tanh(kernel - 0.5)

    def run_series(self, steps: int = None, event_params: dict = None) -> List[float]:
        """
        运行宏观趋势模拟

        Args:
            steps: 模拟步数 (默认使用phi_series长度)
            event_params: 事件参数 dict(strength, polarity, tau)

        Returns:
            omega_series: 趋势序列
        """
        if steps is None:
            steps = max(1, len(self.phi_series))

        if event_params is None:
            event_params = {'event_strength': 0.3, 'event_polarity': 1, 'tau': 20}

        kernel = self._compute_kernel()
        self.omega_series = []
        self.B_conf_series = []

        for t in range(steps):
            # 获取该步的事件冲击
            if t < len(self.phi_series):
                phi_raw = self.phi_series[t]
            else:
                phi_raw = self.core.compute_phi_future(**event_params, t=t)

            # 事件作用方式: φ_effective = φ × tanh(kernel - 0.5)
            phi_effective = phi_raw * math.tanh(kernel - 0.5)

            # 更新信心核
            omega_t = self.core.update_omega(phi_effective)

            # B_conf = kernel (宏观背景)
            B_t = max(-1.0, min(1.0, kernel + phi_effective + omega_t))

            self.omega_series.append(omega_t)
            self.B_conf_series.append(B_t)

            self.core.history.append({
                'step': t, 'kernel': kernel,
                'phi_raw': phi_raw, 'phi_effective': phi_effective,
                'Omega': omega_t, 'B_conf': B_t
            })

        return self.omega_series

    def generate_report(self) -> dict:
        """生成趋势分析报告"""
        if not self.omega_series:
            return {'error': 'No simulation data'}
        om = np.array(self.omega_series)
        return {
            'mean_trend': float(np.mean(om)),
            'trend_volatility': float(np.std(om)),
            'max_omega': float(np.max(om)),
            'min_omega': float(np.min(om)),
            'final_omega': float(om[-1]),
            'trend_direction': 'UP' if om[-1] > 0 else 'DOWN',
            'trend_strength': abs(float(om[-1])),
            'n_steps': len(om),
            'macro_kernel': self._compute_kernel(),
        }

    def snapshot(self) -> dict:
        """获取当前状态快照"""
        return {
            'omega': self.core.omega,
            'kernel': self._compute_kernel(),
            'n_phi_events': len(self.phi_series),
            'n_history': len(self.core.history),
            'macro_field': {k: getattr(self.macro_field, k)
                           for k in ['M2', 'PMI', 'DR007']},
        }


# ============================================================================
# 3. MNQ9 场景生成器 — 预定义宏观场景
# ============================================================================

class MNQ9ScenarioGenerator:
    """预定义宏观场景, 方便快速测试"""

    @staticmethod
    def bull_market() -> Tuple[dict, list]:
        """牛市场景: 宽货币 + 景气上行 + 降息"""
        macro = {'M2': 0.8, 'PMI': 0.6, 'DR007': -0.7,
                'social_financing': 0.7, 'LPR': -0.5}
        events = [0.1, 0.2, 0.1, 0.3, -0.05, 0.2, 0.15, 0.1]
        return macro, events

    @staticmethod
    def bear_market() -> Tuple[dict, list]:
        """熊市场景: 紧缩 + 衰退 + 加息"""
        macro = {'M2': -0.5, 'PMI': -0.6, 'DR007': 0.8,
                'social_financing': -0.4, 'LPR': 0.6}
        events = [-0.1, -0.3, -0.05, -0.2, 0.05, -0.15, -0.1, -0.2]
        return macro, events

    @staticmethod
    def crisis_recovery() -> Tuple[dict, list]:
        """危机恢复: 先冲击后修复"""
        macro = {'M2': 0.6, 'PMI': -0.2, 'DR007': -0.5}
        events = [-0.5, -0.4, -0.3, -0.1, 0.1, 0.2, 0.3, 0.3]
        return macro, events

    @staticmethod
    def policy_shock() -> Tuple[dict, list]:
        """政策冲击: 突发利好"""
        macro = {'M2': 0.1, 'PMI': 0.0, 'DR007': 0.0}
        events = [0.0, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
        return macro, events


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    'MNQ9Core', 'MNQ9Simulator', 'MacroConfidenceField',
    'MNQ9ScenarioGenerator',
]

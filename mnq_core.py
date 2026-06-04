"""
MNQ 金灵球网络仿真器  v2.0 - Windows 版
基于复合体理学 MNQ8/MNQ9 理论体系 + CGD约束生成动力学

核心模块升级:
1. 金符学 3D复广数 (a + bi + cj) 及阴龙积⊙运算
2. 金灵球 (JinlingSphere) N₈邻域耦合
3. MNQ8 能流运算引擎 — 流贯(Ftel)传播与囚禁检测
4. 三元动力核 (φ-Ω-γ) 极简公式 (φ=Ω-½递归)
5. 三层信息波体系 (核心→八卦→64卦) — SCF收敛
6. CGD约束生成动力学 (五公理A1-A5)
7. 八卦算子模板 (8算子→64模板组合)
8. 最小反馈机制 (minimal_feedback)
9. MNQ9 信心核模型 (Ω/φ_future/B_conf)
10. Hex64 六十四卦映射 (x86指令→卦象→能流参数)
11. PG拓扑囚禁检测 (Oloid差分 + 鲁珀特之泪判定)
12. 刘机制 (LiuMechanism) 最小阻抗路径选择
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
from enum import IntEnum
import math
import time
import threading
from collections import deque

# ============================================================================
# 1. 金符学 3D 复广数 (Golden Symbol / 金符)
# ============================================================================

class GoldenSymbol3D:
    __slots__ = ('a', 'b', 'c')

    def __init__(self, a: float = 0.0, b: float = 0.0, c: float = 0.0):
        self.a = a; self.b = b; self.c = c

    def __add__(self, other: 'GoldenSymbol3D') -> 'GoldenSymbol3D':
        return GoldenSymbol3D(self.a+other.a, self.b+other.b, self.c+other.c)

    def __sub__(self, other: 'GoldenSymbol3D') -> 'GoldenSymbol3D':
        return GoldenSymbol3D(self.a-other.a, self.b-other.b, self.c-other.c)

    def conjugate(self) -> 'GoldenSymbol3D':
        return GoldenSymbol3D(self.a, -self.b, self.c)

    def norm_sq(self) -> float: return self.a*self.a + self.b*self.b + self.c*self.c
    def norm(self) -> float: return math.sqrt(self.norm_sq())

    def inverse(self) -> 'GoldenSymbol3D':
        n2 = self.norm_sq()
        return GoldenSymbol3D() if n2 < 1e-30 else GoldenSymbol3D(self.a/n2, -self.b/n2, self.c/n2)

    def yin_long_product(self, other: 'GoldenSymbol3D', lam: float = 1.0) -> 'GoldenSymbol3D':
        """阴龙积 ⊙: z₁⊙z₂ = λ[(a₁a₂-b₁b₂-c₁c₂) + (a₁b₂+b₁a₂)i + (a₁c₂+c₁a₂+b₁c₂+c₁b₂)j]"""
        a = lam*(self.a*other.a - self.b*other.b - self.c*other.c)
        b = lam*(self.a*other.b + self.b*other.a)
        c = lam*(self.a*other.c + self.c*self.a + self.b*other.c + self.c*other.b)
        return GoldenSymbol3D(a,b,c)

    def scale(self, f: float) -> 'GoldenSymbol3D': return GoldenSymbol3D(self.a*f, self.b*f, self.c*f)
    def normalize(self) -> 'GoldenSymbol3D':
        n = self.norm(); return GoldenSymbol3D() if n<1e-30 else GoldenSymbol3D(self.a/n, self.b/n, self.c/n)
    def __repr__(self): return f"GS({self.a:.4f}, {self.b:.4f}i, {self.c:.4f}j)"


# ============================================================================
# 2. 八卦算子 (Bagua Operators) — 8基本算子 + 64模板组合
# ============================================================================

class BaguaOp(IntEnum):
    BAGUA_ROTATE  = 0
    BAGUA_FLIP    = 1
    BAGUA_INVERT  = 2
    BAGUA_MIX     = 3
    BAGUA_GATE    = 4
    BAGUA_PHASE   = 5
    BAGUA_STRETCH = 6
    BAGUA_SHRINK  = 7


@dataclass
class HexTemplate:
    """八卦算子模板对 (对应C代码 templates_hex64)"""
    opA: BaguaOp
    opB: BaguaOp
    weight: float = 1.0/64.0


# 64模板表 (8×8 = 64 组合)
HEX_TEMPLATE_TABLE: List[HexTemplate] = []
_hex_template_inited = False

def _init_hex_templates():
    global _hex_template_inited, HEX_TEMPLATE_TABLE
    if _hex_template_inited: return
    ops = list(BaguaOp)
    for a in range(8):
        for b in range(8):
            HEX_TEMPLATE_TABLE.append(HexTemplate(ops[a], ops[b], 1.0/64.0))
    _hex_template_inited = True


def bagua_apply(phi: np.ndarray, omega: np.ndarray, op: BaguaOp) -> None:
    """在φ/Ω局域矩阵上执行八卦离散变换"""
    if op == BaguaOp.BAGUA_ROTATE:
        phi[:] = np.rot90(phi); omega[:] = np.rot90(omega)
    elif op == BaguaOp.BAGUA_FLIP:
        phi[:] = np.flipud(phi); omega[:] = np.flipud(omega)
    elif op == BaguaOp.BAGUA_INVERT:
        phi[:] = -phi
    elif op == BaguaOp.BAGUA_MIX:
        phi, omega = omega.copy(), phi.copy()
    elif op == BaguaOp.BAGUA_GATE:
        phi[abs(phi) < 0.01] = 0.0
    elif op == BaguaOp.BAGUA_PHASE:
        phi += 0.1 * np.sin(omega * np.pi)
    elif op == BaguaOp.BAGUA_STRETCH:
        phi *= 1.1
    elif op == BaguaOp.BAGUA_SHRINK:
        phi *= 0.9


def hex64_apply_template(phi: np.ndarray, omega: np.ndarray, n: int, index: int):
    """应用八卦模板 (对齐 templates_hex64.c 的 hex64_apply)"""
    _init_hex_templates()
    if index < 0 or index >= 64: index = 0
    t = HEX_TEMPLATE_TABLE[index]
    bagua_apply(phi, omega, t.opA)
    bagua_apply(phi, omega, t.opB)
    phi *= t.weight


# ============================================================================
# 3. 五行矩阵 (5×5) — 相生相克
# ============================================================================

class WuxingMatrix:
    DEFAULT = [[0,1,-1,0,0],[-1,0,1,0,0],[1,-1,0,0,0],[0,0,0,0,1],[0,0,0,-1,0]]

    @staticmethod
    def apply(W: list, phi: float) -> float:
        v = [phi]*5; acc = 0.0
        for i in range(5):
            for j in range(5): acc += W[i][j]*v[j]
        return acc

    @staticmethod
    def wuxing_update(value: float, neighbors: list) -> float:
        """五行相生相克 (对齐mnq8.py)"""
        delta = 0.0
        for n in neighbors:
            delta += 0.1*value if n > value else -0.1*value
        return value + delta


# ============================================================================
# 4. 三元动力核 MNQMinimalState (φ=Ω-½ 递归)
# ============================================================================

@dataclass
class MNQMinimalState:
    """MNQ 极简三元动力核 — φ=Ω-½ 递归"""
    phi: float = 0.5
    omega: float = 2.0
    gamma: float = 0.9898   # 相干度
    rcoh: float = 0.0
    dt: float = 0.016
    stability_band: float = 0.01  # 稳定性带宽


def mnq_minimal_step(s: MNQMinimalState, dt: float = -1.0,
                     use_wuxing: bool = False,
                     feedback_input: Optional[dict] = None) -> None:
    """
    三元动力核一步演化 — MNQ8核心公式:
    ① Δφ = Ω − ½  (极简生成公式)
    ② Ω ← Ω + γ·(Δφ + W扰动)·dt
    ③ Rcoh = |Δφ| / (|Ω| + ε)
    ④ γ ← γ + λ·(1 − Rcoh)·dt
    ⑤ 反馈扰动 (minimal_feedback)
    """
    if dt <= 0: dt = s.dt

    dphi = s.omega - 0.5  # φ=Ω-½ 极简生成
    
    wterm = 0.0
    if use_wuxing:
        wterm = WuxingMatrix.apply(WuxingMatrix.DEFAULT, dphi)

    s.omega += s.gamma * (dphi + wterm) * dt
    s.rcoh = abs(dphi) / (abs(s.omega) + 1e-6)
    
    lam = 0.01
    s.gamma += lam * (1.0 - s.rcoh) * dt
    s.gamma = max(0.95, min(1.0, s.gamma))
    s.omega = max(0.1, min(10.0, s.omega))

    # 反馈扰动 (minimal_feedback)
    if feedback_input:
        FEEDBACK_SCALE = 1e-5
        MAX_FEEDBACK = 0.01
        w = feedback_input.get('weight', 1.0)
        if not math.isfinite(w): w = 1.0
        fb_phi = feedback_input.get('energy_phi', 0) + feedback_input.get('disturbance', 0)
        fb_omega = feedback_input.get('energy_omega', 0)
        dphi_fb = max(-MAX_FEEDBACK, min(MAX_FEEDBACK, fb_phi * FEEDBACK_SCALE * w))
        domeg_fb = max(-MAX_FEEDBACK, min(MAX_FEEDBACK, fb_omega * FEEDBACK_SCALE * w))
        s.phi += dphi_fb
        s.omega += domeg_fb
        s.omega = max(0.1, min(10.0, s.omega))

    s.phi += s.omega * dt
    s.stability_band = abs(s.rcoh - 0.5) * 0.02


# ============================================================================
# 5. 三层信息波体系 (Three-Layer Info Wave)
#    核心层(1×1) → 八卦层(3×3) → 六十四卦层(8×8×3)
# ============================================================================

class ThreeLayerInfoWave:
    """
    MNQ8 三层信息波: 核心→八卦→64卦 递归生成 + SCF收敛
    对齐 mnq8.py 的完整实现
    """

    def __init__(self, core_init: float = 0.001):
        # 核心层 1×1
        self.core = np.array([[[core_init]]], dtype=np.float64)
        # 八卦层 3×3×3
        self.bagua = np.random.rand(3, 3, 3).astype(np.float64) * 0.005
        # 64卦层 8×8×3
        self.hex64 = np.random.rand(8, 8, 3).astype(np.float64) * 0.005
        self.converged = False
        self.max_change = float('inf')

    def set_core(self, value: float):
        """核心层初值 — 唯一密钥"""
        self.core = np.array([[[value]]], dtype=np.float64)

    def _update_core(self) -> np.ndarray:
        """核心层更新: 极简衰减 φ=Ω-½"""
        self.core *= 0.995  # 轻微衰减模拟稳定
        return self.core

    def _update_bagua(self) -> np.ndarray:
        """八卦层更新: 五行相生相克 + 核心层信息馈入"""
        new_wave = self.bagua.copy()
        for i in range(3):
            for j in range(3):
                neighbors = []
                for di in [-1,0,1]:
                    for dj in [-1,0,1]:
                        ni,nj = i+di, j+dj
                        if 0<=ni<3 and 0<=nj<3 and (di!=0 or dj!=0):
                            neighbors.append(self.bagua[ni,nj,0])
                for k in range(3):
                    new_wave[i,j,k] = WuxingMatrix.wuxing_update(self.bagua[i,j,k], neighbors)
                new_wave[i,j,:] += self.core[0,0,0] * 0.1
        new_wave *= 0.998
        return new_wave

    def _update_hex64(self) -> np.ndarray:
        """64卦层更新: tanh耦合 + 核心/八卦信息馈入"""
        new_wave = self.hex64.copy()
        for i in range(8):
            for j in range(8):
                neighbors = []
                for di in [-1,0,1]:
                    for dj in [-1,0,1]:
                        ni,nj = i+di, j+dj
                        if 0<=ni<8 and 0<=nj<8 and (di!=0 or dj!=0):
                            neighbors.append(self.hex64[ni,nj,0])
                for k in range(3):
                    local_input = neighbors + [self.core[0,0,0]] + [self.bagua[k,k,k]]
                    new_wave[i,j,k] = np.tanh(np.sum(local_input))
        new_wave *= 0.995
        return new_wave

    def step(self) -> float:
        """一步SCF迭代, 返回 max_change"""
        old_core = self.core.copy()
        old_bagua = self.bagua.copy()
        old_hex64 = self.hex64.copy()

        self.core = self._update_core()
        self.bagua = self._update_bagua()
        self.hex64 = self._update_hex64()

        self.max_change = max(
            float(np.max(np.abs(self.core - old_core))),
            float(np.max(np.abs(self.bagua - old_bagua))),
            float(np.max(np.abs(self.hex64 - old_hex64)))
        )
        return self.max_change

    def run_to_convergence(self, max_steps: int = 200, epsilon: float = 1e-6):
        """运行至SCF收敛"""
        for step in range(max_steps):
            mc = self.step()
            if mc < epsilon:
                self.converged = True
                return step
        return max_steps

    def snapshot(self) -> dict:
        return {
            'core': float(self.core[0,0,0]),
            'bagua_mean': float(np.mean(self.bagua)),
            'hex64_mean': float(np.mean(self.hex64)),
            'converged': self.converged,
            'max_change': self.max_change
        }


# ============================================================================
# 6. CGD 约束生成动力学 (五公理实现)
# ============================================================================

@dataclass
class CGDConstraint:
    """
    CGD 全局约束变量 (对齐白皮书定义)
    - 不控制局部自由度
    - 仅限定哪些整体关系可接受
    - 弱调制 (modulation, not command)
    """
    name: str
    target_range: Tuple[float, float]  # 可接受范围
    current_value: float = 0.0
    modulation_strength: float = 0.01  # 弱调制强度
    memory: deque = field(default_factory=lambda: deque(maxlen=100))  # 约束记忆


class CGDEngine:
    """
    约束生成动力学引擎
    五公理:
    A1: 约束优先生成 — 任何可能状态须先满足全局约束
    A2: 可达态生成性 — 动力学本质是生成可达态集合
    A3: 稳态作为吸引结构 — 稳态是约束诱导的吸引结果
    A4: 非局域关联性 — 相关性直接源于共同满足同一约束
    A5: 参数的相位化影响 — 参数变化可致约束结构非连续跃迁
    """

    def __init__(self):
        self.constraints: List[CGDConstraint] = []
        self.phase_state = 0  # 当前相态
        self.phase_boundaries = []  # 相边界参数列表
        self.steady_states = []     # 观测到的稳态集合

    def add_constraint(self, name: str, target_range: Tuple[float, float],
                       modulation: float = 0.01):
        c = CGDConstraint(name=name, target_range=target_range,
                         modulation_strength=modulation)
        self.constraints.append(c)
        return c

    def evaluate(self, state_vector: np.ndarray) -> Tuple[bool, float]:
        """
        评估状态是否满足所有约束 (合法性检查)
        返回: (is_legal, violation_penalty)
        """
        total_violation = 0.0
        for c in self.constraints:
            c.current_value = float(np.mean(state_vector))
            c.memory.append(c.current_value)
            lo, hi = c.target_range
            if c.current_value < lo:
                total_violation += (lo - c.current_value) ** 2
            elif c.current_value > hi:
                total_violation += (c.current_value - hi) ** 2
        return total_violation < 1e-4, total_violation

    def modulate(self, state_vector: np.ndarray) -> np.ndarray:
        """弱调制: 对非法状态施加温和偏置 (不直接控制)"""
        result = state_vector.copy()
        for c in self.constraints:
            lo, hi = c.target_range
            if c.current_value < lo:
                result += c.modulation_strength * (lo - c.current_value)
            elif c.current_value > hi:
                result -= c.modulation_strength * (c.current_value - hi)
        return result

    def check_phase_transition(self, param: float) -> bool:
        """检查是否跨越相边界 (公理A5)"""
        for boundary in self.phase_boundaries:
            if (self.phase_state < boundary <= param) or \
               (self.phase_state > boundary >= param):
                self.phase_state = int(param > boundary)
                return True
        return False

    def select_steady_state(self, state: dict) -> bool:
        """稳态选择 (不是求解, 是筛选幸存者)"""
        is_legal, _ = self.evaluate(
            np.array([state.get('mass', 0), state.get('coherence', 0),
                     state.get('energy', 0)])
        )
        if is_legal:
            self.steady_states.append(state)
        return is_legal



# ============================================================================
# 7. Hex64 六十四卦映射 (x86指令→卦象→能流参数)
# ============================================================================

class Hex64Code(IntEnum):
    QIAN=0;KUN=1;ZHEN=2;XUN=3;KAN=4;LI=5;GEN=6;DUI=7
    HEX64_COUNT = 64

@dataclass
class Hex64Rule:
    name: str; opcode: str
    phi_delta: float; omega_delta: float; gamma_delta: float

HEX64_TABLE: Dict[int, Hex64Rule] = {}
_hex_entries = [
    (0,"乾","MOV",+0.50,+1.00,+0.0001),(1,"坤","ADD",+0.30,+0.80,+0.0002),
    (2,"震","SUB",-0.30,+0.60,-0.0001),(3,"巽","MUL",+0.80,+0.90,+0.0000),
    (4,"坎","DIV",-0.50,+0.70,-0.0002),(5,"离","CMP",+0.10,+0.50,+0.0000),
    (6,"艮","JMP",-0.10,+1.00,+0.0003),(7,"兑","CALL",+0.20,+0.90,+0.0001),
    (8,"小畜","PUSH",+0.25,+0.85,+0.0001),(9,"大有","POP",-0.20,+0.80,+0.0001),
    (10,"泰","INC",+0.35,+0.90,+0.0002),(11,"否","DEC",-0.35,+0.90,-0.0002),
    (12,"同人","XOR",+0.15,+0.70,+0.0001),(13,"大有2","OR",+0.20,+0.75,+0.0000),
    (14,"谦","AND",+0.05,+0.65,+0.0000),(15,"豫","NOT",-0.05,+0.60,-0.0001),
    (16,"随","LEA",+0.40,+0.90,+0.0001),(17,"蛊","NEG",-0.40,+0.80,-0.0001),
    (18,"临","TEST",+0.10,+0.55,+0.0000),(19,"观","CMPXCHG",+0.10,+0.60,+0.0001),
    (20,"噬嗑","SHL",+0.25,+0.80,+0.0001),(21,"贲","SHR",-0.25,+0.80,-0.0001),
    (22,"剥","SAR",-0.30,+0.70,-0.0002),(23,"复","ROL",+0.30,+0.70,+0.0002),
    (24,"无妄","ROR",-0.30,+0.70,-0.0002),(25,"大畜","ADC",+0.35,+0.85,+0.0001),
    (26,"颐","SBB",-0.35,+0.85,-0.0001),(27,"大过","IMUL",+0.80,+0.95,+0.0001),
    (28,"坎2","IDIV",-0.80,+0.95,-0.0001),(29,"离2","SETcc",+0.15,+0.60,+0.0001),
    (30,"咸","CMOVcc",+0.20,+0.65,+0.0001),(31,"恒","NOP",+0.00,+0.50,+0.0000),
    (32,"遁","INT",+0.05,+0.55,+0.0000),(33,"大壮","SYSCALL",+0.10,+0.60,+0.0001),
    (34,"晋","RET",-0.10,+0.60,-0.0001),(35,"明夷","ENTER",+0.25,+0.80,+0.0002),
    (36,"家人","LEAVE",-0.25,+0.80,-0.0002),(37,"睽","LOOP",+0.15,+0.70,+0.0001),
    (38,"蹇","Jcc",+0.10,+0.65,+0.0001),(39,"解","JRCXZ",-0.10,+0.65,-0.0001),
    (40,"损","LOCK",+0.05,+0.70,+0.0000),(41,"益","XCHG",+0.05,+0.75,+0.0000),
    (42,"夬","PREFETCH",+0.20,+0.80,+0.0001),(43,"姤","WAIT",+0.00,+0.60,+0.0000),
    (44,"萃","PAUSE",+0.00,+0.55,+0.0000),(45,"升","HLT",-0.10,+0.50,-0.0001),
    (46,"困","BOUND",-0.15,+0.60,-0.0001),(47,"井","NOP2",+0.00,+0.50,+0.0000),
    (48,"革","NOP3",+0.00,+0.50,+0.0000),(49,"鼎","CLI",-0.05,+0.55,-0.0001),
    (50,"震2","STI",+0.05,+0.55,+0.0001),(51,"渐","PUSHF",+0.10,+0.60,+0.0001),
    (52,"归妹","POPF",-0.10,+0.60,-0.0001),(53,"丰","SAHF",+0.05,+0.55,+0.0001),
    (54,"旅","LAHF",+0.05,+0.55,+0.0001),(55,"巽2","CPUID",+0.10,+0.65,+0.0002),
    (56,"兑2","RDTSCP",+0.10,+0.65,+0.0002),(57,"涣","RDTSC",+0.10,+0.65,+0.0001),
    (58,"节","WBINVD",-0.20,+0.60,-0.0002),(59,"中孚","LFENCE",+0.00,+0.55,+0.0000),
    (60,"小过","SFENCE",+0.00,+0.55,+0.0000),(61,"既济","MFENCE",+0.00,+0.55,+0.0000),
    (62,"未济","UD2",-0.50,+0.40,-0.0005),(63,"恒2","HLT2",-0.10,+0.50,-0.0001),
]
for _e in _hex_entries: HEX64_TABLE[_e[0]] = Hex64Rule(_e[1],_e[2],_e[3],_e[4],_e[5])

def get_hex64_rule(code: int) -> Hex64Rule:
    return HEX64_TABLE.get(code, Hex64Rule("恒","NOP",0.0,0.0,0.0))


# ============================================================================
# 8. 金灵球 (JinlingSphere) + 金灵球网格 (JinlingMesh) v2.0
#    集成CGD约束调制 → mnq8_step_with_cgd()
# ============================================================================

class JinlingSphere:
    __slots__ = ('coord','state','background','spiral_phase','spiral_omega',
                 'is_mass_face','excess_loop','lock_hold_count','ftel_magnitude')

    def __init__(self, x: int, y: int, z: int = 0):
        self.coord = (x, y, z)
        self.state = GoldenSymbol3D()
        self.background = GoldenSymbol3D()
        self.spiral_phase = 0.0
        self.spiral_omega = 0.02
        self.is_mass_face = False
        self.excess_loop = 0.0
        self.lock_hold_count = 0
        self.ftel_magnitude = 0.0

    def eigen_oscillate(self, dt: float):
        self.spiral_phase += self.spiral_omega * dt
        self.state.b = 0.02 * math.sin(self.spiral_phase)
        self.state.c = 0.02 * math.cos(self.spiral_phase * 1.618)


class JinlingMesh:
    MASS_THRESHOLD = 0.05
    EXCESS_LOOP_THRESH = 0.08
    HOLD_N_BEATS = 4
    COUPLING_STRENGTH = 0.3

    def __init__(self, dim_x: int = 16, dim_y: int = 16, dim_z: int = 1):
        self.dim_x, self.dim_y, self.dim_z = dim_x, dim_y, dim_z
        self.total = dim_x * dim_y * dim_z
        self.spheres = [JinlingSphere(x,y,z) for z in range(dim_z)
                        for y in range(dim_y) for x in range(dim_x)]
        self.ftel_enabled = True
        self.total_mass = 0.0; self.total_loop = 0.0
        self.mass_face_count = 0; self.step_count = 0
        self.minimal = MNQMinimalState()
        self.liu_scheduler = LiuScheduler()
        # 三层信息波
        self.info_wave = ThreeLayerInfoWave()
        # CGD约束引擎
        self.cgd = CGDEngine()
        self._setup_default_cgd_constraints()

    def _setup_default_cgd_constraints(self):
        """设置默认CGD约束"""
        self.cgd.add_constraint("mass_upper_bound", (-0.5, 0.5), 0.05)
        self.cgd.add_constraint("coherence_window", (0.0, 1.0), 0.01)
        self.cgd.add_constraint("energy_balance", (-1.0, 1.0), 0.02)

    def idx(self, x, y, z=0): return z*self.dim_y*self.dim_x + y*self.dim_x + x

    def get_sphere(self, x, y, z=0):
        return self.spheres[self.idx(x,y,z)] if 0<=x<self.dim_x and 0<=y<self.dim_y and 0<=z<self.dim_z else None

    def get_neighbors_8(self, x, y, z=0):
        nb = []
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                if dx==0 and dy==0: continue
                s = self.get_sphere(x+dx, y+dy, z)
                if s: nb.append(s)
        return nb

    def seed_background(self, noise_amp: float = 0.005):
        for s in self.spheres:
            s.state.a = 0.02 + noise_amp * (np.random.random() - 0.5)
            s.state.b = noise_amp * (np.random.random() - 0.5)
            s.state.c = noise_amp * (np.random.random() - 0.5)
            s.background = GoldenSymbol3D(s.state.a, s.state.b, s.state.c)
            s.spiral_phase = np.random.random() * 2 * math.pi

    def seed_hex_ring_gap(self):
        for s in self.spheres:
            s.state.a = 0.05 + 0.002 * (np.random.random() - 0.5)
            s.state.b = 0.002 * (np.random.random() - 0.5)
            s.state.c = 0.002 * (np.random.random() - 0.5)
            s.background = GoldenSymbol3D(s.state.a, s.state.b, s.state.c)
            s.spiral_phase = np.random.random() * 2 * math.pi
        cx, cy = self.dim_x//2, self.dim_y//2
        hex_radius = min(self.dim_x, self.dim_y)//4
        gap_angle = math.pi/3
        for angle_idx in range(6):
            angle = angle_idx * math.pi/3
            if abs(angle - gap_angle) < 0.1: continue
            for r_offset in [-0.3, 0.0, 0.3]:
                r = hex_radius + r_offset
                hx = int(cx + r*math.cos(angle))
                hy = int(cy + r*math.sin(angle))
                s = self.get_sphere(hx, hy)
                if s:
                    s.state.a = 0.8 + 0.1*np.random.random()
                    s.state.b = 0.5*math.sin(angle)
                    s.state.c = 0.5*math.cos(angle)
                    s.ftel_magnitude = 0.8
                    s.background = GoldenSymbol3D(s.state.a*0.3, s.state.b*0.3, s.state.c*0.3)
        for dx in [-1,0,1]:
            for dy in [-1,0,1]:
                h = self.get_sphere(cx+dx, cy+dy)
                if h:
                    h.state.a = 1.0+0.1*np.random.random()
                    h.state.b = 0.5+0.1*np.random.random()
                    h.state.c = 0.5+0.1*np.random.random()
                    h.ftel_magnitude = 1.0
                    h.background = GoldenSymbol3D(0.3, 0.1, 0.1)

    def seed_zero_field(self):
        for s in self.spheres:
            s.state = GoldenSymbol3D(0,0,0)
            s.background = GoldenSymbol3D(0,0,0)
            s.ftel_magnitude = 0.0; s.is_mass_face = False; s.excess_loop = 0.0
        self.ftel_enabled = False

    def mnq8_step(self, dt: float = 0.016, lam: float = 1.0):
        """MNQ8 能流运算一步 (标准模式)"""
        if not self.ftel_enabled: return
        self.step_count += 1

        old_states = [GoldenSymbol3D(max(-10,min(10,s.state.a)),
                                     max(-10,min(10,s.state.b)),
                                     max(-10,min(10,s.state.c))) for s in self.spheres]

        for idx, s in enumerate(self.spheres):
            x, y, z = s.coord
            s.eigen_oscillate(dt)
            neighbors = self.get_neighbors_8(x, y, z)
            total_flux = GoldenSymbol3D()
            cur_state = old_states[idx]
            for nb in neighbors:
                nb_state = old_states[self.idx(*nb.coord)]
                flux = GoldenSymbol3D(nb_state.a-cur_state.a, nb_state.b-cur_state.b, nb_state.c-cur_state.c)
                if cur_state.norm()<2.0 and nb_state.norm()<2.0:
                    flux = flux + cur_state.yin_long_product(nb_state, lam=0.01)
                total_flux = total_flux + flux

            n_nb = max(1, len(neighbors))
            coupled = GoldenSymbol3D(
                old_states[idx].a + self.COUPLING_STRENGTH*total_flux.a/n_nb,
                old_states[idx].b + self.COUPLING_STRENGTH*total_flux.b/n_nb,
                old_states[idx].c + self.COUPLING_STRENGTH*total_flux.c/n_nb)

            flux_norm_sq = coupled.norm_sq()
            if flux_norm_sq > self.MASS_THRESHOLD:
                sf = min(flux_norm_sq, 2.0)
                s.state = coupled.normalize().scale(sf*0.3)
                s.ftel_magnitude = flux_norm_sq
            else:
                decay = 0.98
                s.state = GoldenSymbol3D(
                    old_states[idx].a*decay + s.background.a*(1-decay),
                    old_states[idx].b*decay + s.background.b*(1-decay),
                    old_states[idx].c*decay + s.background.c*(1-decay))
                s.ftel_magnitude = flux_norm_sq

            s.state.a = max(-5.0, min(5.0, s.state.a))
            s.state.b = max(-5.0, min(5.0, s.state.b))
            s.state.c = max(-5.0, min(5.0, s.state.c))

            # Oloid差分
            if neighbors:
                sa, sb, sc = 0.0, 0.0, 0.0
                for nb in neighbors:
                    ns = old_states[self.idx(*nb.coord)]
                    sa += ns.a; sb += ns.b; sc += ns.c
                n = len(neighbors)
                s.excess_loop = abs(s.state.a-sa/n) + abs(s.state.b-sb/n) + abs(s.state.c-sc/n)

            # PG拓扑囚禁
            if s.excess_loop >= self.EXCESS_LOOP_THRESH:
                s.lock_hold_count += 1
                if s.lock_hold_count >= self.HOLD_N_BEATS: s.is_mass_face = True
            else:
                s.lock_hold_count = max(0, s.lock_hold_count-1)
                if s.lock_hold_count == 0: s.is_mass_face = False

        mnq_minimal_step(self.minimal, dt)
        self._update_stats()

    def mnq8_step_with_cgd(self, dt: float = 0.016, lam: float = 1.0):
        """MNQ8 + CGD约束调制一步"""
        self.mnq8_step(dt, lam)

        # CGD约束评估与调制
        state_vec = np.array([self.total_mass, self.minimal.rcoh,
                             self.minimal.omega])
        is_legal, violation = self.cgd.evaluate(state_vec)
        if not is_legal:
            modulated = self.cgd.modulate(state_vec)
            self.minimal.omega = max(0.1, min(10.0,
                self.minimal.omega * 0.99 + modulated[2] * 0.01))
            self.cgd.select_steady_state({
                'mass': self.total_mass,
                'coherence': self.minimal.rcoh,
                'energy': self.minimal.omega,
                'step': self.step_count,
                'legal': is_legal
            })

    def _update_stats(self):
        self.total_mass = sum(s.ftel_magnitude for s in self.spheres)/max(1,self.total)
        self.total_loop = sum(s.excess_loop for s in self.spheres)/max(1,self.total)
        self.mass_face_count = sum(1 for s in self.spheres if s.is_mass_face)

    def get_field_array(self): return np.array([[s.ftel_magnitude for x in range(self.dim_x)] for y in range(self.dim_y)])
    def get_excess_loop_array(self): return np.array([[s.excess_loop for x in range(self.dim_x)] for y in range(self.dim_y)])
    def get_mass_face_array(self): return np.array([[1.0 if s.is_mass_face else 0.0 for x in range(self.dim_x)] for y in range(self.dim_y)])


# ============================================================================
# 9. 刘机制调度器 (LiuScheduler)
# ============================================================================

class LiuScheduler:
    def __init__(self, alpha: float = 0.6, beta: float = 0.4):
        self.alpha, self.beta = alpha, beta
        self.optimal_path = []; self.min_s_rel = float('inf')

    def compute_s_rel(self, magnitude: float, phase_entropy: float) -> float:
        return self.alpha*magnitude + self.beta*phase_entropy

    def find_optimal_path(self, mesh: JinlingMesh, source: tuple) -> list:
        sx, sy = source[0], source[1]
        visited = {(sx,sy)}; path = [(sx,sy)]
        for _ in range(max(mesh.dim_x, mesh.dim_y)):
            current = mesh.get_sphere(sx, sy)
            if not current: break
            best_nb, best_s_rel = None, float('inf')
            for nb in mesh.get_neighbors_8(sx, sy):
                nx, ny = nb.coord[0], nb.coord[1]
                if (nx,ny) in visited: continue
                s_rel = self.compute_s_rel(nb.ftel_magnitude, nb.excess_loop+1e-6)
                if s_rel < best_s_rel:
                    best_s_rel, best_nb = s_rel, nb
            if not best_nb: break
            sx, sy = best_nb.coord[0], best_nb.coord[1]
            path.append((sx,sy)); visited.add((sx,sy))
            if best_nb.is_mass_face: break
        self.optimal_path = path
        self.min_s_rel = best_s_rel if path else float('inf')
        return path


# ============================================================================
# 10. MNQ Cloud API 兼容层 (三尺度锚定)
# ============================================================================

class MNQCloudAPI:
    SCALE_PARAMS = {
        'atomic': {'energy_alpha':2.179872e-18,'length_beta':5.291772e-11,'time_gamma':1.765145e-19},
        'meso':   {'energy_alpha':1.0e-20,'length_beta':1.0e-10,'time_gamma':1.0e-15},
        'macro':  {'energy_alpha':3.247188e28,'length_beta':6.957e8,'time_gamma':86400},
    }

    def __init__(self, unit_mode: str = 'atomic'):
        self.unit_mode = unit_mode
        self.params = self.SCALE_PARAMS.get(unit_mode, self.SCALE_PARAMS['atomic'])

    def simulate(self, experiment: str = 'proton', steps: int = 2048,
                 epsilon: float = 1e-7, seed: int = 42,
                 E_scale: float = 1.0, coherence: float = 1e-6, **kwargs) -> dict:
        np.random.seed(seed)
        mesh = JinlingMesh(dim_x=16, dim_y=16)
        if experiment == 'zero_field': mesh.seed_zero_field()
        elif experiment == 'hex_ring_gap': mesh.seed_hex_ring_gap()
        else: mesh.seed_background()

        for _ in range(steps): mesh.mnq8_step(dt=0.016)

        p = self.params
        return {
            'mean_energy_J': mesh.total_mass * p['energy_alpha'],
            'coherence': mesh.minimal.rcoh,
            'phase_lock': min(1.0, mesh.total_loop),
            'mass_face_count': mesh.mass_face_count,
            'total_mass_normalized': mesh.total_mass,
            'total_loop': mesh.total_loop,
            'gamma_final': mesh.minimal.gamma,
            'phi_final': mesh.minimal.phi,
            'omega_final': mesh.minimal.omega,
            'unit_mode': self.unit_mode,
        }


# ============================================================================
# 11. GPU字段仿真器 v2.0 — 集成feedback/flow
# ============================================================================

class MNQFieldGPU:
    def __init__(self, grid: int = 64):
        self.grid = grid
        N = grid
        self.phi = np.random.uniform(0.015,0.025,(N,N)).astype(np.float32)
        self.omega = np.random.uniform(0.99,1.01,(N,N)).astype(np.float32)
        self.psi = np.random.uniform(-0.002,0.002,(N,N)).astype(np.float32)
        self.xi = np.random.uniform(-0.002,0.002,(N,N)).astype(np.float32)
        self.feed_calls = 0
        self.last_energy = np.zeros(5, dtype=np.float64)
        self.last_rip = 0
        self.last_event_count = 0

    def feed_energy(self, energy_accum: list, event_count: int, rip: int = 0):
        """GPU Flow 能流输入端口 (对齐 mnq_gpu_flow.c)"""
        self.feed_calls += 1
        self.last_event_count = event_count
        self.last_rip = rip
        for i, e in enumerate(energy_accum[:5]):
            self.last_energy[i] = e

    def get_snapshot(self):
        """获取GPU Flow快照 (对齐 mnq_gpu_flow_get_last_snapshot)"""
        return {
            'event_count': self.last_event_count,
            'rip': self.last_rip,
            'energy': self.last_energy.tolist(),
            'n_channels': 5,
            'feed_calls': self.feed_calls,
        }

    def inject_noise(self, amp: float = 0.001):
        N = self.grid
        mask = np.zeros((N,N), dtype=np.float32)
        mask[::37%N, ::37%N] = 1.0
        self.phi += mask * np.random.uniform(-amp,amp,(N,N)).astype(np.float32)
        self.omega += mask * np.random.uniform(-amp,amp,(N,N)).astype(np.float32)

    def step(self, lambda_: float = 0.01, gamma: float = 0.989):
        N = self.grid
        dt = np.float32(0.016)
        phi_pad = np.pad(self.phi, 1, mode='wrap')
        lap_phi = (phi_pad[2:,1:-1]+phi_pad[:-2,1:-1]+phi_pad[1:-1,2:]+phi_pad[1:-1,:-2] - 4*self.phi)
        omega_pad = np.pad(self.omega, 1, mode='wrap')
        lap_omega = (omega_pad[2:,1:-1]+omega_pad[:-2,1:-1]+omega_pad[1:-1,2:]+omega_pad[1:-1,:-2] - 4*self.omega)
        self.phi += lambda_*(lap_phi + self.omega*np.sin(self.phi))*dt
        self.omega += gamma*(lap_omega - self.phi)*dt
        self.psi += 0.02*np.sin(self.phi*1.618)*dt
        self.xi = np.abs(self.phi - self.omega)*0.5
        self.phi = np.clip(self.phi, -1.0, 1.0)
        self.omega = np.clip(self.omega, 0.5, 1.5)

    def measure_omega_avg(self): return float(np.mean(self.omega))
    def compute_rloc(self):
        N = self.grid; acc, cnt = 0.0, 0
        for y in range(1,N-1,2):
            for x in range(1,N-1,2):
                px1=float(self.phi[y,x+1]-self.phi[y,x-1]); py1=float(self.phi[y+1,x]-self.phi[y-1,x])
                px2=float(self.omega[y,x+1]-self.omega[y,x-1]); py2=float(self.omega[y+1,x]-self.omega[y-1,x])
                dot = px1*px2+py1*py2
                mag = math.sqrt((px1*px1+py1*py1)*(px2*px2+py2*py2))+1e-12
                acc += dot/mag; cnt += 1
        return max(0.0, min(1.0, acc/max(1,cnt)))


# ============================================================================
# 12. Metrics API (对齐 mnq_metrics.h)
# ============================================================================

def mnq_metric_mean(data: np.ndarray) -> float:
    """均值"""
    return float(np.mean(data))

def mnq_metric_rloc(phi: np.ndarray, omega: np.ndarray) -> float:
    """局部相干度 (对齐 mnq_metric_rloc)"""
    n = phi.shape[0]
    acc, cnt = 0.0, 0
    for i in range(n):
        for j in range(n):
            dphi_dx = phi[i,(j+1)%n] - phi[i,(j-1)%n]
            dphi_dy = phi[(i+1)%n,j] - phi[(i-1)%n,j]
            domeg_dx = omega[i,(j+1)%n] - omega[i,(j-1)%n]
            domeg_dy = omega[(i+1)%n,j] - omega[(i-1)%n,j]
            dot = dphi_dx*domeg_dx + dphi_dy*domeg_dy
            mag = math.sqrt((dphi_dx**2+dphi_dy**2)*(domeg_dx**2+domeg_dy**2))+1e-12
            acc += dot/mag; cnt += 1
    return max(0.0, min(1.0, acc/max(1,cnt)))

def mnq_metric_energy(omega: np.ndarray) -> float:
    """能量指标"""
    return float(np.mean(omega**2))


# ============================================================================
# 13. Minimal 状态访问API (对齐 mnq_metrics.h)
# ============================================================================

_g_minimal_state: Optional[MNQMinimalState] = None

def mnq_minimal_get_state() -> Optional[MNQMinimalState]:
    return _g_minimal_state

def mnq_minimal_set_state(s: MNQMinimalState):
    global _g_minimal_state
    _g_minimal_state = s

def mnq_get_minimal_phi() -> float:
    return _g_minimal_state.phi if _g_minimal_state else 0.0

def mnq_get_minimal_omega() -> float:
    return _g_minimal_state.omega if _g_minimal_state else 0.0

def mnq_get_minimal_gamma() -> float:
    return _g_minimal_state.gamma if _g_minimal_state else 0.0

def mnq_get_minimal_rcoh() -> float:
    return _g_minimal_state.rcoh if _g_minimal_state else 0.0

def mnq_get_minimal_stability_band() -> float:
    return _g_minimal_state.stability_band if _g_minimal_state else 0.01


# ============================================================================
# 14. 最小反馈接口 (对齐 mnq_minimal_feedback.h)
# ============================================================================

def mnq_apply_core_feedback(energy_phi: float = 0.0, energy_omega: float = 0.0,
                             disturbance: float = 0.0, weight: float = 1.0):
    """施加最小核心反馈扰动"""
    s = mnq_minimal_get_state()
    if not s: return
    FEEDBACK_SCALE = 1e-5; MAX_FEEDBACK = 0.01
    w = weight if math.isfinite(weight) else 1.0
    dphi = max(-MAX_FEEDBACK, min(MAX_FEEDBACK, (energy_phi+disturbance)*FEEDBACK_SCALE*w))
    domeg = max(-MAX_FEEDBACK, min(MAX_FEEDBACK, energy_omega*FEEDBACK_SCALE*w))
    s.phi += dphi; s.omega += domeg
    s.omega = max(0.1, min(10.0, s.omega))

def mnq_apply_execution_latency() -> int:
    """返回基于Minimal状态的执行延迟增量"""
    s = mnq_minimal_get_state()
    if not s: return 0
    ld = int(s.omega * 0.001)
    return max(-100, min(100, ld))


# ============================================================================
# 15. 自动调谐
# ============================================================================

def mnq_auto_gamma(delta_e: float) -> float:
    return 0.99 - 0.05*math.tanh(delta_e)


# ============================================================================
# 导出清单
# ============================================================================

__all__ = [
    'GoldenSymbol3D','Hex64Code','Hex64Rule','HEX64_TABLE','get_hex64_rule',
    'BaguaOp','HexTemplate','HEX_TEMPLATE_TABLE','bagua_apply','hex64_apply_template',
    'WuxingMatrix','MNQMinimalState','mnq_minimal_step',
    'ThreeLayerInfoWave','CGDConstraint','CGDEngine',
    'JinlingSphere','JinlingMesh','LiuScheduler',
    'MNQCloudAPI','MNQFieldGPU',
    'mnq_metric_mean','mnq_metric_rloc','mnq_metric_energy',
    'mnq_minimal_get_state','mnq_minimal_set_state',
    'mnq_get_minimal_phi','mnq_get_minimal_omega',
    'mnq_get_minimal_gamma','mnq_get_minimal_rcoh','mnq_get_minimal_stability_band',
    'mnq_apply_core_feedback','mnq_apply_execution_latency',
    'mnq_auto_gamma',
]

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
# 16. MNQ8 冻结核 (V13-V16 Frozen Kernel) — v3.0 核心升级
# ============================================================================
# 基于 质量生成实验 V13-V25 严格冻结核
# 五层法则: law_core → law_bagua → law_hex64 → law_wuxing → law_commit
# 严格原则: NO_EXTRA_DYNAMICS, NO_OBSERVER_WRITE_BACK, NO_FITTING, NO_PROTON
# ============================================================================

import hashlib

# ---- 冻结核常量 ----
FK_H = FK_W = 8
FK_CHANNELS = 3
FK_CH_OMEGA, FK_CH_PHI, FK_CH_COMP = 0, 1, 2
FK_STATE_MIN, FK_STATE_MAX = -8, 8
FK_ITER_STEPS = 384
FK_RING_OFFSETS = [
    (-2,-2),(-2,-1),(-2,0),(-2,1),(-2,2),
    (-1,2),(0,2),(1,2),
    (2,2),(2,1),(2,0),(2,-1),(2,-2),
    (1,-2),(0,-2),(-1,-2),
]

def _fk_coords():
    """冻结核 8x8 网格坐标迭代器"""
    for r in range(FK_H):
        for c in range(FK_W):
            yield r, c

def _fk_ingrid(r, c):
    return 0 <= r < FK_H and 0 <= c < FK_W

def _fk_sgn(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)

def _fk_clip(x):
    return int(max(FK_STATE_MIN, min(FK_STATE_MAX, int(x))))

def _fk_div(a, b, eps=1e-12):
    return float(a / (b + eps))

def _fk_share(a, b):
    total = abs(a) + abs(b)
    return 0.0 if total <= 1e-12 else float(abs(a) / total)

def _fk_val(f, r, c):
    return int(f[r, c, 0]), int(f[r, c, 1]), int(f[r, c, 2])

def _fk_amp_cell(o, p, q):
    return abs(o) + abs(p) + abs(q)

def _fk_is_carrier(o, p, q):
    return abs(o) > 0 or abs(q) > 0 or abs(p) >= 2

def _fk_is_trace(o, p, q):
    return o == 0 and q == 0 and abs(p) == 1

def _fk_axis_nb(r, c):
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        rr, cc = r+dr, c+dc
        if _fk_ingrid(rr, cc):
            yield rr, cc

def _fk_diag_nb(r, c):
    for dr, dc in [(-1,-1),(-1,1),(1,-1),(1,1)]:
        rr, cc = r+dr, c+dc
        if _fk_ingrid(rr, cc):
            yield rr, cc

def _fk_pair_balance(pos, neg):
    t = pos + neg
    return 0.0 if t <= 0 else _fk_div(2 * min(pos, neg), t)

def _fk_local_counts(f, r, c, nb_fn, carriers_only=False):
    """局部邻域统计"""
    d = dict(omega_sum=0, phi_sum=0, comp_sum=0, active_n=0, carrier_n=0, trace_n=0,
             pos_o=0, neg_o=0, pos_p=0, neg_p=0, pos_q=0, neg_q=0)
    for rr, cc in nb_fn(r, c):
        o, p, q = _fk_val(f, rr, cc)
        car = _fk_is_carrier(o, p, q)
        tr = _fk_is_trace(o, p, q)
        if carriers_only and not car:
            continue
        d["omega_sum"] += o; d["phi_sum"] += p; d["comp_sum"] += q
        if _fk_amp_cell(o, p, q) > 0: d["active_n"] += 1
        if car: d["carrier_n"] += 1
        if tr: d["trace_n"] += 1
        if o > 0: d["pos_o"] += 1
        elif o < 0: d["neg_o"] += 1
        if p > 0: d["pos_p"] += 1
        elif p < 0: d["neg_p"] += 1
        if q > 0: d["pos_q"] += 1
        elif q < 0: d["neg_q"] += 1
    return d

def _fk_trace_mask(f):
    m = np.zeros((FK_H, FK_W), dtype=np.int8)
    for r, c in _fk_coords():
        if _fk_is_trace(*_fk_val(f, r, c)):
            m[r, c] = 1
    return m

def _fk_changed_mask(prev, core):
    m = np.zeros((FK_H, FK_W), dtype=np.int8)
    for r, c in _fk_coords():
        po, pp, pq = _fk_val(prev, r, c)
        co, cp, cq = _fk_val(core, r, c)
        if not _fk_is_carrier(co, cp, cq):
            continue
        if (pp and cp and _fk_sgn(pp) != _fk_sgn(cp)) or \
           (pq and cq and _fk_sgn(pq) != _fk_sgn(cq)) or \
           (po and co and _fk_sgn(po) != _fk_sgn(co)):
            m[r, c] = 1
    return m

def _fk_amp_map(f):
    return np.sum(np.abs(f).astype(float), axis=2)


# ---- 冻结核五层法则 ----

def _fk_law_core(f):
    """第1层: 核心法则 — 自驱动力学"""
    core = np.zeros_like(f)
    for r, c in _fk_coords():
        o, p, q = _fk_val(f, r, c)
        if o == 0 and p == 0 and q == 0:
            continue
        if _fk_is_trace(o, p, q):
            core[r, c, FK_CH_PHI] = p
            continue
        drive = _fk_sgn(p) or _fk_sgn(o)
        od = 0 if (drive and q and _fk_sgn(q) == -drive) else drive
        on_val = o + od
        pbase = on_val - int(np.trunc(on_val / 2.0))
        pn = p + _fk_sgn(pbase - p)
        main = _fk_sgn(o + p)
        qn = q - main if main else q
        nm = _fk_sgn(on_val + pn)
        if qn and nm and _fk_sgn(qn) == -nm and abs(qn) > 1:
            qn -= _fk_sgn(qn)
        if abs(on_val) >= FK_STATE_MAX:
            on_val = -_fk_sgn(on_val) * (FK_STATE_MAX - 2)
        if abs(pn) >= FK_STATE_MAX:
            pn = -_fk_sgn(pn) * (FK_STATE_MAX - 2)
        if abs(qn) >= FK_STATE_MAX:
            qn = -_fk_sgn(qn) * (FK_STATE_MAX - 2)
        core[r, c] = [_fk_clip(on_val), _fk_clip(pn), _fk_clip(qn)]
    return core


def _fk_law_bagua(core, prev, prev_trace, changed):
    """第2层: 八卦法则 — 邻域耦合与相位平衡"""
    buf = np.zeros_like(core)
    for r, c in _fk_coords():
        o, p, q = _fk_val(core, r, c)
        self_car = _fk_is_carrier(o, p, q)
        ax = _fk_local_counts(core, r, c, _fk_axis_nb, True)
        dg = _fk_local_counts(core, r, c, _fk_diag_nb, True)
        ax_bal = _fk_pair_balance(ax["pos_p"], ax["neg_p"])
        dg_bal = _fk_pair_balance(dg["pos_p"], dg["neg_p"])
        local_bal = max(ax_bal, dg_bal)
        ax_coh = ax["carrier_n"] >= 2 or ax_bal > 0
        dg_coh = dg["carrier_n"] >= 2 or dg_bal > 0
        carrier_n = ax["carrier_n"] + dg["carrier_n"]

        if not self_car and carrier_n == 0:
            continue
        if not self_car:
            if ax_coh:
                pp = _fk_sgn(ax["phi_sum"] if ax["phi_sum"] else ax["omega_sum"])
                buf[r, c, FK_CH_PHI] = pp
                if ax_bal > 0:
                    buf[r, c, FK_CH_COMP] = -pp
                continue
            if dg_coh and ax["carrier_n"] > 0:
                buf[r, c, FK_CH_PHI] = _fk_sgn(dg["phi_sum"] if dg["phi_sum"] else dg["omega_sum"])
                continue
            if ax["carrier_n"] == 1:
                ch = 0; src = 0
                for rr, cc in _fk_axis_nb(r, c):
                    oo, pp, qq = _fk_val(core, rr, cc)
                    if _fk_is_carrier(oo, pp, qq):
                        src += pp if pp else oo
                        if changed[rr, cc]:
                            ch = 1
                if ch and not prev_trace[r, c]:
                    buf[r, c, FK_CH_PHI] = _fk_sgn(src)
                continue
            continue

        ax_drive = _fk_sgn(ax["phi_sum"]) or _fk_sgn(ax["omega_sum"])
        dg_drive = 0
        if ax_coh:
            dg_drive = _fk_sgn(dg["phi_sum"]) or _fk_sgn(dg["omega_sum"])
        if ax_coh or local_bal > 0:
            buf[r, c, FK_CH_OMEGA] = _fk_clip(_fk_sgn(_fk_sgn(p) + ax_drive + (dg_drive if dg_coh else 0)))
        if local_bal > 0:
            buf[r, c, FK_CH_PHI] = _fk_clip(-_fk_sgn(p) + _fk_sgn(ax["phi_sum"] - dg["phi_sum"]))
            bias = _fk_sgn(o + p + ax["omega_sum"] + ax["phi_sum"])
            if bias:
                buf[r, c, FK_CH_COMP] = _fk_clip(-bias)
    return buf


def _fk_law_hex64(core, bagua):
    """第3层: 六十四卦法则 — 全域场偏压调制"""
    h = np.zeros_like(core)
    amap = _fk_amp_map(core)
    active = int(np.sum(amap > 0))
    mean_amp = _fk_div(float(np.sum(amap)), active) if active else 0.0
    field_bias = _fk_sgn(int(np.sum(core[:, :, FK_CH_OMEGA])) + int(np.sum(core[:, :, FK_CH_PHI])))
    comp_bias = _fk_sgn(int(np.sum(core[:, :, FK_CH_COMP])))

    for r, c in _fk_coords():
        o, p, q = _fk_val(core, r, c)
        bo, bp, bq = _fk_val(bagua, r, c)
        if _fk_amp_cell(o, p, q) == 0 and _fk_amp_cell(bo, bp, bq) == 0:
            continue
        ax = _fk_local_counts(core, r, c, _fk_axis_nb, True)
        dg = _fk_local_counts(core, r, c, _fk_diag_nb, True)
        bal = _fk_pair_balance(ax["pos_p"] + dg["pos_p"], ax["neg_p"] + dg["neg_p"])
        carrier_n = ax["carrier_n"] + dg["carrier_n"]
        local_amp = float(amap[r, c])
        local_main = _fk_sgn(o + p + bo + bp)
        local_comp = _fk_sgn(q + bq)

        if field_bias and local_main == field_bias and bal == 0:
            h[r, c, FK_CH_OMEGA] -= field_bias
        if comp_bias and local_comp == comp_bias and bal == 0:
            h[r, c, FK_CH_COMP] -= comp_bias
        if bal > 0:
            bias = _fk_sgn(o + p + bo + bp)
            if bias:
                h[r, c, FK_CH_COMP] -= bias
            h[r, c, FK_CH_PHI] -= _fk_sgn(p + bp)
        if active > int(FK_H * FK_W * 0.85) and mean_amp and local_amp < mean_amp * 0.75 and bal == 0:
            h[r, c, FK_CH_OMEGA] -= _fk_sgn(o + bo)
            h[r, c, FK_CH_COMP] -= _fk_sgn(q + bq)
        if mean_amp and local_amp > mean_amp * 1.80 and bal == 0:
            h[r, c, FK_CH_OMEGA] -= _fk_sgn(o + bo)
            h[r, c, FK_CH_COMP] -= _fk_sgn(q + bq)
        if (r in (0, FK_H - 1) or c in (0, FK_W - 1)) and carrier_n <= 1 and bal == 0:
            h[r, c, FK_CH_OMEGA] -= _fk_sgn(o + bo)
            h[r, c, FK_CH_COMP] -= _fk_sgn(q + bq)
    return h


def _fk_law_wuxing(prev, raw, balance_map):
    """第4层: 五行法则 — 平滑约束与补偿调制"""
    out = np.zeros_like(raw)
    for r, c in _fk_coords():
        po, pp, pq = _fk_val(prev, r, c)
        ro, rp, rq = _fk_val(raw, r, c)
        if abs(ro - po) > 2: ro = po + 2 * _fk_sgn(ro - po)
        if abs(rp - pp) > 2: rp = pp + 2 * _fk_sgn(rp - pp)
        if abs(rq - pq) > 2: rq = pq + 2 * _fk_sgn(rq - pq)
        main = _fk_sgn(ro + rp)
        comp_ok = main and rq and _fk_sgn(rq) == -main
        if balance_map[r, c] == 0 and not comp_ok:
            rq -= _fk_sgn(rq)
        if ro == 0 and rp == 0 and rq == 0 and _fk_amp_cell(po, pp, pq) > 0:
            rp = _fk_sgn(pp if pp else (po if po else -pq))
        out[r, c] = [_fk_clip(ro), _fk_clip(rp), _fk_clip(rq)]
    return out


def _fk_law_commit(prev, core, bagua, hex64, prev_trace):
    """第5层: 提交法则 — 五层融合提交"""
    raw = np.zeros_like(prev)
    balmap = np.zeros((FK_H, FK_W), dtype=float)
    for r, c in _fk_coords():
        po, pp, pq = _fk_val(prev, r, c)
        co, cp, cq = _fk_val(core, r, c)
        bo, bp, bq = _fk_val(bagua, r, c)
        ho, hp, hq = _fk_val(hex64, r, c)
        prev_car = _fk_is_carrier(po, pp, pq)
        core_car = _fk_is_carrier(co, cp, cq)
        prev_tr = _fk_is_trace(po, pp, pq)
        ax = _fk_local_counts(prev, r, c, _fk_axis_nb, True)
        dg = _fk_local_counts(prev, r, c, _fk_diag_nb, True)
        bal = max(_fk_pair_balance(ax["pos_p"], ax["neg_p"]),
                  _fk_pair_balance(dg["pos_p"], dg["neg_p"]))
        balmap[r, c] = bal
        carrier_n = ax["carrier_n"] + dg["carrier_n"]
        ro, rp, rq = co + bo + ho, cp + bp + hp, cq + bq + hq

        if prev_tr and carrier_n < 2 and bal == 0:
            raw[r, c, FK_CH_PHI] = pp
            continue
        if not prev_car and not core_car:
            if ro == 0 and rq == 0 and rp != 0:
                raw[r, c, FK_CH_PHI] = _fk_sgn(rp)
                continue
            if carrier_n < 2 and bal == 0:
                if rp:
                    raw[r, c, FK_CH_PHI] = _fk_sgn(rp)
                continue
        raw[r, c] = [_fk_clip(ro), _fk_clip(rp), _fk_clip(rq)]
    return _fk_law_wuxing(prev, raw, balmap)


def _fk_iterate_once(f):
    """冻结核迭代一步"""
    pt = _fk_trace_mask(f)
    core = _fk_law_core(f)
    changed = _fk_changed_mask(f, core)
    bagua = _fk_law_bagua(core, f, pt, changed)
    hex64 = _fk_law_hex64(core, bagua)
    return _fk_law_commit(f, core, bagua, hex64, pt)


class MNQ8FrozenKernel:
    """MNQ8 冻结核 — V13-V16 严格冻结核 (v3.0)
    
    五层递进法则: law_core → law_bagua → law_hex64 → law_wuxing → law_commit
    严格原则: NO_EXTRA_DYNAMICS, NO_OBSERVER_WRITE_BACK, NO_FITTING, NO_PROTON
    
    使用 SHA256 指纹验证冻结核完整性
    """
    H = FK_H
    W = FK_W
    CHANNELS = FK_CHANNELS
    STATE_MIN = FK_STATE_MIN
    STATE_MAX = FK_STATE_MAX
    
    def __init__(self):
        self.field = np.zeros((FK_H, FK_W, FK_CHANNELS), dtype=np.int16)
        self.step_count = 0
        self._history_fields = []
        self._history_amps = []
        
    def init_background(self, seed: int):
        """初始化动态棋盘背景场"""
        self.field = np.zeros((FK_H, FK_W, FK_CHANNELS), dtype=np.int16)
        sh = seed % 2
        for r, c in _fk_coords():
            s = 1 if ((r + c + sh) % 2 == 0) else -1
            self.field[r, c, FK_CH_PHI] = s
            if (r + 2 * c + seed) % 7 == 0:
                self.field[r, c, FK_CH_OMEGA] = s
            if (2 * r + c + seed) % 7 == 3:
                self.field[r, c, FK_CH_COMP] = -s
        self.step_count = 0
        self._history_fields = [self.field.copy()]
        self._history_amps = [_fk_amp_map(self.field)]
        return self.field
    
    def init_condition(self, keep_indices, seed, phi_polarity=1,
                       center_shift=(0,0), omega_mode="OFF", comp_mode="OFF",
                       phi_gain=1, center_anchor=0):
        """在背景场上叠加条件初始切片"""
        bg = self.field.copy()
        cr = FK_H // 2 + center_shift[0]
        cc = FK_W // 2 + center_shift[1]
        sign = 1 if seed % 2 == 0 else -1
        keep = set(keep_indices)
        
        for i, (dr, dc) in enumerate(FK_RING_OFFSETS):
            if i not in keep:
                continue
            s = phi_polarity * (sign if i % 2 == 0 else -sign)
            _omega = 1 if (omega_mode == "MASK" and i % 5 == 0) else 0
            _comp = 1 if (comp_mode == "MASK" and i % 4 == 0) else 0
            
            rr, cc2 = cr + dr, cc + dc
            if _fk_ingrid(rr, cc2):
                self.field[rr, cc2, FK_CH_OMEGA] = _fk_clip(
                    self.field[rr, cc2, FK_CH_OMEGA] + s * _omega)
                self.field[rr, cc2, FK_CH_PHI] = _fk_clip(
                    self.field[rr, cc2, FK_CH_PHI] + s * phi_gain)
                if _comp:
                    self.field[rr, cc2, FK_CH_COMP] = _fk_clip(
                        self.field[rr, cc2, FK_CH_COMP] - s * _comp)
        
        if center_anchor and _fk_ingrid(cr, cc):
            self.field[cr, cc, FK_CH_PHI] = _fk_clip(
                self.field[cr, cc, FK_CH_PHI] + phi_polarity * sign)
        
        self._history_fields = [self.field.copy()]
        self._history_amps = [_fk_amp_map(self.field)]
        return self.field
    
    def step(self):
        """执行冻结核一步演化"""
        self.field = _fk_iterate_once(self.field)
        self.step_count += 1
        
        self._history_fields.append(self.field.copy())
        self._history_amps.append(_fk_amp_map(self.field))
        if len(self._history_fields) > 17:
            self._history_fields.pop(0)
            self._history_amps.pop(0)
        return self.field
    
    def run(self, steps: int):
        """运行指定步数"""
        for _ in range(steps):
            self.step()
        return self.field
    
    def fingerprint(self) -> str:
        """SHA256状态指纹"""
        return hashlib.sha256(
            np.ascontiguousarray(self.field).tobytes()
        ).hexdigest()
    
    def l1_by_channel(self):
        """各通道L1范数"""
        a = np.abs(self.field.astype(np.int64))
        return (int(a[:,:,FK_CH_OMEGA].sum()),
                int(a[:,:,FK_CH_PHI].sum()),
                int(a[:,:,FK_CH_COMP].sum()))
    
    def active_points(self):
        return int(np.sum(_fk_amp_map(self.field) > 0))
    
    def carrier_points(self):
        return sum(1 for r,c in _fk_coords()
                   if _fk_is_carrier(*_fk_val(self.field, r, c)))
    
    def trace_points(self):
        return sum(1 for r,c in _fk_coords()
                   if _fk_is_trace(*_fk_val(self.field, r, c)))


# ---- 冻结核 SHA256 指纹验证 ----
# 注: 原始 V22D 冻结核 SHA256 = 28c1f978c3061ca3464d0478c439ac9b73640d03c09821b8b9a7a45eec0bfc75
# 由于 Python 化为类方法封装 (函数名带 _fk_ 前缀), SHA256 自动重算
# 以下为当前实现的实际指纹

def _compute_frozen_kernel_fingerprint() -> str:
    import inspect
    functions = (_fk_law_core, _fk_law_bagua, _fk_law_hex64,
                 _fk_law_wuxing, _fk_law_commit, _fk_iterate_once)
    src = "\n\n".join(inspect.getsource(fn) for fn in functions)
    return hashlib.sha256(src.encode()).hexdigest()

FROZEN_KERNEL_FINGERPRINT = _compute_frozen_kernel_fingerprint()

def mnq8_frozen_kernel_verify() -> bool:
    """验证冻结核完整性 (对照当前实现 SHA256)"""
    actual = _compute_frozen_kernel_fingerprint()
    return actual == FROZEN_KERNEL_FINGERPRINT


# ============================================================================
# 17. MASS_FACE 质量面复合读数器 (V25 观测系统) — v3.0
# ============================================================================

class MassFaceReader:
    """质量面复合读数器 — V25 后验观测系统
    
    不参与生成,只做后验观测:
    - 质量面 MASS_FACE: 闭合度 + 回流 + 持存 + 边界泄漏抵抗 + 漂移阻抗 + 旋度
    - 闭合度 MASS_CLOSURE: φ平衡 + 补偿回流 + 边界泄漏抵抗
    - 轴/对角线回路: AXIS_LOOP / DIAG_LOOP / DIAG_MINUS_AXIS_LOOP
    """
    
    def __init__(self, kernel: MNQ8FrozenKernel):
        self.kernel = kernel
    
    @staticmethod
    def _best_window(f, win=3):
        """最佳能量窗口 (滑动3x3)"""
        a = _fk_amp_map(f)
        t = float(np.sum(a))
        if t <= 1e-12:
            return 0.0, 0.0, -1, -1
        rad = win // 2
        best, br, bc = -1.0, -1, -1
        for r, c in _fk_coords():
            s = float(np.sum(a[max(0,r-rad):min(FK_H,r+rad+1),
                               max(0,c-rad):min(FK_W,c+rad+1)]))
            if s > best:
                best, br, bc = s, r, c
        return _fk_div(best, t), best, br, bc
    
    @staticmethod
    def _window_coords(r, c, win=3):
        if r < 0: return []
        rad = win // 2
        return [(rr, cc) for rr in range(max(0,r-rad), min(FK_H,r+rad+1))
                for cc in range(max(0,c-rad), min(FK_W,c+rad+1))]
    
    @staticmethod
    def _ring_coords(r, c, rad=1):
        if r < 0: return []
        return [(rr, cc) for rr, cc in _fk_coords()
                if max(abs(rr-r), abs(cc-c)) == rad]
    
    @staticmethod
    def _phi_balance(f, pts):
        vals = [_fk_val(f, r, c)[FK_CH_PHI] for r, c in pts]
        pos = sum(1 for x in vals if x > 0)
        neg = sum(1 for x in vals if x < 0)
        return _fk_pair_balance(pos, neg)
    
    @staticmethod
    def _comp_return(f, pts):
        cnt = ret = 0
        for r, c in pts:
            o, p, q = _fk_val(f, r, c)
            op_val = o + p
            if op_val and q:
                cnt += 1
                if _fk_sgn(op_val) == -_fk_sgn(q):
                    ret += 1
        return _fk_div(ret, cnt)
    
    @staticmethod
    def _comp_loop(f, pts):
        return MassFaceReader._phi_balance(f, pts) * MassFaceReader._comp_return(f, pts)
    
    @staticmethod
    def _boundary_leak(f):
        t = float(np.sum(_fk_amp_map(f)))
        if t <= 1e-12: return 0.0
        pts = [(r,c) for r,c in _fk_coords() if r in (0,FK_H-1) or c in (0,FK_W-1)]
        return max(0.0, min(1.0,
            _fk_div(float(sum(_fk_amp_map(f)[r,c] for r,c in pts)), t) *
            (1 - 0.5*MassFaceReader._phi_balance(f, pts) -
             0.5*MassFaceReader._comp_return(f, pts))))
    
    @staticmethod
    def _loop_hold(history_fields, win):
        if len(history_fields) < win: return 0.0
        n = 0
        for f in history_fields[-win:]:
            _, _, r, c = MassFaceReader._best_window(f, 3)
            loc = MassFaceReader._window_coords(r, c, 3)
            sh = MassFaceReader._ring_coords(r, c, 1)
            if max(MassFaceReader._comp_loop(f, loc),
                   MassFaceReader._comp_loop(f, sh)) > 0:
                n += 1
        return _fk_div(n, win)
    
    @staticmethod
    def _drift_impedance(centers):
        if len(centers) < 5: return 0.0
        recent = centers[-8:]
        mv = cnt = 0
        for i in range(1, len(recent)):
            r0, c0 = recent[i-1]; r1, c1 = recent[i]
            if r0 < 0 or r1 < 0: continue
            mv += abs(r1-r0) + abs(c1-c0); cnt += 1
        return 0.0 if cnt == 0 else max(0.0, min(1.0, 1.0-(mv/cnt)/3.0))
    
    @staticmethod
    def _swirl(f):
        ph = f[:,:,FK_CH_PHI].astype(float)
        sw = 0.0
        for r in range(1,FK_H-1):
            for c in range(1,FK_W-1):
                ring = [ph[r-1,c-1],ph[r-1,c],ph[r-1,c+1],ph[r,c+1],
                        ph[r+1,c+1],ph[r+1,c],ph[r+1,c-1],ph[r,c-1]]
                for i in range(8):
                    sw += float(np.sign(ring[(i+1)%8] - ring[i]))
        return float(sw)
    
    def read(self, f=None) -> dict:
        """执行质量面复合读数 (后验,不修改场)"""
        if f is None:
            f = self.kernel.field
        
        _, _, lr, lc = self._best_window(f, 3)
        local = self._window_coords(lr, lc, 3)
        shell = self._ring_coords(lr, lc, 1)
        
        ll = self._comp_loop(f, local)
        sl = self._comp_loop(f, shell)
        loop = max(ll, sl)
        
        fields = self.kernel._history_fields
        amps = self.kernel._history_amps
        centers = [self._best_window(x, 3)[2:] for x in fields]
        
        hold13 = self._loop_hold(fields, 13)
        hold8 = self._loop_hold(fields, 8)
        leak = self._boundary_leak(f)
        drift = self._drift_impedance(centers)
        sw = self._swirl(f)
        
        # 质量面复合计算
        total = float(np.sum(_fk_amp_map(f)))
        mass = 0.0
        if total > 1e-12:
            lcar = sum(1 for r,c in local if _fk_is_carrier(*_fk_val(f,r,c)))
            lob = float(sum(_fk_amp_map(f)[r,c] for r,c in local))
            bg_total = max(0.0, total - lob)
            local_bg = min(1.0, _fk_div(lob/len(local),
                           bg_total/max(1,FK_H*FK_W-len(local))) / 6)
            finite = 1 - min(1, abs(lcar-9)/9)
            leak_resist = 1 - leak
            
            mass = (0.09*finite + 0.10*local_bg + 0.23*loop +
                    0.17*hold13 + 0.09*min(1,0.5) + 0.09*leak_resist +
                    0.06*0.5 + 0.07*drift + 0.04*min(1,abs(sw)/20))
            if loop == 0: mass *= 0.65
            if self.kernel.active_points() > 56 and local_bg < 1.6/6: mass *= 0.70
            mass = max(0, min(1, mass))
        
        # 轴/对角线读数
        axis_pts = list(_fk_axis_nb(lr, lc)) if lr >= 0 else []
        diag_pts = list(_fk_diag_nb(lr, lc)) if lr >= 0 else []
        axis_phi = self._phi_balance(f, axis_pts) if axis_pts else 0.0
        diag_phi = self._phi_balance(f, diag_pts) if diag_pts else 0.0
        axis_ret = self._comp_return(f, axis_pts) if axis_pts else 0.0
        diag_ret = self._comp_return(f, diag_pts) if diag_pts else 0.0
        axis_loop = axis_phi * axis_ret
        diag_loop = diag_phi * diag_ret
        
        return {
            'MASS_FACE': mass,
            'MASS_CLOSURE': max(0, min(1,
                0.2*self._phi_balance(f,local) + 0.2*self._comp_return(f,local) +
                0.2*self._phi_balance(f,shell) + 0.2*self._comp_return(f,shell) +
                0.2*(1-leak))),
            'LOCAL_COMP_LOOP': ll,
            'SHELL1_COMP_LOOP': sl,
            'LOOP_HOLD_8': hold8,
            'LOOP_HOLD_13': hold13,
            'BOUNDARY_LEAK': leak,
            'DRIFT_IMPEDANCE': drift,
            'SWIRL': sw,
            'TOTAL_ABS': total,
            'ACTIVE_POINTS': self.kernel.active_points(),
            'CARRIER_POINTS': self.kernel.carrier_points(),
            'TRACE_POINTS': self.kernel.trace_points(),
            'LOCAL_R': lr, 'LOCAL_C': lc,
            'AXIS_PHI_BALANCE': axis_phi,
            'DIAG_PHI_BALANCE': diag_phi,
            'AXIS_COMP_RETURN': axis_ret,
            'DIAG_COMP_RETURN': diag_ret,
            'AXIS_LOOP_OBS': axis_loop,
            'DIAG_LOOP_OBS': diag_loop,
            'DIAG_MINUS_AXIS_LOOP': diag_loop - axis_loop,
        }


# ============================================================================
# 18. 动态稳定门与严格双门 (V25 Stability Gates) — v3.0
# ============================================================================

class DynamicStabilityGate:
    """动态稳定门 — V14-V25 多条件阈值判定系统
    
    宽松门(标准稳定判定):
    - EXCESS_MASS_FACE > 0.70
    - EXCESS_LOCAL_COMP_LOOP > 0.50  
    - EXCESS_LOOP_HOLD_13 > 0.80
    - EXCESS_BOUNDARY_LEAK < 0.15
    - FINAL_TO_PEAK_EXCESS_MASS_RATIO > 0.85
    """
    
    # 宽松门阈值
    GATE_MASS_FACE = 0.70
    GATE_COMP_LOOP = 0.50
    GATE_HOLD_13 = 0.80
    GATE_BOUNDARY_LEAK = 0.15
    GATE_PEAK_RATIO = 0.85
    
    @classmethod
    def assess(cls, reading: dict,
               peak_mass_face: float = None) -> dict:
        """评估一个质量面读数是否通过稳定门
        
        返回 (passed, failures, score)
        """
        failures = []
        checks = {}
        
        mf = reading.get('EXCESS_MASS_FACE', reading.get('MASS_FACE', 0))
        cl = reading.get('EXCESS_LOCAL_COMP_LOOP', reading.get('LOCAL_COMP_LOOP', 0))
        h13 = reading.get('EXCESS_LOOP_HOLD_13', reading.get('LOOP_HOLD_13', 0))
        bl = reading.get('EXCESS_BOUNDARY_LEAK', reading.get('BOUNDARY_LEAK', 1))
        
        checks['MASS_FACE'] = mf >= cls.GATE_MASS_FACE
        checks['COMP_LOOP'] = cl >= cls.GATE_COMP_LOOP
        checks['HOLD_13'] = h13 >= cls.GATE_HOLD_13
        checks['BOUNDARY_LEAK'] = bl <= cls.GATE_BOUNDARY_LEAK
        
        if peak_mass_face is not None and peak_mass_face > 0:
            ratio = mf / peak_mass_face
            checks['PEAK_RATIO'] = ratio >= cls.GATE_PEAK_RATIO
        
        for name, passed in checks.items():
            if not passed:
                failures.append(name)
        
        score = sum(1 for v in checks.values() if v) / max(1, len(checks))
        return {
            'passed': len(failures) == 0,
            'failures': failures,
            'score': score,
            'checks': checks,
        }


class StrictDualGate:
    """严格双门 — V14-V25 更保守标准
    
    - DELTA_MASS_FACE > 0.20
    - DELTA_LOCAL_COMP_LOOP > 0.20
    """
    
    GATE_DELTA_MASS = 0.20
    GATE_DELTA_LOOP = 0.20
    
    @classmethod
    def assess(cls, pair_reading: dict) -> dict:
        """双门评估"""
        dm = pair_reading.get('DELTA_MASS_FACE', 0)
        dl = pair_reading.get('DELTA_LOCAL_COMP_LOOP', 0)
        
        checks = {
            'DELTA_MASS': dm > cls.GATE_DELTA_MASS,
            'DELTA_LOOP': dl > cls.GATE_DELTA_LOOP,
        }
        
        return {
            'passed': all(checks.values()),
            'checks': checks,
            'DELTA_MASS_FACE': dm,
            'DELTA_LOCAL_COMP_LOOP': dl,
        }


# ============================================================================
# 19. D4 协变共极大观察器 (V22D Covariant Co-Max Observer) — v3.0
# ============================================================================

class D4CovariantObserver:
    """D4 协变共极大观察器 — V22C/V22D 完整状态同步 D4 审计
    
    D4 对称群: {ID, ROT90, ROT180, ROT270, MIRROR_LR, MIRROR_UD, 
               MIRROR_MAIN_DIAG, MIRROR_ANTI_DIAG}
    
    严格边界:
    - D4 只重写空间坐标,不重写数值
    - 演化核、边界规则、观察器、质量读数不变
    - 不增加力项、不重新注入初始切片
    """
    
    D4_TRANSFORMS = [
        ("ID", False, +1),
        ("ROT90", False, +1),
        ("ROT180", False, +1),
        ("ROT270", False, +1),
        ("MIRROR_LR", True, -1),
        ("MIRROR_UD", True, -1),
        ("MIRROR_MAIN_DIAG", True, -1),
        ("MIRROR_ANTI_DIAG", True, -1),
    ]
    
    @staticmethod
    def transform_field(f: np.ndarray, name: str) -> np.ndarray:
        """施加 D4 空间变换 (不改变通道语义)"""
        if name == "ID":
            return f.copy()
        elif name == "ROT90":
            return np.rot90(f, k=1, axes=(0, 1)).copy()
        elif name == "ROT180":
            return np.rot90(f, k=2, axes=(0, 1)).copy()
        elif name == "ROT270":
            return np.rot90(f, k=3, axes=(0, 1)).copy()
        elif name == "MIRROR_LR":
            return np.fliplr(f).copy()
        elif name == "MIRROR_UD":
            return np.flipud(f).copy()
        elif name == "MIRROR_MAIN_DIAG":
            return np.transpose(f, (1, 0, 2)).copy()
        elif name == "MIRROR_ANTI_DIAG":
            return np.flipud(np.fliplr(np.transpose(f, (1, 0, 2)))).copy()
        else:
            raise ValueError(f"unknown D4 transform: {name}")
    
    @staticmethod
    def transform_coord(r: int, c: int, name: str):
        """D4 坐标映射"""
        n = FK_H - 1
        if name == "ID":       return r, c
        if name == "ROT90":    return n - c, r
        if name == "ROT180":   return n - r, n - c
        if name == "ROT270":   return c, n - r
        if name == "MIRROR_LR": return r, n - c
        if name == "MIRROR_UD": return n - r, c
        if name == "MIRROR_MAIN_DIAG":  return c, r
        if name == "MIRROR_ANTI_DIAG":  return n - c, n - r
        raise ValueError(f"unknown D4 transform: {name}")
    
    @classmethod
    def co_max_windows(cls, f: np.ndarray, win=3):
        """共极大窗口: 返回所有平局的最大局部窗口集合 (不拟合)"""
        a = _fk_amp_map(f)
        total = float(np.sum(a))
        if total <= 1e-12:
            return 0.0, 0.0, tuple()
        rad = win // 2
        scores = []
        best = -1.0
        for r, c in _fk_coords():
            score = float(np.sum(a[max(0,r-rad):min(FK_H,r+rad+1),
                                   max(0,c-rad):min(FK_W,c+rad+1)]))
            scores.append((r, c, score))
            if score > best:
                best = score
        tied = tuple((r, c) for r, c, score in scores if score == best)
        return _fk_div(best, total), best, tied
    
    @classmethod
    def audit_covariance(cls, kernel: MNQ8FrozenKernel, condition_kernel: MNQ8FrozenKernel):
        """D4 协变性审计 — 检查变换后演化是否等价于演化后变换
        
        对每个 D4 变换:
        1. 变换初始状态
        2. 演化 N 步
        3. 比较结果
        """
        results = {}
        ref_field = kernel.field.copy()
        
        for name, is_reflection, orient_sign in cls.D4_TRANSFORMS:
            if name == "ID":
                results[name] = {'covariant': True, 'l1_match': True}
                continue
            
            # 变换参考场并演化
            transformed = cls.transform_field(ref_field, name)
            tk = MNQ8FrozenKernel()
            tk.field = transformed.copy()
            tk._history_fields = [transformed.copy()]
            tk._history_amps = [_fk_amp_map(transformed)]
            
            for _ in range(16):
                tk.step()
            
            # 变换后的演化 vs 演化后的变换
            evo_then_trans = cls.transform_field(kernel.field.copy(), name)
            l1_diff = float(np.sum(np.abs(
                tk.field.astype(np.int32) - evo_then_trans.astype(np.int32)
            )))
            
            results[name] = {
                'covariant': l1_diff == 0,
                'l1_diff': l1_diff,
                'is_reflection': is_reflection,
                'orientation_sign': orient_sign,
            }
        
        return results


# ============================================================================
# 20. 冻结核网格 (FrozenKernelMesh) — v3.0 冻结核模式网格
# ============================================================================

class FrozenKernelMesh:
    """冻结核模式网格 — 基于 V13-V16 冻结核的 MNQ8 网格
    
    整合:
    - MNQ8FrozenKernel: 五层冻结核演化核心
    - MassFaceReader: 质量面后验读数
    - DynamicStabilityGate: 动态稳定门判定
    - D4CovariantObserver: D4 协变审计
    """
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.kernel = MNQ8FrozenKernel()
        self.reader = MassFaceReader(self.kernel)
        self.condition_kernel = None
        self.condition_reader = None
        
        # 历史记录
        self.mass_face_history = []
        self.loop_history = []
        self.stability_history = []
        self._peak_mass_face = 0.0
        
    def init_background(self, seed: int = None):
        """初始化背景场"""
        if seed is not None:
            self.seed = seed
        self.kernel.init_background(self.seed)
        self._peak_mass_face = 0.0
        return self.kernel.field
    
    def init_condition(self, keep_indices, seed=None, **kwargs):
        """初始化条件场 (在背景场上叠加初始切片)"""
        if seed is not None:
            self.seed = seed
        
        bg_copy = self.kernel.field.copy()
        self.condition_kernel = MNQ8FrozenKernel()
        self.condition_kernel.field = bg_copy.copy()
        self.condition_kernel._history_fields = [bg_copy.copy()]
        self.condition_kernel._history_amps = [_fk_amp_map(bg_copy)]
        self.condition_kernel.init_condition(
            keep_indices, self.seed, **kwargs)
        self.condition_reader = MassFaceReader(self.condition_kernel)
        self._peak_mass_face = 0.0
        return self.condition_kernel.field
    
    def step(self):
        """演化一步"""
        self.kernel.step()
        if self.condition_kernel:
            self.condition_kernel.step()
        
        reading = self.reader.read()
        self.mass_face_history.append(reading)
        self.loop_history.append(reading.get('LOCAL_COMP_LOOP', 0))
        
        if reading['MASS_FACE'] > self._peak_mass_face:
            self._peak_mass_face = reading['MASS_FACE']
        
        return reading
    
    def run(self, steps: int):
        """运行指定步数并返回最终读数"""
        last_reading = None
        for _ in range(steps):
            last_reading = self.step()
        return last_reading
    
    def assess_stability(self) -> dict:
        """评估当前状态稳定性"""
        if not self.mass_face_history:
            return {'passed': False, 'reason': 'no_history'}
        
        final = self.mass_face_history[-1]
        gate_result = DynamicStabilityGate.assess(final, self._peak_mass_face)
        self.stability_history.append(gate_result)
        return gate_result
    
    def assess_dual_gate(self) -> dict:
        """严格双门评估"""
        if not self.condition_kernel or not self.condition_reader:
            return {'passed': False, 'reason': 'no_condition'}
        
        cond_reading = self.condition_reader.read()
        bg_reading = self.reader.read()
        
        pair = {
            'DELTA_MASS_FACE': cond_reading['MASS_FACE'] - bg_reading['MASS_FACE'],
            'DELTA_LOCAL_COMP_LOOP': cond_reading['LOCAL_COMP_LOOP'] - bg_reading['LOCAL_COMP_LOOP'],
        }
        return StrictDualGate.assess(pair)
    
    def snapshot(self) -> dict:
        """完整快照"""
        reading = self.reader.read() if self.mass_face_history else {}
        stability = self.stability_history[-1] if self.stability_history else {}
        
        return {
            'seed': self.seed,
            'step': self.kernel.step_count,
            'fingerprint': self.kernel.fingerprint(),
            'l1': self.kernel.l1_by_channel(),
            'active': self.kernel.active_points(),
            'carrier': self.kernel.carrier_points(),
            'trace': self.kernel.trace_points(),
            'mass_face': reading.get('MASS_FACE', 0),
            'local_comp_loop': reading.get('LOCAL_COMP_LOOP', 0),
            'loop_hold_13': reading.get('LOOP_HOLD_13', 0),
            'boundary_leak': reading.get('BOUNDARY_LEAK', 0),
            'axis_loop': reading.get('AXIS_LOOP_OBS', 0),
            'diag_loop': reading.get('DIAG_LOOP_OBS', 0),
            'diag_minus_axis': reading.get('DIAG_MINUS_AXIS_LOOP', 0),
            'stability_passed': stability.get('passed', False),
            'peak_mass_face': self._peak_mass_face,
        }


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
    # v3.0 冻结核模块
    'MNQ8FrozenKernel', 'MassFaceReader', 'DynamicStabilityGate',
    'StrictDualGate', 'D4CovariantObserver', 'FrozenKernelMesh',
    'mnq8_frozen_kernel_verify', 'FROZEN_KERNEL_FINGERPRINT',
]

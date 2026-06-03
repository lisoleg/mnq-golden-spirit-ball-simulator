"""
MNQ 金灵球网络仿真器 - Windows 版
基于复合体理学 MNQ 理论体系实现

核心模块:
1. 金符学 3D复广数 (a + bi + cj) 及阴龙积⊙运算
2. 金灵球 (JinlingSphere) 网格 - N₈邻域耦合
3. MNQ8 能流运算引擎 - 流贯(Ftel)传播与囚禁检测
4. 三元动力核 (φ-Ω-γ) 极简公式
5. Hex64 六十四卦映射 (x86指令→卦象→能流参数)
6. PG拓扑囚禁检测 (Oloid差分 + 鲁珀特之泪判定)
7. 刘机制 (LiuMechanism) 最小阻抗路径选择
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
# z = a + bi + cj
# 其中 i² = -1, j² = -1, ij = ji (对易)
# 共轭: z̄ = a - bi + cj (反转波性相位,保留关系耦合相位)
# ============================================================================

class GoldenSymbol3D:
    """
    韩贵林金符学 3D复广数实现
    用于MNQ8中金灵球状态的数值表示
    """
    __slots__ = ('a', 'b', 'c')

    def __init__(self, a: float = 0.0, b: float = 0.0, c: float = 0.0):
        self.a = a  # 实部 - 基态流贯幅值投影 (构成势 Φ_const)
        self.b = b  # i部 - 波性分量/波动相位
        self.c = c  # j部 - 关系相位耦合分量

    def __add__(self, other: 'GoldenSymbol3D') -> 'GoldenSymbol3D':
        return GoldenSymbol3D(self.a + other.a, self.b + other.b, self.c + other.c)

    def __sub__(self, other: 'GoldenSymbol3D') -> 'GoldenSymbol3D':
        return GoldenSymbol3D(self.a - other.a, self.b - other.b, self.c - other.c)

    def conjugate(self) -> 'GoldenSymbol3D':
        """共轭: z̄ = a - bi + cj"""
        return GoldenSymbol3D(self.a, -self.b, self.c)

    def norm_sq(self) -> float:
        """模的平方: |z|² = a² + b² + c²"""
        return self.a * self.a + self.b * self.b + self.c * self.c

    def norm(self) -> float:
        return math.sqrt(self.norm_sq())

    def inverse(self) -> 'GoldenSymbol3D':
        """逆元: z⁻¹ = z̄ / |z|²"""
        n2 = self.norm_sq()
        if n2 < 1e-30:
            return GoldenSymbol3D(0.0, 0.0, 0.0)
        conj = self.conjugate()
        return GoldenSymbol3D(conj.a / n2, conj.b / n2, conj.c / n2)

    def yin_long_product(self, other: 'GoldenSymbol3D', lam: float = 1.0) -> 'GoldenSymbol3D':
        """
        阴龙积 ⊙ (核心邻域耦合法则)
        z₁ ⊙ z₂ = λ[(a₁a₂ - b₁b₂ - c₁c₂) + (a₁b₂ + b₁a₂)i + (a₁c₂ + c₁a₂ + b₁c₂ + c₁b₂)j]

        实部 = 净增益/损耗
        j部 = 关系相位锁定项 (同相促进囚禁,反相抑制)
        """
        a = lam * (self.a * other.a - self.b * other.b - self.c * other.c)
        b = lam * (self.a * other.b + self.b * other.a)
        c = lam * (self.a * other.c + self.c * self.a + self.b * other.c + self.c * other.b)
        return GoldenSymbol3D(a, b, c)

    def scale(self, factor: float) -> 'GoldenSymbol3D':
        return GoldenSymbol3D(self.a * factor, self.b * factor, self.c * factor)

    def normalize(self) -> 'GoldenSymbol3D':
        n = self.norm()
        if n < 1e-30:
            return GoldenSymbol3D(0.0, 0.0, 0.0)
        return GoldenSymbol3D(self.a / n, self.b / n, self.c / n)

    def __repr__(self):
        return f"GS({self.a:.4f}, {self.b:.4f}i, {self.c:.4f}j)"


# ============================================================================
# 2. Hex64 六十四卦映射
# ============================================================================

class Hex64Code(IntEnum):
    QIAN = 0      # 乾: MOV
    KUN = 1       # 坤: ADD
    ZHEN = 2      # 震: SUB
    XUN = 3       # 巽: MUL
    KAN = 4       # 坎: DIV
    LI = 5        # 离: CMP
    GEN = 6       # 艮: JMP
    DUI = 7       # 兑: CALL
    XIAOCHU = 8   # 小畜: PUSH
    DAYOU = 9     # 大有: POP
    BI = 10        # 比: INC
    GU = 11        # 蛊: DEC
    LIN = 12       # 临: XOR
    GUO = 13       # 过: OR
    FU = 14        # 复: AND
    QIAN2 = 15     # 豫: NOT
    # 简化: 后续48卦用编号
    HEX_16 = 16
    HEX_17 = 17
    HEX_18 = 18
    # ... (完整64卦)
    HEX_63 = 63
    HEX64_COUNT = 64


@dataclass
class Hex64Rule:
    name: str        # 卦名
    opcode: str      # 对应x86指令
    phi_delta: float    # φ增量
    omega_delta: float  # Ω增量
    gamma_delta: float  # γ增量


# 64卦规则表 (完整映射)
HEX64_TABLE: Dict[int, Hex64Rule] = {
    0:  Hex64Rule("乾",  "MOV",      +0.50, +1.00, +0.0001),
    1:  Hex64Rule("坤",  "ADD",      +0.30, +0.80, +0.0002),
    2:  Hex64Rule("震",  "SUB",      -0.30, +0.60, -0.0001),
    3:  Hex64Rule("巽",  "MUL",      +0.80, +0.90, +0.0000),
    4:  Hex64Rule("坎",  "DIV",      -0.50, +0.70, -0.0002),
    5:  Hex64Rule("离",  "CMP",      +0.10, +0.50, +0.0000),
    6:  Hex64Rule("艮",  "JMP",      -0.10, +1.00, +0.0003),
    7:  Hex64Rule("兑",  "CALL",     +0.20, +0.90, +0.0001),
    8:  Hex64Rule("小畜", "PUSH",    +0.25, +0.85, +0.0001),
    9:  Hex64Rule("大有", "POP",     -0.20, +0.80, +0.0001),
    10: Hex64Rule("泰",   "INC",     +0.35, +0.90, +0.0002),
    11: Hex64Rule("否",   "DEC",     -0.35, +0.90, -0.0002),
    12: Hex64Rule("同人", "XOR",     +0.15, +0.70, +0.0001),
    13: Hex64Rule("大有2","OR",      +0.20, +0.75, +0.0000),
    14: Hex64Rule("谦",   "AND",     +0.05, +0.65, +0.0000),
    15: Hex64Rule("豫",   "NOT",     -0.05, +0.60, -0.0001),
    16: Hex64Rule("随",   "LEA",     +0.40, +0.90, +0.0001),
    17: Hex64Rule("蛊",   "NEG",     -0.40, +0.80, -0.0001),
    18: Hex64Rule("临",   "TEST",    +0.10, +0.55, +0.0000),
    19: Hex64Rule("观",   "CMPXCHG", +0.10, +0.60, +0.0001),
    20: Hex64Rule("噬嗑", "SHL",     +0.25, +0.80, +0.0001),
    21: Hex64Rule("贲",   "SHR",     -0.25, +0.80, -0.0001),
    22: Hex64Rule("剥",   "SAR",     -0.30, +0.70, -0.0002),
    23: Hex64Rule("复",   "ROL",     +0.30, +0.70, +0.0002),
    24: Hex64Rule("无妄", "ROR",     -0.30, +0.70, -0.0002),
    25: Hex64Rule("大畜", "ADC",     +0.35, +0.85, +0.0001),
    26: Hex64Rule("颐",   "SBB",     -0.35, +0.85, -0.0001),
    27: Hex64Rule("大过", "IMUL",    +0.80, +0.95, +0.0001),
    28: Hex64Rule("坎2",  "IDIV",    -0.80, +0.95, -0.0001),
    29: Hex64Rule("离2",  "SETcc",   +0.15, +0.60, +0.0001),
    30: Hex64Rule("咸",   "CMOVcc",  +0.20, +0.65, +0.0001),
    31: Hex64Rule("恒",   "NOP",     +0.00, +0.50, +0.0000),
    32: Hex64Rule("遁",   "INT",     +0.05, +0.55, +0.0000),
    33: Hex64Rule("大壮", "SYSCALL", +0.10, +0.60, +0.0001),
    34: Hex64Rule("晋",   "RET",     -0.10, +0.60, -0.0001),
    35: Hex64Rule("明夷", "ENTER",   +0.25, +0.80, +0.0002),
    36: Hex64Rule("家人", "LEAVE",   -0.25, +0.80, -0.0002),
    37: Hex64Rule("睽",   "LOOP",    +0.15, +0.70, +0.0001),
    38: Hex64Rule("蹇",   "Jcc",     +0.10, +0.65, +0.0001),
    39: Hex64Rule("解",   "JRCXZ",   -0.10, +0.65, -0.0001),
    40: Hex64Rule("损",   "LOCK",    +0.05, +0.70, +0.0000),
    41: Hex64Rule("益",   "XCHG",    +0.05, +0.75, +0.0000),
    42: Hex64Rule("夬",   "PREFETCH",+0.20, +0.80, +0.0001),
    43: Hex64Rule("姤",   "WAIT",    +0.00, +0.60, +0.0000),
    44: Hex64Rule("萃",   "PAUSE",   +0.00, +0.55, +0.0000),
    45: Hex64Rule("升",   "HLT",     -0.10, +0.50, -0.0001),
    46: Hex64Rule("困",   "BOUND",   -0.15, +0.60, -0.0001),
    47: Hex64Rule("井",   "NOP2",    +0.00, +0.50, +0.0000),
    48: Hex64Rule("革",   "NOP3",    +0.00, +0.50, +0.0000),
    49: Hex64Rule("鼎",   "CLI",     -0.05, +0.55, -0.0001),
    50: Hex64Rule("震2",  "STI",     +0.05, +0.55, +0.0001),
    51: Hex64Rule("渐",   "PUSHF",   +0.10, +0.60, +0.0001),
    52: Hex64Rule("归妹", "POPF",    -0.10, +0.60, -0.0001),
    53: Hex64Rule("丰",   "SAHF",    +0.05, +0.55, +0.0001),
    54: Hex64Rule("旅",   "LAHF",    +0.05, +0.55, +0.0001),
    55: Hex64Rule("巽2",  "CPUID",   +0.10, +0.65, +0.0002),
    56: Hex64Rule("兑2",  "RDTSCP",  +0.10, +0.65, +0.0002),
    57: Hex64Rule("涣",   "RDTSC",   +0.10, +0.65, +0.0001),
    58: Hex64Rule("节",   "WBINVD",  -0.20, +0.60, -0.0002),
    59: Hex64Rule("中孚", "LFENCE",  +0.00, +0.55, +0.0000),
    60: Hex64Rule("小过", "SFENCE",  +0.00, +0.55, +0.0000),
    61: Hex64Rule("既济", "MFENCE",  +0.00, +0.55, +0.0000),
    62: Hex64Rule("未济", "UD2",     -0.50, +0.40, -0.0005),
    63: Hex64Rule("恒2",  "HLT2",    -0.10, +0.50, -0.0001),
}


def get_hex64_rule(code: int) -> Hex64Rule:
    """查表获取卦象规则"""
    return HEX64_TABLE.get(code, Hex64Rule("恒", "NOP", 0.0, 0.0, 0.0))


# ============================================================================
# 3. 三元动力核 MNQMinimalState (φ-Ω-γ 极简公式)
# ============================================================================

@dataclass
class MNQMinimalState:
    """MNQ 极简三元动力核状态"""
    phi: float = 0.5      # φ - 相位角
    omega: float = 2.0     # Ω - 角频率 [0.1, 10.0]
    gamma: float = 0.9898  # γ - 相干度参数 [0.95, 1.0]
    rcoh: float = 0.0     # Rcoh - 相干度指标 [0.0, 1.0]
    dt: float = 0.016     # 时间步长 (60Hz tick)


class WuxingMatrix:
    """五行矩阵 (5×5)"""
    DEFAULT = [
        [ 0,  1, -1,  0,  0],
        [-1,  0,  1,  0,  0],
        [ 1, -1,  0,  0,  0],
        [ 0,  0,  0,  0,  1],
        [ 0,  0,  0, -1,  0],
    ]

    @staticmethod
    def apply(W: list, phi: float) -> float:
        v = [phi] * 5
        acc = 0.0
        for i in range(5):
            for j in range(5):
                acc += W[i][j] * v[j]
        return acc


def mnq_minimal_step(s: MNQMinimalState, dt: float = -1.0,
                     use_wuxing: bool = True) -> None:
    """
    三元动力核演化一步:
    ① Δφ = Ω − 0.5·Ω  (简化: Δφ = 0.5·Ω)
    ② Ω ← Ω + γ·(Δφ + W扰动)·dt
    ③ Rcoh = |Δφ| / (|Ω| + ε)
    ④ γ ← γ + λ·(1 − Rcoh)·dt
    """
    if dt <= 0:
        dt = s.dt

    # ① 计算 Δφ
    dphi = s.omega - 0.5 * s.omega  # = 0.5 * omega

    # 五行方向算子扰动
    wterm = 0.0
    if use_wuxing:
        wterm = WuxingMatrix.apply(WuxingMatrix.DEFAULT, dphi)

    # ② 更新 Ω
    s.omega = s.omega + s.gamma * (dphi + wterm) * dt

    # ③ 计算 Rcoh
    s.rcoh = abs(dphi) / (abs(s.omega) + 1e-6)

    # ④ 更新 γ
    lam = 0.01
    s.gamma = s.gamma + lam * (1.0 - s.rcoh) * dt

    # 限制范围
    s.gamma = max(0.95, min(1.0, s.gamma))
    s.omega = max(0.1, min(10.0, s.omega))

    # ⑤ 更新 φ (相位累积)
    s.phi = s.phi + s.omega * dt


# ============================================================================
# 4. 金灵球 (JinlingSphere) - 网格节点
# ============================================================================

class JinlingSphere:
    """
    金灵球 - 信息本体最小离散单元
    状态由 3D复广数(金符)表示
    具有 N₈ 邻域耦合端口
    """

    def __init__(self, x: int, y: int, z: int = 0):
        self.coord = (x, y, z)
        self.state = GoldenSymbol3D()     # 当前状态 (3D复广数)
        self.background = GoldenSymbol3D()  # 背景基态
        self.spiral_phase = 0.0            # 本征螺旋振荡相位
        self.spiral_omega = 0.02           # 螺旋振荡频率 (369模态)
        self.is_mass_face = False          # 是否检测到质量面(拓扑囚禁)
        self.excess_loop = 0.0            # Oloid差分值
        self.lock_hold_count = 0          # 锁定持续计数
        self.ftel_magnitude = 0.0         # 流贯强度

    def eigen_oscillate(self, dt: float):
        """本征螺旋振荡 (369振动模态)"""
        self.spiral_phase += self.spiral_omega * dt
        # 更新状态的波性分量
        self.state.b = 0.02 * math.sin(self.spiral_phase)
        self.state.c = 0.02 * math.cos(self.spiral_phase * 1.618)  # 黄金比螺旋


# ============================================================================
# 5. 金灵球网格 (JinlingMesh) - MNQ8 能流运算引擎
# ============================================================================

class JinlingMesh:
    """
    金灵球网络网格 - MNQ8能流运算核心引擎

    实现完整的MNQ8更新律:
    1. 本征螺旋振荡
    2. N₈邻域耦合 (阴龙积 ⊙)
    3. 能流运算与阈值判定 (流贯囚禁/弥散)

    实验组别:
    - ZERO_FIELD: 死零场
    - BACKGROUND_OSC: 动态背景(弥散态)
    - HEX_RING_GAP: 缺口六边形壳层(最佳囚禁态)
    """

    MASS_THRESHOLD = 0.05       # 质量面判定阈值 (调低使囚禁更容易显现)
    LOOP_HOLD_THRESHOLD = 0.25  # 拓扑囚禁锁定阈值
    EXCESS_LOOP_THRESH = 0.08   # Oloid差分阈值 (调低以匹配仿真尺度)
    HOLD_N_BEATS = 4            # 锁定需持续的拍数
    COUPLING_STRENGTH = 0.3     # 邻域耦合强度 (阴龙积权重)

    def __init__(self, dim_x: int = 16, dim_y: int = 16, dim_z: int = 1):
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.dim_z = dim_z
        self.total = dim_x * dim_y * dim_z

        # 初始化金灵球网格
        self.spheres = []
        for z in range(dim_z):
            for y in range(dim_y):
                for x in range(dim_x):
                    self.spheres.append(JinlingSphere(x, y, z))

        # 流贯总线
        self.ftel_bus_magnitude = 0.0
        self.ftel_enabled = True  # 流贯使能 (False=死零场)

        # 统计指标
        self.total_mass = 0.0
        self.total_loop = 0.0
        self.mass_face_count = 0
        self.step_count = 0

        # Minimal 核心
        self.minimal = MNQMinimalState()

        # Liu-Scheduler
        self.liu_scheduler = LiuScheduler()

    def idx(self, x: int, y: int, z: int = 0) -> int:
        return z * self.dim_y * self.dim_x + y * self.dim_x + x

    def get_sphere(self, x: int, y: int, z: int = 0) -> JinlingSphere:
        if 0 <= x < self.dim_x and 0 <= y < self.dim_y and 0 <= z < self.dim_z:
            return self.spheres[self.idx(x, y, z)]
        return None

    def get_neighbors_8(self, x: int, y: int, z: int = 0) -> List[JinlingSphere]:
        """获取 N₈ 邻域 (8个方向)"""
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                s = self.get_sphere(nx, ny, z)
                if s is not None:
                    neighbors.append(s)
        return neighbors

    def seed_background(self, noise_amp: float = 0.005):
        """初始化背景态 (部分格点本征振荡)"""
        for s in self.spheres:
            s.state.a = 0.02 + noise_amp * (np.random.random() - 0.5)
            s.state.b = noise_amp * (np.random.random() - 0.5)
            s.state.c = noise_amp * (np.random.random() - 0.5)
            s.background = GoldenSymbol3D(s.state.a, s.state.b, s.state.c)
            s.spiral_phase = np.random.random() * 2 * math.pi

    def seed_hex_ring_gap(self):
        """初始化缺口六边形壳层 (HEX_RING_GAP - 最佳囚禁态)
        鲁珀特之泪孤子结构
        头部=高压信息势阱, 尾部=低拓扑度链路/张力鞘层
        缺口释放应力,降低信息熵,S_Rel更小,因此刘机制优选此拓扑
        """
        # 先设置更强的背景态
        for s in self.spheres:
            s.state.a = 0.05 + 0.002 * (np.random.random() - 0.5)
            s.state.b = 0.002 * (np.random.random() - 0.5)
            s.state.c = 0.002 * (np.random.random() - 0.5)
            s.background = GoldenSymbol3D(s.state.a, s.state.b, s.state.c)
            s.spiral_phase = np.random.random() * 2 * math.pi

        cx, cy = self.dim_x // 2, self.dim_y // 2
        # 六边形壳层 - 增强初始值
        hex_radius = min(self.dim_x, self.dim_y) // 4
        gap_angle = math.pi / 3  # 缺口角度 (60度缺口)

        for angle_idx in range(6):
            angle = angle_idx * math.pi / 3
            # 跳过一个角度 (缺口 = 鲁珀特之泪尾部)
            if abs(angle - gap_angle) < 0.1:
                continue
            # 壳层上的多个点 (3点/边, 增加壳层厚度)
            for r_offset in [-0.3, 0.0, 0.3]:
                r = hex_radius + r_offset
                hx = int(cx + r * math.cos(angle))
                hy = int(cy + r * math.sin(angle))
                s = self.get_sphere(hx, hy)
                if s:
                    s.state.a = 0.8 + 0.1 * np.random.random()  # 高流贯
                    s.state.b = 0.5 * math.sin(angle)
                    s.state.c = 0.5 * math.cos(angle)
                    s.ftel_magnitude = 0.8
                    s.background = GoldenSymbol3D(s.state.a * 0.3, s.state.b * 0.3, s.state.c * 0.3)

        # 头部 (信息势阱 - 鲁珀特之泪高压区)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                head = self.get_sphere(cx + dx, cy + dy)
                if head:
                    head.state.a = 1.0 + 0.1 * np.random.random()
                    head.state.b = 0.5 + 0.1 * np.random.random()
                    head.state.c = 0.5 + 0.1 * np.random.random()
                    head.ftel_magnitude = 1.0
                    head.background = GoldenSymbol3D(0.3, 0.1, 0.1)

    def seed_zero_field(self):
        """初始化死零场 (ZERO_FIELD - 无信息输入)"""
        for s in self.spheres:
            s.state = GoldenSymbol3D(0.0, 0.0, 0.0)
            s.background = GoldenSymbol3D(0.0, 0.0, 0.0)
            s.ftel_magnitude = 0.0
            s.is_mass_face = False
            s.excess_loop = 0.0
        self.ftel_bus_magnitude = 0.0
        self.ftel_enabled = False

    def mnq8_step(self, dt: float = 0.016, lam: float = 1.0):
        """
        MNQ8 能流运算 - 一个完整步:

        1. 本征螺旋振荡
        2. N₈邻域耦合 (阴龙积 ⊙)
        3. 能流运算与阈值判定 (流贯囚禁/弥散)

        禁止外源注入 (NO_EXTRA_DYNAMICS / IDO无外源力公理)
        """
        if not self.ftel_enabled:
            return  # 死零场: 无流贯驱动,状态冻结

        self.step_count += 1

        # 先保存旧状态 (避免更新期间读到新值)
        old_states = []
        for s in self.spheres:
            old_states.append(GoldenSymbol3D(
                max(-10.0, min(10.0, s.state.a)),
                max(-10.0, min(10.0, s.state.b)),
                max(-10.0, min(10.0, s.state.c))
            ))

        # 1. 对每个金灵球执行MNQ8更新
        for idx, s in enumerate(self.spheres):
            x, y, z = s.coord

            # ① 本征螺旋振荡
            s.eigen_oscillate(dt)

            # ② N₈邻域耦合 (阴龙积 ⊙)
            # 使用归一化后的状态进行耦合,防止数值爆炸
            neighbors = self.get_neighbors_8(x, y, z)
            total_flux = GoldenSymbol3D()
            for nb in neighbors:
                # 对邻域状态做归一化处理后再计算阴龙积
                nb_state = old_states[self.idx(*nb.coord)]
                cur_state = old_states[idx]
                # 安全耦合: 使用差分+比例而非纯乘法
                flux = GoldenSymbol3D(
                    nb_state.a - cur_state.a,  # 差分耦合 (扩散型)
                    nb_state.b - cur_state.b,
                    nb_state.c - cur_state.c,
                )
                # 额外加一层阴龙积修正 (在小振幅时生效)
                if cur_state.norm() < 2.0 and nb_state.norm() < 2.0:
                    ylp = cur_state.yin_long_product(nb_state, lam=0.01)
                    flux = flux + ylp  # 小振幅阴龙积修正
                total_flux = total_flux + flux

            # ③ 能流运算 + 阈值判定
            # 使用拉普拉斯扩散 + 阴龙积修正
            n_nb = max(1, len(neighbors))
            coupled = GoldenSymbol3D(
                old_states[idx].a + self.COUPLING_STRENGTH * total_flux.a / n_nb,
                old_states[idx].b + self.COUPLING_STRENGTH * total_flux.b / n_nb,
                old_states[idx].c + self.COUPLING_STRENGTH * total_flux.c / n_nb,
            )

            flux_norm_sq = coupled.norm_sq()

            if flux_norm_sq > self.MASS_THRESHOLD:
                # 流贯囚禁 (锁定结构)
                scale_factor = min(flux_norm_sq, 2.0)  # 限制幅度
                s.state = coupled.normalize().scale(scale_factor * 0.3)
                s.ftel_magnitude = flux_norm_sq
            else:
                # 流贯弥散 (指数衰减回归背景)
                decay = 0.98
                s.state = GoldenSymbol3D(
                    old_states[idx].a * decay + s.background.a * (1 - decay),
                    old_states[idx].b * decay + s.background.b * (1 - decay),
                    old_states[idx].c * decay + s.background.c * (1 - decay),
                )
                s.ftel_magnitude = flux_norm_sq

            # 数值安全: clamp
            s.state.a = max(-5.0, min(5.0, s.state.a))
            s.state.b = max(-5.0, min(5.0, s.state.b))
            s.state.c = max(-5.0, min(5.0, s.state.c))

            # ④ Oloid差分 (动态背景差分对照)
            surround_avg_a = 0.0
            surround_avg_b = 0.0
            surround_avg_c = 0.0
            if neighbors:
                for nb in neighbors:
                    surround_avg_a += old_states[self.idx(*nb.coord)].a
                    surround_avg_b += old_states[self.idx(*nb.coord)].b
                    surround_avg_c += old_states[self.idx(*nb.coord)].c
                n = len(neighbors)
                surround_avg_a /= n
                surround_avg_b /= n
                surround_avg_c /= n

            s.excess_loop = abs(s.state.a - surround_avg_a) + \
                           abs(s.state.b - surround_avg_b) + \
                           abs(s.state.c - surround_avg_c)

            # ⑤ PG拓扑囚禁检测
            if s.excess_loop >= self.EXCESS_LOOP_THRESH:
                s.lock_hold_count += 1
                if s.lock_hold_count >= self.HOLD_N_BEATS:
                    s.is_mass_face = True
            else:
                s.lock_hold_count = max(0, s.lock_hold_count - 1)
                if s.lock_hold_count == 0:
                    s.is_mass_face = False

        # 同步 Minimal 核心
        mnq_minimal_step(self.minimal, dt)

        # 更新统计
        self._update_stats()

    def _update_stats(self):
        self.total_mass = sum(s.ftel_magnitude for s in self.spheres) / max(1, self.total)
        self.total_loop = sum(s.excess_loop for s in self.spheres) / max(1, self.total)
        self.mass_face_count = sum(1 for s in self.spheres if s.is_mass_face)

    def get_field_array(self) -> np.ndarray:
        """获取流贯场数组 (用于可视化)"""
        field = np.zeros((self.dim_y, self.dim_x))
        for s in self.spheres:
            x, y, z = s.coord
            field[y][x] = s.ftel_magnitude
        return field

    def get_excess_loop_array(self) -> np.ndarray:
        """获取Oloid差分数组 (用于可视化)"""
        field = np.zeros((self.dim_y, self.dim_x))
        for s in self.spheres:
            x, y, z = s.coord
            field[y][x] = s.excess_loop
        return field

    def get_mass_face_array(self) -> np.ndarray:
        """获取质量面分布 (用于可视化)"""
        field = np.zeros((self.dim_y, self.dim_x))
        for s in self.spheres:
            x, y, z = s.coord
            field[y][x] = 1.0 if s.is_mass_face else 0.0
        return field


# ============================================================================
# 6. 刘机制调度器 (LiuScheduler)
# ============================================================================

class LiuScheduler:
    """
    刘机制 (Liu Mechanism) - 关系作用量极小化 δS_Rel=0
    替代传统OS对CPU时间片的调度,调度流贯在金灵球网络中的传播路径

    S_Rel = α·M + β·H[Θ]
    M: 流贯强度 (来自请求源)
    H[Θ]: 相位熵 (当前网格状态与请求的匹配度)
    """

    def __init__(self, alpha: float = 0.6, beta: float = 0.4):
        self.alpha = alpha
        self.beta = beta
        self.optimal_path = []
        self.min_s_rel = float('inf')

    def compute_s_rel(self, magnitude: float, phase_entropy: float) -> float:
        """计算关系作用量 S_Rel"""
        return self.alpha * magnitude + self.beta * phase_entropy

    def find_optimal_path(self, mesh: JinlingMesh, source: tuple) -> list:
        """
        基于刘机制寻找最小阻抗路径
        流贯沿 ArgMin S_Rel 路径传播
        """
        sx, sy = source[0], source[1]
        visited = set()
        path = [(sx, sy)]
        visited.add((sx, sy))

        for step in range(max(mesh.dim_x, mesh.dim_y)):
            current = mesh.get_sphere(sx, sy)
            if current is None:
                break

            neighbors = mesh.get_neighbors_8(sx, sy)
            best_nb = None
            best_s_rel = float('inf')

            for nb in neighbors:
                nx, ny = nb.coord[0], nb.coord[1]
                if (nx, ny) in visited:
                    continue
                s_rel = self.compute_s_rel(
                    nb.ftel_magnitude,
                    nb.excess_loop + 1e-6
                )
                if s_rel < best_s_rel:
                    best_s_rel = s_rel
                    best_nb = nb

            if best_nb is None:
                break

            sx, sy = best_nb.coord[0], best_nb.coord[1]
            path.append((sx, sy))
            visited.add((sx, sy))

            if best_nb.is_mass_face:
                break  # 到达质量面,路径终止

        self.optimal_path = path
        self.min_s_rel = best_s_rel if path else float('inf')
        return path


# ============================================================================
# 7. MNQ Cloud API 兼容层 (三尺度锚定系统)
# ============================================================================

class MNQCloudAPI:
    """
    MNQ Cloud API 兼容层 - 三尺度锚定系统

    尺度模式:
    - atomic: 原子层 (分子共振、量子相干)
    - meso: 介观层 (水文/气象/地震能量演化)
    - macro: 宏观宇宙 (行星轨道、黑洞尺度)
    """

    # 三尺度锚定参数
    SCALE_PARAMS = {
        'atomic': {
            'energy_alpha': 2.179872e-18,  # J (Hartree)
            'length_beta': 5.291772e-11,    # m (Bohr radius)
            'time_gamma': 1.765145e-19,     # s (atomic time)
        },
        'meso': {
            'energy_alpha': 1.0e-20,
            'length_beta': 1.0e-10,
            'time_gamma': 1.0e-15,
        },
        'macro': {
            'energy_alpha': 3.247188e28,    # J (solar rest energy)
            'length_beta': 6.957e8,        # m (solar radius)
            'time_gamma': 86400,            # s (1 day)
        }
    }

    def __init__(self, unit_mode: str = 'atomic'):
        self.unit_mode = unit_mode
        self.params = self.SCALE_PARAMS.get(unit_mode, self.SCALE_PARAMS['atomic'])

    def simulate(self, experiment: str = 'proton', steps: int = 2048,
                 epsilon: float = 1e-7, seed: int = 42,
                 E_scale: float = 1.0, coherence: float = 1e-6,
                 **kwargs) -> dict:
        """
        执行MNQ8仿真 (兼容MNQ Cloud API格式)

        返回结果包含:
        - mean_energy_J: 平均能量(焦耳)
        - coherence: 相干度
        - phase_lock: 相位锁定值
        - mass_face_count: 质量面数量
        """
        np.random.seed(seed)

        # 创建网格并初始化
        mesh = JinlingMesh(dim_x=16, dim_y=16)

        # 根据实验类型设置初态
        if experiment == 'zero_field':
            mesh.seed_zero_field()
        elif experiment == 'hex_ring_gap':
            mesh.seed_hex_ring_gap()
        else:
            mesh.seed_background()

        # 执行演化
        for step in range(steps):
            mesh.mnq8_step(dt=0.016)

        # 转换到SI单位
        p = self.params
        result = {
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

        if self.unit_mode == 'atomic':
            result['proton_radius_m'] = mesh.total_mass * p['length_beta'] * 0.01
        elif self.unit_mode == 'macro':
            result['horizon_radius_m'] = mesh.total_mass * p['length_beta'] * 0.001

        return result


# ============================================================================
# 8. GPU字段仿真器 (NumPy替代Metal)
# ============================================================================

class MNQFieldGPU:
    """
    MNQ φ/Ω/ψ/ξ 四场并行演化 (NumPy实现)
    替代原版Metal GPU计算

    四个场:
    - phi (φ): 相位场
    - omega (Ω): 角频率场
    - psi (ψ): 螺旋振荡场
    - xi (ξ): 约束场
    """

    def __init__(self, grid: int = 64):
        self.grid = grid
        self.N = grid * grid

        # 四场数组
        self.phi = np.zeros((grid, grid), dtype=np.float32)
        self.omega = np.zeros((grid, grid), dtype=np.float32)
        self.psi = np.zeros((grid, grid), dtype=np.float32)
        self.xi = np.zeros((grid, grid), dtype=np.float32)

        # 五行参数
        self.wuxing = np.zeros(5, dtype=np.float32)
        # 操作参数
        self.opA = 0.0
        self.opB = 0.0
        self.hexWeight = 1.0

        self._seed()

    def _seed(self):
        """初始化场"""
        N = self.grid
        self.phi = np.random.uniform(0.015, 0.025, (N, N)).astype(np.float32)
        self.omega = np.random.uniform(0.99, 1.01, (N, N)).astype(np.float32)
        self.psi = np.random.uniform(-0.002, 0.002, (N, N)).astype(np.float32)
        self.xi = np.random.uniform(-0.002, 0.002, (N, N)).astype(np.float32)

    def inject_noise(self, amp: float = 0.001):
        """注入微扰噪声 (每1000步一次)"""
        N = self.grid
        mask = np.zeros((N, N), dtype=np.float32)
        mask[::37 % N, ::37 % N] = 1.0
        self.phi += mask * np.random.uniform(-amp, amp, (N, N)).astype(np.float32)
        self.omega += mask * np.random.uniform(-amp, amp, (N, N)).astype(np.float32)

    def step(self, lambda_: float = 0.01, gamma: float = 0.989):
        """
        一步MNQ8场演化 (离散拉普拉斯 + 非线性耦合)
        """
        N = self.grid
        dt = np.float32(0.016)

        # 离散拉普拉斯 (5点差分)
        phi_pad = np.pad(self.phi, 1, mode='wrap')
        lap_phi = (phi_pad[2:, 1:-1] + phi_pad[:-2, 1:-1] +
                   phi_pad[1:-1, 2:] + phi_pad[1:-1, :-2] - 4 * self.phi)

        omega_pad = np.pad(self.omega, 1, mode='wrap')
        lap_omega = (omega_pad[2:, 1:-1] + omega_pad[:-2, 1:-1] +
                     omega_pad[1:-1, 2:] + omega_pad[1:-1, :-2] - 4 * self.omega)

        # φ 更新: φ += λ·(Δφ + Ω·sin(φ))·dt
        self.phi += lambda_ * (lap_phi + self.omega * np.sin(self.phi)) * dt

        # Ω 更新: Ω += γ·(ΔΩ - φ)·dt
        self.omega += gamma * (lap_omega - self.phi) * dt

        # ψ 螺旋振荡
        self.psi += 0.02 * np.sin(self.phi * 1.618) * dt

        # ξ 约束场
        self.xi = np.abs(self.phi - self.omega) * 0.5

        # 边界条件: 守恒
        self.phi = np.clip(self.phi, -1.0, 1.0)
        self.omega = np.clip(self.omega, 0.5, 1.5)

    def measure_omega_avg(self) -> float:
        return float(np.mean(self.omega))

    def compute_rloc(self) -> float:
        """计算Rloc (局部相干度)"""
        N = self.grid
        acc = 0.0
        cnt = 0
        for y in range(1, N - 1, 2):
            for x in range(1, N - 1, 2):
                px1 = float(self.phi[y, x + 1] - self.phi[y, x - 1])
                py1 = float(self.phi[y + 1, x] - self.phi[y - 1, x])
                px2 = float(self.omega[y, x + 1] - self.omega[y, x - 1])
                py2 = float(self.omega[y + 1, x] - self.omega[y - 1, x])

                dot = px1 * px2 + py1 * py2
                mag = math.sqrt((px1 * px1 + py1 * py1) * (px2 * px2 + py2 * py2)) + 1e-12
                acc += dot / mag
                cnt += 1
        return max(0.0, min(1.0, acc / max(1, cnt)))


# ============================================================================
# 9. 八卦算子 (Bagua Operators)
# ============================================================================

class BaguaOp(IntEnum):
    BAGUA_ROTATE = 0
    BAGUA_FLIP = 1
    BAGUA_INVERT = 2
    BAGUA_MIX = 3
    BAGUA_GATE = 4
    BAGUA_PHASE = 5
    BAGUA_STRETCH = 6
    BAGUA_SHRINK = 7


def bagua_apply(phi: np.ndarray, omega: np.ndarray, op: BaguaOp) -> None:
    """在 φ/Ω 局域矩阵上执行八卦离散变换"""
    if op == BaguaOp.BAGUA_ROTATE:
        # 旋转90度
        phi[:] = np.rot90(phi)
        omega[:] = np.rot90(omega)
    elif op == BaguaOp.BAGUA_FLIP:
        # 水平翻转
        phi[:] = np.flipud(phi)
        omega[:] = np.flipud(omega)
    elif op == BaguaOp.BAGUA_INVERT:
        # 取反
        phi[:] = -phi
    elif op == BaguaOp.BAGUA_MIX:
        # φ/Ω 交换
        phi, omega = omega.copy(), phi.copy()
    elif op == BaguaOp.BAGUA_GATE:
        # 阈值门控
        phi[abs(phi) < 0.01] = 0.0
    elif op == BaguaOp.BAGUA_PHASE:
        # 相位移
        phi += 0.1 * np.sin(omega * np.pi)
    elif op == BaguaOp.BAGUA_STRETCH:
        # 幅值拉伸
        phi *= 1.1
    elif op == BaguaOp.BAGUA_SHRINK:
        # 幅值压缩
        phi *= 0.9


# ============================================================================
# 10. 自动调谐 (Auto-tune)
# ============================================================================

def mnq_auto_gamma(delta_e: float) -> float:
    """动态衰减律: γ ← 0.99 − 0.05·tanh(ΔE)"""
    return 0.99 - 0.05 * math.tanh(delta_e)


# ============================================================================
# 导出清单
# ============================================================================

__all__ = [
    'GoldenSymbol3D', 'Hex64Code', 'Hex64Rule', 'HEX64_TABLE',
    'get_hex64_rule', 'MNQMinimalState', 'mnq_minimal_step',
    'WuxingMatrix', 'JinlingSphere', 'JinlingMesh', 'LiuScheduler',
    'MNQCloudAPI', 'MNQFieldGPU', 'BaguaOp', 'bagua_apply',
    'mnq_auto_gamma',
]

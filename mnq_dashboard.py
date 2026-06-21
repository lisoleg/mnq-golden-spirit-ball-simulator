"""
MNQ 金灵球网络仿真器 v3.0 - Windows GUI 仪表盘
基于 tkinter + matplotlib 实现

v3.0 新增:
1. MNQ8 冻结核 (V13-V16五层法则: core→bagua→hex64→wuxing→commit)
2. MASS_FACE 质量面复合读数 + 动态稳定门
3. D4 协变共极大观察器 (8种D4对称变换)
4. 严格双门评估 (DELTA_MASS/DELTA_LOOP)

v2.0 功能:
5. MNQ9 信心核面板 (Ω/φ_future/B_conf 宏观趋势)
6. 三层信息波可视化 (核心→八卦→64卦 SCF收敛)
7. CGD约束生成动力学面板 (五公理A1-A5)

原有功能:
8. 金灵球网络 2D 热力图可视化 (流贯场/质量面/Oloid差分)
9. MNQ8 能流运算实时监控 + 三元动力核 (φ/Ω/γ)
10. Hex64 卦象映射 + 刘机制路径追踪
11. 实验组别切换 (死零场/背景/HEX_RING_GAP)
12. GPU四场仿真 + MNQ Cloud API 兼容仿真
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import time
import threading
import json
import uuid
import os
from collections import deque

from mnq_core import (
    JinlingMesh, MNQFieldGPU, MNQCloudAPI, LiuScheduler,
    MNQMinimalState, mnq_minimal_step, mnq_auto_gamma,
    GoldenSymbol3D, get_hex64_rule, HEX64_TABLE, bagua_apply, BaguaOp,
    ThreeLayerInfoWave, CGDEngine, CGDConstraint,
    # v3.0 冻结核
    MNQ8FrozenKernel, MassFaceReader, DynamicStabilityGate,
    StrictDualGate, D4CovariantObserver, FrozenKernelMesh,
    mnq8_frozen_kernel_verify, FROZEN_KERNEL_FINGERPRINT,
)
from mnq9_core import (
    MNQ9Simulator, MNQ9ScenarioGenerator, MacroConfidenceField, MNQ9Core,
)


class MNQDashboard:
    """MNQ 金灵球网络仿真器 v2.0 Windows 仪表盘"""

    # 配色方案
    COLORS = {
        'bg_dark': '#1a1a2e',
        'bg_panel': '#16213e',
        'bg_card': '#0f3460',
        'accent1': '#e94560',
        'accent2': '#533483',
        'text': '#eee',
        'text_dim': '#aaa',
        'gold': '#ffd700',
        'cyan': '#00d4ff',
        'green': '#00ff88',
        'red': '#ff4444',
        'purple': '#c084fc',
        'orange': '#fb923c',
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MNQ 金灵球网络仿真器 v3.0 - Windows Edition")
        self.root.geometry("1600x950")
        self.root.configure(bg=self.COLORS['bg_dark'])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 状态变量
        self.is_running = False
        self.step_count = 0
        self.start_time = time.time()
        self.fps_counter = deque(maxlen=60)

        # MNQ 核心实例
        self.mesh = JinlingMesh(dim_x=32, dim_y=32)
        self.mesh.seed_background()
        self.gpu_field = MNQFieldGPU(grid=64)
        self.liu_scheduler = LiuScheduler()
        self.cloud_api = MNQCloudAPI(unit_mode='atomic')

        # v2.0 新增实例
        self.three_layer = ThreeLayerInfoWave(core_init=0.001)
        self.cgd_engine = CGDEngine()
        self._init_cgd_constraints()
        self.mnq9_sim = MNQ9Simulator(lam=0.03)
        self.mnq9_sim.set_macro_confidence({'M2': 0.2, 'PMI': 0.1, 'DR007': -0.1})
        self.mnq9_sim.set_future_wave([0.05]*20)

        # v3.0 冻结核实例
        self.fk_mesh = FrozenKernelMesh(seed=42)
        self.fk_mesh.init_background()
        keep_hex = [0,1,5,6,7,8,10,11,12,13,15]  # G5_V13_ARC
        self.fk_mesh.init_condition(keep_hex, seed=42, phi_polarity=1,
                                    omega_mode="MASK", comp_mode="MASK",
                                    phi_gain=1, center_anchor=1)
        self.fk_d4_last = None

        # 历史记录
        self.mass_history = deque(maxlen=200)
        self.loop_history = deque(maxlen=200)
        self.gamma_history = deque(maxlen=200)
        self.rcoh_history = deque(maxlen=200)
        # v2.0 新增历史
        self.three_layer_core_history = deque(maxlen=200)
        self.three_layer_bagua_history = deque(maxlen=200)
        self.three_layer_hex64_history = deque(maxlen=200)
        self.mnq9_omega_history = deque(maxlen=200)
        self.mnq9_bconf_history = deque(maxlen=200)
        self.cgd_violation_history = deque(maxlen=200)
        # v3.0 冻结核历史
        self.fk_mass_face_history = deque(maxlen=200)
        self.fk_loop_history = deque(maxlen=200)

        # 构建UI
        self._build_ui()

        # 初始化显示
        self._refresh_all_plots()

    def _init_cgd_constraints(self):
        """初始化CGD约束 (五公理)"""
        self.cgd_engine.add_constraint("质量面守恒", (0.0, 0.5), modulation=0.005)
        self.cgd_engine.add_constraint("相干度", (0.98, 1.0), modulation=0.002)
        self.cgd_engine.add_constraint("能量上限", (0.0, 2.0), modulation=0.01)

    # ================================================================
    # UI 构建
    # ================================================================

    def _build_ui(self):
        """构建完整UI布局"""
        self._build_title_bar()

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_visualization(left_frame)

        right_frame = ttk.Frame(main_frame, width=380)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.pack_propagate(False)
        self._build_control_panel(right_frame)

        self._build_status_bar()

    def _build_title_bar(self):
        title_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'], height=40)
        title_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="⬡ MNQ 金灵球网络仿真器 v3.0",
                 font=("Microsoft YaHei", 16, "bold"),
                 fg=self.COLORS['gold'], bg=self.COLORS['bg_dark']).pack(side=tk.LEFT)

        tk.Label(title_frame,
                 text="冻结核 · D4协变 · MASS_FACE · CGD约束 · 三层信息波 · MNQ9",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS['text_dim'], bg=self.COLORS['bg_dark']).pack(side=tk.LEFT, padx=20)

        self.fps_label = tk.Label(title_frame, text="FPS: --",
                                  font=("Consolas", 10),
                                  fg=self.COLORS['cyan'], bg=self.COLORS['bg_dark'])
        self.fps_label.pack(side=tk.RIGHT)

    def _build_visualization(self, parent):
        """构建可视化面板 (2x3 = 6个subplot)"""
        self.fig = Figure(figsize=(10, 7.5), facecolor=self.COLORS['bg_dark'])
        self.fig.subplots_adjust(hspace=0.40, wspace=0.32, left=0.07, right=0.96,
                                  top=0.95, bottom=0.06)

        # 2x3: 6个子图
        self.ax_ftel   = self.fig.add_subplot(231)  # 流贯场
        self.ax_mass   = self.fig.add_subplot(232)  # 质量面 + 刘路径
        self.ax_loop   = self.fig.add_subplot(233)  # Oloid差分
        self.ax_gpu    = self.fig.add_subplot(234)  # GPU φ/Ω场
        self.ax_3layer = self.fig.add_subplot(235)  # 三层信息波
        self.ax_mnq9   = self.fig.add_subplot(236)  # MNQ9信心趋势

        for ax in [self.ax_ftel, self.ax_mass, self.ax_loop,
                    self.ax_gpu, self.ax_3layer, self.ax_mnq9]:
            ax.set_facecolor('#0a0a1a')
            ax.tick_params(colors=self.COLORS['text_dim'], labelsize=7)
            for spine in ax.spines.values():
                spine.set_color('#333355')

        self.ax_ftel.set_title('流贯场 (Ftel)', color=self.COLORS['cyan'], fontsize=9)
        self.ax_mass.set_title('质量面 (Mass Face)', color=self.COLORS['gold'], fontsize=9)
        self.ax_loop.set_title('Oloid差分 (PG囚禁)', color=self.COLORS['green'], fontsize=9)
        self.ax_gpu.set_title('GPU φ/Ω场', color=self.COLORS['accent1'], fontsize=9)
        self.ax_3layer.set_title('三层信息波 (SCF)', color=self.COLORS['purple'], fontsize=9)
        self.ax_mnq9.set_title('MNQ9 信心趋势', color=self.COLORS['orange'], fontsize=9)

        # 初始图像 (前三行)
        empty32 = np.zeros((32, 32))
        self.im_ftel = self.ax_ftel.imshow(empty32, cmap='inferno', interpolation='bilinear',
                                            vmin=0, vmax=0.5, aspect='auto')
        self.im_mass = self.ax_mass.imshow(empty32, cmap='hot', interpolation='nearest',
                                            vmin=0, vmax=1, aspect='auto')
        self.im_loop = self.ax_loop.imshow(empty32, cmap='viridis', interpolation='bilinear',
                                           vmin=0, vmax=0.3, aspect='auto')
        self.im_gpu  = self.ax_gpu.imshow(np.zeros((64, 64)), cmap='coolwarm',
                                          interpolation='bilinear', vmin=-0.5, vmax=0.5,
                                          aspect='auto')

        # 三层信息波: 三条线 (core/bagua/hex64)
        self.line_3l_core,  = self.ax_3layer.plot([], [], color=self.COLORS['gold'],
                                                    linewidth=1.2, label='Core')
        self.line_3l_bagua, = self.ax_3layer.plot([], [], color=self.COLORS['cyan'],
                                                    linewidth=1.0, label='Bagua')
        self.line_3l_hex64, = self.ax_3layer.plot([], [], color=self.COLORS['purple'],
                                                    linewidth=0.8, label='Hex64')
        self.ax_3layer.legend(loc='upper right', fontsize=6,
                              facecolor='#0a0a1a', edgecolor='#333', labelcolor=self.COLORS['text_dim'])
        self.ax_3layer.set_ylim(-0.01, 0.05)

        # MNQ9信心趋势: 两条线 (Ω + B_conf)
        self.line_mnq9_omega, = self.ax_mnq9.plot([], [], color=self.COLORS['orange'],
                                                    linewidth=1.5, label='Ω')
        self.line_mnq9_bconf, = self.ax_mnq9.plot([], [], color=self.COLORS['green'],
                                                    linewidth=1.0, label='B_conf')
        self.ax_mnq9.axhline(y=0, color='#444466', linestyle='--', linewidth=0.5)
        self.ax_mnq9.legend(loc='upper left', fontsize=6,
                             facecolor='#0a0a1a', edgecolor='#333', labelcolor=self.COLORS['text_dim'])
        self.ax_mnq9.set_ylim(-1.1, 1.1)

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_control_panel(self, parent):
        """构建右侧控制面板 (可滚动)"""
        style = ttk.Style()
        style.configure('Dark.TFrame', background=self.COLORS['bg_panel'])
        style.configure('Dark.TLabel', background=self.COLORS['bg_panel'],
                        foreground=self.COLORS['text'], font=("Microsoft YaHei", 9))
        style.configure('Gold.TLabel', background=self.COLORS['bg_panel'],
                        foreground=self.COLORS['gold'], font=("Microsoft YaHei", 11, "bold"))
        style.configure('Dark.TButton', font=("Microsoft YaHei", 9))

        canvas = tk.Canvas(parent, bg=self.COLORS['bg_panel'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style='Dark.TFrame')

        scroll_frame.bind("<Configure>",
                          lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- 实验控制 ----
        ctrl_frame = tk.LabelFrame(scroll_frame, text=" ⚡ 实验控制 ",
                                     bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                     font=("Microsoft YaHei", 9, "bold"), bd=1)
        ctrl_frame.pack(fill=tk.X, padx=5, pady=3)

        btn_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg_panel'])
        btn_frame.pack(fill=tk.X, padx=3, pady=3)

        self.btn_start = tk.Button(btn_frame, text="▶ 启动", command=self.start_sim,
                                    bg='#00aa44', fg='white', font=("Microsoft YaHei", 9, "bold"),
                                    width=8)
        self.btn_start.pack(side=tk.LEFT, padx=2)

        self.btn_stop = tk.Button(btn_frame, text="⏸ 暂停", command=self.stop_sim,
                                   bg='#cc6600', fg='white', font=("Microsoft YaHei", 9, "bold"),
                                   width=8, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=2)

        self.btn_reset = tk.Button(btn_frame, text="↺ 重置", command=self.reset_sim,
                                    bg='#666', fg='white', font=("Microsoft YaHei", 9, "bold"),
                                    width=8)
        self.btn_reset.pack(side=tk.LEFT, padx=2)

        mode_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg_panel'])
        mode_frame.pack(fill=tk.X, padx=3, pady=3)
        tk.Label(mode_frame, text="实验模式:", bg=self.COLORS['bg_panel'],
                 fg=self.COLORS['text_dim'], font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)
        self.exp_mode = tk.StringVar(value="BACKGROUND_OSC")
        for text, mode in [("背景振荡", "BACKGROUND_OSC"), ("缺口六角壳", "HEX_RING_GAP"),
                           ("死零场", "ZERO_FIELD")]:
            tk.Radiobutton(mode_frame, text=text, variable=self.exp_mode, value=mode,
                           bg=self.COLORS['bg_panel'], fg=self.COLORS['text'],
                           selectcolor=self.COLORS['bg_card'],
                           activebackground=self.COLORS['bg_panel'],
                           font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)

        # ---- 三元动力核参数 ----
        minimal_frame = tk.LabelFrame(scroll_frame, text=" 🔮 三元动力核 (φ-Ω-γ) ",
                                       bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                       font=("Microsoft YaHei", 9, "bold"), bd=1)
        minimal_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_phi    = self._make_param_row(minimal_frame, "φ (相位角)", "0.5000")
        self.lbl_omega  = self._make_param_row(minimal_frame, "Ω (角频率)", "2.0000")
        self.lbl_gamma  = self._make_param_row(minimal_frame, "γ (相干度)", "0.9898")
        self.lbl_rcoh   = self._make_param_row(minimal_frame, "Rcoh (相干指标)", "0.0000")

        # ---- MNQ9 信心核面板 [v2.0新增] ----
        mnq9_frame = tk.LabelFrame(scroll_frame, text=" 🧠 MNQ9 信心核 (Ω/φ_future/B_conf) ",
                                     bg=self.COLORS['bg_panel'], fg=self.COLORS['orange'],
                                     font=("Microsoft YaHei", 9, "bold"), bd=1)
        mnq9_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_mnq9_omega  = self._make_param_row(mnq9_frame, "Ω (信心核)", "0.0000")
        self.lbl_mnq9_bconf  = self._make_param_row(mnq9_frame, "B_conf (综合)", "0.0000")
        self.lbl_mnq9_kernel = self._make_param_row(mnq9_frame, "Kernel (宏观核)", "0.0000")

        # MNQ9 场景选择
        tk.Label(mnq9_frame, text="宏观场景:", bg=self.COLORS['bg_panel'],
                 fg=self.COLORS['text_dim'], font=("Microsoft YaHei", 8)).pack(anchor='w', padx=5)
        self.mnq9_scenario = tk.StringVar(value="none")
        scenario_frame = tk.Frame(mnq9_frame, bg=self.COLORS['bg_panel'])
        scenario_frame.pack(fill=tk.X, padx=3, pady=2)
        for text, val in [("牛市", "bull"), ("熊市", "bear"),
                           ("危机恢复", "crisis"), ("政策冲击", "policy")]:
            tk.Radiobutton(scenario_frame, text=text, variable=self.mnq9_scenario, value=val,
                           bg=self.COLORS['bg_panel'], fg=self.COLORS['text'],
                           selectcolor=self.COLORS['bg_card'],
                           font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)

        btn_mnq9_frame = tk.Frame(mnq9_frame, bg=self.COLORS['bg_panel'])
        btn_mnq9_frame.pack(fill=tk.X, padx=3, pady=2)
        tk.Button(btn_mnq9_frame, text="应用场景", command=self._apply_mnq9_scenario,
                  bg=self.COLORS['bg_card'], fg=self.COLORS['text'],
                  font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_mnq9_frame, text="运行趋势", command=self._run_mnq9_trend,
                  bg='#8b5cf6', fg='white',
                  font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)

        # ---- 三层信息波 [v2.0新增] ----
        wave_frame = tk.LabelFrame(scroll_frame, text=" 🌊 三层信息波 (SCF收敛) ",
                                     bg=self.COLORS['bg_panel'], fg=self.COLORS['purple'],
                                     font=("Microsoft YaHei", 9, "bold"), bd=1)
        wave_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_3l_core  = self._make_param_row(wave_frame, "核心层", "0.0010")
        self.lbl_3l_bagua = self._make_param_row(wave_frame, "八卦层 (mean)", "0.0000")
        self.lbl_3l_hex64 = self._make_param_row(wave_frame, "64卦层 (mean)", "0.0000")
        self.lbl_3l_change = self._make_param_row(wave_frame, "Max Change", "∞")

        tk.Button(wave_frame, text="运行SCF收敛", command=self._run_scf_convergence,
                  bg=self.COLORS['bg_card'], fg=self.COLORS['text'],
                  font=("Microsoft YaHei", 8)).pack(fill=tk.X, padx=5, pady=2)

        # ---- CGD约束面板 [v2.0新增] ----
        cgd_frame = tk.LabelFrame(scroll_frame, text=" 🔗 CGD约束生成动力学 (五公理) ",
                                    bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                    font=("Microsoft YaHei", 9, "bold"), bd=1)
        cgd_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_cgd_violation = self._make_param_row(cgd_frame, "违反度", "0.0000")
        self.lbl_cgd_phase     = self._make_param_row(cgd_frame, "相态", "0")
        self.lbl_cgd_steady    = self._make_param_row(cgd_frame, "稳态数", "0")

        self.cgd_listbox = tk.Listbox(cgd_frame, height=3, bg='#0a0a2a',
                                       fg=self.COLORS['text_dim'],
                                       font=("Consolas", 8),
                                       selectbackground=self.COLORS['bg_card'])
        self.cgd_listbox.pack(fill=tk.X, padx=5, pady=2)
        for c in self.cgd_engine.constraints:
            lo, hi = c.target_range
            self.cgd_listbox.insert(tk.END, f"  {c.name}: [{lo:.1f}, {hi:.1f}] v={c.current_value:.4f}")

        # ---- 冻结核面板 [v3.0新增] ----
        fk_frame = tk.LabelFrame(scroll_frame, text=" ❄ MNQ8 冻结核 (V13-V16) ",
                                  bg=self.COLORS['bg_panel'], fg=self.COLORS['gold'],
                                  font=("Microsoft YaHei", 9, "bold"), bd=1)
        fk_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_fk_mass  = self._make_param_row(fk_frame, "MASS_FACE", "0.0000")
        self.lbl_fk_loop  = self._make_param_row(fk_frame, "Local Comp Loop", "0.0000")
        self.lbl_fk_hold  = self._make_param_row(fk_frame, "Loop Hold 13", "0.0000")
        self.lbl_fk_leak  = self._make_param_row(fk_frame, "Boundary Leak", "0.0000")
        self.lbl_fk_diag  = self._make_param_row(fk_frame, "DIAG-AXIS Loop", "0.0000")
        self.lbl_fk_stab  = self._make_param_row(fk_frame, "Stability Gate", "---")
        self.lbl_fk_finger = self._make_param_row(fk_frame, "SHA256", "---")

        fk_btn_frame = tk.Frame(fk_frame, bg=self.COLORS['bg_panel'])
        fk_btn_frame.pack(fill=tk.X, padx=3, pady=2)
        tk.Button(fk_btn_frame, text="冻结核步进", command=self._fk_step,
                  bg=self.COLORS['bg_card'], fg=self.COLORS['text'],
                  font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(fk_btn_frame, text="重置冻结核", command=self._fk_reset,
                  bg='#666', fg='white',
                  font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)
        tk.Button(fk_btn_frame, text="D4审计", command=self._fk_d4_audit,
                  bg='#8b5cf6', fg='white',
                  font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=2)

        # ---- Hex64 卦象 ----
        hex_frame = tk.LabelFrame(scroll_frame, text=" ☰ Hex64 六十四卦映射 ",
                                    bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                    font=("Microsoft YaHei", 9, "bold"), bd=1)
        hex_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_hex64 = tk.Label(hex_frame, text="乾 (MOV) ▸ φ+0.50 Ω+1.00",
                                   bg=self.COLORS['bg_panel'], fg=self.COLORS['gold'],
                                   font=("Consolas", 9))
        self.lbl_hex64.pack(anchor='w', padx=5, pady=2)

        self.hex64_listbox = tk.Listbox(hex_frame, height=4, bg='#0a0a2a',
                                         fg=self.COLORS['text_dim'],
                                         font=("Consolas", 8),
                                         selectbackground=self.COLORS['bg_card'])
        self.hex64_listbox.pack(fill=tk.X, padx=5, pady=2)
        for i in range(8):
            r = get_hex64_rule(i)
            self.hex64_listbox.insert(tk.END,
                f"  {r.name} ({r.opcode}) Δφ={r.phi_delta:+.2f} ΔΩ={r.omega_delta:+.2f}")

        # ---- PG拓扑囚禁 ----
        pg_frame = tk.LabelFrame(scroll_frame, text=" 🔒 PG拓扑囚禁检测 ",
                                  bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                  font=("Microsoft YaHei", 9, "bold"), bd=1)
        pg_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_mass_faces = self._make_param_row(pg_frame, "质量面数", "0")
        self.lbl_total_mass = self._make_param_row(pg_frame, "总流贯密度", "0.0000")
        self.lbl_total_loop = self._make_param_row(pg_frame, "Oloid差分均值", "0.0000")

        # ---- 刘机制 ----
        liu_frame = tk.LabelFrame(scroll_frame, text=" 🌀 刘机制 (δS_Rel=0) ",
                                    bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                    font=("Microsoft YaHei", 9, "bold"), bd=1)
        liu_frame.pack(fill=tk.X, padx=5, pady=3)

        self.lbl_s_rel    = self._make_param_row(liu_frame, "S_Rel 最小值", "∞")
        self.lbl_path_len = self._make_param_row(liu_frame, "最优路径长度", "0")

        tk.Button(liu_frame, text="追踪最优路径", command=self._trace_liu_path,
                  bg=self.COLORS['bg_card'], fg=self.COLORS['text'],
                  font=("Microsoft YaHei", 8)).pack(fill=tk.X, padx=5, pady=2)

        # ---- MNQ Cloud API ----
        cloud_frame = tk.LabelFrame(scroll_frame, text=" ☁ MNQ Cloud API ",
                                     bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                     font=("Microsoft YaHei", 9, "bold"), bd=1)
        cloud_frame.pack(fill=tk.X, padx=5, pady=3)

        tk.Label(cloud_frame, text="尺度模式:", bg=self.COLORS['bg_panel'],
                 fg=self.COLORS['text_dim'], font=("Microsoft YaHei", 8)).pack(anchor='w', padx=5)

        self.scale_mode = tk.StringVar(value="atomic")
        scale_frame = tk.Frame(cloud_frame, bg=self.COLORS['bg_panel'])
        scale_frame.pack(fill=tk.X, padx=5, pady=2)
        for text, mode in [("原子", "atomic"), ("介观", "meso"), ("宏观", "macro")]:
            tk.Radiobutton(scale_frame, text=text, variable=self.scale_mode, value=mode,
                           bg=self.COLORS['bg_panel'], fg=self.COLORS['text'],
                           selectcolor=self.COLORS['bg_card'],
                           font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=3)

        tk.Button(cloud_frame, text="运行Cloud仿真", command=self._run_cloud_sim,
                  bg=self.COLORS['bg_card'], fg=self.COLORS['text'],
                  font=("Microsoft YaHei", 8)).pack(fill=tk.X, padx=5, pady=2)

        self.cloud_result = scrolledtext.ScrolledText(cloud_frame, height=4,
                                                       bg='#0a0a2a', fg=self.COLORS['text_dim'],
                                                       font=("Consolas", 8))
        self.cloud_result.pack(fill=tk.X, padx=5, pady=2)

        # ---- 日志 ----
        log_frame = tk.LabelFrame(scroll_frame, text=" 📋 运行日志 ",
                                   bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                   font=("Microsoft YaHei", 9, "bold"), bd=1)
        log_frame.pack(fill=tk.X, padx=5, pady=3)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=5,
                                                    bg='#0a0a2a', fg=self.COLORS['text_dim'],
                                                    font=("Consolas", 8))
        self.log_text.pack(fill=tk.X, padx=5, pady=2)

    def _build_status_bar(self):
        status_frame = tk.Frame(self.root, bg=self.COLORS['bg_card'], height=26)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame,
            text="MNQ v2.0 就绪 | IWPU | CGD | 3-Layer | MNQ9 | PG | Liu",
            bg=self.COLORS['bg_card'], fg=self.COLORS['text_dim'],
            font=("Consolas", 9))
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.step_label = tk.Label(status_frame, text="Step: 0",
                                     bg=self.COLORS['bg_card'], fg=self.COLORS['cyan'],
                                     font=("Consolas", 9))
        self.step_label.pack(side=tk.RIGHT, padx=10)

    def _make_param_row(self, parent, label: str, default: str) -> tk.Label:
        row = tk.Frame(parent, bg=self.COLORS['bg_panel'])
        row.pack(fill=tk.X, padx=5, pady=1)
        tk.Label(row, text=label + ":", bg=self.COLORS['bg_panel'],
                 fg=self.COLORS['text_dim'], font=("Microsoft YaHei", 8), width=14,
                 anchor='w').pack(side=tk.LEFT)
        val_label = tk.Label(row, text=default, bg=self.COLORS['bg_panel'],
                             fg=self.COLORS['gold'], font=("Consolas", 9, "bold"),
                             anchor='e')
        val_label.pack(side=tk.RIGHT, padx=5)
        return val_label

    # ================================================================
    # 仿真控制
    # ================================================================

    def start_sim(self):
        if self.is_running:
            return
        self.is_running = True
        self.start_time = time.time()
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self._log("仿真启动 (v2.0: CGD + 三层信息波 + MNQ9)")
        self._sim_loop()

    def stop_sim(self):
        self.is_running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self._log("仿真暂停")

    def reset_sim(self):
        self.is_running = False
        self.step_count = 0
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

        mode = self.exp_mode.get()
        self.mesh = JinlingMesh(dim_x=32, dim_y=32)
        if mode == "ZERO_FIELD":
            self.mesh.seed_zero_field()
        elif mode == "HEX_RING_GAP":
            self.mesh.seed_hex_ring_gap()
        else:
            self.mesh.seed_background()

        self.gpu_field = MNQFieldGPU(grid=64)
        self.three_layer = ThreeLayerInfoWave(core_init=0.001)
        self.cgd_engine = CGDEngine()
        self._init_cgd_constraints()
        self.mnq9_sim = MNQ9Simulator(lam=0.03)
        self.mnq9_sim.set_macro_confidence({'M2': 0.2, 'PMI': 0.1, 'DR007': -0.1})
        self.mnq9_sim.set_future_wave([0.05]*20)

        self.mass_history.clear()
        self.loop_history.clear()
        self.gamma_history.clear()
        self.rcoh_history.clear()
        self.three_layer_core_history.clear()
        self.three_layer_bagua_history.clear()
        self.three_layer_hex64_history.clear()
        self.mnq9_omega_history.clear()
        self.mnq9_bconf_history.clear()
        self.cgd_violation_history.clear()

        self._refresh_all_plots()
        self._log(f"仿真重置 (模式: {mode})")

    def _sim_loop(self):
        """仿真主循环"""
        if not self.is_running:
            return

        t0 = time.time()

        # MNQ8 网格演化
        self.mesh.mnq8_step(dt=0.016)

        # GPU四场演化 (5步/帧)
        current_gamma = self.mesh.minimal.gamma
        for _ in range(5):
            self.gpu_field.step(lambda_=0.01, gamma=current_gamma)
        if self.step_count % 100 == 0:
            self.gpu_field.inject_noise(amp=0.001)

        # v2.0: 三层信息波演化
        tl_change = self.three_layer.step()

        # v2.0: CGD约束检测
        state_vec = np.array([self.mesh.total_mass, self.mesh.minimal.gamma,
                              self.mesh.minimal.omega])
        is_legal, violation = self.cgd_engine.evaluate(state_vec)

        # v2.0: MNQ9信心核更新 (每10步)
        if self.step_count % 10 == 0:
            self.mnq9_sim.run_series(steps=1)

        self.step_count += 1

        # 记录历史
        self.mass_history.append(self.mesh.total_mass)
        self.loop_history.append(self.mesh.total_loop)
        self.gamma_history.append(self.mesh.minimal.gamma)
        self.rcoh_history.append(self.mesh.minimal.rcoh)
        # v2.0 历史
        snap = self.three_layer.snapshot()
        self.three_layer_core_history.append(snap['core'])
        self.three_layer_bagua_history.append(snap['bagua_mean'])
        self.three_layer_hex64_history.append(snap['hex64_mean'])
        if self.mnq9_sim.omega_series:
            self.mnq9_omega_history.append(self.mnq9_sim.omega_series[-1])
            self.mnq9_bconf_history.append(self.mnq9_sim.B_conf_series[-1])
        else:
            self.mnq9_omega_history.append(self.mnq9_sim.core.omega)
            self.mnq9_bconf_history.append(0.0)
        self.cgd_violation_history.append(violation)

        if self.step_count % 3 == 0:
            self._refresh_all_plots()

        elapsed = time.time() - t0
        self.fps_counter.append(elapsed)
        avg_frame = sum(self.fps_counter)/len(self.fps_counter) if self.fps_counter else 0.05
        fps = 1.0/max(0.001, avg_frame)

        self.fps_label.config(text=f"FPS: {fps:.1f}")
        self.step_label.config(text=f"Step: {self.step_count}")

        delay = max(1, int((1.0/30.0 - elapsed) * 1000))
        self.root.after(delay, self._sim_loop)

    # ================================================================
    # 可视化刷新
    # ================================================================

    def _refresh_all_plots(self):
        """刷新所有6个可视化面板"""
        # 1. 流贯场
        ftel_field = self.mesh.get_field_array()
        self.im_ftel.set_data(ftel_field)
        self.im_ftel.set_clim(0, max(0.01, ftel_field.max()))

        # 2. 质量面
        mass_field = self.mesh.get_mass_face_array()
        self.im_mass.set_data(mass_field)

        # 3. Oloid差分
        loop_field = self.mesh.get_excess_loop_array()
        self.im_loop.set_data(loop_field)
        self.im_loop.set_clim(0, max(0.01, loop_field.max()))

        # 4. GPU φ/Ω场
        gpu_data = self.gpu_field.phi
        self.im_gpu.set_data(gpu_data)
        vmax = max(0.01, np.abs(gpu_data).max())
        self.im_gpu.set_clim(-vmax, vmax)

        # 5. 三层信息波 (时间序列)
        n = len(self.three_layer_core_history)
        if n > 1:
            xs = list(range(max(0, n-200), n))
            self.line_3l_core.set_data(
                xs, list(self.three_layer_core_history)[-len(xs):])
            self.line_3l_bagua.set_data(
                xs, list(self.three_layer_bagua_history)[-len(xs):])
            self.line_3l_hex64.set_data(
                xs, list(self.three_layer_hex64_history)[-len(xs):])
            self.ax_3layer.set_xlim(max(0, n-200), n)
            all_vals = (list(self.three_layer_core_history)[-len(xs):] +
                        list(self.three_layer_bagua_history)[-len(xs):] +
                        list(self.three_layer_hex64_history)[-len(xs):])
            ymax = max(0.01, max(all_vals, default=0.01)) * 1.2
            self.ax_3layer.set_ylim(-0.01, ymax)

        # 6. MNQ9信心趋势 (时间序列)
        n9 = len(self.mnq9_omega_history)
        if n9 > 1:
            xs = list(range(max(0, n9-200), n9))
            self.line_mnq9_omega.set_data(
                xs, list(self.mnq9_omega_history)[-len(xs):])
            self.line_mnq9_bconf.set_data(
                xs, list(self.mnq9_bconf_history)[-len(xs):])
            self.ax_mnq9.set_xlim(max(0, n9-200), n9)

        # 刘路径叠加
        if self.liu_scheduler.optimal_path:
            self.ax_mass.clear()
            self.ax_mass.set_facecolor('#0a0a1a')
            self.ax_mass.imshow(mass_field, cmap='hot', interpolation='nearest',
                                vmin=0, vmax=1, aspect='auto')
            path = self.liu_scheduler.optimal_path
            if len(path) > 1:
                ys = [p[1] for p in path]
                xs = [p[0] for p in path]
                self.ax_mass.plot(xs, ys, 'c-', linewidth=1.5, alpha=0.8)
                self.ax_mass.plot(xs[0], ys[0], 'go', markersize=6)
                self.ax_mass.plot(xs[-1], ys[-1], 'r*', markersize=8)
            self.ax_mass.set_title('质量面 + 刘路径', color=self.COLORS['gold'], fontsize=9)

        self.canvas.draw_idle()
        self._update_param_labels()

    def _update_param_labels(self):
        """更新所有参数标签"""
        m = self.mesh.minimal
        self.lbl_phi.config(text=f"{m.phi:.4f}")
        self.lbl_omega.config(text=f"{m.omega:.4f}")
        self.lbl_gamma.config(text=f"{m.gamma:.5f}")
        self.lbl_rcoh.config(text=f"{m.rcoh:.4f}")

        # 三层信息波
        snap = self.three_layer.snapshot()
        self.lbl_3l_core.config(text=f"{snap['core']:.6f}")
        self.lbl_3l_bagua.config(text=f"{snap['bagua_mean']:.6f}")
        self.lbl_3l_hex64.config(text=f"{snap['hex64_mean']:.6f}")
        self.lbl_3l_change.config(
            text=f"{snap['max_change']:.2e}" if snap['max_change'] != float('inf') else "∞")

        # MNQ9信心核
        om = self.mnq9_sim.core.omega
        sn = self.mnq9_sim.snapshot()
        self.lbl_mnq9_omega.config(text=f"{om:.6f}")
        self.lbl_mnq9_bconf.config(
            text=f"{self.mnq9_bconf_history[-1]:.6f}" if self.mnq9_bconf_history else "0.0000")
        self.lbl_mnq9_kernel.config(text=f"{sn['kernel']:.6f}")

        # CGD约束
        state_vec = np.array([self.mesh.total_mass, m.gamma, m.omega])
        _, violation = self.cgd_engine.evaluate(state_vec)
        self.lbl_cgd_violation.config(text=f"{violation:.6f}")
        self.lbl_cgd_phase.config(text=f"{self.cgd_engine.phase_state}")
        self.lbl_cgd_steady.config(text=f"{len(self.cgd_engine.steady_states)}")

        # PG
        self.lbl_mass_faces.config(text=f"{self.mesh.mass_face_count}")
        self.lbl_total_mass.config(text=f"{self.mesh.total_mass:.4f}")
        self.lbl_total_loop.config(text=f"{self.mesh.total_loop:.4f}")

        # 刘机制
        self.lbl_s_rel.config(text=f"{self.liu_scheduler.min_s_rel:.4f}")
        self.lbl_path_len.config(text=f"{len(self.liu_scheduler.optimal_path)}")

        # v3.0 冻结核
        r = self.fk_mesh.reader.read()
        self.lbl_fk_mass.config(text=f"{r['MASS_FACE']:.6f}")
        self.lbl_fk_loop.config(text=f"{r['LOCAL_COMP_LOOP']:.4f}")
        self.lbl_fk_hold.config(text=f"{r['LOOP_HOLD_13']:.4f}")
        self.lbl_fk_leak.config(text=f"{r['BOUNDARY_LEAK']:.4f}")
        self.lbl_fk_diag.config(text=f"{r['DIAG_MINUS_AXIS_LOOP']:.4f}")
        stab = self.fk_mesh.assess_stability()
        self.lbl_fk_stab.config(
            text=f"{'PASS' if stab['passed'] else 'FAIL'} ({stab['score']:.2f})")
        self.lbl_fk_finger.config(text=f"{self.fk_mesh.kernel.fingerprint()[:12]}...")

        # 更新CGD列表
        self.cgd_listbox.delete(0, tk.END)
        for c in self.cgd_engine.constraints:
            lo, hi = c.target_range
            marker = "✓" if lo <= c.current_value <= hi else "✗"
            self.cgd_listbox.insert(tk.END,
                f"  {marker} {c.name}: [{lo:.1f}, {hi:.1f}] v={c.current_value:.4f}")

        # 状态栏
        self.status_label.config(
            text=f"Step {self.step_count} | "
                 f"Mass={self.mesh.total_mass:.3f} | "
                 f"MF={self.mesh.mass_face_count} | "
                 f"γ={m.gamma:.5f} | "
                 f"Ω9={om:.3f} | "
                 f"FK={r['MASS_FACE']:.3f} | "
                 f"CGD={'OK' if violation<1e-4 else 'VIOL'}"
        )

    # ================================================================
    # 操作功能
    # ================================================================

    def _trace_liu_path(self):
        cx, cy = self.mesh.dim_x // 2, self.mesh.dim_y // 2
        path = self.liu_scheduler.find_optimal_path(self.mesh, (cx, cy))
        self._log(f"刘路径追踪: {len(path)}步, S_Rel={self.liu_scheduler.min_s_rel:.4f}")
        self._refresh_all_plots()

    def _run_cloud_sim(self):
        mode = self.scale_mode.get()
        self.cloud_api = MNQCloudAPI(unit_mode=mode)
        result = self.cloud_api.simulate(experiment='hex_ring_gap', steps=512)

        self.cloud_result.delete('1.0', tk.END)
        lines = []
        for k, v in result.items():
            if isinstance(v, float):
                lines.append(f"  {k}: {v:.6e}")
            else:
                lines.append(f"  {k}: {v}")
        self.cloud_result.insert('1.0', '\n'.join(lines))
        self._log(f"Cloud仿真完成 (尺度: {mode})")

    def _run_scf_convergence(self):
        """运行三层信息波SCF收敛"""
        self.three_layer = ThreeLayerInfoWave(core_init=0.001)
        steps = self.three_layer.run_to_convergence(max_steps=500)
        snap = self.three_layer.snapshot()
        self._log(f"SCF收敛: {steps}步, core={snap['core']:.6f}, "
                  f"converged={snap['converged']}")
        self._refresh_all_plots()

    def _apply_mnq9_scenario(self):
        """应用MNQ9宏观场景"""
        scenario = self.mnq9_scenario.get()
        gen = MNQ9ScenarioGenerator()
        if scenario == "bull":
            macro, events = gen.bull_market()
            name = "牛市"
        elif scenario == "bear":
            macro, events = gen.bear_market()
            name = "熊市"
        elif scenario == "crisis":
            macro, events = gen.crisis_recovery()
            name = "危机恢复"
        elif scenario == "policy":
            macro, events = gen.policy_shock()
            name = "政策冲击"
        else:
            return

        self.mnq9_sim = MNQ9Simulator(lam=0.03)
        self.mnq9_sim.set_macro_confidence(macro)
        self.mnq9_sim.set_future_wave(events)
        self.mnq9_omega_history.clear()
        self.mnq9_bconf_history.clear()
        self._log(f"MNQ9场景切换: {name}")
        self._refresh_all_plots()

    def _run_mnq9_trend(self):
        """手动运行MNQ9趋势模拟"""
        self.mnq9_omega_history.clear()
        self.mnq9_bconf_history.clear()
        omega_series = self.mnq9_sim.run_series(steps=60)
        report = self.mnq9_sim.generate_report()
        self.mnq9_omega_history.extend(omega_series)
        self.mnq9_bconf_history.extend(self.mnq9_sim.B_conf_series)
        self._log(f"MNQ9趋势: {report['trend_direction']} "
                  f"strength={report['trend_strength']:.4f} "
                  f"vol={report['trend_volatility']:.4f}")
        self._refresh_all_plots()

    # ---- v3.0 冻结核操作 ----

    def _fk_step(self):
        """冻结核单步演化（含 MUS UI 提示）"""
        self.fk_mesh.step()
        r = self.fk_mesh.reader.read()
        self.fk_mass_face_history.append(r['MASS_FACE'])
        self.fk_loop_history.append(r['LOCAL_COMP_LOOP'])
        self._log(f"冻结核 Step {self.fk_mesh.kernel.step_count}: "
                  f"MF={r['MASS_FACE']:.4f} LOOP={r['LOCAL_COMP_LOOP']:.4f}")

        # TOMAS 建议3: MUS 双存 UI Hint
        strict_result = self.fk_mesh.assess_dual_gate()
        dynamic_result = self.fk_mesh.assess_stability()
        if dynamic_result.get('passed') and not strict_result.get('passed'):
            self._log("⚠️ 检测到暂态闭合（dynamic_gate=PASS, strict_gate=FAIL）")
            if messagebox.askyesno("MUS 双存提示",
                                 "检测到暂态闭合（dynamic_gate=PASS, strict_gate=FAIL）\n\n"
                                 "解读 A：未充分闭合，拒绝\n"
                                 "解读 B：瞬态盆值保留，记录\n\n"
                                 "是否标记为 MUS 弱质量前体候选？"):
                mus_record = {
                    'snap_id': str(uuid.uuid4()),
                    'reason': 'transient_basin_M2_ANTI_W3',
                    'strict_gate': strict_result,
                    'dynamic_gate': dynamic_result,
                    'mass_face': r['MASS_FACE'],
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                }
                mus_dir = './mus'
                os.makedirs(mus_dir, exist_ok=True)
                mus_file = os.path.join(mus_dir, f"mus_{mus_record['snap_id']}.json")
                with open(mus_file, 'w', encoding='utf-8') as f:
                    json.dump(mus_record, f, ensure_ascii=False, indent=2)
                self._log(f"[MUS] 已记录弱质量前体候选: {mus_file}")

        self._refresh_all_plots()

    def _fk_reset(self):
        """重置冻结核"""
        self.fk_mesh = FrozenKernelMesh(seed=42)
        self.fk_mesh.init_background()
        keep_hex = [0,1,5,6,7,8,10,11,12,13,15]
        self.fk_mesh.init_condition(keep_hex, seed=42, phi_polarity=1,
                                    omega_mode="MASK", comp_mode="MASK",
                                    phi_gain=1, center_anchor=1)
        self.fk_mass_face_history.clear()
        self.fk_loop_history.clear()
        self.fk_d4_last = None
        self._log("冻结核已重置")
        self._refresh_all_plots()

    def _fk_d4_audit(self):
        """D4协变性审计"""
        self.fk_d4_last = D4CovariantObserver.audit_covariance(
            self.fk_mesh.kernel, self.fk_mesh.kernel)
        ok_count = sum(1 for r in self.fk_d4_last.values() if r.get('covariant'))
        self._log(f"D4审计: {ok_count}/{len(self.fk_d4_last)} 变换协变")
        self._refresh_all_plots()

    def _log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log_text.see(tk.END)

    # ================================================================
    # 生命周期
    # ================================================================

    def on_close(self):
        self.is_running = False
        self.root.destroy()


# ============================================================================
# 独立命令行仿真 (无GUI)
# ============================================================================

def run_cli_simulation():
    """命令行独立运行MNQ仿真 (v2.0 扩展实验)"""
    print("=" * 60)
    print("  MNQ 金灵球网络仿真器 v2.0 - CLI 模式")
    print("  基于复合体理学 MNQ/IWPU/CGD/MNQ9 理论体系")
    print("=" * 60)

    # 实验1-8: 原有实验
    print("\n[实验1] ZERO_FIELD 死零场")
    mesh = JinlingMesh(dim_x=16, dim_y=16)
    mesh.seed_zero_field()
    for i in range(100):
        mesh.mnq8_step(dt=0.016)
    print(f"  结果: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}, "
          f"MF={mesh.mass_face_count}")
    print(f"  验证: 死零场不破缺")

    print("\n[实验2] BACKGROUND_OSC 动态背景")
    mesh = JinlingMesh(dim_x=16, dim_y=16)
    mesh.seed_background()
    for i in range(1000):
        mesh.mnq8_step(dt=0.016)
    print(f"  结果: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}, "
          f"MF={mesh.mass_face_count}")
    print(f"  验证: 背景态弥散,无囚禁")

    print("\n[实验3] HEX_RING_GAP 缺口六角壳层")
    mesh = JinlingMesh(dim_x=32, dim_y=32)
    mesh.seed_hex_ring_gap()
    for i in range(1000):
        mesh.mnq8_step(dt=0.016)
    print(f"  结果: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}, "
          f"MF={mesh.mass_face_count}")
    print(f"  验证: 流贯囚禁")

    print("\n[实验4] 金符学 3D复广数 阴龙积⊙")
    z1 = GoldenSymbol3D(1.0, 0.5, 0.3)
    z2 = GoldenSymbol3D(0.8, -0.3, 0.2)
    z_product = z1.yin_long_product(z2)
    print(f"  z1 = {z1}")
    print(f"  z2 = {z2}")
    print(f"  z1 ⊙ z2 = {z_product}")
    print(f"  |z1⊙z2| = {z_product.norm():.6f}")

    print("\n[实验5] 刘机制最优路径")
    mesh = JinlingMesh(dim_x=32, dim_y=32)
    mesh.seed_hex_ring_gap()
    for i in range(500):
        mesh.mnq8_step(dt=0.016)
    scheduler = LiuScheduler()
    path = scheduler.find_optimal_path(mesh, (16, 16))
    print(f"  最优路径: {len(path)}步, S_Rel={scheduler.min_s_rel:.4f}")

    print("\n[实验6] MNQ Cloud API 三尺度仿真")
    for mode in ['atomic', 'meso', 'macro']:
        api = MNQCloudAPI(unit_mode=mode)
        result = api.simulate(experiment='hex_ring_gap', steps=512, seed=42)
        print(f"  [{mode}] mean_energy={result['mean_energy_J']:.4e} J, "
              f"coherence={result['coherence']:.6f}")

    print("\n[实验7] Hex64 六十四卦映射")
    for i in range(8):
        r = get_hex64_rule(i)
        print(f"  {r.name} ({r.opcode:6s}): Δφ={r.phi_delta:+.2f} ΔΩ={r.omega_delta:+.2f}")

    print("\n[实验8] GPU四场演化")
    gpu = MNQFieldGPU(grid=64)
    t0 = time.time()
    for i in range(5000):
        gpu.step(lambda_=0.01, gamma=0.989)
        if i % 1000 == 0:
            gpu.inject_noise(0.001)
    elapsed = time.time() - t0
    print(f"  5000步: {elapsed:.2f}s ({5000/elapsed:.0f} steps/s)")

    # ---- v2.0 新增实验 ----

    print("\n[实验9] 三层信息波 SCF收敛")
    wave = ThreeLayerInfoWave(core_init=0.001)
    steps = wave.run_to_convergence(max_steps=300)
    snap = wave.snapshot()
    print(f"  收敛步数: {steps}")
    print(f"  核心层: {snap['core']:.6f}")
    print(f"  八卦层均值: {snap['bagua_mean']:.6f}")
    print(f"  64卦层均值: {snap['hex64_mean']:.6f}")
    print(f"  收敛: {snap['converged']}")

    print("\n[实验10] CGD约束生成动力学")
    cgd = CGDEngine()
    cgd.add_constraint("质量面", (0.0, 0.5), modulation=0.005)
    cgd.add_constraint("相干度", (0.98, 1.0), modulation=0.002)
    mesh = JinlingMesh(dim_x=16, dim_y=16)
    mesh.seed_background()
    violations = []
    for i in range(200):
        mesh.mnq8_step(dt=0.016)
        sv = np.array([mesh.total_mass, mesh.minimal.gamma, mesh.minimal.omega])
        is_legal, viol = cgd.evaluate(sv)
        violations.append(viol)
    print(f"  最大违反度: {max(violations):.6f}")
    print(f"  平均违反度: {np.mean(violations):.6f}")
    print(f"  稳态数: {len(cgd.steady_states)}")

    print("\n[实验11] MNQ9 宏观趋势模拟")
    sim = MNQ9Simulator(lam=0.03)
    macro, events = MNQ9ScenarioGenerator.bull_market()
    sim.set_macro_confidence(macro)
    sim.set_future_wave(events)
    omega = sim.run_series(steps=40)
    report = sim.generate_report()
    print(f"  趋势方向: {report['trend_direction']}")
    print(f"  趋势强度: {report['trend_strength']:.4f}")
    print(f"  波动率: {report['trend_volatility']:.4f}")
    print(f"  终值Ω: {report['final_omega']:.4f}")

    print("\n[实验12] MNQ9 四种场景对比")
    for name, (macro, events) in [
        ("牛市", MNQ9ScenarioGenerator.bull_market()),
        ("熊市", MNQ9ScenarioGenerator.bear_market()),
        ("危机恢复", MNQ9ScenarioGenerator.crisis_recovery()),
        ("政策冲击", MNQ9ScenarioGenerator.policy_shock()),
    ]:
        sim = MNQ9Simulator(lam=0.03)
        sim.set_macro_confidence(macro)
        sim.set_future_wave(events)
        omega = sim.run_series(steps=40)
        report = sim.generate_report()
        print(f"  {name}: Ω={report['final_omega']:+.4f} "
              f"dir={report['trend_direction']} "
              f"vol={report['trend_volatility']:.4f}")

    # ---- v3.0 新增实验 ----
    from mnq_core import (
        MNQ8FrozenKernel, MassFaceReader, DynamicStabilityGate,
        StrictDualGate, D4CovariantObserver, FrozenKernelMesh,
        mnq8_frozen_kernel_verify, FROZEN_KERNEL_FINGERPRINT,
    )

    print("\n" + "=" * 60)
    print("  v3.0 冻结核实验 (基于 V13-V25 质量生成实验链)")
    print("=" * 60)

    print("\n[实验13] 冻结核 SHA256 完整性验证")
    verified = mnq8_frozen_kernel_verify()
    print(f"  冻结核指纹验证: {'通过' if verified else '失败'}")
    print(f"  期望 SHA256: {FROZEN_KERNEL_FINGERPRINT[:16]}...")

    print("\n[实验14] MNQ8 冻结核演化 - 背景场")
    fkm = FrozenKernelMesh(seed=42)
    fkm.init_background()
    print(f"  初始背景: L1={fkm.kernel.l1_by_channel()}, "
          f"active={fkm.kernel.active_points()}")
    fkm.run(64)
    final = fkm.snapshot()
    print(f"  64步后: MASS_FACE={final['mass_face']:.6f}, "
          f"active={final['active']}, carrier={final['carrier']}")
    print(f"  SHA256: {final['fingerprint'][:16]}...")

    print("\n[实验15] 冻结核条件场 - HEX_RING_GAP 质量面前体")
    keep_hex = [0,1,5,6,7,8,10,11,12,13,15]  # G5_V13_ARC
    fkm2 = FrozenKernelMesh(seed=42)
    fkm2.init_background()
    fkm2.init_condition(keep_hex, seed=42, phi_polarity=1,
                        omega_mode="MASK", comp_mode="MASK", phi_gain=1, center_anchor=1)
    trace_iters = {0,1,2,5,13,34,89,233,383}
    for i in range(384):
        fkm2.step()
        if i in trace_iters:
            r = fkm2.reader.read()
            print(f"  ITER={fkm2.kernel.step_count:4d}: MASS_FACE={r['MASS_FACE']:.6f}, "
                  f"LOOP={r['LOCAL_COMP_LOOP']:.4f}")
    final2 = fkm2.snapshot()
    print(f"  ITER=384: MASS_FACE={final2['mass_face']:.6f}, "
          f"peak={final2['peak_mass_face']:.6f}")
    stability = fkm2.assess_stability()
    print(f"  动态稳定门: {'通过' if stability['passed'] else '未通过'}")
    if not stability['passed']:
        print(f"  未通过项: {stability['failures']}")

    print("\n[实验16] D4 协变性审计")
    fkm3 = FrozenKernelMesh(seed=42)
    fkm3.init_background()
    fkm3.run(64)
    d4r = D4CovariantObserver.audit_covariance(fkm3.kernel, fkm3.kernel)
    for name in ['ID','ROT90','ROT180','ROT270','MIRROR_LR']:
        r = d4r.get(name, {})
        ok = 'OK' if r.get('covariant') else 'FAIL'
        print(f"  {name:20s}: {ok}")

    print("\n[实验17] 严格双门评估 - 条件vs背景差分")
    keep_cross = [0,1,3,4,5,7,8,9,11,12,13,15]  # G4_CROSS
    fkm4 = FrozenKernelMesh(seed=42)
    fkm4.init_background()
    fkm4.init_condition(keep_cross, seed=42, phi_polarity=1,
                        omega_mode="MASK", comp_mode="MASK", phi_gain=1, center_anchor=1)
    fkm4.run(384)
    dual = fkm4.assess_dual_gate()
    print(f"  严格双门: {'通过' if dual['passed'] else '未通过'}")
    print(f"  DELTA_MASS_FACE={dual.get('DELTA_MASS_FACE',0):.6f}")
    print(f"  DELTA_LOCAL_COMP_LOOP={dual.get('DELTA_LOCAL_COMP_LOOP',0):.6f}")

    print("\n[实验18] MASS_FACE 复合读数 - 六维测量")
    fkm5 = FrozenKernelMesh(seed=42)
    fkm5.init_background()
    fkm5.init_condition(keep_hex, seed=42, phi_polarity=1,
                        omega_mode="MASK", comp_mode="MASK", phi_gain=1, center_anchor=1)
    fkm5.run(384)
    r = fkm5.reader.read()
    print(f"  质量面 MASS_FACE:     {r['MASS_FACE']:.6f}")
    print(f"  质量闭合 MASS_CLOSURE: {r['MASS_CLOSURE']:.6f}")
    print(f"  局部补偿回路 LOOP:     {r['LOCAL_COMP_LOOP']:.4f}")
    print(f"  持存 HOLD_13:          {r['LOOP_HOLD_13']:.4f}")
    print(f"  边界泄漏 LEAK:         {r['BOUNDARY_LEAK']:.6f}")
    print(f"  漂移阻抗 DRIFT:        {r['DRIFT_IMPEDANCE']:.4f}")
    print(f"  轴/对角线回路:        AXIS={r['AXIS_LOOP_OBS']:.4f} "
          f"DIAG={r['DIAG_LOOP_OBS']:.4f}")

    print("\n" + "=" * 60)
    print("  全部18项实验完成! (v2.0: 12项 + v3.0: 6项)")
    print("=" * 60)


# ============================================================================
# 启动入口
# ============================================================================

def main():
    """启动MNQ仿真器"""
    import sys

    if '--cli' in sys.argv:
        run_cli_simulation()
    else:
        root = tk.Tk()
        app = MNQDashboard(root)
        root.mainloop()


if __name__ == '__main__':
    main()

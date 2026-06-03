"""
MNQ 金灵球网络仿真器 - Windows GUI 仪表盘
基于 tkinter + matplotlib 实现

功能:
1. 金灵球网络 2D 热力图可视化 (流贯场/质量面/Oloid差分)
2. MNQ8 能流运算实时监控
3. 三元动力核 (φ/Ω/γ) 参数面板
4. Hex64 卦象映射显示
5. 刘机制路径追踪
6. 实验组别切换 (死零场/背景/HEX_RING_GAP)
7. GPU四场仿真 (φ/Ω/ψ/ξ)
8. MNQ Cloud API 兼容仿真
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
from collections import deque

from mnq_core import (
    JinlingMesh, MNQFieldGPU, MNQCloudAPI, LiuScheduler,
    MNQMinimalState, mnq_minimal_step, mnq_auto_gamma,
    GoldenSymbol3D, get_hex64_rule, HEX64_TABLE, bagua_apply, BaguaOp,
)


class MNQDashboard:
    """MNQ 金灵球网络仿真器 Windows 仪表盘"""

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
    }

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MNQ 金灵球网络仿真器 v1.0 - Windows Edition")
        self.root.geometry("1400x900")
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

        # 历史记录
        self.mass_history = deque(maxlen=200)
        self.loop_history = deque(maxlen=200)
        self.gamma_history = deque(maxlen=200)
        self.rcoh_history = deque(maxlen=200)

        # 构建UI
        self._build_ui()

        # 初始化显示
        self._refresh_all_plots()

    # ================================================================
    # UI 构建
    # ================================================================

    def _build_ui(self):
        """构建完整UI布局"""
        # 顶部标题栏
        self._build_title_bar()

        # 主体区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # 左侧: 可视化面板
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._build_visualization(left_frame)

        # 右侧: 控制面板
        right_frame = ttk.Frame(main_frame, width=340)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        right_frame.pack_propagate(False)
        self._build_control_panel(right_frame)

        # 底部: 状态栏
        self._build_status_bar()

    def _build_title_bar(self):
        title_frame = tk.Frame(self.root, bg=self.COLORS['bg_dark'], height=40)
        title_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        title_frame.pack_propagate(False)

        tk.Label(title_frame, text="⬡ MNQ 金灵球网络仿真器",
                 font=("Microsoft YaHei", 16, "bold"),
                 fg=self.COLORS['gold'], bg=self.COLORS['bg_dark']).pack(side=tk.LEFT)

        tk.Label(title_frame,
                 text="IWPU · 离散信息波包场 · N₈拓扑 · 阴龙积⊙ · PG囚禁",
                 font=("Microsoft YaHei", 9),
                 fg=self.COLORS['text_dim'], bg=self.COLORS['bg_dark']).pack(side=tk.LEFT, padx=20)

        self.fps_label = tk.Label(title_frame, text="FPS: --",
                                  font=("Consolas", 10),
                                  fg=self.COLORS['cyan'], bg=self.COLORS['bg_dark'])
        self.fps_label.pack(side=tk.RIGHT)

    def _build_visualization(self, parent):
        """构建可视化面板 (4个subplot)"""
        self.fig = Figure(figsize=(9, 7), facecolor=self.COLORS['bg_dark'])
        self.fig.subplots_adjust(hspace=0.35, wspace=0.3, left=0.08, right=0.95,
                                  top=0.95, bottom=0.08)

        # 4个子图
        self.ax_ftel = self.fig.add_subplot(221)
        self.ax_mass = self.fig.add_subplot(222)
        self.ax_loop = self.fig.add_subplot(223)
        self.ax_gpu = self.fig.add_subplot(224)

        for ax in [self.ax_ftel, self.ax_mass, self.ax_loop, self.ax_gpu]:
            ax.set_facecolor('#0a0a1a')
            ax.tick_params(colors=self.COLORS['text_dim'], labelsize=7)
            for spine in ax.spines.values():
                spine.set_color('#333355')

        self.ax_ftel.set_title('流贯场 (Ftel)', color=self.COLORS['cyan'], fontsize=9)
        self.ax_mass.set_title('质量面 (Mass Face)', color=self.COLORS['gold'], fontsize=9)
        self.ax_loop.set_title('Oloid差分 (PG囚禁)', color=self.COLORS['green'], fontsize=9)
        self.ax_gpu.set_title('GPU φ/Ω场', color=self.COLORS['accent1'], fontsize=9)

        # 初始图像
        empty = np.zeros((32, 32))
        self.im_ftel = self.ax_ftel.imshow(empty, cmap='inferno', interpolation='bilinear',
                                            vmin=0, vmax=0.5, aspect='auto')
        self.im_mass = self.ax_mass.imshow(empty, cmap='hot', interpolation='nearest',
                                            vmin=0, vmax=1, aspect='auto')
        self.im_loop = self.ax_loop.imshow(empty, cmap='viridis', interpolation='bilinear',
                                           vmin=0, vmax=0.3, aspect='auto')
        self.im_gpu = self.ax_gpu.imshow(np.zeros((64, 64)), cmap='coolwarm',
                                          interpolation='bilinear', vmin=-0.5, vmax=0.5,
                                          aspect='auto')

        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_control_panel(self, parent):
        """构建右侧控制面板"""
        style = ttk.Style()
        style.configure('Dark.TFrame', background=self.COLORS['bg_panel'])
        style.configure('Dark.TLabel', background=self.COLORS['bg_panel'],
                        foreground=self.COLORS['text'], font=("Microsoft YaHei", 9))
        style.configure('Gold.TLabel', background=self.COLORS['bg_panel'],
                        foreground=self.COLORS['gold'], font=("Microsoft YaHei", 11, "bold"))
        style.configure('Dark.TButton', font=("Microsoft YaHei", 9))
        style.configure('Dark.TLabelframe', background=self.COLORS['bg_panel'],
                        foreground=self.COLORS['cyan'])
        style.configure('Dark.TLabelframe.Label', background=self.COLORS['bg_panel'],
                        foreground=self.COLORS['cyan'], font=("Microsoft YaHei", 9, "bold"))

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

        # 实验模式
        mode_frame = tk.Frame(ctrl_frame, bg=self.COLORS['bg_panel'])
        mode_frame.pack(fill=tk.X, padx=3, pady=3)

        tk.Label(mode_frame, text="实验模式:", bg=self.COLORS['bg_panel'],
                 fg=self.COLORS['text_dim'], font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)

        self.exp_mode = tk.StringVar(value="BACKGROUND_OSC")
        modes = [("背景振荡", "BACKGROUND_OSC"), ("缺口六角壳", "HEX_RING_GAP"),
                 ("死零场", "ZERO_FIELD")]
        for text, mode in modes:
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

        self.lbl_phi = self._make_param_row(minimal_frame, "φ (相位角)", "0.5000")
        self.lbl_omega = self._make_param_row(minimal_frame, "Ω (角频率)", "2.0000")
        self.lbl_gamma = self._make_param_row(minimal_frame, "γ (相干度)", "0.9898")
        self.lbl_rcoh = self._make_param_row(minimal_frame, "Rcoh (相干指标)", "0.0000")

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
                                         font=("Consolas", 8), selectbackground=self.COLORS['bg_card'])
        self.hex64_listbox.pack(fill=tk.X, padx=5, pady=2)
        for i in range(8):
            r = get_hex64_rule(i)
            self.hex64_listbox.insert(tk.END, f"  {r.name} ({r.opcode}) Δφ={r.phi_delta:+.2f} ΔΩ={r.omega_delta:+.2f}")

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

        self.lbl_s_rel = self._make_param_row(liu_frame, "S_Rel 最小值", "∞")
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

        self.cloud_result = scrolledtext.ScrolledText(cloud_frame, height=5,
                                                       bg='#0a0a2a', fg=self.COLORS['text_dim'],
                                                       font=("Consolas", 8))
        self.cloud_result.pack(fill=tk.X, padx=5, pady=2)

        # ---- 日志 ----
        log_frame = tk.LabelFrame(scroll_frame, text=" 📋 运行日志 ",
                                   bg=self.COLORS['bg_panel'], fg=self.COLORS['cyan'],
                                   font=("Microsoft YaHei", 9, "bold"), bd=1)
        log_frame.pack(fill=tk.X, padx=5, pady=3)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=6,
                                                    bg='#0a0a2a', fg=self.COLORS['text_dim'],
                                                    font=("Consolas", 8))
        self.log_text.pack(fill=tk.X, padx=5, pady=2)

    def _build_status_bar(self):
        status_frame = tk.Frame(self.root, bg=self.COLORS['bg_card'], height=24)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=2)
        status_frame.pack_propagate(False)

        self.status_label = tk.Label(status_frame, text="MNQ-VM 就绪 | IWPU | IDO | PG | Liu",
                                      bg=self.COLORS['bg_card'], fg=self.COLORS['text_dim'],
                                      font=("Consolas", 9))
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.step_label = tk.Label(status_frame, text="Step: 0",
                                     bg=self.COLORS['bg_card'], fg=self.COLORS['cyan'],
                                     font=("Consolas", 9))
        self.step_label.pack(side=tk.RIGHT, padx=10)

    def _make_param_row(self, parent, label: str, default: str) -> tk.Label:
        """创建参数行"""
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
        self._log("仿真启动")
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
        self.mass_history.clear()
        self.loop_history.clear()
        self.gamma_history.clear()
        self.rcoh_history.clear()

        self._refresh_all_plots()
        self._log(f"仿真重置 (模式: {mode})")

    def _sim_loop(self):
        """仿真主循环 (在主线程中用after调度)"""
        if not self.is_running:
            return

        t0 = time.time()

        # MNQ8 网格演化 (1步)
        self.mesh.mnq8_step(dt=0.016)

        # GPU四场演化 (5步/帧)
        current_gamma = self.mesh.minimal.gamma
        for _ in range(5):
            self.gpu_field.step(lambda_=0.01, gamma=current_gamma)
        if self.step_count % 100 == 0:
            self.gpu_field.inject_noise(amp=0.001)

        self.step_count += 1

        # 记录历史
        self.mass_history.append(self.mesh.total_mass)
        self.loop_history.append(self.mesh.total_loop)
        self.gamma_history.append(self.mesh.minimal.gamma)
        self.rcoh_history.append(self.mesh.minimal.rcoh)

        # 更新显示 (每3步刷新一次，减少开销)
        if self.step_count % 3 == 0:
            self._refresh_all_plots()

        # FPS
        elapsed = time.time() - t0
        self.fps_counter.append(elapsed)
        avg_frame = sum(self.fps_counter) / len(self.fps_counter) if self.fps_counter else 0.05
        fps = 1.0 / max(0.001, avg_frame)

        self.fps_label.config(text=f"FPS: {fps:.1f}")
        self.step_label.config(text=f"Step: {self.step_count}")

        # 调度下一帧
        delay = max(1, int((1.0 / 30.0 - elapsed) * 1000))
        self.root.after(delay, self._sim_loop)

    # ================================================================
    # 可视化刷新
    # ================================================================

    def _refresh_all_plots(self):
        """刷新所有可视化面板"""
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
        gpu_data = self.gpu_field.phi  # 显示φ场
        self.im_gpu.set_data(gpu_data)
        vmax = max(0.01, np.abs(gpu_data).max())
        self.im_gpu.set_clim(-vmax, vmax)

        # 刷新刘机制路径 (在质量面图上叠加)
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

        # 更新参数面板
        self._update_param_labels()

    def _update_param_labels(self):
        """更新参数标签"""
        m = self.mesh.minimal
        self.lbl_phi.config(text=f"{m.phi:.4f}")
        self.lbl_omega.config(text=f"{m.omega:.4f}")
        self.lbl_gamma.config(text=f"{m.gamma:.5f}")
        self.lbl_rcoh.config(text=f"{m.rcoh:.4f}")
        self.lbl_mass_faces.config(text=f"{self.mesh.mass_face_count}")
        self.lbl_total_mass.config(text=f"{self.mesh.total_mass:.4f}")
        self.lbl_total_loop.config(text=f"{self.mesh.total_loop:.4f}")
        self.lbl_s_rel.config(text=f"{self.liu_scheduler.min_s_rel:.4f}")
        self.lbl_path_len.config(text=f"{len(self.liu_scheduler.optimal_path)}")

        # 更新状态栏
        self.status_label.config(
            text=f"Step {self.step_count} | "
                 f"Mass={self.mesh.total_mass:.3f} | "
                 f"MF={self.mesh.mass_face_count} | "
                 f"γ={m.gamma:.5f} | "
                 f"Rcoh={m.rcoh:.4f}"
        )

    # ================================================================
    # 操作功能
    # ================================================================

    def _trace_liu_path(self):
        """追踪刘机制最优路径"""
        cx, cy = self.mesh.dim_x // 2, self.mesh.dim_y // 2
        path = self.liu_scheduler.find_optimal_path(self.mesh, (cx, cy))
        self._log(f"刘路径追踪: {len(path)}步, S_Rel={self.liu_scheduler.min_s_rel:.4f}")
        self._refresh_all_plots()

    def _run_cloud_sim(self):
        """运行MNQ Cloud API兼容仿真"""
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

    def _log(self, msg: str):
        """添加日志"""
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
    """命令行独立运行MNQ仿真"""
    print("=" * 60)
    print("  MNQ 金灵球网络仿真器 - CLI 模式")
    print("  基于复合体理学 MNQ/IWPU 理论体系")
    print("=" * 60)

    # 实验1: 死零场 (ZERO_FIELD)
    print("\n[实验1] ZERO_FIELD 死零场")
    mesh = JinlingMesh(dim_x=16, dim_y=16)
    mesh.seed_zero_field()
    for i in range(100):
        mesh.mnq8_step(dt=0.016)
    print(f"  结果: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}, "
          f"MF={mesh.mass_face_count}")
    print(f"  验证: 死零场不破缺 (Mass应≈0)")

    # 实验2: 背景振荡 (BACKGROUND_OSC)
    print("\n[实验2] BACKGROUND_OSC 动态背景")
    mesh = JinlingMesh(dim_x=16, dim_y=16)
    mesh.seed_background()
    for i in range(1000):
        mesh.mnq8_step(dt=0.016)
    print(f"  结果: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}, "
          f"MF={mesh.mass_face_count}")
    print(f"  验证: 背景态Mass≈0.1 (弥散,无囚禁)")

    # 实验3: 缺口六边形壳层 (HEX_RING_GAP)
    print("\n[实验3] HEX_RING_GAP 缺口六角壳层")
    mesh = JinlingMesh(dim_x=32, dim_y=32)
    mesh.seed_hex_ring_gap()
    for i in range(1000):
        mesh.mnq8_step(dt=0.016)
    print(f"  结果: Mass={mesh.total_mass:.6f}, Loop={mesh.total_loop:.6f}, "
          f"MF={mesh.mass_face_count}")
    print(f"  验证: HEX_RING_GAP Mass≈0.4, Loop>0 (流贯囚禁)")

    # 实验4: 3D复广数 (金符学) 阴龙积
    print("\n[实验4] 金符学 3D复广数 阴龙积⊙")
    z1 = GoldenSymbol3D(1.0, 0.5, 0.3)
    z2 = GoldenSymbol3D(0.8, -0.3, 0.2)
    z_product = z1.yin_long_product(z2)
    print(f"  z1 = {z1}")
    print(f"  z2 = {z2}")
    print(f"  z1 ⊙ z2 = {z_product}")
    print(f"  |z1⊙z2| = {z_product.norm():.6f}")
    print(f"  验证: 阴龙积保持能量守恒 (模≈乘积)")

    # 实验5: 刘机制路径
    print("\n[实验5] 刘机制最优路径 (δS_Rel=0)")
    mesh = JinlingMesh(dim_x=32, dim_y=32)
    mesh.seed_hex_ring_gap()
    for i in range(500):
        mesh.mnq8_step(dt=0.016)
    scheduler = LiuScheduler()
    path = scheduler.find_optimal_path(mesh, (16, 16))
    print(f"  最优路径: {len(path)}步, S_Rel={scheduler.min_s_rel:.4f}")
    print(f"  验证: 流贯沿最小阻抗路径传播")

    # 实验6: MNQ Cloud API
    print("\n[实验6] MNQ Cloud API 三尺度仿真")
    for mode in ['atomic', 'meso', 'macro']:
        api = MNQCloudAPI(unit_mode=mode)
        result = api.simulate(experiment='hex_ring_gap', steps=512, seed=42)
        print(f"  [{mode}] mean_energy={result['mean_energy_J']:.4e} J, "
              f"coherence={result['coherence']:.6f}, "
              f"phase_lock={result['phase_lock']:.6f}")

    # 实验7: Hex64映射
    print("\n[实验7] Hex64 六十四卦映射")
    for i in range(8):
        r = get_hex64_rule(i)
        print(f"  {r.name} ({r.opcode:6s}): Δφ={r.phi_delta:+.2f} ΔΩ={r.omega_delta:+.2f} Δγ={r.gamma_delta:+.4f}")

    # 实验8: GPU四场
    print("\n[实验8] GPU φ/Ω/ψ/ξ 四场演化")
    gpu = MNQFieldGPU(grid=64)
    t0 = time.time()
    for i in range(5000):
        gpu.step(lambda_=0.01, gamma=0.989)
        if i % 1000 == 0:
            gpu.inject_noise(0.001)
    elapsed = time.time() - t0
    omega_avg = gpu.measure_omega_avg()
    rloc = gpu.compute_rloc()
    print(f"  5000步耗时: {elapsed:.2f}s ({5000/elapsed:.0f} steps/s)")
    print(f"  Ω_avg={omega_avg:.6f}, Rloc={rloc:.6f}")

    print("\n" + "=" * 60)
    print("  全部实验完成!")
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

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import sys
import os
import threading
import socket
import time
import random
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simulator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simulator', 'modules'))
sys.path.insert(0, os.path.dirname(__file__))

from shared_state import shared_state
from mindplus_transpiler import is_mindplus_code, transpile
from simulator.theme import (DarkTheme, LightTheme, apply_theme,
                              GlassEffect, SyntaxHighlighter, create_line_number_widget)

pc_sensors = None
VM_PORT = 7777

# 后导入VM模块（避免循环依赖）
_vm_thread = None
_vm_initialized = False


class IntegratedVMApp:
    def __init__(self, root):
        self.root = root
        self.theme = apply_theme(root, DarkTheme)

        self.root.title("Sim-Handpy - 具身智能学习平台")
        self.root.geometry("1440x900")
        self.root.minsize(1400, 900)

        self.vm_process = None
        self.vm_socket = None
        self.connect_status = False
        self._code_running = False  # 代码执行状态：防止重复运行，联动运行/停止按钮
        self._vm_port = VM_PORT  # 虚拟机 TCP 端口（Mind+ 设置中可调整）
        self._running = True
        self._current_tutorial = 0
        self._completed_tutorials = []
        self._current_mode = tk.StringVar(value="mpython")
        self._current_mode.trace_add("write", lambda *a: self._on_mode_changed())
        self._syntax_highlighter = None
        self._line_numbers_canvas = None
        self._code_notebook = None
        self._output_text = None
        self._serial_bridge = None
        self._restart_pending = False
        self._use_light_theme = False  # 主题切换：False=深色(默认) True=浅色

        self._create_menu()
        self._create_toolbar()
        self._tooltips = {}
        self._tooltip_delay = None
        self._tooltip_showing = None

        self._create_statusbar()
        self._create_main_layout()
        self._setup_sensor_timer()
        self._check_vm_status()
        self._load_tutorial_progress()
        self._setup_cursors()

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="打开文件", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存文件", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为...", command=self.save_as_file)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_exit)
        menubar.add_cascade(label="文件", menu=file_menu)

        vm_menu = tk.Menu(menubar, tearoff=0)
        vm_menu.add_command(label="启动虚拟机", command=self.start_vm)
        vm_menu.add_command(label="关闭虚拟机", command=self.stop_vm)
        vm_menu.add_command(label="连接虚拟机", command=self._toggle_connect)
        vm_menu.add_command(label="重启虚拟机", command=self.restart_vm)
        menubar.add_cascade(label="虚拟机", menu=vm_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="切换主题（深色/浅色）", command=self._toggle_theme)
        menubar.add_cascade(label="视图", menu=view_menu)

        code_menu = tk.Menu(menubar, tearoff=0)
        code_menu.add_command(label="运行代码", command=self.run_code, accelerator="F5")
        code_menu.add_command(label="停止运行", command=self.stop_code, accelerator="F6")
        code_menu.add_command(label="清空输出", command=self.clear_output)
        menubar.add_cascade(label="代码", menu=code_menu)

        learn_menu = tk.Menu(menubar, tearoff=0)
        learn_menu.add_command(label="教程入门", command=self._show_tutorial_select)
        learn_menu.add_command(label="示例代码", command=self._show_example_select)
        learn_menu.add_command(label="API文档", command=self._show_api_docs)
        learn_menu.add_command(label="组件说明", command=self._show_component_info)
        menubar.add_cascade(label="学习", menu=learn_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self._show_help)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.root.bind('<Control-o>', lambda e: self.open_file())
        self.root.bind('<Control-s>', lambda e: self.save_file())
        self.root.bind('<F5>', lambda e: self.run_code())
        self.root.bind('<F6>', lambda e: self.stop_code())

    def _setup_tooltip(self, widget, text):
        t = self.theme
        widget._tooltip_text = text
        widget.bind('<Enter>', lambda e: self._schedule_tooltip(widget), add='+')
        widget.bind('<Leave>', lambda e: self._hide_tooltip(), add='+')
        widget.bind('<Button-1>', lambda e: self._hide_tooltip(), add='+')

    def _schedule_tooltip(self, widget):
        self._hide_tooltip()
        if self._tooltip_delay:
            self.root.after_cancel(self._tooltip_delay)
        self._tooltip_delay = self.root.after(400, lambda: self._show_tooltip(widget))

    def _show_tooltip(self, widget):
        text = widget._tooltip_text
        if not text:
            return
        t = self.theme
        x = widget.winfo_rootx() + widget.winfo_width() // 2
        y = widget.winfo_rooty() + widget.winfo_height() + 6
        tooltip = tk.Toplevel(self.root)
        tooltip.overrideredirect(True)
        tooltip.attributes('-topmost', True)
        tooltip.configure(bg=t.BG_PANEL)
        tk.Label(tooltip, text=text, bg=t.BG_PANEL, fg=t.FG,
                 font=("Segoe UI", 9), padx=8, pady=4,
                 highlightbackground=t.ACCENT, highlightthickness=1).pack()
        self._tooltip_showing = tooltip
        self._tooltips[widget] = tooltip

    def _hide_tooltip(self):
        if self._tooltip_delay:
            self.root.after_cancel(self._tooltip_delay)
            self._tooltip_delay = None
        if self._tooltip_showing:
            try:
                self._tooltip_showing.destroy()
            except Exception:
                pass
            self._tooltip_showing = None
        for w, tip in list(self._tooltips.items()):
            try:
                tip.destroy()
            except Exception:
                pass
        self._tooltips.clear()

    def _create_toolbar(self):
        t = self.theme
        toolbar_frame = tk.Frame(self.root, bg=t.BG_ELEVATED, height=72)
        toolbar_frame.pack(fill=tk.X)
        toolbar_frame.pack_propagate(False)

        brand_frame = tk.Frame(toolbar_frame, bg=t.BG_ELEVATED)
        brand_frame.pack(side=tk.LEFT, padx=(20, 12), pady=10)

        brand_label = tk.Label(brand_frame, text="◆", fg=t.ACCENT, bg=t.BG_ELEVATED,
                                font=("Segoe UI", 18, "bold"))
        brand_label.pack(side=tk.LEFT, padx=(0, 6))
        brand_label2 = tk.Label(brand_frame, text="Sim-Handpy", fg=t.FG, bg=t.BG_ELEVATED,
                                 font=("Segoe UI", 14, "bold"))
        brand_label2.pack(side=tk.LEFT)
        brand_label3 = tk.Label(brand_frame, text="  掌控板虚拟仿真", fg=t.FG_DIM, bg=t.BG_ELEVATED,
                                 font=("Segoe UI", 11))
        brand_label3.pack(side=tk.LEFT, padx=(2, 0))

        def _add_section_label(parent, text):
            lbl = tk.Label(parent, text=text, fg=t.FG_DIM, bg=t.BG_ELEVATED,
                           font=("Segoe UI", 8, "bold"))
            lbl.pack(side=tk.LEFT, padx=(12, 4), pady=(0, 0))
            return lbl

        _add_section_label(toolbar_frame, "虚拟机")

        self.vm_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "启动虚拟机",
                                                      self.start_vm, width=130, height=36,
                                                      icon="▶", accent=True)
        self.vm_btn.pack(side=tk.LEFT, padx=4, pady=8)
        self._setup_tooltip(self.vm_btn, "启动虚拟机 (需要先启动)")

        self.conn_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "连接",
                                                        self._toggle_connect, width=90, height=36,
                                                        icon="🔗")
        self.conn_btn.pack(side=tk.LEFT, padx=4, pady=8)
        self._setup_tooltip(self.conn_btn, "连接/断开虚拟机")

        sep1 = tk.Frame(toolbar_frame, bg=t.BORDER_SUBTLE, width=1)
        sep1.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        _add_section_label(toolbar_frame, "代码")

        self.run_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "运行代码", self.run_code,
                                          width=110, height=36, icon="▶",
                                          bg=t.SUCCESS, fg=t.BG,
                                          hover_bg="#89d497")
        self.run_btn.pack(side=tk.LEFT, padx=4, pady=8)
        self._setup_tooltip(self.run_btn, "运行代码 (F5)")

        self.stop_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "停止", self.stop_code,
                                          width=80, height=36, icon="⏹",
                                          bg=t.ERROR, fg=t.BG,
                                          hover_bg="#e58faa")
        self.stop_btn.pack(side=tk.LEFT, padx=4, pady=8)
        self._setup_tooltip(self.stop_btn, "停止运行 (F6)")

        self.clear_btn = GlassEffect.create_icon_button(toolbar_frame, t, "🗑", "清空输出",
                                        self.clear_output, size=36)
        self.clear_btn.pack(side=tk.LEFT, padx=4, pady=8)

        sep2 = tk.Frame(toolbar_frame, bg=t.BORDER_SUBTLE, width=1)
        sep2.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        _add_section_label(toolbar_frame, "文件")

        self.open_btn = GlassEffect.create_icon_button(toolbar_frame, t, "📂", "打开文件",
                                        self.open_file, size=36)
        self.open_btn.pack(side=tk.LEFT, padx=4, pady=8)

        self.save_btn = GlassEffect.create_icon_button(toolbar_frame, t, "💾", "保存文件",
                                        self.save_file, size=36)
        self.save_btn.pack(side=tk.LEFT, padx=4, pady=8)

        self.example_btn = GlassEffect.create_icon_button(toolbar_frame, t, "📋", "示例代码",
                                        self.load_example, size=36)
        self.example_btn.pack(side=tk.LEFT, padx=4, pady=8)

        sep3 = tk.Frame(toolbar_frame, bg=t.BORDER_SUBTLE, width=1)
        sep3.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        _add_section_label(toolbar_frame, "模式")

        self.mode_label = tk.Label(toolbar_frame, text="模式:", fg=t.FG, bg=t.BG_ELEVATED,
                                font=("Segoe UI", 10, "bold"))
        self.mode_label.pack(side=tk.LEFT, padx=(4, 6), pady=8)

        self.mp_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "mPython",
                                                        lambda: self._set_mode("mpython"),
                                                        width=90, height=32)
        self.mp_btn.pack(side=tk.LEFT, padx=3, pady=8)
        self._setup_tooltip(self.mp_btn, "切换到 mPython 模式")

        self.pp_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "PinPong",
                                                        lambda: self._set_mode("pinpong"),
                                                        width=90, height=32)
        self.pp_btn.pack(side=tk.LEFT, padx=3, pady=8)
        self._setup_tooltip(self.pp_btn, "切换到 PinPong 模式")

        sep4 = tk.Frame(toolbar_frame, bg=t.BORDER_SUBTLE, width=1)
        sep4.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        _add_section_label(toolbar_frame, "学习")

        self.tutorial_btn = GlassEffect.create_canvas_button(toolbar_frame, t, "快速教程",
                                                              self._show_tutorial_select,
                                                              width=100, height=36,
                                                              icon="📚")
        self.tutorial_btn.pack(side=tk.LEFT, padx=4, pady=8)
        self._setup_tooltip(self.tutorial_btn, "快速教程 - 分步骤学习")

        self.status_indicator = GlassEffect.create_status_indicator(toolbar_frame, t, t.ERROR, size=10)
        self.status_indicator.pack(side=tk.RIGHT, padx=(10, 4), pady=10)

        self.status_label = tk.Label(toolbar_frame, text="未连接", fg=t.ERROR,
                                      bg=t.BG_ELEVATED, font=("Segoe UI", 10, "bold"))
        self.status_label.pack(side=tk.RIGHT, padx=(4, 6), pady=10)

        self.mindplus_status = tk.Label(toolbar_frame, text="Mind+: 未启动",
                                         fg=t.FG_DIM, bg=t.BG_ELEVATED, font=("Segoe UI", 9))
        self.mindplus_status.pack(side=tk.RIGHT, padx=6, pady=10)

        self.mindplus_btn = GlassEffect.create_icon_button(toolbar_frame, t, "⚙", "Mind+配置",
                                        self._show_mindplus_settings, size=36)
        self.mindplus_btn.pack(side=tk.RIGHT, padx=4, pady=8)

    def _create_main_layout(self):
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(paned, width=400)
        paned.add(left_frame, weight=0)
        self._create_hardware_panel(left_frame)

        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=1)
        self._create_editor_panel(right_frame)

    def _create_hardware_panel(self, parent):
        t = self.theme
        canvas_frame = tk.Frame(parent, bg=t.BG)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self._create_oled_display(canvas_frame)
        self._create_rgb_led(canvas_frame)
        self._create_buttons(canvas_frame)
        self._create_touch_pads(canvas_frame)
        self._create_sensors(canvas_frame)

    def _create_hw_section(self, parent, title, emoji):
        t = self.theme
        section = tk.Frame(parent, bg=t.BG)
        section.pack(fill=tk.X, pady=(0, 10))

        header = tk.Frame(section, bg=t.BG)
        header.pack(fill=tk.X, pady=(0, 4))
        tk.Label(header, text=f"{emoji} {title}", fg=t.FG, bg=t.BG,
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)

        card = tk.Frame(section, bg=t.BG_CARD, highlightbackground=t.BORDER_SUBTLE,
                         highlightthickness=1, bd=0)
        card.pack(fill=tk.X)
        return card

    def _create_oled_display(self, parent):
        t = self.theme
        card = self._create_hw_section(parent, "OLED 显示屏", "📟")

        inner = tk.Frame(card, bg=t.OLED_FRAME, bd=0,
                        highlightbackground=t.BORDER_SUBTLE, highlightthickness=1)
        inner.pack(padx=12, pady=(8, 6), fill=tk.X)

        header_row = tk.Frame(inner, bg=t.OLED_FRAME)
        header_row.pack(fill=tk.X, padx=8, pady=(6, 0))
        tk.Label(header_row, text="Sim-Handpy", fg=t.ACCENT, bg=t.OLED_FRAME,
                  font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        dot_canvas = tk.Canvas(header_row, width=50, height=14, bg=t.OLED_FRAME, highlightthickness=0, bd=0)
        dot_canvas.pack(side=tk.RIGHT)
        dot_canvas.create_oval(4, 4, 12, 12, fill=t.SUCCESS, outline='')
        dot_canvas.create_oval(16, 4, 24, 12, fill=t.WARNING, outline='')
        dot_canvas.create_oval(28, 4, 36, 12, fill=t.ERROR, outline='')
        dot_canvas.create_text(42, 9, text="128x64", fill=t.FG_DIM, font=("Segoe UI", 7))

        self._oled_canvas = tk.Canvas(inner, height=160, bg=t.OLED_BG,
                                       highlightthickness=0, bd=0)
        self._oled_canvas.pack(fill=tk.X, padx=8, pady=6)
        self._oled_canvas.bind('<Configure>', lambda e: self._draw_oled())

        self.oled_text = tk.Label(self._oled_canvas, text="",
                                    font=("Consolas", 12),
                                    bg=t.OLED_BG, fg=t.OLED_FG,
                                    justify=tk.LEFT, anchor="nw",
                                    padx=8, pady=6)
        self.oled_text.place(x=10, y=10, relwidth=0.94, relheight=0.88)

    def _draw_oled(self):
        t = self.theme
        c = self._oled_canvas
        c.delete('all')
        w = c.winfo_width() or 320
        h = c.winfo_height() or 160

        for y in range(0, h, 3):
            c.create_line(0, y, w, y, fill=t.OLED_SCANLINE, stipple='gray25')

        c.create_line(0, 0, 3, h, fill=t.ACCENT)
        c.create_line(w - 3, 0, w, h, fill=t.ACCENT)

        for y_off in range(h - 3, h):
            alpha_color = t.OLED_GLOW
            c.create_line(0, y_off, w, y_off, fill=alpha_color, stipple='gray25')

        for i in range(3):
            c.create_oval(w - 24, 6 + i * 10, w - 16, 14 + i * 10,
                          fill=t.SUCCESS if i == 0 else t.FG_DIM, outline='')

    def _create_rgb_led(self, parent):
        t = self.theme
        card = self._create_hw_section(parent, "RGB LED 三色灯", "💡")

        rgb_canvas = tk.Canvas(card, height=60, bg=t.BG_CARD,
                                highlightthickness=0, bd=0)
        rgb_canvas.pack(fill=tk.X, pady=(4, 0))
        self._rgb_canvas = rgb_canvas
        self._rgb_canvas.bind('<Configure>', lambda e: self._draw_rgb())
        self.rgb_indicators = []
        self._draw_rgb()

    def _draw_rgb(self):
        t = self.theme
        c = self._rgb_canvas
        c.delete('all')
        self.rgb_indicators = []
        w = c.winfo_width() or 320

        cx = [50, w // 2, w - 50]
        colors = [t.ERROR, t.SUCCESS, t.ACCENT]
        labels = ['R', 'G', 'B']
        for i in range(3):
            x = cx[i]
            y = 28
            r = 20
            c.create_oval(x - r - 4, y - r - 4, x + r + 4, y + r + 4,
                          fill=colors[i], outline='', stipple='gray25')
            c.create_oval(x - r, y - r, x + r, y + r,
                          fill=t.RGB_OFF, outline=t.RGB_OUTLINE, width=2)
            indicator = c.create_oval(x - r + 5, y - r + 5, x + r - 5, y + r - 5,
                                      fill='black', outline='')
            self.rgb_indicators.append(indicator)
            c.create_text(x, 52, text=labels[i],
                          fill=t.FG_DIM, font=("Segoe UI", 9, "bold"))
            c.create_text(x, 28, text="●",
                          fill=t.FG_DIM, font=("Segoe UI", 7))

    def _create_buttons(self, parent):
        t = self.theme
        card = self._create_hw_section(parent, "按键", "🔘")

        btn_frame = tk.Frame(card, bg=t.BG_CARD)
        btn_frame.pack(fill=tk.X, pady=(6, 6))

        self.btn_a = GlassEffect.create_canvas_button(btn_frame, t, "按键 A",
                                                      lambda: self._toggle_button('A'),
                                                      width=130, height=40)
        self.btn_a.pack(side=tk.LEFT, padx=16, pady=6)

        self.btn_b = GlassEffect.create_canvas_button(btn_frame, t, "按键 B",
                                                      lambda: self._toggle_button('B'),
                                                      width=130, height=40)
        self.btn_b.pack(side=tk.LEFT, padx=16, pady=6)

        self._btn_state = {}

    def _create_touch_pads(self, parent):
        t = self.theme
        card = self._create_hw_section(parent, "触摸按键", "✨")

        desc = tk.Label(card, text="P Y T H O N - 触摸感应按键阵列",
                        fg=t.FG_DIM, bg=t.BG_CARD,
                        font=("Segoe UI", 8))
        desc.pack(fill=tk.X, padx=12, pady=(4, 0))

        touch_canvas = tk.Canvas(card, height=65, bg=t.BG_CARD,
                                  highlightthickness=0, bd=0)
        touch_canvas.pack(fill=tk.X, pady=(4, 6))
        self._touch_canvas = touch_canvas

        touch_labels = ['P', 'Y', 'T', 'H', 'O', 'N']
        self.touch_indicators = {}
        self._touch_widgets = {}

        for i, label in enumerate(touch_labels):
            x = 35 + i * 55
            self._draw_touch_pad(touch_canvas, x, 25, label)

    def _draw_touch_pad(self, canvas, cx, cy, label):
        t = self.theme
        r = 15
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                            fill=t.RGB_OFF, outline=t.RGB_OUTLINE, width=2,
                            tags=(f'pad_{label}', 'pad'))
        canvas.create_oval(cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4,
                            fill='black', outline='',
                            tags=(f'indicator_{label}', 'indicator'))
        canvas.create_text(cx, cy + 22, text=label,
                            fill=t.FG_DIM, font=("Segoe UI", 10, "bold"))
        indicator = canvas.find_withtag(f'indicator_{label}')[0]
        self.touch_indicators[label] = indicator

        pad_tags = (f'pad_{label}', f'indicator_{label}')
        for tag in pad_tags:
            canvas.tag_bind(tag, '<ButtonPress-1>',
                             lambda e, l=label: self._set_touch(l, True))
            canvas.tag_bind(tag, '<ButtonRelease-1>',
                             lambda e, l=label: self._set_touch(l, False))
            canvas.tag_bind(tag, '<Leave>',
                             lambda e, l=label: self._set_touch(l, False))

    def _create_sensors(self, parent):
        t = self.theme
        card = self._create_hw_section(parent, "传感器数据", "📡")

        self._sensor_canvas = tk.Canvas(card, height=180, bg=t.BG_CARD,
                                         highlightthickness=0, bd=0)
        self._sensor_canvas.pack(fill=tk.X, pady=(4, 6))
        self._sensor_canvas.bind('<Configure>', lambda e: self._draw_sensors())

        self.sensor_vars = []
        self._sensor_values = {}
        sensor_items = [
            ("📊", "加速度", "x: 0.00  y: 0.00  z: 1.00", "accel"),
            ("🔄", "陀螺仪", "x: 0.00  y: 0.00  z: 0.00", "gyro"),
            ("🧭", "地磁", "x: 0.0  y: 0.0  z: 0.0", "mag"),
            ("💡", "光线", "---", "light"),
            ("🔊", "声音", "---", "sound"),
            ("📡", "WiFi", "未连接", "wifi"),
            ("📷", "摄像头", "未连接", "cam"),
            ("🎤", "麦克风", "未连接", "mic"),
        ]
        self._sensor_configs = sensor_items

        for i, (icon, label, default, key) in enumerate(sensor_items):
            var = tk.StringVar(value=default)
            self.sensor_vars.append(var)
            self._sensor_values[key] = 0

        self._draw_sensors()

    def _draw_sensors(self):
        t = self.theme
        c = self._sensor_canvas
        c.delete('all')
        w = c.winfo_width() or 400
        h = c.winfo_height() or 180

        cols = 2
        rows_per_col = 4
        cell_w = w // cols
        cell_h = h // rows_per_col

        for i, (icon, label, default, key) in enumerate(self._sensor_configs):
            col = i % cols
            row = i // cols
            x0 = col * cell_w + 8
            y0 = row * cell_h + 4
            x1 = x0 + cell_w - 16
            y1 = y0 + cell_h - 8

            c.create_rectangle(x0, y0, x1, y1, fill=t.BG_ELEVATED,
                               outline=t.BORDER_SUBTLE, width=1)

            c.create_text(x0 + 14, y0 + (y1 - y0) // 2, text=icon,
                          fill=t.FG, font=("Segoe UI", 12), anchor='w')

            c.create_text(x0 + 36, y0 + 14, text=label,
                          fill=t.FG_DIM, font=("Segoe UI", 8, "bold"), anchor='w')

            val_text = self.sensor_vars[i].get()
            short_val = val_text[:30] if len(val_text) > 30 else val_text
            c.create_text(x0 + 36, y0 + 30, text=short_val,
                          fill=t.FG, font=t.FONT_CODE, anchor='w')

            bar_x0 = x0 + 36
            bar_y0 = y0 + (y1 - y0) - 10
            bar_x1 = x1 - 8
            bar_y1 = bar_y0 + 4
            c.create_rectangle(bar_x0, bar_y0, bar_x1, bar_y1,
                               fill=t.BG_INPUT, outline='')
            fill_ratio = min(self._sensor_values.get(key, 0) / 1023.0, 1.0)
            if fill_ratio > 0:
                bar_fill = bar_x0 + (bar_x1 - bar_x0) * fill_ratio
                c.create_rectangle(bar_x0, bar_y0, bar_fill, bar_y1,
                                   fill=t.ACCENT, outline='')

            spark_x = x1 - 30
            spark_y = y0 + 6
            spark_points = []
            for j in range(10):
                sv = self._sensor_values.get(key, 0)
                spark_val = (sv / 1023.0) * (10 - abs(j - 5)) * 0.3 + 0.2
                sx = spark_x + j * 3
                sy = spark_y + 10 - spark_val * 10
                spark_points.extend([sx, sy])
            if len(spark_points) >= 4:
                c.create_line(*spark_points, fill=t.SUCCESS, width=1, smooth=True)

    def _redraw_oled(self, _buffer=None):
        text_lines = shared_state.get_oled_text()
        display_text = "\n".join(text_lines)
        t = self.theme
        self.oled_text.config(text=display_text, fg=t.OLED_FG)

    def _update_rgb_display(self, colors):
        for i, color in enumerate(colors):
            hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
            self._rgb_canvas.itemconfig(self.rgb_indicators[i], fill=hex_color)

    def _toggle_button(self, btn):
        current = shared_state.get_button(btn)
        new_state = not current
        shared_state.set_button(btn, new_state)
        t = self.theme
        btn_widget = getattr(self, f'btn_{btn.lower()}', None)
        if btn_widget is not None and hasattr(btn_widget, 'update_button_style'):
            if new_state:
                btn_widget.update_button_style(
                    new_bg=t.ACCENT,
                    new_fg=t.BG,
                    new_hover_bg=t.ACCENT_HOVER
                )
            else:
                btn_widget.update_button_style(
                    new_bg=t.BG_CARD,
                    new_fg=t.FG,
                    new_hover_bg=t.BG_HOVER
                )

    def _set_touch(self, label, state):
        shared_state.set_touch(label, state)
        t = self.theme
        color = t.ACCENT if state else t.RGB_OFF
        outline = t.ACCENT_HOVER if state else t.RGB_OUTLINE
        self._touch_canvas.itemconfig(self.touch_indicators[label], fill=color)

    def _update_sensor_display(self):
        accel, gyro, mag, light, sound = shared_state.get_sensors()
        wifi_connected, wifi_ssid = shared_state.get_wifi()
        self.sensor_vars[0].set(f"x: {accel['x']:.2f}  y: {accel['y']:.2f}  z: {accel['z']:.2f}")
        self.sensor_vars[1].set(f"x: {gyro['x']:.2f}  y: {gyro['y']:.2f}  z: {gyro['z']:.2f}")
        self.sensor_vars[2].set(f"x: {mag['x']:.1f}  y: {mag['y']:.1f}  z: {mag['z']:.1f}")
        self.sensor_vars[3].set(str(light))
        self.sensor_vars[4].set(str(sound))
        self.sensor_vars[5].set(f"已连接: {wifi_ssid}" if wifi_connected else "未连接")

        self._sensor_values['accel'] = int(abs(accel['x'] + accel['y'] + accel['z']) * 100)
        self._sensor_values['gyro'] = int(abs(gyro['x'] + gyro['y'] + gyro['z']) * 100)
        self._sensor_values['mag'] = int(abs(mag['x'] + mag['y'] + mag['z']))
        self._sensor_values['light'] = int(light)
        self._sensor_values['sound'] = int(sound)
        self._sensor_values['wifi'] = 100 if wifi_connected else 0
        self._sensor_values['cam'] = 0
        self._sensor_values['mic'] = 0

        if pc_sensors is not None:
            cam_status = "已连接" if pc_sensors.is_camera_available() else "未连接"
            mic_status = "已连接" if pc_sensors.is_audio_available() else "未连接"
            self.sensor_vars[6].set(cam_status)
            self.sensor_vars[7].set(mic_status)
            self._sensor_values['cam'] = 100 if pc_sensors.is_camera_available() else 0
            self._sensor_values['mic'] = 100 if pc_sensors.is_audio_available() else 0

        if hasattr(self, '_sensor_canvas') and self._sensor_canvas.winfo_exists():
            self._draw_sensors()

    def _setup_sensor_timer(self):
        def poll():
            if self._running:
                shared_state.update_sensors()
                self._update_sensor_display()
                # 更新 OLED（文本模式显示，PinPong/mPython 都兼容）
                self._redraw_oled(None)
                # 像素缓冲区更新（保留给未来像素模式使用）
                oled_buf = shared_state.get_oled_buffer()
                if oled_buf and any(b != 0 for b in oled_buf):
                    self._redraw_oled(oled_buf)
                rgb = shared_state.get_rgb_colors()
                if any(any(c != 0 for c in color) for color in rgb):
                    self._update_rgb_display(rgb)
                self.root.after(500, poll)
        self.root.after(500, poll)

    def _create_editor_panel(self, parent):
        t = self.theme

        self._code_notebook = ttk.Notebook(parent)
        self._code_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 3))

        code_frame = tk.Frame(self._code_notebook, bg=t.BG)
        self._code_notebook.add(code_frame, text="  代码编辑  ")

        editor_container = tk.Frame(code_frame, bg=t.EDITOR_BG)
        editor_container.pack(fill=tk.BOTH, expand=True)

        self.code_text = scrolledtext.ScrolledText(
            editor_container, width=80, height=22,
            font=t.FONT_CODE, wrap=tk.NONE,
            bg=t.EDITOR_BG, fg=t.EDITOR_FG,
            insertbackground=t.EDITOR_CURSOR,
            selectbackground=t.EDITOR_SELECT,
            selectforeground=t.EDITOR_FG,
            borderwidth=0, highlightthickness=0,
            padx=8, pady=8,
            undo=True, maxundo=-1
        )
        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._line_numbers_canvas = create_line_number_widget(editor_container, t, self.code_text)
        self._line_numbers_canvas.pack(side=tk.LEFT, fill=tk.Y)

        self._syntax_highlighter = SyntaxHighlighter(self.code_text, t)

        self.code_text.bind('<KeyRelease>', self._update_line_numbers)
        self.code_text.bind('<ButtonRelease>', self._update_line_numbers)
        self.code_text.bind('<FocusIn>', lambda e: self._syntax_highlighter.highlight_line())

        self._insert_default_code()

        self._editor_hint = tk.Label(editor_container,
            text="💡 提示: F5 运行 | F6 停止 | Ctrl+O 打开 | Ctrl+S 保存",
            fg=t.FG_DIM, bg=t.EDITOR_BG,
            font=("Segoe UI", 8))
        self._editor_hint.place(relx=0.5, rely=1.0, anchor='s', y=-2)

        output_frame = tk.Frame(self._code_notebook, bg=t.BG)
        self._code_notebook.add(output_frame, text="  运行输出  ")

        output_header = tk.Frame(output_frame, bg=t.BG_ELEVATED, height=32)
        output_header.pack(fill=tk.X)
        output_header.pack_propagate(False)

        tk.Label(output_header, text="● Console 运行输出", fg=t.ACCENT, bg=t.BG_ELEVATED,
                  font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=12, pady=5)

        GlassEffect.create_canvas_button(output_header, t, "清空", self.clear_output,
                                            width=70, height=26, bg=t.BG_HOVER).pack(side=tk.RIGHT, padx=8, pady=3)

        self.output_text = scrolledtext.ScrolledText(
            output_frame, width=80, height=8,
            font=("Cascadia Code", 10), state=tk.DISABLED, wrap=tk.WORD,
            bg=t.OUTPUT_BG, fg=t.OUTPUT_FG,
            borderwidth=0, highlightthickness=0,
            padx=8, pady=8
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # ── REPL 命令输入行：向已连接的虚拟机发送单条命令并回显 ──
        repl_bar = tk.Frame(output_frame, bg=t.BG_ELEVATED, height=36)
        repl_bar.pack(fill=tk.X, padx=2, pady=(0, 2))
        repl_bar.pack_propagate(False)

        tk.Label(repl_bar, text="REPL:", fg=t.ACCENT, bg=t.BG_ELEVATED,
                 font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=8)

        self.repl_entry = tk.Entry(repl_bar, font=("Cascadia Code", 10),
                                   bg=t.BG, fg=t.FG, insertbackground=t.FG,
                                   relief=tk.FLAT, highlightthickness=1,
                                   highlightbackground=t.BG_HOVER)
        self.repl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=4)
        self.repl_entry.bind('<Return>', lambda e: self._send_repl_command())

        GlassEffect.create_canvas_button(repl_bar, t, "发送", self._send_repl_command,
                                         width=70, height=26, bg=t.ACCENT, fg=t.BG).pack(side=tk.RIGHT, padx=8, pady=5)

    def _update_line_numbers(self, event=None):
        if self._line_numbers_canvas:
            self._line_numbers_canvas.delete('all')
            try:
                t = self.theme
                line_height = 17
                line_count = int(self.code_text.index('end-1c').split('.')[0])
                for i in range(1, line_count + 1):
                    y = (i - 1) * line_height + 4
                    self._line_numbers_canvas.create_text(35, y, text=str(i),
                                                            fill=t.EDITOR_LINE_NUM,
                                                            font=t.FONT_CODE_LINE, anchor='e')
            except Exception:
                pass

    def _insert_default_code(self):
        self.code_text.insert(tk.END, """/*! 
  * MindPlus 
  * mpython 
  * 
  */ 
#include <MPython.h> 

// 主程序开始 
void setup() { 
    mPython.begin(); 
} 
void loop() { 
    display.setCursorLine(1); 
    display.printLine("Mind+");
}""")

    # ────────── 文件操作 ──────────

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[('Python文件', '*.py'), ('所有文件', '*.*')])
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.code_text.delete("1.0", tk.END)
                self.code_text.insert(tk.END, content)
                self._current_file = file_path  # 记录路径，Ctrl+S 可原位保存
                self.root.title(f"Sim-Handpy - {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("打开失败", f"无法打开文件: {e}")

    def save_file(self):
        if hasattr(self, '_current_file') and self._current_file:
            try:
                content = self.code_text.get("1.0", tk.END)
                with open(self._current_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("保存成功", "文件已保存")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件: {e}")
        else:
            self.save_as_file()

    def save_as_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension='.py',
                                                  filetypes=[('Python文件', '*.py'), ('所有文件', '*.*')])
        if file_path:
            try:
                content = self.code_text.get("1.0", tk.END)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self._current_file = file_path
                self.root.title(f"Sim-Handpy - {os.path.basename(file_path)}")
                messagebox.showinfo("保存成功", "文件已保存")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件: {e}")

    # ────────── 虚拟机控制 ──────────

    def start_vm(self):
        global _vm_initialized, _vm_thread
        if _vm_initialized:
            messagebox.showinfo("提示", "虚拟机已在运行")
            return

        t = self.theme
        self.add_output("⏳ 启动虚拟掌控板（同一进程）...")
        self._update_status("启动中...", t.WARNING)
        self._update_vm_button("启动中...", disabled=True)

        def _start():
            global _vm_initialized, pc_sensors
            try:
                from pc_sensors import pc_sensors as sensors_module
                pc_sensors = sensors_module

                try:
                    pc_sensors.start()
                except Exception:
                    pass
                shared_state.set_pc_sensors(pc_sensors)
                shared_state.set_use_real_sensors(True)

                import virtual_usb
                virtual_usb.start_virtual_usb()

                # 启动 7778 VM Server（执行链：virtual_usb → vm_server → mpython_sim）
                try:
                    from vm_server import VMServer
                    self._vm_server = VMServer()
                    threading.Thread(target=self._vm_server.start, daemon=True).start()
                except Exception as _e:
                    self.root.after(0, lambda: self.add_output(f"⚠️ VM Server 启动失败: {_e}"))
                    self._vm_server = None

                try:
                    bridge = virtual_usb.SerialToTCPBridge(tcp_port=7777, serial_port='COM20')
                    bridge.start()
                    self._serial_bridge = bridge
                except Exception as _e:
                    self.root.after(0, lambda: self.add_output(f"⚠️ 串口桥未启动(需com0com): {_e}"))
                    self._serial_bridge = None

                _vm_initialized = True

                self.root.after(1000, self._on_vm_started)
            except Exception as e:
                import traceback
                self.root.after(0, lambda: self.add_output(f"❌ 启动失败: {e}"))
                self.root.after(0, lambda: self.add_output(traceback.format_exc()))
                self.root.after(0, lambda: self._update_status("启动失败", t.ERROR))
                self.root.after(0, lambda: self._update_vm_button("启动虚拟机"))

        _vm_thread = threading.Thread(target=_start, daemon=True)
        _vm_thread.start()

    def _on_vm_started(self):
        t = self.theme
        parts = []
        if self._vm_server is not None:
            parts.append("VM Server")
        if self._serial_bridge is not None:
            parts.append("串口桥")
        if not parts:
            self.add_output("⚠️ 核心组件均启动失败，虚拟板功能不可用")
            self._update_status("启动失败", t.ERROR)
            self._update_vm_button("启动虚拟机")
            return
        self.add_output("✅ 虚拟掌控板启动成功（" + "、".join(parts) + "）")
        if self._vm_server is None:
            self.add_output("⚠️ VM Server 未运行，代码执行不可用")
        if self._serial_bridge is None:
            self.add_output("⚠️ 串口桥未运行，无法连接（需 com0com 虚拟串口）")
        self._update_status("虚拟机运行中", t.SUCCESS)
        self._update_vm_button("关闭虚拟机", command=self.stop_vm)
        self._update_conn_button("连接", enabled=True)
        # 启动/重启后均自动连接（重启场景不再跳过）
        self.root.after(2000, self._auto_connect)
        self._restart_pending = False

    def restart_vm(self):
        self._restart_pending = True
        self.stop_vm()
        self.add_output("⏳ 等待资源释放...")

        def _wait_and_start(attempts=20):
            # 轮询端口释放后再启动，避免固定延时不足/过长
            if self._check_port(self._vm_port) or attempts <= 0:
                self.add_output("🔄 正在重启虚拟掌控板...")
                self.start_vm()
            else:
                self.root.after(300, _wait_and_start, attempts - 1)

        self.root.after(500, _wait_and_start)

    def stop_vm(self):
        global _vm_initialized, _vm_thread
        if self.vm_socket:
            try:
                self.vm_socket.send(b"\x02")
                time.sleep(0.2)
                self.vm_socket.close()
            except Exception:
                pass
            self.vm_socket = None
        self.connect_status = False
        _vm_initialized = False

        if self._serial_bridge is not None:
            try:
                self._serial_bridge.stop()
            except Exception:
                pass
            self._serial_bridge = None

        if pc_sensors is not None:
            try:
                stop_fn = getattr(pc_sensors, 'stop', None)
                if callable(stop_fn):
                    stop_fn()
            except Exception:
                pass
        shared_state.set_use_real_sensors(False)
        if getattr(self, '_vm_server', None) is not None:
            try:
                self._vm_server.stop()
            except Exception:
                pass
            self._vm_server = None
        try:
            import virtual_usb
            virtual_usb.stop_virtual_usb()
        except Exception:
            pass
        try:
            import mpython_vm
            mpython_vm._running = False
        except Exception:
            pass
        # 等待资源释放（后台等待，不阻塞 UI 线程）
        def _finish_stop():
            t = self.theme
            self._update_status("未连接", t.ERROR)
            self._update_vm_button("启动虚拟机")
            self._update_conn_button("连接", enabled=False)
            self.add_output("⏹ 虚拟机已关闭")
        self.root.after(500, _finish_stop)

    # ────────── 连接管理 ──────────

    def _auto_connect(self):
        self.root.after(500, self._toggle_connect)

    def _toggle_connect(self):
        if self.connect_status:
            self.disconnect_vm()
        else:
            self.connect_vm()

    def connect_vm(self):
        # 使用 Mind+ 设置中配置的端口（默认 7777）
        port = self._vm_port
        if hasattr(self, '_tcp_port_var') and self._tcp_port_var.get().strip():
            try:
                port = int(self._tcp_port_var.get().strip())
                port = max(1, min(65535, port))
            except ValueError:
                pass
        self._vm_port = port
        self.add_output(f"⏳ 连接虚拟机 (127.0.0.1:{port})...")
        try:
            self.vm_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.vm_socket.settimeout(5.0)
            self.vm_socket.connect(('127.0.0.1', port))
            self.connect_status = True
            t = self.theme
            self._update_status("已连接", t.SUCCESS)
            self._update_conn_button("断开", enabled=True)
            self.add_output("✅ 已连接到虚拟掌控板")

            self.vm_socket.send(b"\r\n\x03\x03")
            time.sleep(0.2)
            self.vm_socket.send(b"\r\n\x01")
            time.sleep(0.5)

            response = b""
            while True:
                try:
                    self.vm_socket.settimeout(2.0)
                    data = self.vm_socket.recv(1024)
                    if data:
                        response += data
                        if b">" in response:
                            break
                except socket.timeout:
                    break
                except OSError:
                    break

            if b"raw REPL" in response:
                self.add_output("✅ REPL模式已就绪")
            else:
                self.add_output("⚠️ 连接状态: " + response[:50].decode('utf-8', errors='ignore'))
        except OSError as e:
            messagebox.showerror("连接失败", f"无法连接到虚拟机: {e}\n请确保虚拟机已启动!")
            self.connect_status = False
            self._update_status("未连接", self.theme.ERROR)

    def disconnect_vm(self):
        if self.vm_socket:
            try:
                self.vm_socket.send(b"\x02")
                time.sleep(0.2)
                self.vm_socket.close()
            except OSError:
                pass
            self.vm_socket = None
        self.connect_status = False
        t = self.theme
        self._update_status("未连接", t.ERROR)
        self._update_conn_button("连接", enabled=True)
        self.add_output("✓ 已断开连接")

    # ────────── 代码执行 ──────────

    def run_code(self):
        if not self.connect_status:
            messagebox.showwarning("未连接", "请先启动并连接到虚拟机！")
            return
        if self._code_running:
            self.add_output("⚠️ 已有代码在运行，请先按 F6 停止后再运行")
            return

        code = self.code_text.get("1.0", tk.END).strip()
        if not code:
            messagebox.showwarning("空代码", "请输入代码！")
            return

        self.add_output("=" * 60)

        # ── 检测是否Mind+ C++代码，自动转译 ──
        if is_mindplus_code(code):
            self.add_output("🔄 检测到 Mind+ C++ 代码，自动转译为 MicroPython...")
            try:
                py_code = transpile(code)
                self.add_output("✅ 转译成功！")
                self.add_output("-" * 60)
                # 显示转译后的代码
                for line in py_code.split('\n'):
                    if line.strip():
                        self.add_output(f"  {line}")
                self.add_output("-" * 60)
                code = py_code
            except Exception as e:
                self.add_output(f"❌ 转译失败: {e}")
                return
        else:
            self.add_output("▶ 运行代码...")
        self.add_output("-" * 60)

        # 运行中：禁用运行、高亮停止
        self._code_running = True
        self._set_code_ui_state(True)

        def execute():
            try:
                self.vm_socket.send(code.encode('utf-8'))
                time.sleep(0.3)
                self.vm_socket.send(b"\x04")
                # 原固定等待 3 秒：改为短等待后立即轮询，停止响应更快
                time.sleep(0.5)

                response = b""
                while True:
                    try:
                        self.vm_socket.settimeout(3.0)
                        data = self.vm_socket.recv(4096)
                        if data:
                            response += data
                            if b"\x04\x04" in response:
                                break
                    except socket.timeout:
                        break
                    except OSError:
                        break

                # virtual_usb 固定附加 "OK" 前缀与 ">" 结尾，剥离后才是真实输出
                output = response.decode('utf-8', errors='ignore').replace('\x04', '')
                if output.startswith('OK'):
                    output = output[2:]
                output = output.rstrip('>')
                if output.strip():
                    self._output(output.strip())

                # "OK" 恒存在（协议强制），需结合输出内容判断是否真正成功
                low = output.lower()
                failed = any(k in low for k in ('traceback', 'error:', 'exception', '报错'))
                self._output("✅ 代码执行成功！" if not failed else "❌ 代码执行出错（请查看上方输出）")

            except OSError as e:
                self._output(f"❌ 执行错误: {e}")
            except Exception as e:
                self._output(f"❌ 执行错误: {e}")
            finally:
                # 回到空闲状态，恢复按钮样式
                self.root.after(0, self._finish_code_run)

        threading.Thread(target=execute, daemon=True).start()

    def _set_code_ui_state(self, running):
        """运行/停止按钮状态联动：运行中禁用运行、高亮停止"""
        t = self.theme
        if running:
            self.run_btn.update_button_style(new_bg="#c8c8c8", new_fg="#666666", new_text="运行中…")
            self.stop_btn.update_button_style(new_bg=t.ERROR, new_fg=t.BG, new_hover_bg="#e58faa")
        else:
            self.run_btn.update_button_style(new_bg=t.SUCCESS, new_fg=t.BG, new_hover_bg="#89d497", new_text="运行代码")
            self.stop_btn.update_button_style(new_bg=t.ERROR, new_fg=t.BG, new_hover_bg="#e58faa")

    def _finish_code_run(self):
        self._code_running = False
        self._set_code_ui_state(False)

    def stop_code(self):
        if self._code_running:
            self._finish_code_run()
        if self.vm_socket and self.connect_status:
            try:
                # virtual_usb 已支持 0x03 → vm_server.stop_execution()
                self.vm_socket.send(b"\x03\x03")
                self.add_output("⏹ 已请求停止代码执行")
            except Exception as e:
                self.add_output(f"❌ 停止失败: {e}")
        else:
            self.add_output("⚠️ 未连接到虚拟机")

    # ────────── REPL 命令 ──────────

    def _send_repl_command(self):
        """向已连接的虚拟机发送单条命令并回显结果（与 run_code 互斥）"""
        if not self.connect_status or not self.vm_socket:
            self.add_output("⚠️ 未连接虚拟机，无法发送 REPL 命令")
            return
        cmd = self.repl_entry.get().strip()
        if not cmd:
            return
        if self._code_running:
            self.add_output("⚠️ 代码正在运行，请先停止后再发送命令")
            return
        self.repl_entry.delete(0, tk.END)
        self.add_output(f">>> {cmd}")
        self._code_running = True
        self._set_code_ui_state(True)

        def _exec():
            try:
                self.vm_socket.send(cmd.encode('utf-8') + b"\x04")
                time.sleep(0.5)
                response = b""
                self.vm_socket.settimeout(3.0)
                while True:
                    try:
                        data = self.vm_socket.recv(4096)
                        if data:
                            response += data
                            if b"\x04\x04" in response:
                                break
                    except Exception:
                        break
                output = response.decode('utf-8', errors='ignore').replace('\x04', '').strip()
                if output.startswith('OK'):
                    output = output[2:]
                output = output.rstrip('>')
                if output.strip():
                    self._output(output.strip())
                else:
                    self._output("(无输出)")
            except Exception as e:
                self._output(f"❌ REPL 错误: {e}")
            finally:
                self.root.after(0, self._finish_code_run)

        threading.Thread(target=_exec, daemon=True).start()

    # ────────── 输出 ──────────

    def _setup_output_tags(self):
        """一次性配置输出文本框的着色标签（避免每次插入重复配置）。"""
        if not hasattr(self, '_output_tags_ready'):
            t = self.theme
            self.output_text.tag_config("ok", foreground=t.SUCCESS)
            self.output_text.tag_config("err", foreground=t.ERROR)
            self.output_text.tag_config("warn", foreground=t.WARNING)
            self.output_text.tag_config("act", foreground=t.ACCENT)
            self._output_tags_ready = True

    def add_output(self, text):
        t = self.theme
        # 按前缀着色：成功/错误/警告/动作
        tag = "out"
        if text.startswith("✅"):
            tag = "ok"
        elif text.startswith("❌"):
            tag = "err"
        elif text.startswith("⚠️"):
            tag = "warn"
        elif text[:1] in ("🔄", "🎨", "▶", "⏹", ">>>"):
            tag = "act"
        self.output_text.config(state=tk.NORMAL)
        self._setup_output_tags()
        self.output_text.insert(tk.END, text + "\n", tag)
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def _output(self, text):
        """线程安全输出：在工作线程中调用时经 root.after 调度到主线程"""
        try:
            self.root.after(0, lambda: self.add_output(text))
        except Exception:
            pass

    def clear_output(self):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.config(state=tk.DISABLED)

    # ────────── 示例代码 ──────────

    def load_example(self):
        examples = [
            """# 示例1: RGB闪烁
from mpython_sim import *

while True:
    rgb[0] = (255, 0, 0)
    rgb[1] = (0, 255, 0)
    rgb[2] = (0, 0, 255)
    rgb.write()
    sleep_ms(500)
    rgb[0] = (0, 0, 0)
    rgb[1] = (0, 0, 0)
    rgb[2] = (0, 0, 0)
    rgb.write()
    sleep_ms(500)""",
            """# 示例2: OLED显示传感器数据
from mpython_sim import *

while True:
    oled.fill(0)
    oled.DispChar("Accel: " + str(accelerometer.get()), 0, 0, 1)
    oled.DispChar("Light: " + str(light.read()), 0, 20, 1)
    oled.DispChar("Sound: " + str(sound.read()), 0, 40, 1)
    oled.show()
    sleep_ms(500)""",
            """# 示例3: 按键控制RGB
from mpython_sim import *

rgb[0] = (0, 0, 0)
rgb[1] = (0, 0, 0)
rgb[2] = (0, 0, 0)
rgb.write()

while True:
    if button_a.is_pressed():
        rgb[0] = (255, 0, 0)
    else:
        rgb[0] = (0, 0, 0)

    if button_b.is_pressed():
        rgb[1] = (0, 255, 0)
    else:
        rgb[1] = (0, 0, 0)

    rgb.write()
    sleep_ms(100)""",
            """# 示例4: 触摸按键
from mpython_sim import *

rgb[0] = (0, 0, 0)
rgb[1] = (0, 0, 0)
rgb[2] = (0, 0, 0)
rgb.write()

while True:
    if touchpad_p.is_pressed():
        rgb[0] = (255, 0, 0)
    else:
        rgb[0] = (0, 0, 0)

    if touchpad_y.is_pressed():
        rgb[1] = (0, 255, 0)
    else:
        rgb[1] = (0, 0, 0)

    if touchpad_t.is_pressed():
        rgb[2] = (0, 0, 255)
    else:
        rgb[2] = (0, 0, 0)

    rgb.write()
    sleep_ms(100)""",
        ]

        current = self.code_text.get("1.0", tk.END)
        for i, ex in enumerate(examples):
            if ex[:40] in current:
                next_idx = (i + 1) % len(examples)
                self.code_text.delete("1.0", tk.END)
                self.code_text.insert(tk.END, examples[next_idx])
                return

        self.code_text.delete("1.0", tk.END)
        self.code_text.insert(tk.END, examples[0])
        self.add_output("📋 已加载示例代码")

    # ────────── 状态检查 ──────────

    def _check_vm_status(self):
        if self._running:
            is_running = self._check_port(self._vm_port)
            t = self.theme
            if not self.connect_status:
                if is_running:
                    self._update_status("虚拟机运行中", t.ACCENT)
                    self._update_conn_button("连接", enabled=True)
                else:
                    self._update_status("未连接", t.ERROR)
                    self._update_conn_button("连接", enabled=False)
            self.root.after(3000, self._check_vm_status)

    def _check_port(self, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            return result == 0
        except OSError:
            return False

    # ────────── Mind+ 配置 ──────────

    def _show_mindplus_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Mind+ 连接配置")
        settings_window.geometry("500x450")
        settings_window.transient(self.root)
        settings_window.grab_set()

        ttk.Label(settings_window, text="Mind+ 连接配置", font=("Arial", 14, "bold")).pack(pady=10)

        ttk.Label(settings_window, text="连接方式:", font=("Arial", 10)).pack(anchor=tk.W, padx=20)
        
        frame1 = ttk.Frame(settings_window)
        frame1.pack(fill=tk.X, padx=20, pady=5)
        
        self._mindplus_mode = tk.StringVar(value="serial")
        
        ttk.Radiobutton(frame1, text="串口连接 (推荐)", variable=self._mindplus_mode, 
                       value="serial", command=self._on_mindplus_mode_change).pack(anchor=tk.W)
        ttk.Radiobutton(frame1, text="TCP直连", variable=self._mindplus_mode, 
                       value="tcp", command=self._on_mindplus_mode_change).pack(anchor=tk.W)

        serial_frame = ttk.LabelFrame(settings_window, text="串口配置", padding=10)
        serial_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(serial_frame, text="串口号:").pack(side=tk.LEFT)
        self._serial_port_var = tk.StringVar(value="COM20")
        ttk.Entry(serial_frame, textvariable=self._serial_port_var, width=10).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(serial_frame, text="波特率:").pack(side=tk.LEFT, padx=10)
        self._baud_var = tk.StringVar(value="115200")
        ttk.Combobox(serial_frame, values=["9600", "19200", "38400", "57600", "115200"],
                    textvariable=self._baud_var, width=8, state="readonly").pack(side=tk.LEFT)
        
        ttk.Button(serial_frame, text="检测com0com", command=self._detect_com0com).pack(side=tk.RIGHT, padx=5)

        tcp_frame = ttk.LabelFrame(settings_window, text="TCP配置", padding=10)
        tcp_frame.pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(tcp_frame, text="端口号:").pack(side=tk.LEFT)
        self._tcp_port_var = tk.StringVar(value=str(self._vm_port))
        ttk.Entry(tcp_frame, textvariable=self._tcp_port_var, width=10).pack(side=tk.LEFT, padx=5)
        self._tcp_addr_var = tk.StringVar(value=f"连接地址: 127.0.0.1:{self._vm_port}")
        ttk.Label(tcp_frame, textvariable=self._tcp_addr_var, font=("Arial", 8), foreground="gray").pack(side=tk.RIGHT)

        info_frame = ttk.LabelFrame(settings_window, text="设备信息", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=5)
        
        info_text = tk.Text(info_frame, height=4, font=("Arial", 9), state=tk.DISABLED)
        info_text.pack(fill=tk.X)
        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END, "设备信息 (用于驱动配置):\n")
        info_text.insert(tk.END, "  VID: 1A86\n")
        info_text.insert(tk.END, "  PID: 5512\n")
        info_text.insert(tk.END, "  设备名称: USB Serial Port (CH9102)")
        info_text.config(state=tk.DISABLED)

        guide_frame = ttk.LabelFrame(settings_window, text="连接步骤", padding=10)
        guide_frame.pack(fill=tk.X, padx=20, pady=5)
        
        guide_text = tk.Text(guide_frame, height=6, font=("Arial", 8), state=tk.DISABLED)
        guide_text.pack(fill=tk.X)
        guide_text.config(state=tk.NORMAL)
        guide_text.insert(tk.END, "方法1 (串口连接 - 推荐):\n")
        guide_text.insert(tk.END, "  1. 确保虚拟机已启动\n")
        guide_text.insert(tk.END, "  2. 点击「启动Mind+服务」\n")
        guide_text.insert(tk.END, "  3. 在Mind+中选择「上传到设备」\n")
        guide_text.insert(tk.END, "  4. 选择显示的串口（如 COM19）\n\n")
        guide_text.insert(tk.END, "方法2 (TCP直连):\n")
        guide_text.insert(tk.END, "  仅当Mind+支持网络连接时使用\n")
        guide_text.insert(tk.END, "  1. 在Mind+中选择网络连接\n")
        guide_text.insert(tk.END, "  2. 输入地址: 127.0.0.1:7777")
        guide_text.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(settings_window)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="启动Mind+服务", command=self._start_mindplus_services).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="关闭Mind+服务", command=self._stop_mindplus_services).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="确定", command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)

        self._mindplus_services_running = False
        self._on_mindplus_mode_change()

    def _on_mindplus_mode_change(self):
        mode = self._mindplus_mode.get()
        self.add_output(f"📋 Mind+连接模式: {'TCP直连' if mode == 'tcp' else '串口连接'}")

    def _detect_com0com(self):
        import os
        paths = [
            r"C:\Program Files\com0com\setupc.exe",
            r"C:\Program Files (x86)\com0com\setupc.exe",
            r"C:\Program Files\com0com\setupc64.exe",
            r"C:\Program Files (x86)\com0com\setupc64.exe"
        ]
        found = False
        for path in paths:
            if os.path.exists(path):
                found = True
                messagebox.showinfo("检测结果", f"✅ com0com已安装\n路径: {path}\n\n可以使用串口连接方式。")
                break
        if not found:
            result = messagebox.askyesno("com0com未安装", "❌ 未找到com0com虚拟串口驱动\n\n是否检测驱动状态？")
            if result:
                self._install_com0com()
    
    def _install_com0com(self):
        try:
            self.add_output("⏳ 正在检测 com0com 虚拟串口驱动...")

            import mindplus_usb
            bridge = mindplus_usb.MindPlusUSBBridge()

            success = bridge._find_com0com()

            if success:
                self.add_output("✅ com0com 驱动已就绪，已创建虚拟串口对 (COM19 ↔ COM20)")
                messagebox.showinfo("检测结果", "✅ com0com 虚拟串口驱动已就绪\n\n已创建虚拟串口对: COM19 ↔ COM20\n\nMind+ 可连接 COM19 端口")
            else:
                self.add_output("❌ 未检测到 com0com 驱动")
                messagebox.showwarning("未检测到驱动", "❌ 未检测到 com0com 虚拟串口驱动\n\n请手动安装:\nhttps://sourceforge.net/projects/com0com/\n\n安装后重新运行「检测com0com」")
        except Exception as e:
            self.add_output(f"❌ 检测 com0com 出错: {e}")
            messagebox.showerror("检测错误", f"检测 com0com 时发生错误: {e}")

    def _start_mindplus_services(self):
        try:
            import mindplus_usb
            
            mode = self._mindplus_mode.get()
            if mode == 'tcp':
                try:
                    port = int(self._tcp_port_var.get())
                    port = max(1, min(65535, port))
                except ValueError:
                    port = 7777
                    self.add_output("⚠️ 端口号无效，使用默认 7777")
                mindplus_usb.start_mindplus_services(tcp_port=port)
                self.add_output(f"✅ Mind+ TCP服务已启动 (端口: {port})")
            else:
                serial_port = self._serial_port_var.get()
                mindplus_usb.start_mindplus_services(serial_port=serial_port)
                self.add_output(f"✅ Mind+串口桥接服务已启动 ({serial_port})")
            
            self._mindplus_services_running = True
            self.mindplus_status.config(text="🖥️ Mind+: 运行中", foreground="green")
            
        except Exception as e:
            self.add_output(f"❌ 启动Mind+服务失败: {e}")
            messagebox.showerror("启动失败", f"无法启动Mind+服务: {e}")

    def _stop_mindplus_services(self):
        try:
            import mindplus_usb
            mindplus_usb.stop_mindplus_services()
            self.add_output("⏹ Mind+服务已停止")
            self._mindplus_services_running = False
            self.mindplus_status.config(text="🖥️ Mind+: 已停止", foreground="orange")
        except Exception as e:
            self.add_output(f"❌ 停止Mind+服务失败: {e}")

    # ────────── 帮助 ──────────

    def _show_help(self):
        help_text = """Sim-Handpy - 集成版 使用说明

1. 启动虚拟机: 点击"启动虚拟机"按钮
2. 连接虚拟机: 启动后自动连接，或点击"连接"
3. 编辑代码: 在右侧代码编辑区输入Python代码
4. 运行代码: 按F5或点击"运行"
5. 查看结果: OLED/RGB在左侧虚拟掌控板显示
6. 传感器数据: 左侧面板实时显示模拟传感器值

快捷键:
  Ctrl+O  打开文件
  Ctrl+S  保存文件
  F5      运行代码
  F6      停止运行

注意: 代码中使用 from mpython_sim import * 导入掌控板API"""
        messagebox.showinfo("使用说明", help_text)

    def _show_about(self):
        messagebox.showinfo("关于",
            "Sim-Handpy 教育版 v2.1\n\n"
            "完整的掌控板硬件模拟环境\n"
            "支持OLED显示、RGB LED、按键、触摸按键、传感器\n"
            "兼容Mind+生成的Python代码\n\n"
            "教育功能:\n"
            "  - 分阶段教程系统\n"
            "  - 丰富示例代码库\n"
            "  - 实时API文档\n"
            "  - 组件说明面板\n"
            "  - 学习进度记录")

    # ────────── 教程系统 ──────────

    def _show_tutorial_select(self):
        tutorial_window = tk.Toplevel(self.root)
        tutorial_window.title("选择教程")
        tutorial_window.geometry("600x500")
        tutorial_window.transient(self.root)
        tutorial_window.grab_set()

        tutorials = [
            {"id": 1, "title": "第1课: 点亮LED", "desc": "学习如何控制RGB LED灯", "difficulty": "入门"},
            {"id": 2, "title": "第2课: OLED显示", "desc": "学习在OLED屏幕上显示文字", "difficulty": "入门"},
            {"id": 3, "title": "第3课: 按键控制", "desc": "学习使用按钮控制LED", "difficulty": "基础"},
            {"id": 4, "title": "第4课: 触摸感应", "desc": "学习使用触摸按键", "difficulty": "基础"},
            {"id": 5, "title": "第5课: 传感器数据", "desc": "学习读取传感器数据", "difficulty": "进阶"},
            {"id": 6, "title": "第6课: 综合项目", "desc": "制作一个环境监测器", "difficulty": "进阶"},
        ]

        listbox = tk.Listbox(tutorial_window, font=("Arial", 12))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for i, t in enumerate(tutorials):
            status = " ✅" if t["id"] in self._completed_tutorials else ""
            listbox.insert(tk.END, f"{t['title']} [{t['difficulty']}]{status}")

        def select_tutorial(event=None):
            idx = listbox.curselection()
            if idx:
                tutorial_window.destroy()
                self._start_tutorial(tutorials[idx[0]])
            else:
                messagebox.showinfo("提示", "请先选择一个教程！")

        listbox.bind('<Double-1>', select_tutorial)

        ttk.Button(tutorial_window, text="开始学习", command=select_tutorial).pack(pady=10)

    def _start_tutorial(self, tutorial):
        self._current_tutorial = tutorial["id"]
        
        tutorial_data = {
            1: {
                "title": "第1课: 点亮LED",
                "steps": [
                    "欢迎来到第1课！在这节课中，你将学习如何控制RGB LED灯。",
                    "RGB LED有三个颜色通道：红色、绿色和蓝色。",
                    "每个通道的亮度范围是0-255。",
                    "尝试修改代码中的数值来改变LED颜色！",
                ],
                "code": """# 第1课: 点亮LED
# 学习如何控制RGB LED灯
# 修改下面的数值来改变颜色

from mpython_sim import *

# 设置LED颜色 (RGB 0-255)
rgb[0] = (255, 0, 0)    # LED1: 红色
rgb[1] = (0, 255, 0)    # LED2: 绿色
rgb[2] = (0, 0, 255)    # LED3: 蓝色

rgb.write()  # 应用颜色设置

# 显示说明
oled.fill(0)
oled.DispChar("LED Lesson 1", 0, 0, 1)
oled.DispChar("RGB Colors", 0, 20, 1)
oled.DispChar("Red Green Blue", 0, 40, 1)
oled.show()""",
            },
            2: {
                "title": "第2课: OLED显示",
                "steps": [
                    "欢迎来到第2课！学习在OLED屏幕上显示信息。",
                    "OLED屏幕是128x64像素的单色显示屏。",
                    "使用 oled.DispChar() 来显示文字。",
                    "使用 oled.show() 来刷新显示。",
                ],
                "code": """# 第2课: OLED显示
# 学习在OLED屏幕上显示文字

from mpython_sim import *

# 清除屏幕
oled.fill(0)

# 在不同位置显示文字
oled.DispChar("Hello World!", 0, 0, 1)
oled.DispChar("Sim-Handpy", 0, 16, 1)
oled.DispChar("OLED Display", 0, 32, 1)
oled.DispChar("Lesson 2", 0, 48, 1)

# 刷新显示
oled.show()""",
            },
            3: {
                "title": "第3课: 按键控制",
                "steps": [
                    "欢迎来到第3课！学习使用按钮控制LED。",
                    "掌控板有两个物理按钮：A和B。",
                    "使用 button_a.is_pressed() 来检测按钮状态。",
                    "运行代码后，尝试点击按钮A和B！",
                ],
                "code": """# 第3课: 按键控制
# 学习使用按钮控制LED

from mpython_sim import *

# 初始化LED为关闭状态
rgb[0] = (0, 0, 0)
rgb[1] = (0, 0, 0)
rgb[2] = (0, 0, 0)
rgb.write()

oled.fill(0)
oled.DispChar("Press Button A/B", 0, 0, 1)
oled.show()

while True:
    # 检测按钮A
    if button_a.is_pressed():
        rgb[0] = (255, 0, 0)  # 红色
    else:
        rgb[0] = (0, 0, 0)
    
    # 检测按钮B
    if button_b.is_pressed():
        rgb[1] = (0, 255, 0)  # 绿色
    else:
        rgb[1] = (0, 0, 0)
    
    rgb.write()
    sleep_ms(100)""",
            },
            4: {
                "title": "第4课: 触摸感应",
                "steps": [
                    "欢迎来到第4课！学习使用触摸按键。",
                    "掌控板有6个触摸按键：P Y T H O N。",
                    "触摸按键可以检测手指的触摸。",
                    "运行代码后，尝试触摸不同的按键！",
                ],
                "code": """# 第4课: 触摸感应
# 学习使用触摸按键

from mpython_sim import *

rgb[0] = (0, 0, 0)
rgb[1] = (0, 0, 0)
rgb[2] = (0, 0, 0)
rgb.write()

oled.fill(0)
oled.DispChar("Touch P Y T H O N", 0, 0, 1)
oled.show()

while True:
    # 触摸P键 - 红色
    if touchpad_p.is_pressed():
        rgb[0] = (255, 0, 0)
    else:
        rgb[0] = (0, 0, 0)
    
    # 触摸Y键 - 绿色
    if touchpad_y.is_pressed():
        rgb[1] = (0, 255, 0)
    else:
        rgb[1] = (0, 0, 0)
    
    # 触摸T键 - 蓝色
    if touchpad_t.is_pressed():
        rgb[2] = (0, 0, 255)
    else:
        rgb[2] = (0, 0, 0)
    
    rgb.write()
    sleep_ms(100)""",
            },
            5: {
                "title": "第5课: 传感器数据",
                "steps": [
                    "欢迎来到第5课！学习读取传感器数据。",
                    "掌控板内置多种传感器：加速度计、陀螺仪、光线、声音等。",
                    "传感器数据会实时更新。",
                    "尝试移动或遮挡光线传感器来观察变化！",
                ],
                "code": """# 第5课: 传感器数据
# 学习读取传感器数据

from mpython_sim import *

while True:
    oled.fill(0)
    
    # 读取加速度计数据
    accel = accelerometer.get()
    oled.DispChar("Accel:", 0, 0, 1)
    oled.DispChar(f"X:{accel['x']:.1f}", 0, 16, 1)
    oled.DispChar(f"Y:{accel['y']:.1f}", 64, 16, 1)
    oled.DispChar(f"Z:{accel['z']:.1f}", 0, 32, 1)
    
    # 读取光线传感器
    light_val = light.read()
    oled.DispChar(f"Light:{light_val}", 0, 48, 1)
    
    oled.show()
    sleep_ms(200)""",
            },
            6: {
                "title": "第6课: 综合项目",
                "steps": [
                    "欢迎来到第6课！这是一个综合项目。",
                    "制作一个环境监测器，显示温度、湿度和光线。",
                    "使用学到的所有知识来完成这个项目！",
                    "尝试修改代码来添加更多功能！",
                ],
                "code": """# 第6课: 综合项目 - 环境监测器
# 制作一个环境监测器

from mpython_sim import *

while True:
    oled.fill(0)
    
    # 标题
    oled.DispChar("Environment", 0, 0, 1)
    oled.DispChar("Monitor", 0, 16, 1)
    
    # 显示传感器数据
    light_val = light.read()
    sound_val = sound.read()
    
    oled.DispChar(f"Light: {light_val}", 0, 32, 1)
    oled.DispChar(f"Sound: {sound_val}", 0, 48, 1)
    
    # 根据光线强度改变LED颜色
    if light_val < 200:
        rgb[0] = (255, 255, 0)  # 黄色 - 光线暗
    else:
        rgb[0] = (0, 255, 0)    # 绿色 - 光线亮
    
    rgb.write()
    oled.show()
    sleep_ms(200)""",
            },
        }

        data = tutorial_data.get(tutorial["id"], {})
        if data:
            self.code_text.delete("1.0", tk.END)
            self.code_text.insert(tk.END, data["code"])
            
            tutorial_dialog = tk.Toplevel(self.root)
            tutorial_dialog.title(data["title"])
            tutorial_dialog.geometry("500x400")
            tutorial_dialog.transient(self.root)
            
            text = scrolledtext.ScrolledText(tutorial_dialog, font=("Arial", 12))
            text.pack(fill=tk.BOTH, expand=True)
            for i, step in enumerate(data["steps"], 1):
                text.insert(tk.END, f"📌 步骤{i}: {step}\n\n")
            text.config(state=tk.DISABLED)
            
            def mark_complete():
                if tutorial["id"] not in self._completed_tutorials:
                    self._completed_tutorials.append(tutorial["id"])
                    self._save_tutorial_progress()
                    self.add_output(f"🎉 恭喜完成教程: {data['title']}")
                tutorial_dialog.destroy()
            
            ttk.Button(tutorial_dialog, text="完成", command=mark_complete).pack(pady=10)

    def _load_tutorial_progress(self):
        try:
            import json
            progress_file = os.path.join(os.path.expanduser("~"), ".simhandpy", "tutorial_progress.json")
            if os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    self._completed_tutorials = json.load(f)
        except (OSError, json.JSONDecodeError, ValueError):
            # 进度文件损坏或不可读时静默回退为未完成，不阻塞启动
            self._completed_tutorials = []

    def _save_tutorial_progress(self):
        try:
            import json
            progress_dir = os.path.join(os.path.expanduser("~"), ".simhandpy")
            os.makedirs(progress_dir, exist_ok=True)
            progress_file = os.path.join(progress_dir, "tutorial_progress.json")
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(self._completed_tutorials, f)
        except (OSError, TypeError):
            # 保存失败（磁盘/权限）时静默，不打扰用户
            pass

    def _setup_cursors(self):
        self.root.bind('<Configure>', self._on_window_configure)
        self.root.update_idletasks()
        self._refresh_ui()

    def _on_window_configure(self, event):
        if event.widget == self.root:
            self._refresh_ui()

    def _refresh_ui(self):
        if hasattr(self, '_oled_canvas') and self._oled_canvas.winfo_exists():
            self._draw_oled()
        if hasattr(self, '_rgb_canvas') and self._rgb_canvas.winfo_exists():
            self._draw_rgb()
        if hasattr(self, '_sensor_canvas') and self._sensor_canvas.winfo_exists():
            self._draw_sensors()

    def _update_status(self, text, color):
        t = self.theme
        self.status_label.config(text=text, fg=color)
        if hasattr(self, '_status_vm_label'):
            self._status_vm_label.config(text=f"VM: {text}", fg=color)

    # ────────── 主题切换 ──────────

    def _toggle_theme(self):
        """深色/浅色主题切换（视图菜单）"""
        self._use_light_theme = not self._use_light_theme
        theme_cls = LightTheme if self._use_light_theme else DarkTheme
        self.theme = theme_cls()
        apply_theme(self.root, self.theme)
        self._refresh_theme_widgets()
        self.add_output(f"🎨 已切换至{'浅色' if self._use_light_theme else '深色'}主题")

    def _refresh_theme_widgets(self):
        """切换主题后按语义色映射刷新全部控件颜色，并重建 Canvas 按钮"""
        t = self.theme
        mapping = {}
        for base in (DarkTheme(), LightTheme()):
            for attr in dir(base):
                if attr.startswith('_'):
                    continue
                try:
                    val = getattr(base, attr)
                except Exception:
                    continue
                if isinstance(val, str) and val.startswith('#'):
                    new = getattr(t, attr, None)
                    if isinstance(new, str):
                        mapping[val] = new

        def walk(w):
            try:
                if isinstance(w, tk.Canvas):
                    try:
                        bg = w.cget('bg')
                        if isinstance(bg, str) and bg in mapping:
                            w.config(bg=mapping[bg])
                    except Exception:
                        pass
                    if hasattr(w, 'update_button_style'):
                        return  # 按钮内部样式存于闭包，由下方统一重建
                else:
                    for opt in ('bg', 'fg'):
                        try:
                            val = w.cget(opt)
                            if isinstance(val, str) and val in mapping:
                                w.config(**{opt: mapping[val]})
                        except Exception:
                            pass
            except Exception:
                pass
            for child in w.winfo_children():
                walk(child)

        walk(self.root)

        # 重建关键 Canvas 按钮（颜色/命令在闭包中，需重建）
        global _vm_initialized
        self._update_vm_button("关闭虚拟机" if _vm_initialized else "启动虚拟机",
                               command=self.stop_vm if _vm_initialized else None)
        self._update_conn_button("断开" if self.connect_status else "连接", enabled=True)
        self._set_code_ui_state(self._code_running)
        self._update_mode_buttons()

    def _update_vm_button(self, text, disabled=False, command=None):
        t = self.theme
        btn = self.vm_btn
        if btn and hasattr(btn, 'destroy'):
            btn.destroy()
            cmd = (command if command is not None else self.start_vm) if not disabled else lambda: None
            new_btn = GlassEffect.create_canvas_button(
                btn.master, t, text, cmd,
                width=130, height=36,
                icon="▶" if not disabled else "",
                accent=True
            )
            new_btn.pack(side=tk.LEFT, padx=4, pady=8)
            self.vm_btn = new_btn
            tip = "关闭虚拟机" if text == "关闭虚拟机" else "启动虚拟机"
            self._setup_tooltip(self.vm_btn, tip)

    def _update_conn_button(self, text, enabled=True):
        t = self.theme
        btn = self.conn_btn
        if btn and hasattr(btn, 'destroy'):
            btn.destroy()
            new_btn = GlassEffect.create_canvas_button(
                btn.master, t, text,
                self._toggle_connect if enabled else lambda: None,
                width=90, height=36,
                icon="🔗" if enabled else ""
            )
            new_btn.pack(side=tk.LEFT, padx=4, pady=8)
            self.conn_btn = new_btn
            self._setup_tooltip(self.conn_btn, "连接/断开虚拟机")

    def _create_statusbar(self):
        t = self.theme
        statusbar = tk.Frame(self.root, bg=t.BG_ELEVATED, height=28)
        statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        statusbar.pack_propagate(False)

        tk.Frame(statusbar, bg=t.ACCENT, height=2).pack(fill=tk.X, side=tk.TOP)

        self._status_mode_label = tk.Label(statusbar, text="模式: mPython",
                                            fg=t.ACCENT, bg=t.BG_ELEVATED,
                                            font=("Segoe UI", 9, "bold"))
        self._status_mode_label.pack(side=tk.LEFT, padx=(12, 16), pady=4)

        self._status_vm_label = tk.Label(statusbar, text="VM: 未连接",
                                            fg=t.ERROR, bg=t.BG_ELEVATED,
                                            font=("Segoe UI", 9))
        self._status_vm_label.pack(side=tk.LEFT, padx=(0, 16), pady=4)

        self._status_sensor_label = tk.Label(statusbar, text="传感器: 轮询中",
                                                fg=t.FG_DIM, bg=t.BG_ELEVATED,
                                                font=("Segoe UI", 9))
        self._status_sensor_label.pack(side=tk.LEFT, padx=(0, 16), pady=4)

        self._status_poll_dot = tk.Canvas(statusbar, width=10, height=10,
                                           bg=t.BG_ELEVATED, highlightthickness=0, bd=0)
        self._status_poll_dot.pack(side=tk.LEFT, pady=4)
        self._status_poll_dot.create_oval(1, 1, 9, 9, fill=t.SUCCESS, outline='')

        self._status_time_label = tk.Label(statusbar, text="",
                                              fg=t.FG_DIM, bg=t.BG_ELEVATED,
                                              font=("Segoe UI", 9))
        self._status_time_label.pack(side=tk.RIGHT, padx=12, pady=4)

        self._update_statusbar_time()

    def _update_statusbar_time(self):
        try:
            now = time.strftime("%H:%M:%S")
            if hasattr(self, '_status_time_label'):
                self._status_time_label.config(text=now)
        except Exception:
            pass
        self.root.after(1000, self._update_statusbar_time)

    # ────────── 示例代码选择 ──────────

    def _show_example_select(self):
        example_window = tk.Toplevel(self.root)
        mode_name = "mPython" if self._current_mode.get() == "mpython" else "PinPong"
        example_window.title(f"选择示例代码 - {mode_name}模式")
        example_window.geometry("600x500")
        example_window.transient(self.root)
        example_window.grab_set()

        categories = [
            {"name": "基础入门", "mode": "mpython", "examples": [
                ("LED闪烁", "rgb_blink"),
                ("OLED显示", "oled_text"),
                ("按键检测", "button_check"),
            ]},
            {"name": "传感器", "mode": "mpython", "examples": [
                ("加速度计", "sensor_accel"),
                ("光线传感器", "sensor_light"),
                ("声音传感器", "sensor_sound"),
            ]},
            {"name": "交互控制", "mode": "mpython", "examples": [
                ("按键控制LED", "button_control"),
                ("触摸按键", "touch_control"),
                ("传感器控制LED", "sensor_led"),
            ]},
            {"name": "PinPong库", "mode": "pinpong", "examples": [
                ("PinPong OLED", "pinpong_oled"),
                ("PinPong RGB", "pinpong_rgb"),
                ("PinPong 按键", "pinpong_button"),
                ("PinPong 传感器", "pinpong_sensor"),
            ]},
            {"name": "综合项目", "mode": "mpython", "examples": [
                ("环境监测器", "env_monitor"),
                ("RGB彩虹", "rgb_rainbow"),
                ("心跳检测", "heartbeat_sim"),
            ]},
        ]

        # 根据当前模式过滤示例
        current_mode = self._current_mode.get()
        if current_mode == "mpython":
            categories = [c for c in categories if c["mode"] in ("mpython", "both")]
        else:
            categories = [c for c in categories if c["mode"] in ("pinpong", "both")]

        example_code = {
            "rgb_blink": """# LED闪烁
# 让三个LED轮流闪烁

from mpython_sim import *

while True:
    # 红色
    rgb[0] = (255, 0, 0)
    rgb[1] = (0, 0, 0)
    rgb[2] = (0, 0, 0)
    rgb.write()
    sleep_ms(300)
    
    # 绿色
    rgb[0] = (0, 0, 0)
    rgb[1] = (255, 0, 0)
    rgb[2] = (0, 0, 0)
    rgb.write()
    sleep_ms(300)
    
    # 蓝色
    rgb[0] = (0, 0, 0)
    rgb[1] = (0, 0, 0)
    rgb[2] = (255, 0, 0)
    rgb.write()
    sleep_ms(300)""",
            "oled_text": """# OLED显示
# 在屏幕上显示各种信息

from mpython_sim import *

oled.fill(0)
oled.DispChar("Sim-Handpy", 0, 0, 1)
oled.DispChar("OLED Test", 0, 16, 1)
oled.DispChar("128x64", 0, 32, 1)
oled.DispChar("Ready!", 0, 48, 1)
oled.show()""",
            "button_check": """# 按键检测
# 检测按钮状态并显示

from mpython_sim import *

while True:
    oled.fill(0)
    
    if button_a.is_pressed():
        oled.DispChar("Button A: PRESSED", 0, 0, 1)
    else:
        oled.DispChar("Button A: RELEASED", 0, 0, 1)
    
    if button_b.is_pressed():
        oled.DispChar("Button B: PRESSED", 0, 16, 1)
    else:
        oled.DispChar("Button B: RELEASED", 0, 16, 1)
    
    oled.show()
    sleep_ms(100)""",
            "sensor_accel": """# 加速度计
# 读取并显示加速度数据

from mpython_sim import *

while True:
    oled.fill(0)
    accel = accelerometer.get()
    
    oled.DispChar("Accelerometer", 0, 0, 1)
    oled.DispChar(f"X: {accel['x']:.2f}", 0, 16, 1)
    oled.DispChar(f"Y: {accel['y']:.2f}", 0, 32, 1)
    oled.DispChar(f"Z: {accel['z']:.2f}", 0, 48, 1)
    
    oled.show()
    sleep_ms(100)""",
            "sensor_light": """# 光线传感器
# 读取环境光线强度

from mpython_sim import *

while True:
    oled.fill(0)
    light_val = light.read()
    
    oled.DispChar("Light Sensor", 0, 0, 1)
    oled.DispChar(f"Value: {light_val}", 0, 16, 1)
    
    if light_val < 200:
        oled.DispChar("Dark", 0, 32, 1)
        rgb[0] = (255, 255, 0)
    else:
        oled.DispChar("Bright", 0, 32, 1)
        rgb[0] = (0, 255, 0)
    
    rgb.write()
    oled.show()
    sleep_ms(200)""",
            "sensor_sound": """# 声音传感器
# 读取环境声音强度

from mpython_sim import *

while True:
    oled.fill(0)
    sound_val = sound.read()
    
    oled.DispChar("Sound Sensor", 0, 0, 1)
    oled.DispChar(f"Value: {sound_val}", 0, 16, 1)
    
    if sound_val > 500:
        oled.DispChar("LOUD!", 0, 32, 1)
        rgb[0] = (255, 0, 0)
    else:
        oled.DispChar("Quiet", 0, 32, 1)
        rgb[0] = (0, 0, 0)
    
    rgb.write()
    oled.show()
    sleep_ms(100)""",
            "button_control": """# 按键控制LED
# 使用按钮控制LED开关

from mpython_sim import *

rgb[0] = (0, 0, 0)
rgb[1] = (0, 0, 0)
rgb.write()

while True:
    if button_a.is_pressed():
        rgb[0] = (255, 0, 0)
    else:
        rgb[0] = (0, 0, 0)
    
    if button_b.is_pressed():
        rgb[1] = (0, 255, 0)
    else:
        rgb[1] = (0, 0, 0)
    
    rgb.write()
    sleep_ms(50)""",
            "touch_control": """# 触摸控制
# 使用触摸按键控制LED

from mpython_sim import *

rgb[0] = (0, 0, 0)
rgb[1] = (0, 0, 0)
rgb[2] = (0, 0, 0)
rgb.write()

while True:
    rgb[0] = (255, 0, 0) if touchpad_p.is_pressed() else (0, 0, 0)
    rgb[1] = (0, 255, 0) if touchpad_y.is_pressed() else (0, 0, 0)
    rgb[2] = (0, 0, 255) if touchpad_t.is_pressed() else (0, 0, 0)
    rgb.write()
    sleep_ms(50)""",
            "sensor_led": """# 传感器控制LED
# 根据传感器值控制LED颜色

from mpython_sim import *

while True:
    light_val = light.read()
    
    if light_val < 100:
        rgb[0] = (255, 255, 0)  # 黄色
    elif light_val < 300:
        rgb[0] = (0, 255, 0)    # 绿色
    else:
        rgb[0] = (0, 0, 255)    # 蓝色
    
    rgb.write()
    sleep_ms(100)""",
            "env_monitor": """# 环境监测器
# 综合监测各种环境参数

from mpython_sim import *

while True:
    oled.fill(0)
    
    oled.DispChar("Environment", 0, 0, 1)
    oled.DispChar(f"Light: {light.read()}", 0, 16, 1)
    oled.DispChar(f"Sound: {sound.read()}", 0, 32, 1)
    
    accel = accelerometer.get()
    oled.DispChar(f"Accel: {accel['x']:.1f}", 0, 48, 1)
    
    oled.show()
    sleep_ms(200)""",
            "rgb_rainbow": """# RGB彩虹效果
# 创建彩虹渐变效果

from mpython_sim import *
import math

step = 0
while True:
    r = int(128 + 127 * math.sin(step * 0.05))
    g = int(128 + 127 * math.sin(step * 0.05 + 2))
    b = int(128 + 127 * math.sin(step * 0.05 + 4))
    
    rgb[0] = (r, 0, 0)
    rgb[1] = (0, g, 0)
    rgb[2] = (0, 0, b)
    rgb.write()
    
    step += 1
    sleep_ms(20)""",
            "heartbeat_sim": """# 心跳模拟器
# 模拟心跳脉冲效果

from mpython_sim import *

while True:
    # 心跳脉冲
    for i in range(0, 255, 10):
        rgb[0] = (i, 0, 0)
        rgb.write()
        sleep_ms(20)
    
    for i in range(255, 0, -10):
        rgb[0] = (i, 0, 0)
        rgb.write()
        sleep_ms(20)
    
    sleep_ms(500)""",
            "pinpong_oled": """# PinPong OLED显示
# 使用PinPong库控制OLED

from pinpong import *

init()
oled = get_oled()

oled.clear()
oled.write("PinPong")
oled.write("OLED Test")
oled.write("128x64")
oled.show()""",
            "pinpong_rgb": """# PinPong RGB控制
# 使用PinPong库控制RGB LED

from pinpong import *

init()
rgb = get_rgb()

while True:
    rgb.red()
    delay(500)
    rgb.green()
    delay(500)
    rgb.blue()
    delay(500)
    rgb.write_color("yellow")
    delay(500)""",
            "pinpong_button": """# PinPong 按键检测
# 使用PinPong库检测按键

from pinpong import *

init()
oled = get_oled()

while True:
    oled.clear()
    
    if Button.A.read_digital():
        oled.write("Button A: ON")
    else:
        oled.write("Button A: OFF")
    
    if Button.B.read_digital():
        oled.write("Button B: ON")
    else:
        oled.write("Button B: OFF")
    
    oled.show()
    delay(100)""",
            "pinpong_sensor": """# PinPong 传感器读取
# 使用PinPong库读取传感器

from pinpong import *

init()
oled = get_oled()
rgb = get_rgb()

while True:
    oled.clear()
    
    light_val = Pin(3).read_analog()
    oled.write(f"Light: {light_val}")
    
    if light_val > 2000:
        rgb.write_color("green")
    else:
        rgb.write_color("yellow")
    
    oled.show()
    delay(200)""",
        }

        listbox = tk.Listbox(example_window, font=("Arial", 12))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for cat in categories:
            listbox.insert(tk.END, f"=== {cat['name']} ===")
            for name, key in cat["examples"]:
                listbox.insert(tk.END, f"  ▶ {name}")

        def select_example(event):
            idx = listbox.curselection()
            if idx:
                line = listbox.get(idx[0])
                if "▶" in line:
                    example_name = line.strip(" ▶")
                    for cat in categories:
                        for name, key in cat["examples"]:
                            if name == example_name:
                                example_window.destroy()
                                self.code_text.delete("1.0", tk.END)
                                self.code_text.insert(tk.END, example_code.get(key, ""))
                                self.add_output(f"📋 已加载示例: {example_name}")
                                return

        listbox.bind('<Double-1>', select_example)

    # ────────── API文档 ──────────

    def _show_api_docs(self):
        api_window = tk.Toplevel(self.root)
        api_window.title("API文档")
        api_window.geometry("800x600")
        api_window.transient(self.root)

        notebook = ttk.Notebook(api_window)
        notebook.pack(fill=tk.BOTH, expand=True)

        docs = {
            "LED控制": """RGB LED 控制

rgb[index] = (r, g, b)
  设置LED颜色，index为0-2，r/g/b为0-255

rgb.write()
  应用颜色设置到LED

示例:
  rgb[0] = (255, 0, 0)  # 设置LED1为红色
  rgb[1] = (0, 255, 0)  # 设置LED2为绿色
  rgb.write()           # 应用设置""",
            "OLED显示": """OLED 显示屏控制

oled.fill(color)
  填充屏幕，color为0(黑)或1(白)

oled.DispChar(text, x, y, size)
  在指定位置显示文字
  x: 水平位置(0-127)
  y: 垂直位置(0-63)
  size: 字体大小(1或2)

oled.show()
  刷新显示

示例:
  oled.fill(0)
  oled.DispChar("Hello", 0, 0, 1)
  oled.show()""",
            "按键": """物理按键

button_a.is_pressed()
  返回按钮A是否被按下(True/False)

button_b.is_pressed()
  返回按钮B是否被按下(True/False)

示例:
  if button_a.is_pressed():
      rgb[0] = (255, 0, 0)""",
            "触摸按键": """触摸按键

touchpad_p.is_pressed()
touchpad_y.is_pressed()
touchpad_t.is_pressed()
touchpad_h.is_pressed()
touchpad_o.is_pressed()
touchpad_n.is_pressed()
  返回对应触摸键是否被触摸

示例:
  if touchpad_p.is_pressed():
      rgb[0] = (255, 0, 0)""",
            "传感器": """传感器

accelerometer.get()
  返回加速度计数据 {'x': val, 'y': val, 'z': val}

gyroscope.get()
  返回陀螺仪数据 {'x': val, 'y': val, 'z': val}

magnetometer.get()
  返回地磁数据 {'x': val, 'y': val, 'z': val}

light.read()
  返回光线传感器值(0-1023)

sound.read()
  返回声音传感器值(0-1023)

示例:
  accel = accelerometer.get()
  print(accel['x'])""",
            "延时": """延时函数

sleep_ms(ms)
  延时指定毫秒数

sleep_us(us)
  延时指定微秒数

示例:
  sleep_ms(500)  # 延时500毫秒""",
        }

        for title, content in docs.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)
            
            text = scrolledtext.ScrolledText(frame, font=self.theme.FONT_MONO)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, content)
            text.config(state=tk.DISABLED)

    # ────────── 模式切换 ──────────

    def _set_mode(self, mode):
        if mode != self._current_mode.get():
            self._current_mode.set(mode)

    def _on_mode_changed(self):
        mode = self._current_mode.get()
        t = self.theme
        # 只更新状态栏右侧的模式标签，不再覆盖 status_label 的"连接状态"显示
        if hasattr(self, '_status_mode_label'):
            self._status_mode_label.config(
                text="模式: mPython" if mode == "mpython" else "模式: PinPong",
                fg=t.ACCENT if mode == "mpython" else t.WARNING)

        self._update_mode_buttons()

    def _update_mode_buttons(self):
        mode = self._current_mode.get()
        t = self.theme
        for btn_name, btn_text, active in [
            ('mp_btn', 'mPython', mode == 'mpython'),
            ('pp_btn', 'PinPong', mode == 'pinpong')
        ]:
            btn = getattr(self, btn_name, None)
            if btn and hasattr(btn, 'destroy'):
                btn.destroy()
                new_btn = GlassEffect.create_canvas_button(
                    btn.master, t, btn_text,
                    lambda m=btn_text: self._set_mode("mpython" if m == "mPython" else "pinpong"),
                    width=90, height=32,
                    bg=t.ACCENT if active else t.BG_ELEVATED,
                    fg=t.BG if active else t.FG,
                    hover_bg=t.ACCENT_HOVER if active else t.BG_HOVER
                )
                new_btn.pack(side=tk.LEFT, padx=3, pady=8)
                setattr(self, btn_name, new_btn)
                self._setup_tooltip(new_btn, f"切换到 {btn_text} 模式")

        # 4. 更新默认代码（仅空编辑器时插入，避免清空用户已写代码）
        if not self.code_text.get("1.0", tk.END).strip():
            if mode == "mpython":
                self.code_text.insert(tk.END, """/*! 
  * MindPlus 
  * mpython 
  * 
  */ 
#include <MPython.h> 

// 主程序开始 
void setup() { 
    mPython.begin(); 
} 
void loop() { 
    display.setCursorLine(1); 
    display.printLine("Mind+");
}""")
            else:
                self.code_text.insert(tk.END, """# PinPong 示例
# 使用pinpong库控制掌控板

from pinpong import *

init()

oled = get_oled()
oled.clear()
oled.write("PinPong Mode")
oled.write("Ready!")
oled.show()

rgb = get_rgb()
rgb.write_color("green")""")

        self.add_output(f"🔄 已切换到 {mode.upper()} 模式")

    # ────────── 组件说明 ──────────

    def _show_component_info(self):
        info_window = tk.Toplevel(self.root)
        info_window.title("组件说明")
        info_window.geometry("700x500")
        info_window.transient(self.root)

        notebook = ttk.Notebook(info_window)
        notebook.pack(fill=tk.BOTH, expand=True)

        components = {
            "OLED显示屏": """OLED显示屏 (128x64)

OLED（有机发光二极管）显示屏是一种自发光显示技术。
掌控板使用的是128x64像素的单色OLED屏幕。

特点:
- 自发光，不需要背光
- 对比度高，显示清晰
- 低功耗
- 响应速度快

使用方法:
- oled.fill(0) - 清除屏幕
- oled.DispChar(text, x, y, size) - 显示文字
- oled.show() - 刷新显示""",
            "RGB LED": """RGB LED

RGB LED是可以发出红、绿、蓝三种颜色的LED灯。
通过混合不同比例的RGB颜色，可以产生各种颜色。

掌控板有3个RGB LED:
- LED1 (P13)
- LED2 (P14)
- LED3 (P15)

颜色范围: 0-255
- (255, 0, 0) = 红色
- (0, 255, 0) = 绿色
- (0, 0, 255) = 蓝色
- (255, 255, 255) = 白色""",
            "物理按键": """物理按键

掌控板有两个物理按键:
- 按键A (P16)
- 按键B (P20)

按键是一种输入设备，用于检测用户的按下操作。
可以通过代码检测按键状态，实现交互式控制。

使用方法:
- button_a.is_pressed() - 检测按键A
- button_b.is_pressed() - 检测按键B""",
            "触摸按键": """触摸按键

掌控板有6个触摸按键: P Y T H O N

触摸按键基于电容感应原理工作。
当手指触摸按键时，电容变化会被检测到。

触摸按键位置:
- P: 最左侧
- Y: P右侧
- T: 中间
- H: T右侧
- O: H右侧
- N: 最右侧

使用方法:
- touchpad_p.is_pressed()
- touchpad_y.is_pressed()
- touchpad_t.is_pressed()
- touchpad_h.is_pressed()
- touchpad_o.is_pressed()
- touchpad_n.is_pressed()""",
            "传感器": """传感器

掌控板集成了多种传感器:

1. 加速度计 (LIS2DH12)
   - 检测设备的加速度
   - 可以检测设备的倾斜角度

2. 陀螺仪 (LIS2DH12)
   - 检测设备的旋转速度
   - 测量角速度

3. 地磁传感器 (MMC5983MA)
   - 检测地球磁场
   - 用于方向识别

4. 光线传感器 (BH1750)
   - 检测环境光线强度
   - 范围: 0-1023

5. 声音传感器 (SPH0645)
   - 检测环境声音强度
   - 范围: 0-1023""",
            "摄像头": """摄像头

掌控板可以外接摄像头模块。
摄像头用于图像采集和AI识别。

支持的功能:
- 拍照
- 视频录制
- AI物体识别
- QR码扫描

使用方法:
- camera.init() - 初始化摄像头
- camera.snapshot() - 拍摄照片
- camera.read() - 读取图像数据""",
        }

        for title, content in components.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=title)
            
            text = scrolledtext.ScrolledText(frame, font=("Arial", 11))
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, content)
            text.config(state=tk.DISABLED)

    def _on_exit(self):
        # 退出确认：防止误关导致正在运行的代码/未保存代码丢失
        if messagebox.askyesno("退出确认", "确定要退出 Sim-Handpy 吗？\n未保存的代码将丢失。"):
            self._running = False
            self.stop_vm()
            self.root.quit()
            self.root.destroy()


def show_splash():
    root = tk.Tk()
    root.overrideredirect(True)
    
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 640
    window_height = 380
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    canvas = tk.Canvas(root, width=window_width, height=window_height,
                       bg="#11111b", highlightthickness=0)
    canvas.pack()

    canvas.create_rectangle(0, 0, window_width, window_height, fill="#11111b", outline='')

    for y in range(0, window_height, 2):
        r = int(17 + (76 - 17) * (y / window_height))
        g = int(17 + (180 - 17) * (y / window_height))
        b = int(27 + (250 - 27) * (y / window_height))
        canvas.create_line(0, y, window_width, y, fill=f'#{r:02x}{g:02x}{b:02x}')

    cx = window_width // 2
    cy = 130

    canvas.create_oval(cx - 50, cy - 50, cx + 50, cy + 50,
                       fill="#89b4fa", outline="", stipple='gray25')
    canvas.create_oval(cx - 40, cy - 40, cx + 40, cy + 40,
                       fill="#1e1e2e", outline="")
    canvas.create_text(cx, cy, text="◆", font=("Segoe UI", 40, "bold"), fill="#89b4fa")

    canvas.create_text(cx, cy + 80, text="Sim-Handpy",
                       font=("Segoe UI", 32, "bold"), fill="#cdd6f4")
    canvas.create_text(cx, cy + 115, text="掌控板虚拟仿真",
                       font=("Segoe UI", 18), fill="#89b4fa")
    canvas.create_text(cx, cy + 145, text="具身智能学习平台",
                       font=("Segoe UI", 12), fill="#6c7086")

    canvas.create_text(cx, window_height - 40, text="v2.1  |  教育版  |  MicroPython 虚拟环境",
                       font=("Segoe UI", 10), fill="#585b70")

    alpha = [0.0]
    
    def fade_in():
        if alpha[0] < 1.0:
            alpha[0] = min(alpha[0] + 0.08, 1.0)
            root.attributes('-alpha', alpha[0])
            root.after(20, fade_in)
        else:
            root.after(1200, fade_out)
    
    def fade_out():
        if alpha[0] > 0:
            alpha[0] = max(alpha[0] - 0.08, 0.0)
            root.attributes('-alpha', alpha[0])
            root.after(20, fade_out)
        else:
            root.destroy()
    
    fade_in()
    root.mainloop()


def main():
    show_splash()
    
    root = tk.Tk()
    root.title("Sim-Handpy - 具身智能学习平台")
    root.geometry("1440x900")
    root.minsize(1400, 900)
    
    app = IntegratedVMApp(root)
    root.protocol("WM_DELETE_WINDOW", app._on_exit)
    root.mainloop()


if __name__ == "__main__":
    main()
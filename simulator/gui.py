import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import random

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from shared_state import shared_state
from lang import t, load_language, get_all_languages, get_current_lang

class VirtualMachineGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(t("title"))
        self.root.geometry("600x520")
        self.root.resizable(False, False)
        
        self._running = True
        self._sensor_thread = None
        
        self._init_ui()
        self._setup_callbacks()
        self._start_sensor_thread()
        
    def _setup_callbacks(self):
        shared_state.set_callbacks(
            oled_callback=self._on_oled_update,
            rgb_callback=self._on_rgb_update,
            sensor_callback=self._on_sensor_update
        )

    def _init_ui(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self._lang_var = tk.StringVar(value=get_current_lang())
        lang_menu = ttk.Combobox(top_frame, textvariable=self._lang_var, 
                                 values=list(get_all_languages().keys()),
                                 state='readonly', width=10)
        lang_menu.pack(side=tk.LEFT)
        
        lang_display_names = {code: name for code, name in get_all_languages().items()}
        lang_menu.configure(postcommand=lambda: self._update_lang_menu(lang_menu, lang_display_names))
        
        lang_menu.bind('<<ComboboxSelected>>', self._on_lang_change)
        
        ttk.Label(top_frame, text=t("board_title"), font=("Arial", 16, "bold")).pack(side=tk.RIGHT)
        
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        board_frame = ttk.Frame(main_frame, padding=10)
        board_frame.grid(row=0, column=0, sticky="nsew")
        
        oled_frame = ttk.LabelFrame(board_frame, text=t("oled_label"), padding=5)
        oled_frame.pack(pady=10)
        
        self.oled_canvas = tk.Canvas(oled_frame, width=256, height=128, bg="black", borderwidth=2, relief="solid")
        self.oled_canvas.pack()
        
        self._draw_oled_grid()
        
        rgb_frame = ttk.LabelFrame(board_frame, text=t("rgb_label"), padding=5)
        rgb_frame.pack(pady=5)
        
        rgb_canvas = tk.Canvas(rgb_frame, width=150, height=50, bg="#222")
        rgb_canvas.pack()
        self._rgb_canvas = rgb_canvas
        
        self.rgb_indicators = []
        for i in range(3):
            x = 20 + i * 45
            indicator = rgb_canvas.create_oval(x, 10, x + 25, 35, fill="black", outline="#444")
            self.rgb_indicators.append(indicator)
        
        buttons_frame = ttk.LabelFrame(board_frame, text=t("buttons_label"), padding=5)
        buttons_frame.pack(pady=5)
        
        btn_frame = ttk.Frame(buttons_frame)
        btn_frame.pack()
        
        self.btn_a = ttk.Button(btn_frame, text=t("btn_a"), width=8, 
                                command=lambda: self._toggle_button('A'))
        self.btn_a.grid(row=0, column=0, padx=5)
        
        self.btn_b = ttk.Button(btn_frame, text=t("btn_b"), width=8,
                                command=lambda: self._toggle_button('B'))
        self.btn_b.grid(row=0, column=1, padx=5)
        
        touch_frame = ttk.LabelFrame(board_frame, text=t("touch_label"), padding=5)
        touch_frame.pack(pady=5)
        
        touch_canvas = tk.Canvas(touch_frame, width=200, height=60, bg="#333")
        touch_canvas.pack()
        self._touch_canvas = touch_canvas
        
        touch_positions = [20, 55, 90, 125, 160, 195]
        touch_labels = ['P', 'Y', 'T', 'H', 'O', 'N']
        self.touch_indicators = {}
        
        for i, label in enumerate(touch_labels):
            x = touch_positions[i]
            indicator = touch_canvas.create_oval(x, 15, x + 20, 35, fill="#555", outline="#777")
            text = touch_canvas.create_text(x + 10, 50, text=label, fill="#AAA", font=("Arial", 10))
            self.touch_indicators[label] = indicator
            touch_canvas.tag_bind(indicator, '<ButtonPress-1>', lambda e, l=label: self._set_touch(l, True))
            touch_canvas.tag_bind(indicator, '<ButtonRelease-1>', lambda e, l=label: self._set_touch(l, False))
            touch_canvas.tag_bind(text, '<ButtonPress-1>', lambda e, l=label: self._set_touch(l, True))
            touch_canvas.tag_bind(text, '<ButtonRelease-1>', lambda e, l=label: self._set_touch(l, False))
        
        info_frame = ttk.LabelFrame(main_frame, text=t("sensor_label"), padding=5)
        info_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        
        sensor_config = [
            ("accel_label", "x: {:.2f}  y: {:.2f}  z: {:.2f}"),
            ("gyro_label", "x: {:.2f}  y: {:.2f}  z: {:.2f}"),
            ("mag_label", "x: {:.2f}  y: {:.2f}  z: {:.2f}"),
            ("light_label", "{}"),
            ("sound_label", "{}"),
            ("wifi_label", "{}"),
        ]
        
        self.sensor_frames = []
        self.sensor_labels = []
        self.sensor_vars = []
        
        for label_key, fmt in sensor_config:
            frame = ttk.Frame(info_frame)
            frame.pack(fill=tk.X, pady=2)
            label = ttk.Label(frame, text=t(label_key), width=15)
            label.pack(side=tk.LEFT)
            count = fmt.count('{')
            if '.2f' in fmt:
                var = tk.StringVar(value=fmt.format(*([0.0] * count)))
            else:
                var = tk.StringVar(value=fmt.format(*(["--"] * count)))
            self.sensor_vars.append(var)
            val_label = ttk.Label(frame, textvariable=var)
            val_label.pack(side=tk.LEFT)
            self.sensor_frames.append(frame)
            self.sensor_labels.append(label)
        
        control_frame = ttk.LabelFrame(main_frame, text=t("control_label"), padding=5)
        control_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        
        btn_run = ttk.Button(control_frame, text=t("btn_run"), command=self._run_test_script)
        btn_run.pack(side=tk.LEFT, padx=5)
        
        btn_clear = ttk.Button(control_frame, text=t("btn_clear"), command=self._clear_oled)
        btn_clear.pack(side=tk.LEFT, padx=5)
        
        btn_exit = ttk.Button(control_frame, text=t("btn_exit"), command=self._exit)
        btn_exit.pack(side=tk.RIGHT, padx=5)
        
        self._widgets = {
            'title': self.root,
            'board_title': top_frame.winfo_children()[1],
            'oled_label': oled_frame,
            'rgb_label': rgb_frame,
            'buttons_label': buttons_frame,
            'btn_a': self.btn_a,
            'btn_b': self.btn_b,
            'touch_label': touch_frame,
            'sensor_label': info_frame,
            'control_label': control_frame,
            'btn_run': btn_run,
            'btn_clear': btn_clear,
            'btn_exit': btn_exit,
        }
        
        self._sensor_label_keys = sensor_config
    
    def _update_lang_menu(self, menu, display_names):
        for i, code in enumerate(menu.cget('values')):
            menu.option_add(f'*TCombobox*values[{i}]', display_names.get(code, code))
    
    def _on_lang_change(self, event):
        lang_code = self._lang_var.get()
        load_language(lang_code)
        self._refresh_ui()
    
    def _refresh_ui(self):
        self.root.title(t("title"))
        
        for key, widget in self._widgets.items():
            if hasattr(widget, 'configure'):
                try:
                    if key == 'title':
                        widget.title(t("title"))
                    else:
                        widget.configure(text=t(key))
                except:
                    pass
        
        for i, (label_key, _) in enumerate(self._sensor_label_keys):
            self.sensor_labels[i].configure(text=t(label_key))
    
    def _draw_oled_grid(self):
        for i in range(8):
            self.oled_canvas.create_line(0, i * 16, 256, i * 16, fill="#111")
        for i in range(32):
            self.oled_canvas.create_line(i * 8, 0, i * 8, 128, fill="#111")
    
    def _on_oled_update(self, buffer):
        self.root.after(0, self._redraw_oled, buffer)
    
    def _redraw_oled(self, buffer):
        self.oled_canvas.delete("pixel")
        for page in range(8):
            for col in range(128):
                byte_val = buffer[page * 128 + col]
                for bit in range(8):
                    if byte_val & (1 << (7 - bit)):
                        x = col * 2
                        y = page * 16 + bit * 2
                        self.oled_canvas.create_rectangle(x, y, x + 2, y + 2, 
                                                           fill="white", outline="white", tags="pixel")
    
    def _on_rgb_update(self, colors):
        self.root.after(0, self._update_rgb_display, colors)
    
    def _update_rgb_display(self, colors):
        for i, color in enumerate(colors):
            if i >= len(self.rgb_indicators):
                break
            hex_color = '#{:02x}{:02x}{:02x}'.format(color[0], color[1], color[2])
            self._rgb_canvas.itemconfig(self.rgb_indicators[i], fill=hex_color)
    
    def _toggle_button(self, btn):
        current = shared_state.get_button(btn)
        new_state = not current
        shared_state.set_button(btn, new_state)
        target = self.btn_a if btn == 'A' else self.btn_b
        target.state(['pressed'] if new_state else ['!pressed'])
    
    def _set_touch(self, label, state):
        shared_state.set_touch(label, state)
        color = "#2196F3" if state else "#555"
        self._touch_canvas.itemconfig(self.touch_indicators[label], fill=color)
    
    def _on_sensor_update(self, accel, gyro, mag, light, sound):
        self.root.after(0, self._update_sensor_display, accel, gyro, mag, light, sound)
    
    def _start_sensor_thread(self):
        self._sensor_thread = threading.Thread(target=self._sensor_update_loop, daemon=True)
        self._sensor_thread.start()
    
    def _sensor_update_loop(self):
        while self._running:
            shared_state.update_sensors()
            time.sleep(0.1)
    
    def _update_sensor_display(self, accel, gyro, mag, light, sound):
        self.sensor_vars[0].set("x: {:.2f}  y: {:.2f}  z: {:.2f}".format(
            accel['x'], accel['y'], accel['z']))
        self.sensor_vars[1].set("x: {:.2f}  y: {:.2f}  z: {:.2f}".format(
            gyro['x'], gyro['y'], gyro['z']))
        self.sensor_vars[2].set("x: {:.2f}  y: {:.2f}  z: {:.2f}".format(
            mag['x'], mag['y'], mag['z']))
        self.sensor_vars[3].set(str(light))
        self.sensor_vars[4].set(str(sound))
        wifi_connected, wifi_ssid = shared_state.get_wifi()
        self.sensor_vars[5].set(t("wifi_connected").format(wifi_ssid) if wifi_connected else t("wifi_disconnected"))
    
    def _run_test_script(self):
        import subprocess
        subprocess.Popen([sys.executable, "demo.py"])
    
    def _clear_oled(self):
        shared_state.clear_oled_text()
    
    def _exit(self):
        self._running = False
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()
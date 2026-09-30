import tkinter as tk
from tkinter import ttk
import socket
import json
import threading
import time

class DisplayGUI:
    def __init__(self, root, vm_host='127.0.0.1', vm_port=7778):
        self.root = root
        self.root.title("Sim-Handpy")
        self.root.geometry("400x820")
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.focus_force()
        
        self.vm_host = vm_host
        self.vm_port = vm_port
        self.socket = None
        self._running = True
        self._last_state = None
        self._send_lock = threading.Lock()

        # 蜂鸣器：记录上一次频率，仅在状态变化时启动/停止发声线程
        self._buzzer_freq = None
        self._buzzer_stop = threading.Event()
        
        self._connected_sensors = {
            'camera': False,
            'microphone': True,
            'speaker': False,
            'battery': False,
            'display': False,
            'accelerometer': True,
            'gyro': False,
            'magnetic': False,
            'light': False,
            'sound': True
        }
        
        self._cached_sensors = None
        
        self._create_widgets()
        self._start_polling()
        self._detect_sensors_async()
    
    def _create_widgets(self):
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(top_frame, text="Sim-Handpy", font=("Arial", 12, "bold")).pack(side=tk.LEFT, padx=10)
        ttk.Button(top_frame, text="⚙️ Settings", width=10, command=self._show_settings).pack(side=tk.RIGHT, padx=10)
        
        board_frame = ttk.LabelFrame(self.root, text="Hardware Simulation", padding=8)
        board_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_oled(board_frame)
        self._create_rgb(board_frame)
        self._create_buzzer(board_frame)
        self._create_buttons(board_frame)
        self._create_touch(board_frame)
        self._create_sensors(board_frame)
        self._create_control(board_frame)
        self._create_status(board_frame)
    
    def _create_oled(self, parent):
        oled_frame = ttk.LabelFrame(parent, text="OLED Display (128x64)", padding=0)
        oled_frame.pack(pady=5)
        
        outer_frame = tk.Frame(oled_frame, bg="#2a2a2a", bd=0, highlightthickness=0)
        outer_frame.pack(padx=12, pady=12)
        
        inner_frame = tk.Frame(outer_frame, bg="#0a0a1a", bd=0, highlightthickness=0)
        inner_frame.pack(padx=8, pady=8)
        
        self.oled_text = tk.Label(inner_frame, text="Waiting for connection...", font=("Courier New", 10),
                                  bg="#0a0a1a", fg="#b4d4ff", justify=tk.LEFT, anchor="nw",
                                  width=21, height=8, padx=4, pady=4)
        self.oled_text.pack()
        
        label_frame = tk.Frame(outer_frame, bg="#2a2a2a")
        label_frame.pack(fill=tk.X, padx=8, pady=(0, 6))
        tk.Label(label_frame, text="128×64 OLED", fg="#666", bg="#2a2a2a", font=("Arial", 7)).pack(side=tk.LEFT)
        self.oled_status = tk.Label(label_frame, text="●", fg="#f00", bg="#2a2a2a", font=("Arial", 6))
        self.oled_status.pack(side=tk.RIGHT)
    
    def _create_rgb(self, parent):
        rgb_frame = ttk.LabelFrame(parent, text="RGB LED", padding=3)
        rgb_frame.pack(fill=tk.X, pady=5)
        
        self._rgb_canvas = tk.Canvas(rgb_frame, width=256, height=40, bg="#222", highlightthickness=0)
        self._rgb_canvas.pack()
        self.rgb_indicators = []
        for i in range(3):
            x = 20 + i * 80
            indicator = self._rgb_canvas.create_oval(x, 8, x + 40, 32, fill="black", outline="#444")
            self.rgb_indicators.append(indicator)

    def _create_buzzer(self, parent):
        """蜂鸣器指示栏：发声时显示当前音调频率（实际声音由 _update_buzzer 播放）"""
        buzzer_frame = ttk.LabelFrame(parent, text="Buzzer", padding=3)
        buzzer_frame.pack(fill=tk.X, pady=5)
        self.buzzer_label = tk.Label(buzzer_frame, text="♪ 静音", fg="#888",
                                     font=("Arial", 10, "bold"))
        self.buzzer_label.pack()
    
    def _create_buttons(self, parent):
        btn_frame = ttk.LabelFrame(parent, text="Buttons", padding=3)
        btn_frame.pack(fill=tk.X, pady=5)
        
        btn_row = ttk.Frame(btn_frame)
        btn_row.pack()
        
        self.btn_a = ttk.Button(btn_row, text="Button A", width=10)
        self.btn_a.pack(side=tk.LEFT, padx=10, pady=2)
        self.btn_a.bind('<ButtonPress-1>', lambda e: self._send_button('A', True))
        self.btn_a.bind('<ButtonRelease-1>', lambda e: self._send_button('A', False))
        
        self.btn_b = ttk.Button(btn_row, text="Button B", width=10)
        self.btn_b.pack(side=tk.LEFT, padx=10, pady=2)
        self.btn_b.bind('<ButtonPress-1>', lambda e: self._send_button('B', True))
        self.btn_b.bind('<ButtonRelease-1>', lambda e: self._send_button('B', False))
    
    def _create_touch(self, parent):
        touch_frame = ttk.LabelFrame(parent, text="Touch Pads (P Y T H O N)", padding=3)
        touch_frame.pack(fill=tk.X, pady=5)
        
        self._touch_canvas = tk.Canvas(touch_frame, width=256, height=45, bg="#333", highlightthickness=0)
        self._touch_canvas.pack()
        
        self.touch_indicators = {}
        for i, label in enumerate(['P', 'Y', 'T', 'H', 'O', 'N']):
            x = 15 + i * 40
            indicator = self._touch_canvas.create_oval(x, 8, x + 22, 28, fill="#555", outline="#777")
            text = self._touch_canvas.create_text(x + 11, 38, text=label, fill="#AAA", font=("Arial", 8))
            self.touch_indicators[label] = indicator
            self._touch_canvas.tag_bind(indicator, '<ButtonPress-1>', lambda e, l=label: self._send_touch(l, True))
            self._touch_canvas.tag_bind(indicator, '<ButtonRelease-1>', lambda e, l=label: self._send_touch(l, False))
            self._touch_canvas.tag_bind(text, '<ButtonPress-1>', lambda e, l=label: self._send_touch(l, True))
            self._touch_canvas.tag_bind(text, '<ButtonRelease-1>', lambda e, l=label: self._send_touch(l, False))
    
    def _create_sensors(self, parent):
        sensor_frame = ttk.LabelFrame(parent, text="Sensor Data", padding=3)
        sensor_frame.pack(fill=tk.X, pady=5)
        
        self.sensor_vars = []
        for label, default in [
            ("Accel:", "x: 0.00  y: 0.00  z: 1.00"),
            ("Light:", "---"),
            ("Sound:", "---"),
        ]:
            row = ttk.Frame(sensor_frame)
            row.pack(fill=tk.X, pady=1)
            ttk.Label(row, text=label, width=8, font=("Arial", 8)).pack(side=tk.LEFT)
            var = tk.StringVar(value=default)
            self.sensor_vars.append(var)
            ttk.Label(row, textvariable=var, font=("Arial", 8)).pack(side=tk.LEFT)
    
    def _create_control(self, parent):
        control_frame = ttk.LabelFrame(parent, text="Sensor Control", padding=3)
        control_frame.pack(fill=tk.X, pady=5)
        
        self._manual_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(control_frame, text="Manual Mode", variable=self._manual_mode_var,
                       command=self._toggle_manual_mode).pack(anchor=tk.W)
        
        manual_frame = ttk.Frame(control_frame)
        manual_frame.pack(fill=tk.X, pady=3)
        
        light_row = ttk.Frame(manual_frame)
        light_row.pack(fill=tk.X, pady=2)
        ttk.Label(light_row, text="Light:", width=6, font=("Arial", 8)).pack(side=tk.LEFT)
        self._light_slider = ttk.Scale(light_row, from_=0, to=4095, orient=tk.HORIZONTAL,
                                      command=lambda v: self._set_sensor('light', int(float(v))))
        self._light_slider.set(500)
        self._light_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._light_label = ttk.Label(light_row, text="500", width=6, font=("Arial", 8))
        self._light_label.pack(side=tk.LEFT)
        
        sound_row = ttk.Frame(manual_frame)
        sound_row.pack(fill=tk.X, pady=2)
        ttk.Label(sound_row, text="Sound:", width=6, font=("Arial", 8)).pack(side=tk.LEFT)
        self._sound_slider = ttk.Scale(sound_row, from_=0, to=4095, orient=tk.HORIZONTAL,
                                       command=lambda v: self._set_sensor('sound', int(float(v))))
        self._sound_slider.set(200)
        self._sound_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._sound_label = ttk.Label(sound_row, text="200", width=6, font=("Arial", 8))
        self._sound_label.pack(side=tk.LEFT)
        
        action_frame = ttk.LabelFrame(control_frame, text="Accelerometer Actions", padding=3)
        action_frame.pack(fill=tk.X, pady=3)
        
        actions = [
            ("Still", lambda: self._set_accel(0.0, 0.0, 1.0)),
            ("Shake", self._shake_action),
            ("Tilt Forward", lambda: self._set_accel(0.0, 1.0, 0.1)),
            ("Tilt Back", lambda: self._set_accel(0.0, -1.0, 0.1)),
            ("Tilt Left", lambda: self._set_accel(-1.0, 0.0, 0.1)),
            ("Tilt Right", lambda: self._set_accel(1.0, 0.0, 0.1)),
        ]
        
        for i in range(2):
            btn_row = ttk.Frame(action_frame)
            btn_row.pack(fill=tk.X)
            for name, cmd in actions[i*3:(i+1)*3]:
                ttk.Button(btn_row, text=name, width=10, command=cmd).pack(side=tk.LEFT, padx=2, pady=2)
    
    def _create_status(self, parent):
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="🔌 Disconnected", foreground="red", font=("Arial", 8))
        self.status_label.pack(side=tk.LEFT, padx=5)
        self.update_time = ttk.Label(status_frame, text="", font=("Arial", 8))
        self.update_time.pack(side=tk.RIGHT)
    
    def _detect_sensors_async(self):
        def detect():
            self._cached_sensors = self._detect_real_sensors()
        threading.Thread(target=detect, daemon=True).start()
    
    def _detect_real_sensors(self):
        devices = []
        
        try:
            import wmi
            c = wmi.WMI()
            
            for dev_name, keywords, label in [
                ('camera', ['camera', '摄像头', 'video'], 'Camera'),
                ('microphone', ['microphone', '麦克风'], 'Microphone'),
                ('speaker', ['speaker', '扬声器'], 'Speaker'),
            ]:
                found = []
                for dev in c.Win32_PnPEntity():
                    name = str(dev.Name).lower()
                    if any(k in name for k in keywords):
                        found.append(dev.Name)
                devices.append((dev_name, label, ', '.join(found[:2]) if found else 'Not detected', bool(found)))
            
            batteries = []
            for dev in c.Win32_Battery():
                batteries.append(f"{dev.Caption} ({dev.EstimatedChargeRemaining}%)")
            devices.append(('battery', 'Battery', ', '.join(batteries) if batteries else 'Not detected', bool(batteries)))
            
            displays = []
            for dev in c.Win32_DesktopMonitor():
                displays.append(dev.Name)
            devices.append(('display', 'Display', ', '.join(displays[:2]) if displays else 'Not detected', bool(displays)))
            
        except:
            try:
                import cv2
                cap = cv2.VideoCapture(0)
                devices.append(('camera', 'Camera', 'Webcam' if cap.isOpened() else 'Not detected', cap.isOpened()))
                cap.release()
            except:
                devices.append(('camera', 'Camera', 'Not detected', False))
            
            try:
                import pyaudio
                pa = pyaudio.PyAudio()
                info = pa.get_host_api_info_by_index(0)
                has_mic = any(pa.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels', 0) > 0 
                            for i in range(info.get('deviceCount', 0)))
                pa.terminate()
                devices.append(('microphone', 'Microphone', 'Detected' if has_mic else 'Not detected', has_mic))
            except:
                devices.append(('microphone', 'Microphone', 'Not detected', False))
            
            try:
                import psutil
                battery = psutil.sensors_battery()
                devices.append(('battery', 'Battery', f"{battery.percent}%{' (Charging)' if battery.power_plugged else ''}" if battery else 'Not detected', bool(battery)))
            except:
                devices.append(('battery', 'Battery', 'Not detected', False))
        
        for dev_name, label in [
            ('accelerometer', 'Accelerometer'),
            ('gyro', 'Gyroscope'),
            ('magnetic', 'Magnetic Sensor'),
            ('light', 'Light Sensor'),
            ('sound', 'Sound Sensor'),
        ]:
            devices.append((dev_name, label, 'Virtual Sensor', True))
        
        return devices
    
    def _show_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Sensor Settings")
        settings_window.geometry("350x500")
        settings_window.attributes('-topmost', True)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        ttk.Label(settings_window, text="Select Connected Sensors", font=("Arial", 12, "bold")).pack(pady=10)
        
        sensors = self._cached_sensors if self._cached_sensors else [
            (s, s.title(), 'Detecting...', False) for s in ['camera', 'microphone', 'speaker', 'battery', 'display',
                                                            'accelerometer', 'gyro', 'magnetic', 'light', 'sound']
        ]
        
        self._sensor_check_vars = {}
        for sensor_id, name, desc, available in sensors:
            frame = ttk.LabelFrame(settings_window, text=name, padding=5)
            frame.pack(fill=tk.X, padx=10, pady=3)
            
            var = tk.BooleanVar(value=self._connected_sensors.get(sensor_id, False))
            self._sensor_check_vars[sensor_id] = var
            
            check = ttk.Checkbutton(frame, text="Enable", variable=var)
            status_label = ttk.Label(frame, text="✓ Available" if available else "✗ Unavailable", 
                                     font=("Arial", 8), foreground="green" if available else "red")
            
            if not available:
                check.configure(state=tk.DISABLED)
            
            check.pack(side=tk.LEFT)
            status_label.pack(side=tk.RIGHT)
            ttk.Label(frame, text=desc, font=("Arial", 8), foreground="#666").pack(anchor=tk.W, pady=(2, 0))
        
        btn_frame = ttk.Frame(settings_window)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="OK", command=lambda: self._apply_settings(settings_window)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT, padx=5)
    
    def _apply_settings(self, window):
        for sensor_id, var in self._sensor_check_vars.items():
            self._connected_sensors[sensor_id] = var.get()
        
        if self.socket:
            try:
                msg = json.dumps({'action': 'sensor_config', 'sensors': self._connected_sensors}) + "\n"
                self._send_safe(msg)
                
                use_real = self._connected_sensors.get('microphone', False) or \
                          self._connected_sensors.get('camera', False) or \
                          self._connected_sensors.get('light', False)
                msg = json.dumps({'action': 'sensor_set_real', 'enabled': use_real}) + "\n"
                self._send_safe(msg)
            except:
                pass
        
        window.destroy()
    
    def _connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.vm_host, self.vm_port))
            return True
        except:
            self.socket = None
            return False

    def _send_safe(self, msg):
        """线程安全地发送命令并返回是否成功"""
        with self._send_lock:
            if not self.socket:
                return False
            try:
                self.socket.sendall(msg.encode('utf-8'))
                return True
            except Exception:
                self.socket = None
                return False
    
    def _send_button(self, btn, pressed):
        action = 'button_press' if pressed else 'button_release'
        msg = json.dumps({'action': action, 'button': btn}) + "\n"
        self._send_safe(msg)
    
    def _send_touch(self, pad, pressed):
        action = 'touch_press' if pressed else 'touch_release'
        msg = json.dumps({'action': action, 'pad': pad}) + "\n"
        if self._send_safe(msg):
            color = "#2196F3" if pressed else "#555"
            self._touch_canvas.itemconfig(self.touch_indicators[pad], fill=color)
    
    def _set_sensor(self, sensor_type, value):
        msg = json.dumps({'action': 'sensor_set', 'sensor': sensor_type, 'value': value}) + "\n"
        if self._send_safe(msg):
            if sensor_type == 'light':
                self._light_label.config(text=str(value))
            elif sensor_type == 'sound':
                self._sound_label.config(text=str(value))
    
    def _toggle_manual_mode(self):
        msg = json.dumps({'action': 'sensor_manual_mode', 'enabled': self._manual_mode_var.get()}) + "\n"
        self._send_safe(msg)
    
    def _set_accel(self, x, y, z):
        msg = json.dumps({'action': 'sensor_set', 'sensor': 'accelerometer', 'value': {'x': x, 'y': y, 'z': z}}) + "\n"
        self._send_safe(msg)
    
    def _shake_action(self):
        def shake():
            for _ in range(5):
                for dx, dy in [(2.0, 0.5), (-2.0, -0.5), (0.5, 2.0), (-0.5, -2.0)]:
                    self._set_accel(dx, dy, 0.5)
                    time.sleep(0.1)
            self._set_accel(0.0, 0.0, 1.0)
        threading.Thread(target=shake, daemon=True).start()
    
    def _start_polling(self):
        def poll():
            while self._running:
                if not self.socket and not self._connect():
                    time.sleep(1)
                    continue
                
                try:
                    # 连接后保持短超时，防止 recv 永久阻塞导致断线无法感知
                    self.socket.settimeout(1.0)
                    msg = json.dumps({'action': 'get_state'}).encode('utf-8') + b"\n"
                    with self._send_lock:
                        self.socket.sendall(msg)
                    response = ""
                    while True:
                        data = self.socket.recv(4096)
                        if not data:
                            self.socket = None
                            break
                        response += data.decode('utf-8', errors='replace')
                        if "\n" in response:
                            response = response.split("\n")[0]
                            break
                    
                    if response:
                        try:
                            state = json.loads(response)
                        except json.JSONDecodeError:
                            continue
                        # 只接受 get_state 的有效状态回复，忽略命令的 ok 回执
                        if state.get('status') == 'ok' and 'sensors' in state:
                            self._last_state = state
                except socket.timeout:
                    # 服务器繁忙时保留连接，等待下一次轮询
                    continue
                except OSError:
                    self.socket = None
                
                time.sleep(0.1)
        
        threading.Thread(target=poll, daemon=True).start()
        self._schedule_update()
    
    def _schedule_update(self):
        if self._running:
            if self._last_state:
                self._update_display(self._last_state)
                self.status_label.config(text="✅ Connected", foreground="green")
                self.oled_status.config(fg="#0f0")
            else:
                self.status_label.config(text="🔌 Disconnected", foreground="red")
                self.oled_status.config(fg="#f00")
            self.update_time.config(text=time.strftime("%H:%M:%S"))
            self.root.after(100, self._schedule_update)
    
    def _update_display(self, state):
        oled_text = state.get('oled_text', [""] * 8)
        self.oled_text.config(text="\n".join(oled_text))
        
        rgb_colors = state.get('rgb_colors', [(0,0,0),(0,0,0),(0,0,0)])
        for i, color in enumerate(rgb_colors):
            # 颜色值钳位到 0-255，防止异常值导致格式化崩溃
            try:
                r = max(0, min(255, int(color[0])))
                g = max(0, min(255, int(color[1])))
                b = max(0, min(255, int(color[2])))
                hex_color = '#{:02x}{:02x}{:02x}'.format(r, g, b)
            except (TypeError, ValueError, IndexError):
                hex_color = '#000000'
            self._rgb_canvas.itemconfig(self.rgb_indicators[i], fill=hex_color)

        # 蜂鸣器：状态变化时开/关 PC 蜂鸣（独立线程，不卡界面）
        buzzer = state.get('buzzer', {})
        try:
            freq = int(buzzer.get('freq', 0) or 0)
        except (TypeError, ValueError):
            freq = 0
        self._update_buzzer(freq)

        sensors = state.get('sensors', {})
        accel = sensors.get('accelerometer', {'x': 0, 'y': 0, 'z': 0})
        if isinstance(accel, tuple):
            self.sensor_vars[0].set(f"x: {accel[0]:.2f}  y: {accel[1]:.2f}  z: {accel[2]:.2f}")
        else:
            self.sensor_vars[0].set(f"x: {accel.get('x', 0):.2f}  y: {accel.get('y', 0):.2f}  z: {accel.get('z', 0):.2f}")
        self.sensor_vars[1].set(str(sensors.get('light', 0)))
        self.sensor_vars[2].set(str(sensors.get('sound', 0)))

    def _update_buzzer(self, freq):
        """蜂鸣器状态变化时启动/停止发声：winsound.Beep 在独立线程循环播放，避免阻塞 UI"""
        if freq == self._buzzer_freq:
            return
        self._buzzer_freq = freq
        if freq > 0:
            self.buzzer_label.config(text='♪ %d Hz' % freq, fg='#d33')
        else:
            self.buzzer_label.config(text='♪ 静音', fg='#888')

        self._buzzer_stop.set()  # 停掉旧的发声线程
        if freq > 0:
            self._buzzer_stop = threading.Event()
            stop = self._buzzer_stop

            def tone_loop():
                try:
                    import winsound
                    while not stop.is_set():
                        winsound.Beep(freq, 250)  # 发 250ms 短音，循环形成连续蜂鸣
                        stop.wait(0.05)           # 音间 50ms 间隙，保证 off 后迅速静音
                except ImportError:
                    pass  # 非 Windows 无 winsound：仅显示指示，不发声
                except Exception:
                    pass

            threading.Thread(target=tone_loop, daemon=True).start()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Sim-Handpy 悬浮显示窗')
    parser.add_argument('--port', type=int, default=7778, help='VM Server 端口（默认 7778）')
    args = parser.parse_args()
    root = tk.Tk()
    app = DisplayGUI(root, vm_port=args.port)
    root.mainloop()
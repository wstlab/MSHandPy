import threading
import random
import time

# MicroPython 兼容：真实 Python 的 time 模块没有 sleep_ms，
# 模拟器多处直接调用 time.sleep_ms，这里在进程级补一次（幂等）。
if not hasattr(time, 'sleep_ms'):
    time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class SharedState:
    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._oled_buffer = bytearray(128 * 8)
        self._oled_text_lines = [""] * 8
        self._rgb_colors = [(0, 0, 0), (0, 0, 0), (0, 0, 0)]

        self._button_a_pressed = False
        self._button_b_pressed = False
        self._touch_states = {'P': False, 'Y': False, 'T': False, 'H': False, 'O': False, 'N': False}

        self._accel_values = {'x': 0.0, 'y': 0.0, 'z': 1.0}
        self._gyro_values = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._mag_values = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._light_value = 500
        self._sound_value = 200

        self._wifi_connected = False
        self._wifi_ssid = ""

        self._user_led_state = False

        self._lock = threading.Lock()

        self._oled_callback = None
        self._rgb_callback = None
        self._sensor_callback = None

        self._use_real_sensors = False
        self._pc_sensors = None
        self._sensor_manual_mode = False

    def set_oled_buffer(self, buffer):
        with self._lock:
            self._oled_buffer = bytearray(buffer)
        if self._oled_callback:
            try:
                self._oled_callback(buffer)
            except Exception:
                pass

    def get_oled_buffer(self):
        with self._lock:
            return bytes(self._oled_buffer)

    def set_oled_text(self, line_idx, text):
        with self._lock:
            if 0 <= line_idx < 8:
                self._oled_text_lines[line_idx] = text[:20]

    def get_oled_text(self):
        with self._lock:
            return list(self._oled_text_lines)

    def clear_oled_text(self):
        with self._lock:
            self._oled_text_lines = [""] * 8

    def set_rgb_colors(self, colors):
        with self._lock:
            self._rgb_colors = list(colors)
        if self._rgb_callback:
            try:
                self._rgb_callback(self._rgb_colors)
            except Exception:
                pass

    def get_rgb_colors(self):
        with self._lock:
            return list(self._rgb_colors)

    def set_button(self, btn, state):
        with self._lock:
            if btn == 'A':
                self._button_a_pressed = state
            elif btn == 'B':
                self._button_b_pressed = state

    def get_button(self, btn):
        with self._lock:
            if btn == 'A':
                return self._button_a_pressed
            elif btn == 'B':
                return self._button_b_pressed
            return False

    def set_button_state(self, btn, state):
        self.set_button(btn, state)

    def get_button_state(self, btn):
        return 1 if self.get_button(btn) else 0

    def set_touch(self, label, state):
        with self._lock:
            self._touch_states[label] = state

    def get_touch(self, label):
        with self._lock:
            return self._touch_states.get(label, False)

    def set_led_state(self, led_name, state):
        with self._lock:
            if led_name == 'user_led':
                self._user_led_state = state

    def get_led_state(self, led_name):
        with self._lock:
            if led_name == 'user_led':
                return self._user_led_state
            return False

    def set_use_real_sensors(self, enabled):
        with self._lock:
            self._use_real_sensors = enabled

    def set_pc_sensors(self, pc_sensors):
        self._pc_sensors = pc_sensors

    def update_sensors(self):
        sensor_data = None
        if self._pc_sensors is not None:
            try:
                sensor_data = self._pc_sensors.get_sensor_data()
            except Exception:
                sensor_data = None

        with self._lock:
            if sensor_data is not None:
                real_sound = sensor_data.get('sound', 0)
                if real_sound and real_sound > 0:
                    scaled_sound = int(real_sound * 30)
                    self._sound_value = max(0, min(4095, scaled_sound))
                elif not self._sensor_manual_mode and not self._use_real_sensors:
                    self._sound_value = random.randint(100, 3000)

                real_light = sensor_data.get('light', 0)
                if real_light and real_light > 0:
                    scaled_light = int(real_light / 10)
                    self._light_value = max(0, min(4095, scaled_light))
                elif not self._sensor_manual_mode and not self._use_real_sensors:
                    self._light_value = random.randint(100, 4000)

                accel = sensor_data.get('accelerometer')
                if isinstance(accel, dict):
                    for k in ('x', 'y', 'z'):
                        if k in accel:
                            try:
                                self._accel_values[k] = float(accel[k])
                            except (TypeError, ValueError):
                                pass
                elif not self._sensor_manual_mode and not self._use_real_sensors:
                    self._accel_values['x'] = random.uniform(-0.2, 0.2)
                    self._accel_values['y'] = random.uniform(-0.2, 0.2)
                    self._accel_values['z'] = 1.0 + random.uniform(-0.1, 0.1)

                gyro = sensor_data.get('gyroscope')
                if isinstance(gyro, dict):
                    for k in ('x', 'y', 'z'):
                        if k in gyro:
                            try:
                                self._gyro_values[k] = float(gyro[k])
                            except (TypeError, ValueError):
                                pass
                elif not self._sensor_manual_mode and not self._use_real_sensors:
                    self._gyro_values['x'] = random.uniform(-0.5, 0.5)
                    self._gyro_values['y'] = random.uniform(-0.5, 0.5)
                    self._gyro_values['z'] = random.uniform(-0.5, 0.5)

                mag = sensor_data.get('magnetic')
                if isinstance(mag, dict):
                    for k in ('x', 'y', 'z'):
                        if k in mag:
                            try:
                                self._mag_values[k] = float(mag[k])
                            except (TypeError, ValueError):
                                pass
                elif not self._sensor_manual_mode and not self._use_real_sensors:
                    self._mag_values['x'] = random.uniform(-50, 50)
                    self._mag_values['y'] = random.uniform(-50, 50)
                    self._mag_values['z'] = random.uniform(-50, 50)
            elif not self._sensor_manual_mode and not self._use_real_sensors:
                self._accel_values['x'] = random.uniform(-0.2, 0.2)
                self._accel_values['y'] = random.uniform(-0.2, 0.2)
                self._accel_values['z'] = 1.0 + random.uniform(-0.1, 0.1)

                self._gyro_values['x'] = random.uniform(-0.5, 0.5)
                self._gyro_values['y'] = random.uniform(-0.5, 0.5)
                self._gyro_values['z'] = random.uniform(-0.5, 0.5)

                self._mag_values['x'] = random.uniform(-50, 50)
                self._mag_values['y'] = random.uniform(-50, 50)
                self._mag_values['z'] = random.uniform(-50, 50)

                self._light_value = random.randint(100, 4000)
                self._sound_value = random.randint(100, 3000)

        if self._sensor_callback:
            try:
                with self._lock:
                    accel_c = self._accel_values.copy()
                    gyro_c = self._gyro_values.copy()
                    mag_c = self._mag_values.copy()
                    light_c = self._light_value
                    sound_c = self._sound_value
                self._sensor_callback(accel_c, gyro_c, mag_c, light_c, sound_c)
            except Exception:
                pass

    def set_sensor_value(self, sensor_type, value):
        with self._lock:
            if sensor_type == 'light':
                self._light_value = max(0, min(4095, int(value)))
            elif sensor_type == 'sound':
                self._sound_value = max(0, min(4095, int(value)))
            elif sensor_type == 'accelerometer':
                if isinstance(value, dict):
                    for k in ('x', 'y', 'z'):
                        if k in value:
                            try:
                                self._accel_values[k] = float(value[k])
                            except (TypeError, ValueError):
                                pass
            elif sensor_type == 'gyro':
                if isinstance(value, dict):
                    for k in ('x', 'y', 'z'):
                        if k in value:
                            try:
                                self._gyro_values[k] = float(value[k])
                            except (TypeError, ValueError):
                                pass
            elif sensor_type == 'magnetic':
                if isinstance(value, dict):
                    for k in ('x', 'y', 'z'):
                        if k in value:
                            try:
                                self._mag_values[k] = float(value[k])
                            except (TypeError, ValueError):
                                pass

    def set_sensor_manual_mode(self, enabled):
        with self._lock:
            self._sensor_manual_mode = enabled

    def get_sensors(self):
        with self._lock:
            return (self._accel_values.copy(),
                    self._gyro_values.copy(),
                    self._mag_values.copy(),
                    self._light_value,
                    self._sound_value)

    def get_sensor_data(self, sensor_type):
        with self._lock:
            if sensor_type == 'light':
                return self._light_value / 4095.0
            elif sensor_type == 'sound':
                return self._sound_value / 4095.0
            elif sensor_type == 'temperature':
                return 25.0 + random.uniform(-2, 2)
            elif sensor_type == 'accelerometer':
                return self._accel_values.copy()
            elif sensor_type == 'gyroscope':
                return self._gyro_values.copy()
            elif sensor_type == 'magnetic':
                return self._mag_values.copy()
            return 0

    def set_wifi(self, connected, ssid=""):
        with self._lock:
            self._wifi_connected = connected
            self._wifi_ssid = ssid

    def get_wifi(self):
        with self._lock:
            return self._wifi_connected, self._wifi_ssid

    def set_callbacks(self, oled_callback=None, rgb_callback=None, sensor_callback=None):
        self._oled_callback = oled_callback
        self._rgb_callback = rgb_callback
        self._sensor_callback = sensor_callback


shared_state = SharedState()

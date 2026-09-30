import socket
import json
import time


class VirtualOled:
    def __init__(self, client):
        self._client = client

    def fill(self, color):
        self._client.send_command({'action': 'oled_fill', 'color': color})

    def DispChar(self, text, x=0, y=0, size=1):
        self._client.send_command({'action': 'oled_text', 'text': str(text), 'x': x, 'y': y})

    def show(self):
        return self._client.send_command({'action': 'oled_show'})

    def set_cursor(self, x, y):
        pass

    def fill_screen(self, color):
        self.fill(color)
        self.show()

    def clear(self):
        self.fill(0)
        self.show()

    def print(self, text):
        self.DispChar(text, 0, 0)
        self.show()


class VirtualRGB:
    def __init__(self, client, count=3):
        self._client = client
        self._count = count
        self._colors = [(0, 0, 0)] * count

    def __setitem__(self, idx, color):
        if 0 <= idx < self._count:
            self._colors[idx] = tuple(color)

    def __getitem__(self, idx):
        return self._colors[idx]

    def __len__(self):
        return self._count

    def write(self):
        self._client.send_command({'action': 'rgb_write', 'colors': self._colors})

    def fill(self, color):
        c = tuple(color)
        self._colors = [c] * self._count
        self.write()

    def clear(self):
        self.fill((0, 0, 0))


class VirtualBuzzer:
    """虚拟蜂鸣器：on/off 与真机 mPython 的 buzzer API 一致，play 为扩展便捷方法"""

    def __init__(self, client):
        self._client = client

    def on(self, freq=440):
        """以指定频率（Hz）持续发声，悬浮窗会同步显示音调并播放声音"""
        self._client.send_command({'action': 'buzzer_on', 'freq': int(freq)})

    def off(self):
        """停止发声"""
        self._client.send_command({'action': 'buzzer_off'})

    def play(self, tones):
        """播放旋律：tones 为 [(频率Hz, 时长ms), ...]，按节拍逐个发声（阻塞至播完）"""
        import time
        for freq, ms in tones:
            self.on(freq)
            time.sleep(ms / 1000.0)
        self.off()


class VirtualButton:
    def __init__(self, client, name):
        self._client = client
        self._name = name
        self._was_pressed = False

    def is_pressed(self):
        result = self._client.send_command({'action': 'button_read', 'button': self._name})
        return bool(result.get('pressed', False))

    def was_pressed(self):
        pressed = self.is_pressed()
        result = pressed and not self._was_pressed
        self._was_pressed = pressed
        return result

    def value(self):
        return 0 if self.is_pressed() else 1


class VirtualTouchPad:
    def __init__(self, client, pad_label):
        self._client = client
        self._pad = pad_label
        self._last_value = 1000

    def _read_raw(self):
        result = self._client.send_command({'action': 'touch_read', 'pad': self._pad})
        pressed = bool(result.get('pressed', False))
        return 200 if pressed else 1000

    def read(self):
        self._last_value = self._read_raw()
        return self._last_value

    def is_touched(self):
        return self._read_raw() < 500

    def is_pressed(self):
        return self.is_touched()


class VirtualTouch:
    def __init__(self, client):
        self._client = client
        self._pads = {}
        for _label in ['P', 'Y', 'T', 'H', 'O', 'N']:
            self._pads[_label] = VirtualTouchPad(client, _label)
            self._pads[_label.lower()] = self._pads[_label]

    def __getitem__(self, pad):
        label = str(pad).upper()
        if label in self._pads:
            return self._pads[label]
        return VirtualTouchPad(self._client, label)

    def __getattr__(self, name):
        key = name.lower()
        if key.startswith('touchpad_'):
            pad_char = key[-1].upper()
            if pad_char in self._pads:
                return self._pads[pad_char]
        if key in self._pads:
            return self._pads[key]
        raise AttributeError(name)


class VirtualSensor:
    def __init__(self, client, name):
        self._client = client
        self._name = name

    def read(self):
        result = self._client.send_command({'action': 'sensor_read', 'sensor': self._name})
        return result.get('value', 0)

    def value(self):
        return self.read()


class VirtualAccelerometer:
    def __init__(self, client):
        self._client = client
        self._cached = {'x': 0.0, 'y': 0.0, 'z': 1.0}

    def _fetch(self):
        result = self._client.send_command({'action': 'sensor_read', 'sensor': 'accelerometer'})
        val = result.get('value', self._cached)
        if isinstance(val, (list, tuple)) and len(val) == 3:
            self._cached = {'x': float(val[0]), 'y': float(val[1]), 'z': float(val[2])}
        elif isinstance(val, dict):
            try:
                self._cached = {
                    'x': float(val.get('x', 0)),
                    'y': float(val.get('y', 0)),
                    'z': float(val.get('z', 1)),
                }
            except (TypeError, ValueError):
                pass
        return self._cached

    def get(self):
        return self._fetch()

    def get_x(self):
        return self._fetch()['x']

    def get_y(self):
        return self._fetch()['y']

    def get_z(self):
        return self._fetch()['z']

    def values(self):
        d = self._fetch()
        return (d['x'], d['y'], d['z'])


class VirtualGyroscope:
    def __init__(self, client):
        self._client = client

    def _fetch(self):
        result = self._client.send_command({'action': 'sensor_read', 'sensor': 'gyroscope'})
        val = result.get('value', {'x': 0.0, 'y': 0.0, 'z': 0.0})
        if isinstance(val, (list, tuple)) and len(val) == 3:
            return {'x': float(val[0]), 'y': float(val[1]), 'z': float(val[2])}
        if isinstance(val, dict):
            return {
                'x': float(val.get('x', 0)),
                'y': float(val.get('y', 0)),
                'z': float(val.get('z', 0)),
            }
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}

    def get_x(self):
        return self._fetch()['x']

    def get_y(self):
        return self._fetch()['y']

    def get_z(self):
        return self._fetch()['z']

    def get(self):
        return self._fetch()


class VirtualMagnetic:
    def __init__(self, client):
        self._client = client

    def _fetch(self):
        result = self._client.send_command({'action': 'sensor_read', 'sensor': 'magnetic'})
        val = result.get('value', {'x': 0.0, 'y': 0.0, 'z': 0.0})
        if isinstance(val, (list, tuple)) and len(val) == 3:
            return {'x': float(val[0]), 'y': float(val[1]), 'z': float(val[2])}
        if isinstance(val, dict):
            return {
                'x': float(val.get('x', 0)),
                'y': float(val.get('y', 0)),
                'z': float(val.get('z', 0)),
            }
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}

    def read(self):
        d = self._fetch()
        return (d['x'], d['y'], d['z'])

    def get(self):
        return self._fetch()


class mPythonClient:
    def __init__(self, host='127.0.0.1', port=7778):
        self.host = host
        self.port = port
        self.socket = None
        self._connected = False
        self._lock = None

        self.oled = VirtualOled(self)
        self.display = self.oled
        self.rgb = VirtualRGB(self)
        self.buzzer = VirtualBuzzer(self)
        self.button_a = VirtualButton(self, 'A')
        self.button_b = VirtualButton(self, 'B')
        self.touch = VirtualTouch(self)
        self.light = VirtualSensor(self, 'light')
        self.sound = VirtualSensor(self, 'sound')
        self.accelerometer = VirtualAccelerometer(self)
        self.gyroscope = VirtualGyroscope(self)
        self.magnetic = VirtualMagnetic(self)

        for _label in ['P', 'Y', 'T', 'H', 'O', 'N']:
            setattr(self, f'touchpad_{_label.lower()}', self.touch[_label])
            setattr(self, f'touchPad{_label}', self.touch[_label])

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self._connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Make sure vm_server.py is running first!")
            self.socket = None
            self._connected = False
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self._connected = False

    def send_command(self, command):
        if not self._connected or self.socket is None:
            return {'status': 'error', 'message': 'Not connected'}
        try:
            payload = (json.dumps(command) + "\n").encode('utf-8')
            self.socket.sendall(payload)

            self.socket.settimeout(5.0)
            response = b""
            while True:
                try:
                    data = self.socket.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    self._connected = False
                    return {'status': 'error', 'message': 'Connection lost'}
                response += data
                if b"\n" in response:
                    break
            if not response:
                return {'status': 'error', 'message': 'No response'}
            line = response.decode('utf-8', errors='replace').split("\n", 1)[0]
            return json.loads(line) if line else {'status': 'error', 'message': 'Empty response'}
        except Exception as e:
            self._connected = False
            return {'status': 'error', 'message': f'Connection error: {e}'}

    def get_state(self):
        return self.send_command({'action': 'get_state'})


def connect(host='127.0.0.1', port=7778):
    client = mPythonClient(host, port)
    if client.connect():
        return client
    return None

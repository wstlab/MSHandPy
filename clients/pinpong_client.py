import socket
import json
import time

class PinMode:
    OUT = 0
    IN = 1
    ANALOG = 2
    PWM = 3
    SERVO = 4

class PinState:
    LOW = 0
    HIGH = 1

class Pin:
    def __init__(self, pin, client):
        self.pin = pin
        self.mode = PinMode.OUT
        self.value = PinState.LOW
        self._client = client
    
    def write_digital(self, value):
        self.value = value
        if self.pin in [0, 1]:
            action = 'button_press' if value == PinState.HIGH else 'button_release'
            btn = 'A' if self.pin == 0 else 'B'
            self._client.send_command({'action': action, 'button': btn})
    
    def read_digital(self):
        if self.pin in [0, 1]:
            btn = 'A' if self.pin == 0 else 'B'
            result = self._client.send_command({'action': 'button_read', 'button': btn})
            # 官方按键为上拉结构：按下为低电平 0
            return 0 if result.get('pressed', False) else 1
        return self.value

    def is_pressed(self):
        """PinPong Button.is_pressed() 兼容：按下返回 True"""
        return self.read_digital() == 0
    
    def write_analog(self, value):
        self.value = value
    
    def read_analog(self):
        if self.pin in [3, 4]:
            sensor_map = {3: 'light', 4: 'sound'}
            result = self._client.send_command({'action': 'sensor_read', 'sensor': sensor_map[self.pin]})
            return int(result.get('value', 0))
        return int(self.value * 4095)
    
    def set_mode(self, mode):
        self.mode = mode
    
    def on(self):
        self.write_digital(PinState.HIGH)
    
    def off(self):
        self.write_digital(PinState.LOW)

class RGB:
    def __init__(self, client):
        self._client = client
    
    def write(self, r, g, b):
        self._client.send_command({'action': 'rgb_write', 'colors': [(r, g, b), (r, g, b), (r, g, b)]})
    
    def write_color(self, color):
        color_map = {
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'cyan': (0, 255, 255),
            'magenta': (255, 0, 255),
            'white': (255, 255, 255),
            'black': (0, 0, 0),
        }
        if color in color_map:
            self.write(*color_map[color])
    
    def red(self):
        self.write(255, 0, 0)
    
    def green(self):
        self.write(0, 255, 0)
    
    def blue(self):
        self.write(0, 0, 255)
    
    def off(self):
        self.write(0, 0, 0)

class OLED:
    def __init__(self, client, width=128, height=64):
        self._client = client
        self.width = width
        self.height = height
        self._text_buffer = [""] * 8
    
    def init(self):
        self.clear()
    
    def clear(self):
        self._client.send_command({'action': 'oled_fill', 'color': 0})
        self._text_buffer = [""] * 8
    
    def write(self, text):
        lines = text.split('\n')[:8]
        for i, line in enumerate(lines):
            if i < 8:
                self._text_buffer[i] = line[:20]
                self._client.send_command({'action': 'oled_text', 'text': line[:20], 'x': 0, 'y': i * 16})
    
    def show(self):
        self._client.send_command({'action': 'oled_show'})
    
    def text(self, text, x=0, y=0, color=1):
        row = y // 16
        if 0 <= row < 8:
            current_text = self._text_buffer[row]
            self._text_buffer[row] = current_text[:x] + text + current_text[x+len(text):]
            self._client.send_command({'action': 'oled_text', 'text': self._text_buffer[row][:20], 'x': 0, 'y': row * 16})
    
    def fill(self, color):
        if color == 0:
            self.clear()
    
    def print(self, text):
        self.write(text)
        self.show()

class Button:
    A = None
    B = None

class Sensor:
    def __init__(self, pin, client=None):
        self.pin = pin
        self._client = client

    def read(self):
        client = self._client if self._client is not None else _get_client()
        if client is None:
            return 0
        if self.pin in [3, 4]:
            sensor_map = {3: 'light', 4: 'sound'}
            result = client.send_command({'action': 'sensor_read', 'sensor': sensor_map[self.pin]})
            return result.get('value', 0)
        return 0

class PinPongClient:
    def __init__(self, host='127.0.0.1', port=7778):
        self.host = host
        self.port = port
        self.socket = None
        self._connected = False
    
    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self._connected = True
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            print("Make sure vm_server.py is running first!")
            return False
    
    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            self._connected = False
    
    def send_command(self, command):
        if not self._connected:
            return {'status': 'error', 'message': 'Not connected'}
        
        try:
            self.socket.sendall(json.dumps(command).encode('utf-8') + b"\n")
            
            self.socket.settimeout(5.0)
            response = ""
            while True:
                try:
                    data = self.socket.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    self._connected = False
                    return {'status': 'error', 'message': 'Connection lost'}
                response += data.decode('utf-8', errors='replace')
                if "\n" in response:
                    return json.loads(response.split("\n")[0])
            
            return {'status': 'error', 'message': 'No response'}
        except Exception:
            self._connected = False
            return {'status': 'error', 'message': 'Connection error'}

_client = None
_oled = None
_rgb = None
_button_a = None
_button_b = None

def _get_client():
    """返回已连接的全局客户端，未连接时先初始化"""
    global _client
    if _client is None or not getattr(_client, '_connected', False):
        init()
    return _client

def init(board='mpython'):
    global _client, _oled, _rgb, _button_a, _button_b
    if _client is None or not getattr(_client, '_connected', False):
        _client = PinPongClient()
        _client.connect()
        # 客户端已重建（可能重连）：旧对象绑定的 socket 已失效，须一并重建
        _oled = None
        _rgb = None
        _button_a = None
        _button_b = None
    
    if _oled is None:
        _oled = OLED(_client)
    if _rgb is None:
        _rgb = RGB(_client)
    if _button_a is None:
        _button_a = Pin(0, _client)
    if _button_b is None:
        _button_b = Pin(1, _client)
    
    Button.A = _button_a
    Button.B = _button_b

def get_pin(pin):
    client = _get_client()
    if client is None:
        return None
    return Pin(pin, client)

def get_oled():
    global _oled
    if _oled is None:
        init()
    return _oled

def get_rgb():
    global _rgb
    if _rgb is None:
        init()
    return _rgb

def delay(ms):
    time.sleep(ms / 1000)

def sleep(seconds):
    time.sleep(seconds)
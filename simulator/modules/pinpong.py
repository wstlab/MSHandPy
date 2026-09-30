import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared_state import shared_state

_pin_initialized = False
_oled_initialized = False
_rgb_initialized = False

class PinMode:
    OUT = 0
    IN = 1
    ANALOG = 2
    PWM = 3
    SERVO = 4

class PinState:
    LOW = 0
    HIGH = 1

_BUTTON_PIN_MAP = {0: 'A', 1: 'B'}
_SENSOR_PIN_MAP = {3: 'light', 4: 'sound'}


class Pin:
    P0 = 0
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4
    P5 = 5
    P6 = 6
    P7 = 7
    P8 = 8
    P9 = 9
    P10 = 10
    P11 = 11
    P12 = 12
    P13 = 13
    P14 = 14
    P15 = 15
    P16 = 16
    P19 = 19
    P20 = 20

    # 官方 PinPong API：Pin.IN / Pin.OUT / Pin.PULL_UP ...
    IN = PinMode.IN
    OUT = PinMode.OUT
    ANALOG = PinMode.ANALOG
    PWM = PinMode.PWM
    SERVO = PinMode.SERVO
    PULL_UP = 1
    PULL_DOWN = 0
    HIGH = PinState.HIGH
    LOW = PinState.LOW

    def __init__(self, pin, mode=None, pull=None):
        self.pin = pin
        self.mode = mode if mode is not None else PinMode.OUT
        self.pull = pull
        self._digital_value = PinState.LOW
        self._analog_value = 0.0

    def write_digital(self, value):
        self._digital_value = 1 if value else 0
        if self.pin in (0, 1, 2, 25):
            shared_state.set_led_state('user_led', bool(value))

    def read_digital(self):
        if self.pin in _BUTTON_PIN_MAP:
            btn = _BUTTON_PIN_MAP[self.pin]
            return 0 if shared_state.get_button(btn) else 1
        if self.pin >= 0:
            return self._digital_value
        return PinState.HIGH

    def value(self, v=None):
        if v is None:
            return self.read_digital()
        self.write_digital(v)
        return None

    def write_analog(self, value):
        self._analog_value = max(0.0, min(1.0, float(value) / 4095.0 if value > 1 else value))

    def read_analog(self):
        if self.pin in _SENSOR_PIN_MAP:
            stype = _SENSOR_PIN_MAP[self.pin]
            _, _, _, light, sound = shared_state.get_sensors()
            if stype == 'light':
                return light
            elif stype == 'sound':
                return sound
        return int(self._analog_value * 4095)

    def set_mode(self, mode):
        self.mode = mode

    def init(self, mode=None, pull=None):
        # 兼容 PinPong 官方 API：Pin.init(mode, pull)
        if mode is not None:
            self.mode = mode
        if pull is not None:
            self.pull = pull
        return self

    def on(self):
        self.write_digital(PinState.HIGH)

    def off(self):
        self.write_digital(PinState.LOW)

    def irq(self, handler=None, trigger=3):
        self._irq_handler = handler
        return None


class _ButtonPin(Pin):
    def __init__(self, pin, btn):
        super().__init__(pin, PinMode.IN, None)
        self._btn = btn
        self._was_pressed = False

    def is_pressed(self):
        return shared_state.get_button(self._btn)

    def was_pressed(self):
        cur = shared_state.get_button(self._btn)
        result = not self._was_pressed and cur
        self._was_pressed = cur
        return result

    def read_digital(self):
        return 0 if shared_state.get_button(self._btn) else 1

    def value(self, v=None):
        if v is None:
            return self.read_digital()
        return None


class Button:
    A = None
    B = None

    def __init__(self, pin=None, pull=None):
        # 兼容官方 PinPong API：Button(Pin(Pin.P0)) / Button(Pin.P0) / Button()
        pid = getattr(pin, 'pin', pin) if pin is not None else None
        if pid is None:
            self._btn = Button.A
        else:
            pid = int(pid)
            self._btn = _ButtonPin(pid, 'A' if pid == 0 else 'B')

    def read_digital(self):
        return self._btn.read_digital()

    def value(self, v=None):
        return self._btn.value(v)

    def is_pressed(self):
        return self._btn.is_pressed()


Button.A = _ButtonPin(0, 'A')
Button.B = _ButtonPin(1, 'B')


class Sensor:
    def __init__(self, pin):
        self.pin = pin

    def read(self):
        if self.pin in _SENSOR_PIN_MAP:
            stype = _SENSOR_PIN_MAP[self.pin]
            _, _, _, light, sound = shared_state.get_sensors()
            if stype == 'light':
                return light
            elif stype == 'sound':
                return sound
        return 0

    def write(self, value):
        pass


def _get_touchpad_pin(label):
    mapping = {'P': 23, 'Y': 24, 'T': 25, 'H': 26, 'O': 27, 'N': 28}
    return mapping.get(label, 0)


class _TouchPad:
    def __init__(self, label):
        self._label = label
        self.pin = _get_touchpad_pin(label)

    def read(self):
        return 200 if shared_state.get_touch(self._label) else 1000

    def is_touched(self):
        return shared_state.get_touch(self._label)


class RGB:
    def __init__(self):
        global _rgb_initialized
        _rgb_initialized = True
    
    def write(self, r, g, b):
        shared_state.set_rgb_colors([(r, g, b), (r, g, b), (r, g, b)])
    
    def write_color(self, color):
        if isinstance(color, str):
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
    def __init__(self, width=128, height=64):
        global _oled_initialized
        _oled_initialized = True
        self.width = width
        self.height = height
        self._text_buffer = [""] * 8
    
    def init(self):
        shared_state.clear_oled_text()
    
    def clear(self):
        shared_state.clear_oled_text()
        self._text_buffer = [""] * 8
    
    def write(self, text):
        for i, line in enumerate(text.split('\n')[:8]):
            if i < 8:
                self._text_buffer[i] = line[:20]
                shared_state.set_oled_text(i, line[:20])
    
    def show(self):
        pass
    
    def text(self, text, x=0, y=0, color=1):
        row = y // 16
        if 0 <= row < 8:
            current_text = self._text_buffer[row]
            self._text_buffer[row] = current_text[:x] + text + current_text[x+len(text):]
            shared_state.set_oled_text(row, self._text_buffer[row][:20])
    
    def fill(self, color):
        if color == 0:
            self.clear()
    
    def draw_point(self, x, y, color=1):
        pass
    
    def draw_line(self, x1, y1, x2, y2, color=1):
        pass
    
    def draw_rectangle(self, x1, y1, x2, y2, color=1):
        pass
    
    def draw_circle(self, x, y, radius, color=1):
        pass
    
    def print(self, text):
        self.write(text)
        self.show()

def init(board='mpython'):
    global _pin_initialized
    _pin_initialized = True
    shared_state.set_oled_text(0, 'PinPong')
    shared_state.set_oled_text(1, 'Initialized!')
    print(f"PinPong board: {board}")

def get_pin(pin):
    return Pin(pin)

def get_oled():
    return OLED()

def get_rgb():
    return RGB()

def delay(ms):
    import time
    time.sleep(ms / 1000)

def sleep(seconds):
    import time
    time.sleep(seconds)
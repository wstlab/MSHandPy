import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared_state import shared_state
from machine import I2C, PWM, Pin, ADC, TouchPad
from ssd1106 import SSD1106_I2C
import esp, math, time, network
import ustruct, array
from neopixel import NeoPixel
sleep = time.sleep
def sleep_ms(ms):
    time.sleep(ms / 1000)
def sleep_us(us):
    time.sleep(us / 1000000)
import framebuf 
from micropython import schedule, const
import NVS
import ubinascii
import machine

_i2c = I2C(0, scl=Pin(Pin.P19), sda=Pin(Pin.P20), freq=400000)

if '_print' not in dir(): _print = print

def print(_t, *args, sep=' ', end='\n'):
    _s = str(_t)[0:1]
    if u'\u4e00' <= _s <= u'\u9fff':
        _print(' ' + str(_t), *args, sep=sep, end=end)
    else:
        _print(_t, *args, sep=sep, end=end)

def try_connect_wifi(_wifi, _ssid, _pass, _times):
    if _times < 1: return False
    try:
        print("Try Connect WiFi ... {} Times".format(_times) )
        _wifi.connectWiFi(_ssid, _pass)
        if _wifi.sta.isconnected(): return True
        else:
            time.sleep(5)
            return try_connect_wifi(_wifi, _ssid, _pass, _times-1)
    except:
        time.sleep(5)
        return try_connect_wifi(_wifi, _ssid, _pass, _times-1)

class Font(object):
    def __init__(self, font_address=0x400000):
        self.font_address = font_address
        self.height = 16
        self.width = 16

    def GetCharacterData(self, c):
        return None

class TextMode():
    normal = 1
    rev = 2
    trans = 3
    xor = 4

class OLED(SSD1106_I2C):
    def __init__(self):
        super().__init__(128, 64, _i2c)
        self.init_display()
        self.f = Font()
        self._text_buffer = [""] * 8
        self._cursor_line = 0

    def fill(self, color):
        super().fill(color)
        if color == 0:
            self._text_buffer = [""] * 8
            shared_state.clear_oled_text()

    def DispChar(self, s, x, y, mode=TextMode.normal, auto_return=False):
        text = str(s)
        row = y // 16
        if 0 <= row < 8:
            self._text_buffer[row] = text
            shared_state.set_oled_text(row, text)
        str_width = 0
        cur_x = x
        cur_y = y
        for ch in text:
            # 内置 5x7 ASCII 字体，每字符占 6 像素宽（framebuf.text 固定间距）
            width = 6
            if auto_return is True:
                if cur_x > self.width - width:
                    str_width += self.width - cur_x
                    cur_x = 0
                    cur_y += self.f.height
                    if cur_y > (self.height - self.f.height):
                        cur_y, cur_x = 0, 0
            if 32 <= ord(ch) <= 127:
                if mode == TextMode.normal or mode == TextMode.trans:
                    super().text(ch, cur_x, cur_y, 1)
                elif mode == TextMode.rev:
                    super().fill_rect(cur_x, cur_y, width, self.f.height, 1)
                    super().text(ch, cur_x, cur_y, 0)
                else:
                    super().text(ch, cur_x, cur_y, 1)
            str_width += width
            cur_x += width
        return (str_width - 1, (cur_x - 1, cur_y))

    def DispChar_font(self, font, s, x, y, invert=False):
        screen_width = self.width
        screen_height = self.height
        text_row = x
        text_col = y
        text_length = 0
        for c in s:
            char_width = 8
            char_height = 8
            buf = bytearray(char_height * ((char_width + 7) // 8))
            for i in range(len(buf)):
                buf[i] = 0xFF if invert else 0x00
            if text_row + char_width > screen_width - 1:
                text_length += screen_width - text_row
                text_row = 0
                text_col += char_height
            if text_col + char_height > screen_height + 2:
                text_col = 0
            text_row = text_row + char_width + 1
            text_length += char_width + 1
        return (text_length-1, (text_row-1, text_col))

    def bitmap(self, x, y, bitmap_data, w, h, color=1):
        for row in range(h):
            for col in range(w):
                byte_idx = row * ((w + 7) // 8) + (col // 8)
                bit_idx = 7 - (col % 8)
                if byte_idx < len(bitmap_data):
                    if bitmap_data[byte_idx] & (1 << bit_idx):
                        self.pixel(x + col, y + row, color)

    # ---- Mind+ / 兼容 API：行游标与打印 ----
    def setCursor(self, x, y):
        self._cursor_line = max(0, min(7, y // 16))

    def set_cursor(self, x, y):
        self.setCursor(x, y)

    def setCursorLine(self, line):
        self._cursor_line = max(0, min(7, int(line) - 1))

    def printLine(self, s):
        self.DispChar(str(s), 0, self._cursor_line * 16)
        self._cursor_line = min(self._cursor_line + 1, 7)
        self.show()

    def print_line(self, s):
        self.printLine(s)

oled = OLED()
display = oled

class MOTION(object):
    def __init__(self):
        self.i2c = _i2c
        self.chip = 2
        self.IIC_ADDR = 107
        self.x_offset = 0
        self.y_offset = 0
        self.z_offset = 0

    def _readReg(self, reg, nbytes=1):
        return self.i2c.readfrom_mem(self.IIC_ADDR, reg, nbytes)

    def _writeReg(self, reg, value):
        self.i2c.writeto_mem(self.IIC_ADDR, reg, value.to_bytes(1, 'little'))

    class Accelerometer():
        RANGE_2G = const(0)
        RANGE_4G = const(1)
        RANGE_8G = const(2)
        RANGE_16G = const(3)
        RES_14_BIT = const(0)
        RES_12_BIT = const(1)
        RES_10_BIT = const(2)

        TILT_LEFT = const(0)
        TILT_RIGHT = const(1)
        TILT_UP = const(2)
        TILT_DOWN = const(3)
        FACE_UP = const(4)
        FACE_DOWN = const(5)
        SINGLE_CLICK = const(6)
        DOUBLE_CLICK = const(7)
        FREEFALL = const(8)

        def __init__(self):
            self.x_offset = 0
            self.y_offset = 0
            self.z_offset = 0
            self.FS = 2
            self.event_tilt_up = None
            self.event_tilt_down = None
            self.event_tilt_left = None
            self.event_tilt_right = None
            self.event_face_up = None
            self.event_face_down = None
            self.event_single_click = None
            self.event_double_click = None
            self.event_freefall = None

        def irq(self, arg):
            pass

        def set_range(self, range):
            if range == 3:
                range = 64
            else:
                range = range << 4
            self.FS = 2 * (2 ** (range >> 4))

        def get_x(self):
            return shared_state.get_sensor_data('accelerometer')['x'] + self.x_offset

        def get_y(self):
            return shared_state.get_sensor_data('accelerometer')['y'] + self.y_offset

        def get_z(self):
            return shared_state.get_sensor_data('accelerometer')['z'] + self.z_offset

        def get(self):
            d = shared_state.get_sensor_data('accelerometer')
            return {'x': d['x'] + self.x_offset,
                    'y': d['y'] + self.y_offset,
                    'z': d['z'] + self.z_offset}

        def roll_pitch_angle(self):
            x, y, z = self.get_x(), self.get_y(), -self.get_z()
            mag = math.sqrt(x ** 2 + y ** 2 + z ** 2)
            x /= mag
            y /= mag
            z /= mag
            roll = math.degrees(-math.asin(y))
            pitch = math.degrees(math.atan2(x, z))
            return roll, pitch

        def set_offset(self, x=None, y=None, z=None):
            if x is not None:
                self.x_offset = x
            if y is not None:
                self.y_offset = y
            if z is not None:
                self.z_offset = z

    class Gyroscope():
        RANGE_16_DPS = const(0x00)
        RANGE_32_DPS = const(0x10)
        RANGE_64_DPS = const(0x20)
        RANGE_128_DPS = const(0x30)
        RANGE_256_DPS = const(0x40)
        RANGE_512_DPS = const(0x50)
        RANGE_1024_DPS = const(0x60)
        RANGE_2048_DPS = const(0x70)

        def __init__(self):
            self.x_offset = 0
            self.y_offset = 0
            self.z_offset = 0
            self.FS = 256

        def set_range(self, range):
            self.FS = 16 * (2 ** (range >> 4))

        def get_x(self):
            return shared_state.get_sensor_data('gyroscope')['x'] + self.x_offset

        def get_y(self):
            return shared_state.get_sensor_data('gyroscope')['y'] + self.y_offset

        def get_z(self):
            return shared_state.get_sensor_data('gyroscope')['z'] + self.z_offset

        def get(self):
            d = shared_state.get_sensor_data('gyroscope')
            return {'x': d['x'] + self.x_offset,
                    'y': d['y'] + self.y_offset,
                    'z': d['z'] + self.z_offset}

motion = MOTION()
accelerometer = motion.Accelerometer()
gyroscope = motion.Gyroscope()

class Magnetic(object):
    def __init__(self):
        self.addr = 48
        self.i2c = _i2c
        self.chip = 2
        self.product_ID = 16
        self.raw_x = 0.0
        self.raw_y = 0.0
        self.raw_z = 0.0
        self.cali_offset_x = 524288
        self.cali_offset_y = 524288
        self.cali_offset_z = 524288

    def _readReg(self, reg, nbytes=1):
        return self.i2c.readfrom_mem(self.addr, reg, nbytes)

    def _writeReg(self, reg, value):
        self.i2c.writeto_mem(self.addr, reg, value.to_bytes(1, 'little'))

    def get_x(self):
        _, _, mag, _, _ = shared_state.get_sensors()
        return mag['x']

    def get_y(self):
        _, _, mag, _, _ = shared_state.get_sensors()
        return mag['y']

    def get_z(self):
        _, _, mag, _, _ = shared_state.get_sensors()
        return mag['z']

    def get(self):
        _, _, mag, _, _ = shared_state.get_sensors()
        return dict(mag)

    def get_field_strength(self):
        return math.sqrt(self.get_x()**2 + self.get_y()**2 + self.get_z()**2)

    def calibrate(self):
        oled.fill(0)
        oled.DispChar("校准中...", 40, 24, 1)
        oled.show()
        time.sleep(2)
        oled.fill(0)
        oled.DispChar("校准完成", 40, 24, 1)
        oled.show()

    def get_heading(self):
        import random
        return random.uniform(0, 360)

magnetic = Magnetic()
magnetometer = magnetic

class PinMode(object):
    IN = 1
    OUT = 2
    PWM = 3
    ANALOG = 4
    OUT_DRAIN = 5

pins_remap_esp32 = (33, 32, 35, 34, 39, 0, 16, 17, 26, 25, 36, 2, -1, 18, 19, 21, 5, -1, -1, 22, 23, -1, -1, 27, 14, 12,
                    13, 15, 4)

class MPythonPin():
    def __init__(self, pin, mode=PinMode.IN, pull=None):
        if mode not in [PinMode.IN, PinMode.OUT, PinMode.PWM, PinMode.ANALOG, PinMode.OUT_DRAIN]:
            raise TypeError("mode must be 'IN, OUT, PWM, ANALOG,OUT_DRAIN'")
        if pin == 4:
            raise TypeError("P4 is used for light sensor")
        if pin == 10:
            raise TypeError("P10 is used for sound sensor")
        try:
            self.id = pins_remap_esp32[pin]
        except IndexError:
            raise IndexError("Out of Pin range")
        if mode == PinMode.IN:
            self.Pin = Pin(self.id, Pin.IN, pull)
        if mode == PinMode.OUT:
            self.Pin = Pin(self.id, Pin.OUT, pull)
        if mode == PinMode.OUT_DRAIN:
            self.Pin = Pin(self.id, Pin.OPEN_DRAIN, pull)
        if mode == PinMode.PWM:
            self.pwm = PWM(Pin(self.id), duty=0)
        if mode == PinMode.ANALOG:
            self.adc = ADC(Pin(self.id))
            self.adc.atten(ADC.ATTN_11DB)
        self.mode = mode

    def irq(self, handler=None, trigger=Pin.IRQ_RISING):
        if not self.mode == PinMode.IN:
            raise TypeError('the pin is not in IN mode')
        return self.Pin.irq(handler, trigger)

    def read_digital(self):
        if not self.mode == PinMode.IN:
            raise TypeError('the pin is not in IN mode')
        return self.Pin.value()

    def write_digital(self, value):
        if self.mode not in [PinMode.OUT, PinMode.OUT_DRAIN]:
            raise TypeError('the pin is not in OUT or OUT_DRAIN mode')
        self.Pin.value(value)

    def read_analog(self):
        if not self.mode == PinMode.ANALOG:
            raise TypeError('the pin is not in ANALOG mode')
        return self.adc.read()

    def write_analog(self, duty, freq=1000):
        if not self.mode == PinMode.PWM:
            raise TypeError('the pin is not in PWM mode')
        self.pwm.freq(freq)
        self.pwm.duty(duty)

class wifi:
    def __init__(self):
        self.sta = network.WLAN(network.WLAN.STA_IF)
        self.ap = network.WLAN(network.WLAN.AP_IF)

    def connectWiFi(self, ssid, passwd, timeout=10):
        if self.sta.isconnected():
            self.sta.disconnect()
        self.sta.active(True)
        list = self.sta.scan()
        wifi_dbm = '?'
        for i, wifi_info in enumerate(list):
            try:
                if wifi_info[0].decode() == ssid:
                    self.sta.connect(ssid, passwd)
                    wifi_dbm = wifi_info[3]
                    break
            except UnicodeError:
                self.sta.connect(ssid, passwd)
                wifi_dbm = '?'
                break
        start = time.time()
        print("Connection WiFi", end="")
        while (self.sta.ifconfig()[0] == '0.0.0.0'):
            if time.time() - start > timeout:
                print("")
                raise OSError("Timeout!,check your wifi password")
            print(".", end="")
            time.sleep(0.5)
        print("")
        print('WiFi(%s,%sdBm) Connection Successful, Config:%s' % (ssid, str(wifi_dbm), str(self.sta.ifconfig())))

    def disconnectWiFi(self):
        if self.sta.isconnected():
            self.sta.disconnect()
        self.sta.active(False)
        print('disconnect WiFi...')

    def enable_APWiFi(self, essid, password=b'', channel=10):
        self.ap.active(True)
        if password:
            authmode = 4
        else:
            authmode = 0
        self.ap.config(essid=essid, password=password, authmode=authmode, channel=channel)

    def disable_APWiFi(self):
        self.ap.active(False)
        print('disable AP WiFi...')

rgb = NeoPixel(Pin(17, Pin.OUT), 3, 3, 1, brightness=0.3)
rgb.write()

class _Music:
    """蜂鸣器/音乐兼容对象：buzzer.tone / music.pitch 等 API 映射为控制台输出"""
    def pitch(self, freq, duration=0):
        print(f"♪ 蜂鸣器: {int(freq)}Hz 持续 {int(duration)}ms")
        return 0

    def tone(self, freq=1000, duration=None):
        if duration is None:
            print(f"♪ 蜂鸣器: {int(freq)}Hz")
        else:
            print(f"♪ 蜂鸣器: {int(freq)}Hz 持续 {int(duration)}ms")
        return 0

    def noTone(self):
        print("♪ 蜂鸣器停止")

    def stop(self):
        print("♪ 蜂鸣器停止")

music = _Music()
buzzer = _Music()


_light_adc = ADC(Pin(39))
_light_adc.atten(_light_adc.ATTN_11DB)

_sound_adc = ADC(Pin(36))
_sound_adc.atten(_sound_adc.ATTN_11DB)

def _update_sensors():
    _, _, _, light, sound = shared_state.get_sensors()
    _light_adc._value = int(light)
    _sound_adc._value = int(sound)

class LightSensor:
    def read(self):
        _update_sensors()
        return _light_adc._value

class SoundSensor:
    def read(self):
        _update_sensors()
        return _sound_adc._value

light = LightSensor()
sound = SoundSensor()

class Button:
    def __init__(self, pin_num, reverse=False):
        self.__reverse = reverse
        (self.__press_level, self.__release_level) = (0, 1) if not self.__reverse else (1, 0)
        self.__pin = Pin(pin_num, Pin.IN, pull=Pin.PULL_UP)
        self.event_pressed = None
        self.event_released = None
        self.__pressed_count = 0
        self.__was_pressed = False
        self.__prev_state = False

    def is_pressed(self):
        return self.__pin.value() == self.__press_level

    def was_pressed(self):
        pressed = self.is_pressed()
        edge = pressed and not self.__prev_state
        if edge:
            self.__pressed_count += 1
        self.__prev_state = pressed
        return edge

    def get_presses(self):
        r = self.__pressed_count
        self.__pressed_count = 0
        return r

    def value(self):
        return self.__pin.value()

    def status(self):
        val = self.__pin.value()
        if val == 0:
            return 1
        elif val == 1:
            return 0

class Touch:
    def __init__(self, pin):
        self.__touch_pad = TouchPad(pin)
        self.event_pressed = None
        self.event_released = None
        self.__pressed_count = 0
        self.__was_pressed = False
        self.__prev_state = False
        self.__value = 0

    def is_pressed(self):
        self.__value = 1 if self.__touch_pad.read() < self.__touch_pad._threshold else 0
        return bool(self.__value)

    def is_touched(self):
        # 兼容官方 mPython 触摸 API
        return self.is_pressed()

    def was_pressed(self):
        pressed = self.is_pressed()
        edge = pressed and not self.__prev_state
        if edge:
            self.__pressed_count += 1
        self.__prev_state = pressed
        return edge

    def get_presses(self):
        r = self.__pressed_count
        self.__pressed_count = 0
        return r

    def read(self):
        return self.__touch_pad.read()

    def value(self):
        # 兼容 Mind+ / PinPong 风格：1=触摸，0=未触摸
        return 1 if self.is_pressed() else 0

button_a = Button(Pin.P5)
button_b = Button(Pin.P11)

touchpad_p = touchPad_P = Touch(Pin(Pin.P23))
touchpad_y = touchPad_Y = Touch(Pin(Pin.P24))
touchpad_t = touchPad_T = Touch(Pin(Pin.P25))
touchpad_h = touchPad_H = Touch(Pin(Pin.P26))
touchpad_o = touchPad_O = Touch(Pin(Pin.P27))
touchpad_n = touchPad_N = Touch(Pin(Pin.P28))

def numberMap(inputNum, bMin, bMax, cMin, cMax):
    outputNum = 0
    outputNum = ((cMax - cMin) / (bMax - bMin)) * (inputNum - bMin) + cMin
    return outputNum

def uuid():
    uuid = ''
    try:
        uuid = ubinascii.hexlify(machine.unique_id_custom()).decode().upper()
    except Exception as e:
        uuid = ubinascii.hexlify(machine.unique_id()).decode().upper()
    if uuid == 'FFFFFFFFFFFF'.upper():
        uuid = ubinascii.hexlify(machine.unique_id()).decode().upper()
    return uuid
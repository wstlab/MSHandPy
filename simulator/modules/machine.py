import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared_state import shared_state

class Pin:
    IN = 0
    OUT = 1
    OPEN_DRAIN = 2
    PULL_UP = 3
    PULL_DOWN = 4
    IRQ_FALLING = 1
    IRQ_RISING = 2
    IRQ_BOTH = 3

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
    P17 = 17
    P18 = 18
    P19 = 19
    P20 = 20
    P21 = 21
    P22 = 22
    P23 = 23
    P24 = 24
    P25 = 25
    P26 = 26
    P27 = 27
    P28 = 28
    P29 = 29

    _button_pins = {5: 'A', 11: 'B'}
    _touch_pins = {23: 'P', 24: 'Y', 25: 'T', 26: 'H', 27: 'O', 28: 'N'}

    def __init__(self, pin_id, mode=IN, pull=None):
        self.pin_id = pin_id
        self.mode = mode
        self.pull = pull
        self._value = 0 if mode == Pin.IN else 0
        self._irq_handler = None
        self._irq_trigger = 0

    def value(self, val=None):
        if val is None:
            if self.pin_id in Pin._button_pins:
                btn = Pin._button_pins[self.pin_id]
                pressed = shared_state.get_button(btn)
                return 0 if pressed else 1
            return self._value
        self._value = val
        return self._value

    def irq(self, handler=None, trigger=IRQ_FALLING):
        self._irq_handler = handler
        self._irq_trigger = trigger
        return self

    def on(self):
        self._value = 1

    def off(self):
        self._value = 0


class PWM:
    def __init__(self, pin, freq=500, duty=0):
        self.pin = pin
        self._freq = freq
        self._duty = duty

    def freq(self, freq=None):
        if freq is None:
            return self._freq
        self._freq = freq
        return freq

    def duty(self, duty=None):
        if duty is None:
            return self._duty
        self._duty = duty
        return duty


class ADC:
    ATTN_0DB = 0
    ATTN_2_5DB = 1
    ATTN_6DB = 2
    ATTN_11DB = 3

    _sensor_pins = {39: 'light', 36: 'sound'}

    def __init__(self, pin):
        self.pin = pin
        self._atten = ADC.ATTN_0DB
        self._value = 0

    def atten(self, value):
        self._atten = value

    def read(self):
        if hasattr(self.pin, 'pin_id'):
            pin_id = self.pin.pin_id
        else:
            pin_id = self.pin
        
        if pin_id in ADC._sensor_pins:
            sensor_type = ADC._sensor_pins[pin_id]
            accel, gyro, mag, light, sound = shared_state.get_sensors()
            if sensor_type == 'light':
                return light
            elif sensor_type == 'sound':
                return sound
        return self._value

    def read_u16(self):
        # 与 read() 同源（0-4095），映射到 16 位范围
        v = self.read()
        try:
            v = max(0, min(4095, int(v)))
        except (TypeError, ValueError):
            v = 0
        return int(v / 4095 * 65535)


class TouchPad:
    def __init__(self, pin):
        self.pin = pin
        self._value = 1000
        self._threshold = 400
        self._irq_handler = None

    def read(self):
        if hasattr(self.pin, 'pin_id'):
            pin_id = self.pin.pin_id
        else:
            pin_id = self.pin
        
        if pin_id in Pin._touch_pins:
            label = Pin._touch_pins[pin_id]
            if shared_state.get_touch(label):
                return 100
        return 1000

    def irq(self, handler):
        self._irq_handler = handler

    def config(self, threshold):
        self._threshold = threshold


class I2C:
    def __init__(self, id, scl=None, sda=None, freq=400000):
        self.id = id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self._devices = {}

    def scan(self):
        return list(self._devices.keys())

    def writeto(self, addr, buf, stop=True):
        if addr not in self._devices:
            self._devices[addr] = {}
        for i, b in enumerate(buf):
            if isinstance(buf, bytes):
                self._devices[addr][i] = b
            else:
                self._devices[addr][i] = buf[i]

    def readfrom(self, addr, nbytes):
        if addr not in self._devices:
            return bytearray(nbytes)
        result = bytearray(nbytes)
        for i in range(nbytes):
            result[i] = self._devices[addr].get(i, 0)
        return result

    def writeto_mem(self, addr, memaddr, buf, addrsize=8):
        if addr not in self._devices:
            self._devices[addr] = {}
        if isinstance(buf, int):
            buf = bytes([buf])
        if addrsize == 8:
            self._devices[addr][memaddr] = buf[0]
        else:
            self._devices[addr][memaddr] = int.from_bytes(buf, 'little')

    def readfrom_mem(self, addr, memaddr, nbytes, addrsize=8):
        if addr not in self._devices:
            return bytearray(nbytes)
        result = bytearray(nbytes)
        if addrsize == 8:
            for i in range(nbytes):
                result[i] = self._devices[addr].get(memaddr + i, 0)
        else:
            val = self._devices[addr].get(memaddr, 0)
            result[:2] = val.to_bytes(2, 'little')
        return result


class UART:
    def __init__(self, id, baudrate=115200, bits=8, parity=None, stop=1, tx=None, rx=None, rxbuf=256):
        self.id = id
        self.baudrate = baudrate
        self.bits = bits
        self.parity = parity
        self.stop = stop
        self.tx = tx
        self.rx = rx
        self.rxbuf = rxbuf
        self._buffer = []

    def read(self, nbytes=None):
        if nbytes is None:
            result = bytes(self._buffer)
            self._buffer = []
            return result
        result = bytes(self._buffer[:nbytes])
        self._buffer = self._buffer[nbytes:]
        return result

    def readline(self):
        for i, b in enumerate(self._buffer):
            if b == 0x0A:
                result = bytes(self._buffer[:i+1])
                self._buffer = self._buffer[i+1:]
                return result
        return b''

    def write(self, buf):
        pass


def unique_id():
    return b'\x01\x02\x03\x04\x05\x06'


def unique_id_custom():
    return b'\x01\x02\x03\x04\x05\x06'


def reset():
    pass


def sleep(seconds):
    import time
    time.sleep(seconds)


def sleep_ms(ms):
    import time
    time.sleep(ms / 1000)


def sleep_us(us):
    import time
    time.sleep(us / 1000000)
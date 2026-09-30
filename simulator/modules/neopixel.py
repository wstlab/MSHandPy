import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared_state import shared_state

class NeoPixel:
    def __init__(self, pin, n, bpp=3, timing=1, brightness=1.0):
        self.pin = pin
        self.n = n
        self.bpp = bpp
        self.timing = timing
        self.brightness = brightness
        self._buf = bytearray(n * bpp)
        self._callback = None

    def __setitem__(self, index, value):
        if isinstance(value, int):
            r = (value >> 16) & 0xFF
            g = (value >> 8) & 0xFF
            b = value & 0xFF
            value = (r, g, b)
        for i in range(self.bpp):
            self._buf[index * self.bpp + i] = int(value[i] * self.brightness)

    def __getitem__(self, index):
        start = index * self.bpp
        return tuple(self._buf[start:start + self.bpp])

    def fill(self, color):
        if isinstance(color, int):
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            color = (r, g, b)
        for i in range(self.n):
            self[i] = color

    def write(self):
        if self._callback:
            self._callback(self._buf)
        colors = []
        for i in range(self.n):
            start = i * self.bpp
            colors.append(tuple(self._buf[start:start + self.bpp]))
        shared_state.set_rgb_colors(colors)

    def set_callback(self, callback):
        self._callback = callback
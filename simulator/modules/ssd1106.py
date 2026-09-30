from framebuf import FrameBuffer
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared_state import shared_state

class SSD1106_I2C(FrameBuffer):
    def __init__(self, width, height, i2c, addr=0x3C):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.addr = addr
        self.pages = height // 8
        self.buffer = bytearray(self.width * self.pages)
        super().__init__(self.buffer, width, height)
        self._initialized = False

    def init_display(self):
        self.write_cmd(0xAE)
        self.write_cmd(0x00)
        self.write_cmd(0x10)
        self.write_cmd(0x40)
        self.write_cmd(0xB0)
        self.write_cmd(0x81)
        self.write_cmd(0xCF)
        self.write_cmd(0xA1)
        self.write_cmd(0xA6)
        self.write_cmd(0xA8)
        self.write_cmd(0x3F)
        self.write_cmd(0xC8)
        self.write_cmd(0xD3)
        self.write_cmd(0x00)
        self.write_cmd(0xD5)
        self.write_cmd(0x80)
        self.write_cmd(0xD9)
        self.write_cmd(0xF1)
        self.write_cmd(0xDA)
        self.write_cmd(0x12)
        self.write_cmd(0xDB)
        self.write_cmd(0x40)
        self.write_cmd(0x20)
        self.write_cmd(0x02)
        self.write_cmd(0x8D)
        self.write_cmd(0x14)
        self.write_cmd(0xAF)
        self._initialized = True

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, b'\x00' + bytes([cmd]))

    def write_data(self, buf):
        self.i2c.writeto(self.addr, b'\x40' + bytes(buf))

    def show(self):
        for page in range(self.pages):
            self.write_cmd(0xB0 + page)
            self.write_cmd(0x00)
            self.write_cmd(0x10)
            self.write_data(self.buffer[page * self.width:(page + 1) * self.width])
        shared_state.set_oled_buffer(self.buffer)
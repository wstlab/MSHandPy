import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simulator'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'simulator', 'modules'))

import threading
import time
import random
import math

from machine import Pin, PWM, ADC, TouchPad, I2C
from network import WLAN
from esp import flash_read, flash_write, flash_erase
from NVS import NVS
from framebuf import FrameBuffer
from ssd1106 import SSD1106_I2C
from neopixel import NeoPixel

import calibrate_img
import camera
import _boot
import uos
import repl
import pyboard
import virtual_usb

import educore
from educore import *

import v831
from v831 import *

import mpython_sim

_oled_display = None
_rgb_leds = None
_button_a = None
_button_b = None
_touch_pads = {}
_wifi_module = None
_i2c_bus = None
_light_sensor = None
_sound_sensor = None
_accelerometer = None
_gyroscope = None
_magnetic = None

_gui_instance = None
_running = False

# 传感器数据锁：_sensor_loop 写、get_* 读，避免多线程读写竞态
_sensor_lock = threading.Lock()


class VirtualMachine:
    def __init__(self):
        global _oled_display, _rgb_leds, _button_a, _button_b, _touch_pads
        global _wifi_module, _i2c_bus, _light_sensor, _sound_sensor
        global _accelerometer, _gyroscope, _magnetic
        
        self._sensor_thread = None
        self._accel_x = 0.0
        self._accel_y = 0.0
        self._accel_z = 1.0
        self._gyro_x = 0.0
        self._gyro_y = 0.0
        self._gyro_z = 0.0
        self._mag_x = 0.0
        self._mag_y = 0.0
        self._mag_z = 0.0
        self._light_val = 500
        self._sound_val = 200
        
        _i2c_bus = mpython_sim._i2c
        
        _oled_display = mpython_sim.oled
        
        _rgb_leds = mpython_sim.rgb
        
        _button_a = Pin(0, Pin.IN, Pin.PULL_UP)
        _button_b = Pin(2, Pin.IN, Pin.PULL_UP)
        
        _touch_pads = {
            'P': TouchPad(Pin(27)),
            'Y': TouchPad(Pin(14)),
            'T': TouchPad(Pin(12)),
            'H': TouchPad(Pin(13)),
            'O': TouchPad(Pin(15)),
            'N': TouchPad(Pin(4)),
        }
        
        _wifi_module = WLAN(WLAN.STA_IF)
        
        _light_sensor = mpython_sim._light_adc
        
        _sound_sensor = mpython_sim._sound_adc
        
        self._start_sensor_update()
    
    def _start_sensor_update(self):
        self._sensor_thread = threading.Thread(target=self._sensor_loop, daemon=True)
        self._sensor_thread.start()
    
    def _sensor_loop(self):
        global _running, _light_sensor, _sound_sensor
        while _running:
            with _sensor_lock:
                self._accel_x = random.uniform(-0.2, 0.2)
                self._accel_y = random.uniform(-0.2, 0.2)
                self._accel_z = 1.0 + random.uniform(-0.1, 0.1)
                
                self._gyro_x = random.uniform(-0.5, 0.5)
                self._gyro_y = random.uniform(-0.5, 0.5)
                self._gyro_z = random.uniform(-0.5, 0.5)
                
                self._mag_x = random.uniform(-50, 50)
                self._mag_y = random.uniform(-50, 50)
                self._mag_z = random.uniform(-50, 50)
                
                self._light_val = random.randint(100, 4000)
                self._sound_val = random.randint(100, 3000)
            
            if _light_sensor:
                _light_sensor._value = self._light_val
            if _sound_sensor:
                _sound_sensor._value = self._sound_val
            
            time.sleep(0.1)
    
    def get_accelerometer_data(self):
        with _sensor_lock:
            return self._accel_x, self._accel_y, self._accel_z
    
    def get_gyroscope_data(self):
        with _sensor_lock:
            return self._gyro_x, self._gyro_y, self._gyro_z
    
    def get_magnetic_data(self):
        with _sensor_lock:
            return self._mag_x, self._mag_y, self._mag_z
    
    def set_gui(self, gui):
        global _gui_instance
        _gui_instance = gui
    
    def set_button_state(self, btn, pressed):
        global _button_a, _button_b
        value = 0 if pressed else 1
        if btn == 'A' and _button_a:
            _button_a._value = value
            if _button_a._irq_handler:
                _button_a._irq_handler(_button_a)
        elif btn == 'B' and _button_b:
            _button_b._value = value
            if _button_b._irq_handler:
                _button_b._irq_handler(_button_b)
    
    def set_touch_state(self, pad, pressed):
        global _touch_pads
        if pad in _touch_pads:
            tp = _touch_pads[pad]
            tp._value = 300 if pressed else 1000
            if tp._irq_handler:
                tp._irq_handler(1 if pressed else 0)

_vm = None

def start_vm(show_gui=True):
    global _running, _vm
    
    _running = True
    
    try:
        virtual_usb.start_virtual_usb()
    except Exception as e:
        print(f"⚠️ Virtual USB 启动失败: {e}")
    
    # 启动 7778 VM Server（独立运行时保证执行链完整）
    _vm_server = None
    try:
        from vm_server import VMServer
        _vm_server = VMServer()
        threading.Thread(target=_vm_server.start, daemon=True).start()
    except Exception as e:
        print(f"⚠️ VM Server 启动失败: {e}")
    
    if show_gui:
        from gui import VirtualMachineGUI
        gui = VirtualMachineGUI()
        
        _vm = VirtualMachine()
        _vm.set_gui(gui)
        
        try:
            gui.run()
        finally:
            _running = False
            if _vm_server is not None:
                try:
                    _vm_server.stop()
                except Exception:
                    pass
            try:
                virtual_usb.stop_virtual_usb()
            except Exception:
                pass
    else:
        _vm = VirtualMachine()
    
    if _vm_server is not None:
        try:
            _vm_server.stop()
        except Exception:
            pass
    try:
        virtual_usb.stop_virtual_usb()
    except Exception:
        pass
    _running = False

if __name__ == "__main__":
    start_vm()

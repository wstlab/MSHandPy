import time
import gc
import ubinascii
import uos
from simulator.modules.machine import Pin
from simulator.modules.neopixel import NeoPixel
from simulator.modules.uos import bdev

_rgb = NeoPixel(Pin(17, Pin.OUT), 3, 3, 1, 0.1)
_rgb.write()
del _rgb

for count in range(3):
    print("=$%#=")
    time.sleep(0.1)
gc.collect()

mac = '$#mac:{}#$'.format(ubinascii.hexlify(b'\x01\x02\x03\x04\x05\x06').decode().upper())
print(mac)

try:
    uos.check_bootsec()
    print("Filesystem OK")
except:
    print("Initializing filesystem...")
    uos.setup()
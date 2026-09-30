print('educore init')

from ._educore import *
from ._camera1956 import Camera1956
from ._smartcamera import EduSmartCamera
from ._ble import *

class smartcamera(EduSmartCamera):
    def __init__(self, tx=16, rx=15):
        _tx = pins_esp32[tx]
        _rx = pins_esp32[rx]
        super().__init__(tx=_tx, rx=_rx)

class smartcamera1956(Camera1956):
    def __init__(self, tx=15, rx=16):
        _tx = pins_esp32[tx]
        _rx = pins_esp32[rx]
        super().__init__(tx=_tx, rx=_rx)

wifi = WiFi()
oled = OLED()
mqttclient = MqttClient()
webcamera = webcamera()
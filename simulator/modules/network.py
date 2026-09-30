class WLAN:
    STA_IF = 0
    AP_IF = 1

    def __init__(self, interface):
        self.interface = interface
        self._active = False
        self._connected = False
        self._ssid = ""
        self._password = ""
        self._ipconfig = ('0.0.0.0', '255.255.255.0', '192.168.1.1', '8.8.8.8')

    def active(self, is_active=None):
        if is_active is None:
            return self._active
        self._active = is_active
        return is_active

    def isconnected(self):
        return self._connected

    def connect(self, ssid, password):
        self._ssid = ssid
        self._password = password
        import time
        time.sleep(1)
        self._connected = True
        self._ipconfig = ('192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8')

    def disconnect(self):
        self._connected = False
        self._ipconfig = ('0.0.0.0', '255.255.255.0', '192.168.1.1', '8.8.8.8')

    def scan(self):
        return [
            (b'TestWiFi1', b'\x00\x11\x22\x33\x44\x55', 1, -50, 3, 0),
            (b'TestWiFi2', b'\x00\x11\x22\x33\x44\x56', 6, -65, 3, 0),
            (b'mPython_AP', b'\x00\x11\x22\x33\x44\x57', 11, -40, 3, 0),
        ]

    def ifconfig(self):
        return self._ipconfig

    def config(self, **kwargs):
        if 'essid' in kwargs:
            self._ssid = kwargs['essid']
        if 'password' in kwargs:
            self._password = kwargs['password']
        if 'authmode' in kwargs:
            pass
        if 'channel' in kwargs:
            pass
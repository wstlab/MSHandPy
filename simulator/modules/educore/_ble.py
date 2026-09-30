from micropython import const

class keycode():
    CLICK = 1
    DCLICK = 2

    a = const(0x04)
    b = const(0x05)
    c = const(0x06)
    d = const(0x07)
    e = const(0x08)
    f = const(0x09)
    g = const(0x0A)
    h = const(0x0B)
    i = const(0x0C)
    j = const(0x0D)
    k = const(0x0E)
    l = const(0x0F)
    m = const(0x10)
    n = const(0x11)
    o = const(0x12)
    p = const(0x13)
    q = const(0x14)
    r = const(0x15)
    s = const(0x16)
    t = const(0x17)
    u = const(0x18)
    v = const(0x19)
    w = const(0x1A)
    x = const(0x1B)
    y = const(0x1C)
    z = const(0x1D)

    _1 = const(0x1E)
    _2 = const(0x1F)
    _3 = const(0x20)
    _4 = const(0x21)
    _5 = const(0x22)
    _6 = const(0x23)
    _7 = const(0x24)
    _8 = const(0x25)
    _9 = const(0x26)
    _0 = const(0x27)
    ENTER = const(0x28)
    ESCAPE = const(0x29)
    BACKSPACE = const(0x2A)
    TAB = const(0x2B)
    SPACEBAR = const(0x2C)
    SPACE = SPACEBAR
    MINUS = const(0x2D)
    EQUALS = const(0x2E)
    LEFT_BRACKET = const(0x2F)
    RIGHT_BRACKET = const(0x30)
    BACKSLASH = const(0x31)
    POUND = const(0x32)
    SEMICOLON = const(0x33)
    QUOTE = const(0x34)
    GRAVE_ACCENT = const(0x35)
    COMMA = const(0x36)
    PERIOD = const(0x37)
    FORWARD_SLASH = const(0x38)

    CAPS_LOCK = const(0x39)

    F1 = const(0x3A)
    F2 = const(0x3B)
    F3 = const(0x3C)
    F4 = const(0x3D)
    F5 = const(0x3E)
    F6 = const(0x3F)
    F7 = const(0x40)
    F8 = const(0x41)
    F9 = const(0x42)
    F10 = const(0x43)
    F11 = const(0x44)
    F12 = const(0x45)

    PRINT_SCREEN = const(0x46)
    SCROLL_LOCK = const(0x47)
    PAUSE = const(0x48)

    INSERT = const(0x49)
    HOME = const(0x4A)
    PAGE_UP = const(0x4B)
    DELETE = const(0x4C)
    END = const(0x4D)
    PAGE_DOWN = const(0x4E)

    RIGHT_ARROW = const(0x4F)
    RIGHT = RIGHT_ARROW
    LEFT_ARROW = const(0x50)
    LEFT = LEFT_ARROW
    DOWN_ARROW = const(0x51)
    DOWN = DOWN_ARROW
    UP_ARROW = const(0x52)
    UP = UP_ARROW

    KEYPAD_NUMLOCK = const(0x53)
    KEYPAD_FORWARD_SLASH = const(0x54)
    KEYPAD_ASTERISK = const(0x55)
    KEYPAD_MINUS = const(0x56)
    KEYPAD_PLUS = const(0x57)
    KEYPAD_ENTER = const(0x58)
    KEYPAD_ONE = const(0x59)
    KEYPAD_TWO = const(0x5A)
    KEYPAD_THREE = const(0x5B)
    KEYPAD_FOUR = const(0x5C)
    KEYPAD_FIVE = const(0x5D)
    KEYPAD_SIX = const(0x5E)
    KEYPAD_SEVEN = const(0x5F)
    KEYPAD_EIGHT = const(0x60)
    KEYPAD_NINE = const(0x61)
    KEYPAD_ZERO = const(0x62)
    KEYPAD_PERIOD = const(0x63)
    KEYPAD_BACKSLASH = const(0x64)
    KEYPAD_EQUALS = const(0x67)
    F13 = const(0x68)
    F14 = const(0x69)
    F15 = const(0x6A)
    F16 = const(0x6B)
    F17 = const(0x6C)
    F18 = const(0x6D)
    F19 = const(0x6E)

    LEFT_CONTROL = const(0xE0)
    CONTROL = LEFT_CONTROL
    CTRL = CONTROL
    LEFT_SHIFT = const(0xE1)
    SHIFT = LEFT_SHIFT
    LEFT_ALT = const(0xE2)
    ALT = LEFT_ALT
    OPTION = ALT
    LEFT_GUI = const(0xE3)
    RIGHT_CONTROL = const(0xE4)
    RIGHT_SHIFT = const(0xE5)
    RIGHT_ALT = const(0xE6)
    RIGHT_GUI = const(0xE7)

class Mouse():
    SPACE = 0

class hid():
    def __init__(self, name='mpython_hid'):
        self.connection_state = False
        print(f"HID初始化: {name}")
        print("开始广播...")
    
    def _ble_hid_connect_callback(self, _1, _2, _3):
        self.connection_state = True

    def isconnected(self):
        return self.connection_state

    def keyboard_send(self,key):
        if(isinstance(key,list)):
            if(len(key)==2):
                print(f"发送组合键: {key}")
            else:
                print('组合键有误')
        else:
            print(f"发送按键: {key}")

    def mouse_key(self,key):
        if(key==1):
            print("鼠标左键单击")
        elif(key==2):
            print("鼠标左键双击")
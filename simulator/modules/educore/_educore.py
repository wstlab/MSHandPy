import gc
import time
import math
import random

pins_esp32 = (33, 32, 35, 34, 39, 0, 16, 17, 26, 25, 36, 2, -1, 18, 19, 21, 5, -1, -1, 22, 23, -1, -1, 27, 14, 12, 13, 15, 4)
pins_state = [None] * len(pins_esp32)

from machine import Pin, PWM, ADC, I2C
from neopixel import NeoPixel

from simulator.modules.mpython_sim import MPythonPin, PinMode, Button, button_a, button_b, oled, rgb as _rgb, numberMap, Magnetic, accelerometer as _accelerometer, light as _light, sound as _sound

class pin():
    def __init__(self, pin):
        self.pin_num = pin
        self.mode = PinMode.IN
        self.pull = None
        self._event_change = None
        self._event_rising = None
        self._event_falling = None
        self._pin = MPythonPin(self.pin_num, PinMode.IN)
        self._iqr_func = None

    def read_digital(self):
        pins_state[self.pin_num]=PinMode.IN
        self._pin = MPythonPin(self.pin_num, PinMode.IN)
        return self._pin.read_digital()

    def write_digital(self, value):
        pins_state[self.pin_num]=PinMode.OUT
        self._pin = MPythonPin(self.pin_num, PinMode.OUT, Pin.PULL_UP)
        return self._pin.write_digital(value)

    def read_analog(self):
        if self.pin_num not in [0, 1, 2, 3, 4, 10]:
            tmp = self.read_digital()
            if(tmp==0):
                return 0
            elif(tmp==1):
                return 4095
            else:
                return None
        pins_state[self.pin_num]=PinMode.ANALOG
        self._pin = MPythonPin(self.pin_num, PinMode.ANALOG)
        return self._pin.read_analog()
        
    def write_analog(self, value=0, freq=5000):
        pins_state[self.pin_num]=PinMode.PWM
        self._pin = MPythonPin(self.pin_num, PinMode.PWM)
        return self._pin.write_analog(duty=value, freq=freq)

    def irq(self, handler=None, trigger=Pin.IRQ_RISING):
        pins_state[self.pin_num]=PinMode.IN
        self._pin = MPythonPin(self.pin_num, PinMode.IN)
        self._pin.irq(trigger=trigger, handler=handler)
    
    @property
    def event_change(self):
        return self._event_change

    @event_change.setter
    def event_change(self, new_event_change):
        if new_event_change != self._event_change:
            self._event_change = new_event_change
            self._iqr_func = self._event_change
            self.irq(handler=self.func, trigger=Pin.IRQ_RISING|Pin.IRQ_FALLING)

    @property
    def event_rising(self):
        return self._event_rising

    @event_rising.setter
    def event_rising(self, new_event_rising):
        if new_event_rising != self._event_rising:
            self._event_rising = new_event_rising
            self._iqr_func = self._event_rising
            self.irq(handler=self.func, trigger=Pin.IRQ_RISING)

    @property
    def event_falling(self):
        return self._event_falling

    @event_falling.setter
    def event_falling(self, new_event_falling):
        if new_event_falling != self._event_falling:
            self._event_falling = new_event_falling
            self._iqr_func = self._event_falling
            self.irq(handler=self.func, trigger=Pin.IRQ_FALLING)
    
    def func(self,_):
        self._iqr_func()

class sound():
    def __init__(self,pin=None): 
        self.pin_num = pin
        self.type = 1
        if(self.pin_num==None):
            self.type = 1
        else:
            self.type = 2
            self.pin = MPythonPin(self.pin_num, PinMode.ANALOG)

    def read(self):
        if(self.type == 1):
            return _sound.read()
        elif(self.type == 2):
            return self.pin.read_analog()

class light():
    def __init__(self,pin=None): 
        self.pin_num = pin
        self.type = 1
        if(self.pin_num==None):
            self.type = 1
        else:
            self.type = 2
            self.pin = MPythonPin(self.pin_num, PinMode.ANALOG)

    def read(self):
        if(self.type == 1):
            return _light.read()
        elif(self.type == 2):
            return self.pin.read_analog()

class Accelerometer():
    def __init__(self) :
        self.shake_status = False
        self.X = 0.0
        self.Y = 0.0
        self.Z = 0.0

    def x(self):
        self.X = _accelerometer.get_x()
        return self.X

    def y(self):
        self.Y = _accelerometer.get_y()
        return self.Y

    def z(self):
        self.Z = _accelerometer.get_z()
        return self.Z

    def shake(self):
        return self.shake_status

class OLED(oled.__class__):
    def __init__(self):
        super().__init__()
    
    def print(self, _str):
        try:
            self.fill(0)
            _str = str(_str)
            if "\n" in _str:
                _str = _str.split("\n") 
                if(len(_str)<4):
                    for i in range(len(_str)):
                        self.DispChar(str(_str[i]), 0, i*16, 1, False)
                else:
                    for i in range(4):
                        self.DispChar(str(_str[i]), 0, i*16, 1, False)
            else:
                self.DispChar(str(_str), 0, 0, 1, True)
            self.show()
        except Exception as e:
            print('oled print err:'+str(e))

    def clear(self):
        self.fill(0)
        self.show()

class parrot():
    M1 = 1
    M2 = 2

    def __init__(self, *args, **kwargs):
        args_list = []
        self.in0 = kwargs.get('in0', None)
        self.in1 = kwargs.get('in1', None)

        if(self.in0==None):
            self.type = 1
            self.mode = True
            for arg in args:
                args_list.append(arg)
            if(self.in0 is None and len(args_list)!=1):
                print('位置参数数量错误')
            else:
                self.args_list = args_list
        else:
            self.type = 2
            self.mode = False
            if(self.in0==None or self.in1==None):
                print('关键字参数错误')
            self.out0 = MPythonPin(self.in0, PinMode.PWM)
            self.out1 = MPythonPin(self.in1, PinMode.PWM)
           
    def speed(self,speed):
        if(self.type==1):
            print(f"电机{self.args_list[0]}速度: {speed}")
        elif(self.type==2):
            if(speed>=0):
                speed = int(numberMap(speed, 0, 100, 0, 1023))
                self.out0.write_analog(speed)
                time.sleep_ms(2)
                self.out1.write_analog(0)
                time.sleep_ms(2)
            elif(speed<0):
                speed = int(numberMap(math.fabs(speed), 0, 100, 0, 1023))
                self.out1.write_analog(speed)
                time.sleep_ms(2)
                self.out0.write_analog(0)
                time.sleep_ms(2)

class servo():
    def __init__(self,pin):
        self.pin = pin
        self.pwm = PWM(Pin(pins_esp32[pin]), freq=50, duty=0)
    
    def angle(self, value):
        value = int(value)
        if(value<0):
            value = 0
        if(value>180):
            value = 180
        duty = int(numberMap(value, 0, 180, 26, 123))
        self.pwm.duty(duty)

class rfid():
    def __init__(self,sda,scl):
        _sda = pins_esp32[sda]
        _scl = pins_esp32[scl]
        if(sda==20 or scl==19):
            self.i2c = I2C(0, scl=Pin(Pin.P19), sda=Pin(Pin.P20), freq=400000)
        else:
            self.i2c = I2C(scl=Pin(_scl), sda=Pin(_sda), freq=400000)
            time.sleep_ms(100)
        print("RFID模块初始化完成")
    
    def scanning(self,wait=True):
        if(isinstance(wait, bool)):
            if(wait):
                while True:
                    rf = f"RFID_{random.randint(100000, 999999)}"
                    if random.random() > 0.7:
                        return rf
                    else:
                        time.sleep_ms(200)
            else:
                if random.random() > 0.5:
                    return f"RFID_{random.randint(100000, 999999)}"
                else:
                    return None
        elif(isinstance(wait, int)):
            time_start = time.time()
            while True:
                if (int(time.time()-time_start) > wait):
                    return None
                if random.random() > 0.5:
                    return f"RFID_{random.randint(100000, 999999)}"
                else:
                    time.sleep_ms(200)

from simulator.modules.mpython_sim import wifi

class WiFi(wifi):
    def __init__(self):
        super().__init__()

    def connect(self, ssid, psd, timeout=10000):
        self.connectWiFi(ssid, psd, int(timeout/1000))
    
    def status(self):
        return self.sta.isconnected()

    def info(self):
        return str(self.sta.ifconfig())

class MqttClient():
    def __init__(self):
        self.client = None
        self.server = None
        self.port = None
        self.client_id = None
        self.user = None
        self.passsword = None
        self.topic_msg_dict = {}
        self.topic_callback = {}
        self.tim_count = 0
        self._connected = False
        self.lock = False

    def connect(self, **kwargs):
        server = kwargs.get('server',"iot.mpython.cn" )
        port = kwargs.get('port',1883 )
        client_id = kwargs.get('client_id',"" )
        user = kwargs.get('user',"" )
        psd = kwargs.get('psd',None)
        password = kwargs.get('password',None)
        if(psd==None and password==None):
            psd = ""
        elif(password!=None):
            psd = password
        try:
            self.server = server
            self.port = port
            self.client_id = client_id
            self.user = user
            self.passsword = psd
            print('Connected to MQTT Broker "{}"'.format(self.server))
            self._connected = True
            gc.collect()
        except Exception as e:
            print('Connected to MQTT Broker error:{}'.format(e))

    def connected(self):
        return self._connected

    def publish(self, topic, content):
        try:
            self.lock = True
            print(f"发布消息: topic={topic}, content={content}")
            self.lock = False
        except Exception as e:
            print('publish error:{}'.format(e))

    def message(self, topic):
        topic = str(topic)
        if(not topic in self.topic_msg_dict):
            self.topic_callback[topic] = False 
            self.subscribe(topic, self.default_callbak)
            return self.topic_msg_dict.get(topic)
        else:
            return self.topic_msg_dict.get(topic)
        
    def received(self, topic, callback):
        self.subscribe(topic, callback)

    def subscribe(self, topic, callback):
        self.lock = True
        try:
            topic = str(topic)
            if(not topic in self.topic_msg_dict):
                self.topic_msg_dict[topic] = None
                self.topic_callback[topic] = True
                print(f"订阅主题: {topic}")
                time.sleep(0.1)
            elif(topic in self.topic_msg_dict and self.topic_callback[topic] == False):
                self.topic_callback[topic] = True
                time.sleep(0.1)
            else:
                print('Already subscribed to the topic:{}'.format(topic))
            self.lock = False
        except Exception as e:
            print('MQTT subscribe error:'+str(e))

    def on_message(self, topic, msg):
        try:
            gc.collect()
            topic = topic.decode('utf-8', 'ignore')
            msg = msg.decode('utf-8', 'ignore')
            if(topic in self.topic_msg_dict):
                self.topic_msg_dict[topic] = msg
        except Exception as e:
            print('MQTT on_message error:'+str(e))
    
    def default_callbak(self):
        pass
    
    def mqtt_check_msg(self):
        pass

    def mqtt_heartbeat(self,_):
        self.tim_count += 1 
        if(not self.lock):
            self.mqtt_check_msg()
        if(self.tim_count==200):
            self.tim_count = 0
            try:
                self._connected = True
            except Exception as e:
                print('MQTT keepalive ping error:'+str(e))
                self._connected = False

class ultrasonic():
    def __init__(self, **kwargs):
        self.type = -1
        sda = kwargs.get('sda',None)
        scl = kwargs.get('scl',None)
        trig = kwargs.get('trig',None)
        echo = kwargs.get('echo',None)
        if(sda != None and scl != None):
            self.type = 1
            _sda = pins_esp32[sda]
            _scl = pins_esp32[scl]
            if(sda==20 or scl==19):
                self.i2c = I2C(0, scl=Pin(Pin.P19), sda=Pin(Pin.P20), freq=400000)
            else:
                self.i2c = I2C(scl=Pin(_scl), sda=Pin(_sda), freq=400000)
                time.sleep_ms(100)
        elif(trig != None and echo != None):
            self.type = 2
            self._trig = pins_esp32[trig]
            self._echo = pins_esp32[echo]
            
    def distance(self):
        try:
            if(self.type==1):
                distanceCM = random.randint(5, 150)
                return distanceCM
            elif(self.type==2):
                distanceCM = random.randint(5, 150)
                return distanceCM
        except Exception as e:
            print(e)
            return None

class _dht11():
    def __init__(self, pin):
        self._pin = pins_esp32[pin]
        self.temperature = 25.0
        self.humidity = 50.0

    def read(self):
        self.temperature += random.uniform(-0.5, 0.5)
        self.humidity += random.uniform(-1, 1)
        return round(self.temperature, 1), round(self.humidity, 1)

dht11_old_pin = None
dht11_thing = None

def dht(pin):
    global dht11_old_pin,dht11_thing
    if dht11_old_pin != pin:
        dht11_thing = _dht11(pin)
        dht11_old_pin = pin
    return dht11_thing

class ds18b20():
    def __init__(self, pin):
        self._pin = pins_esp32[pin]
        self.temperature = 25.0
   
    def read(self):
        self.temperature += random.uniform(-0.3, 0.3)
        return round(self.temperature, 2)

def get_dict_from_file(dict_file):
    d = {}
    try:
        with open(dict_file) as f:
            d = dict(x.rstrip().split(None, 1) for x in f)
    except:
        pass
    return d 

def get_dict_from_str(s):
    _str = str(s)
    d = {}
    if "\n" in _str:
        _str = _str.split("\n")
        for i in _str:
            tmp = i.strip().split(' ')
            if len(tmp) >= 2:
                key = tmp[0]
                value = tmp[1]
                d[key] = value
        return d
    elif ";" in _str:
        _str = _str.split(";")
        for i in _str:
            tmp = i.strip().split(' ')
            if len(tmp) >= 2:
                key = tmp[0]
                value = tmp[1]
                d[key] = value
        return d
    else:
        return d

class accelerometer():
    def __init__(self):
        self.tim_count = 0
        self._is_shaked = False
        self._last_x = 0
        self._last_y = 0
        self._last_z = 0
        self._count_shaked = 0
        self.accelerometer = Accelerometer()

    def X(self):
        return self.accelerometer.x()
    
    def Y(self):
        return self.accelerometer.y()
    
    def Z(self):
        return self.accelerometer.z()
    
    def shake(self):
        return self.accelerometer.shake()

class FCR:
    def __init__(self):
        self.id = None
        self.blinks = None
        self.mouth = None
        self.status = 0

class webcamera():
    def __init__(self): 
        self.fcr = FCR()
    
    def connect(self, id):
        self.id = str(id)
        self.topic = str(id)
        self._MQTTClient = MqttClient()
        self._MQTTClient.connect(server='8.135.108.214', port=1883, client_id=self.id, user=self.id, psd=self.id)
        self._MQTTClient.received(self.topic, self.callbackFunction)
    
    def result(self):
        d = {"blink":self.fcr.blinks,"mouth_open":self.fcr.mouth,"status":self.fcr.status}
        return d

    def callbackFunction(self):
        try:
            msg = self._MQTTClient.message(topic=self.topic)
            if(msg):
                msg = eval(msg)
                self.fcr.blinks = msg["blink"]
                self.fcr.mouth = msg["mouth_open"]
                self.fcr.status = msg["status"]
            else:
                self.fcr.blinks = None
                self.fcr.mouth = None
                self.fcr.status = 0
        except Exception as e:
            print(e)
            self.fcr.blinks = None
            self.fcr.mouth = None
            self.fcr.status = 0

class button:
    a = 'a'
    b = 'b'
    def __init__(self,_type='a'): 
        self.button_a = button_a
        self.button_b = button_b
        self.type = _type
        self.func_event_change = None
        if(self.type not in ['a','b']):
            self.pin = pins_esp32[self.type]
            self.button = Button(self.pin)

    def func(self,_):
        self.func_event_change()

    @property
    def event_pressed(self):
        return self.func_event_change

    @event_pressed.setter
    def event_pressed(self, new_event_change):
        if new_event_change != self.func_event_change:
            self.func_event_change = new_event_change
            if(self.type=='a'):
                self.button_a.event_pressed = self.func
            elif(self.type=='b'):
                self.button_b.event_pressed = self.func
            else:
                self.button.event_pressed = self.func

    def status(self):
        if(self.type=='a'):
            return self.button_a.status()
        elif(self.type=='b'):
            return self.button_b.status()
        else:
            return self.button.status()

class speaker():
    def __init__(self,pin=None): 
        self.pin = pin
        self.type = 1
        if(pin==None):
            self.type = 1
        else:
            self.type = 2

    def tone(self,freq=1000,dur=None):
        if(isinstance(freq,list)):
            freq = freq[0]
        if(dur==None):
            print(f"播放音调: {freq}Hz")
        else:
            print(f"播放音调: {freq}Hz, 时长: {dur}ms")

    def stop(self):
        print("停止播放")

class rgb():
    def __init__(self,pin=None): 
        self.pin_num = pin
        self.type = 1
        if(self.pin_num==None):
            self.type = 1
        else:
            self.type = 2
            self.pin = pins_esp32[self.pin_num]
            self.my_rgb = NeoPixel(Pin(self.pin), n=10, bpp=3, timing=1)

    def write(self,index=[0,1,2],r=0,g=0,b=0):
        if(self.type == 1):
            for i in index:
                _rgb[i]=(r,g,b)
                _rgb.write()
                time.sleep_ms(1)
        elif(self.type == 2):
            for i in index:
                self.my_rgb[i]=(r,g,b)
                self.my_rgb.write()
                time.sleep_ms(1)
            
    def clear(self):
        if(self.type == 1):
            _rgb.fill((0,0,0))
            _rgb.write()
            time.sleep_ms(1)
        elif(self.type == 2):
            self.my_rgb.fill((0,0,0))
            self.my_rgb.write()
            time.sleep_ms(1)

class tsd():
    def __init__(self,pin=None): 
        self.pin_num = pin
        self.type = 1
        self.pin = MPythonPin(self.pin_num, PinMode.IN)

    def read(self):
        return self.pin.read_digital()

class pressure(object):
    def __init__(self, sda=20, scl=19):
        _sda = pins_esp32[sda]
        _scl = pins_esp32[scl]
        if(sda==20 or scl==19):
            self.i2c = I2C(0, scl=Pin(Pin.P19), sda=Pin(Pin.P20), freq=400000)
        else:
            self.i2c = I2C(scl=Pin(_scl), sda=Pin(_sda), freq=400000)
            time.sleep_ms(100)
        self.pressure_val = 1013.25

    def read(self):
        self.pressure_val += random.uniform(-0.5, 0.5)
        return round(self.pressure_val, 2)

class compass(object):
    def __init__(self):
        self.type = 1
        self.magnetic = Magnetic()
    
    def adjust(self):
        self.magnetic.calibrate()

    def direction(self):
        return self.magnetic.get_heading()

class force(object):
    def __init__(self, sda=20, scl=19):
        self._zero_scale = 0
        _sda = pins_esp32[sda]
        _scl = pins_esp32[scl]
        if(sda==20 or scl==19):
            self.i2c = I2C(0, scl=Pin(Pin.P19), sda=Pin(Pin.P20), freq=400000)
        else:
            self.i2c = I2C(scl=Pin(_scl), sda=Pin(_sda), freq=400000)
            time.sleep_ms(100)
        self.force_val = 0

    def zero(self):
        self._zero_scale = self.force_val

    def read(self,mass=True):
        tmp = random.uniform(-1, 10) - self._zero_scale
        if(tmp!=None):
            if(mass):
                m = round((tmp/9.80665)*1000,2)
                return m
            else:
                return round(tmp,2)
        else:
            return None

def abs(num):
    return math.fabs(num)
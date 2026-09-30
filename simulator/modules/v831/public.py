import gc
import threading
import time

AI ={
    'reset':[0xff, 0x01, 0x02],
    'sw_mode':[],
    'config':[0x03,0x01,0x02],
    'lcd':[0x10,0x01,0x02],
    'image':[0x64,0x01],
    'sensor':[0x64,0x01],
    'kpu':[],
    'light':[],
    'button':[],
    'button_A':[],
    'button_B':[],
    'mnist':[0x02,0x01,0x02],
    '20yolo':[0x03,0x01,0x02],
    'face_detection':[0x04,0x01,0x02],
    'face_recognize':[0x05,0x01,0x02,0x03,0x04,0x05],
    'self_learn':[0x06,0x01,0x02,0x03,0x04,0x05],
    'color':[0x07,0x01,0x02,0x03],
    'qrcode':[0x08,0x01,0x02,0x03],
    '1000class':[0x09,0x01,0x02,0x03],
    'guidepost':[0x0a,0x01,0x02],
    'kpu_model':[0x0b,0x01,0x02,0x03],
    'track':[0x0c,0x01,0x02,0x03,0x04],
    'VISUAL_TRACKING_MODE':[0x0d,0x01,0x02,0x03,0x04],
    'color_extracto':[0x0e,0x01,0x02],
    'apriltag':[0x0f,0x01,0x02,0x03],
    'model_yolo':[0x10,0x01,0x02],
    'model_restnet18':[0x11,0x01,0x02],
    'lpr':[0x12,0x01,0x02],
    'sobel':[0x13,0x01,0x02],
    'image_capture':[0x14,0x01,0x02]
}

DEFAULT_MODE = 1
MNIST_MODE = 2
OBJECT_RECOGNIZATION_MODE = 3
FACE_DETECTION_MODE = 4
FACE_RECOGNIZATION_MODE = 5
SELF_LEARNING_CLASSIFIER_MODE = 6
COLOE_MODE = 7
QRCODE_MODE = 8
RESNET18_1000_MODE = 9
GUIDEPOST_MODE = 10
KPU_MODEL_MODE = 11
TRACK_MODE = 12
VISUAL_TRACKING_MODE = 13
COLOR_EXTRACTO_MODE = 14
APRILTAG_MODE = 15
MODEL_YOLO_MODE = 16
MODEL_resnet18_MODE = 17
LPR_MODE = 18
SOBEL_MODE = 19
IMAGE_CAPTURE = 20

Factory_MODE = 0xFD

MODE=['保留','默认','数字识别','物体识别','人脸检测','人脸识别','自学习分类','颜色识别','二维码识别','语音识别','交通标志识别','自定义模型','寻找色块识别','图像寻线','LAB颜色提取器','AprilTag','自定义模型','resnet18模型']

def CheckCode(tmp):
    sum = 0
    for i in range(len(tmp)):
        sum += tmp[i]
    return sum & 0xff

def uart_handle(uart):
    gc.collect()
    return []

def uart_handle_str(uart):
    gc.collect()
    return []

def AI_Uart_CMD(uart, data_type, cmd, cmd_type, cmd_data=[0, 0, 0, 0, 0, 0, 0, 0]):
    gc.collect()
    check_sum = 0
    CMD = [0xAA, data_type, cmd, cmd_type]
    CMD.extend(cmd_data)
    for i in range(8-len(cmd_data)):
        CMD.append(0)
    for i in range(len(CMD)):
        check_sum = check_sum+CMD[i]
    CMD.append(check_sum & 0xFF)
    uart.write(bytes(CMD))

def AI_Uart_CMD_String(uart=None, cmd=0xfe, cmd_type=0xfe, cmd_data=[0, 0, 0], str_len=0, str_buf=''):
    gc.collect()
    check_sum = 0
    CMD = [0xAA, 0x02, cmd, cmd_type]
    CMD.extend(cmd_data)
    for i in range(3-len(cmd_data)):
        CMD.append(0)
    for i in range(len(CMD)):
        check_sum = check_sum + CMD[i]
    str_temp = bytes(str_buf, 'utf-8')
    str_len = len(str_temp)
    for i in range(len(str_temp)):
        check_sum = check_sum + str_temp[i]
    CMD = bytes(CMD) + bytes([str_len]) + str_temp + bytes([check_sum & 0xFF])
    uart.write(CMD)

def print_x16(date):
    for i in range(len(date)):
        print('{:2x}'.format(date[i]),end=' ')
    print('')

def hammingWeight(n):
    ans = 0
    for i in range(16):
        if n & 1 == 1:
            ans = i
        n >>= 1
    return ans

class TASK:
    def __init__(self, func=lambda: None, sec=-1, *args, **kwargs):
        self._thread = threading
        self.sec = sec
        self.func = func
        self.args, self.kwargs = args, kwargs
        self.enable = True
        self.lock = threading.Lock()
        self.stop_lock = threading.Lock()
        self.lock.acquire()
        self.stop_lock.acquire()
        self.thread_id = self._thread.Thread(target=self.__run, daemon=True).start()
        
    def __run(self):
        while True:
            self.lock.acquire()
            try:
                self.func(*self.args, **self.kwargs)
            except Exception as e:
                print('Task_function_error:', e)
                pass
            if self.sec < 0 or not self.enable:
                self.stop_lock.release()
            else:
                time.sleep(self.sec)
                self.lock.release()

    def start(self):
        self.lock.release()

    def stop(self):
        self.enable = False
        self.stop_lock.acquire()
        self.enable = True
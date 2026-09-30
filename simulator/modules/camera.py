from machine import Pin, UART
from v831.public import * 
from v831.ai import * 
import time
import gc
gc.collect()

class CameraV831:
    def __init__(self, rx=Pin.P15, tx=Pin.P16):
        self.uart = UART(2, baudrate=1500000, rx=rx, tx=tx, rxbuf=4096)
        self.mode = DEFAULT_MODE
        self.lock = False
        time.sleep(0.1)
        self.wait_for_ai_init()

    def wait_for_ai_init(self): 
        self.lock = True
        print("AI摄像头初始化中...")
        time.sleep(1)
        print("==AI摄像头通信成功==")
        self.lock = False

    def Generate_CMD(self, cmd_data=[0]):
        check_sum = 0
        CMD = [0xEF]
        CMD.extend(cmd_data)
        for i in range(len(CMD)):
            check_sum = check_sum + CMD[i]
        CMD.extend([check_sum & 0xFF])
        return CMD

    def face_detect_init(self):
        self.face_detect = FACE_DETECT(self.uart)
        self.mode = FACE_DETECTION_MODE
        print("人脸检测模式")
    
    def mnist_init(self):
        self.mnist = MNIST(self.uart)
        self.mode = MNIST_MODE
        print("数字识别模式")

    def yolo_detect_init(self):
        self.yolo_detect = YOLO(self.uart)
        self.mode = OBJECT_RECOGNIZATION_MODE
        print("物体识别模式")

    def face_recognize_init(self, face_num, accuracy):
        self.fcr = Face_recogization(self.uart, face_num=face_num, accuracy=accuracy)
        self.mode = FACE_RECOGNIZATION_MODE
        print(f"人脸识别模式: face_num={face_num}, accuracy={accuracy}")

    def self_learning_classifier_init(self, class_num, sample_num):
        self.slc = Self_learning_classfier(self.uart, class_num=class_num, sample_num=sample_num)
        self.mode = SELF_LEARNING_CLASSIFIER_MODE
        self.slc_parameter = [class_num, sample_num]
        print(f"自学习分类模式: class_num={class_num}, sample_num={sample_num}")

    def qrcode_init(self):
        self.qrcode = QRCode_recognization(self.uart)
        self.mode = QRCODE_MODE
        print("二维码识别模式")
    
    def apriltag_init(self):
        self.apriltag = Apriltag(self.uart)
        self.mode = APRILTAG_MODE
        print("AprilTag模式")
    
    def find_line_init(self):
        self.find_line = VisualTracking(self.uart)
        self.mode = VISUAL_TRACKING_MODE
        print("视觉寻线模式")

    def color_extracto_init(self):
        self.color_extracto = Color_Extracto(self.uart)
        self.mode = COLOR_EXTRACTO_MODE
        print("LAB颜色提取模式")

    def color_init(self):
        self.color = Color_recognization(self.uart)
        self.mode = COLOE_MODE
        print("颜色识别模式")

    def track_init(self):
        self.track = Track(self.uart)
        self.mode = TRACK_MODE
        print("色块追踪模式")
    
    def track_set_up(self,threshold,area_threshold):
        self.track.set_up(threshold=threshold,area_threshold=area_threshold)

    def model_yolo_init(self, labels, model_param, model_bin, width, height, anchors):
        self.yolo_model = YOLO_MODEL(uart=self.uart, labels=labels, model_param=model_param, model_bin=model_bin, width=width, height=height, anchors=anchors)
        self.mode = MODEL_YOLO_MODE 
        print("自定义YOLO模型模式")
    
    def model_restnet18_init(self, labels, model_param, model_bin, width, height):
        self.restnet18_model = Restnet18_MODEL(uart=self.uart, labels=labels, model_param=model_param, model_bin=model_bin, width=width, height=height)
        self.mode = MODEL_resnet18_MODE
        print("自定义ResNet18模型模式")

    def guidepost_init(self):
        self.guidepost = Guidepost(self.uart)
        self.mode = GUIDEPOST_MODE
        print("交通标志识别模式")

    def factory_init(self):
        AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFD)
        self.mode = Factory_MODE
        print("出厂设置模式")

    def restnet1000_init(self):
        self.restnet1000 = Restnet18_MODEL_1000(self.uart)
        self.mode = RESNET18_1000_MODE
        print("ResNet18 1000类识别模式")

    def lpr_init(self):
        self.lpr = LPR(self.uart)
        self.mode = LPR_MODE
        print("车牌识别模式")
    
    def canvas_init(self):
        AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFA, [0x01])
        self.mode = DEFAULT_MODE
        print("画布模式")
    
    def canvas_clear(self):
        AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFA, [0x02])
        print("画布清除")
    
    def canvas_txt(self,txt='',scale=1,x=0,y=0):
        _str = str([x,y,txt])
        AI_Uart_CMD_String(uart=self.uart, cmd=0x01, cmd_type=0xFA, cmd_data=[scale], str_buf=_str)
        print(f"画布文字: {txt}")

    def img_capture_init(self,path,width,high):
        self.img_capture = IMAGE_CAPTURE(self.uart,path,width,high)
        self.mode = IMAGE_CAPTURE
        print(f"图像采集模式: path={path}, width={width}, height={high}")

    def set_led(self,power=False):
        if(power):
            AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFC, [0x01])
        else:
            AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFC, [0x02])
        time.sleep(0.1)
        print(f"LED: {'开启' if power else '关闭'}")
        
    def set_rgb(self,r=255,g=255,b=255):
        AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFB, [0x01,int(r),int(g),int(b)])
        time.sleep(0.1)
        print(f"RGB: ({r},{g},{b})")
    
    def rgb_off(self):
        AI_Uart_CMD(self.uart, 0x01, 0x01, 0xFB, [0x02])
        time.sleep(0.1)
        print("RGB关闭")

    def switcher_mode(self, mode=-1):
        self.lock = True
        
        if(self.mode==mode):
            print('模式相同，未切换')
            print('当前模式:',MODE[self.mode])
            self.lock = False
            time.sleep(1.5)
            return

        if(mode==GUIDEPOST_MODE):
            self.guidepost_init()    
        elif(mode==TRACK_MODE):
            self.track_init()
        elif(mode==VISUAL_TRACKING_MODE):
            self.find_line_init()
        elif(mode==COLOR_EXTRACTO_MODE):
            self.color_extracto_init()
        elif(mode==APRILTAG_MODE):
            self.apriltag_init()
        elif(mode==SELF_LEARNING_CLASSIFIER_MODE):
            self.self_learning_classifier_init(3,15)
        elif(mode==OBJECT_RECOGNIZATION_MODE):
            self.yolo_detect_init()
        elif(mode==MODEL_YOLO_MODE):
            self.mode = MODEL_YOLO_MODE

        time.sleep(0.5)
        print('当前模式:',MODE[self.mode])
        self.lock = False
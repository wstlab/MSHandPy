from v831.public import *
import gc
import time
import random

OBJ_TYPE = ['飞机','自行车','鸟','船','瓶子','公交车','汽车','猫','椅子','奶牛','餐桌','狗','屋子','摩托','人','盆栽','羊','沙发','火车','电视']

class Face_recogization(object):
    def __init__(self, uart, face_num=1, accuracy=80):
        self.uart = uart
        self.face_num = face_num
        self.accuracy = accuracy
        self.id = None
        self.max_score = None
        self.count = 0
        self.lock = False
        print("人脸识别初始化完成")

    def add_face(self):
        print("添加人脸")

    def recognize(self):
        time.sleep_ms(10)
        if random.random() > 0.5:
            self.id = random.randint(0, self.face_num-1)
            self.max_score = round(random.uniform(0.7, 1.0), 2)
        else:
            self.id, self.max_score = None, None

class Self_learning_classfier(object):
    def __init__(self, uart=None, class_num=1, sample_num=5):
        self.uart = uart
        self.class_num = class_num
        self.sample_num = sample_num
        self.id = None
        self.max_score = None
        self.count = 0
        self.lock = False
        print("自学习分类器初始化完成")
        
    def add_class_img(self):
        print("添加分类图像")

    def add_sample_img(self):
        pass

    def train(self):
        print("训练中...")
        time.sleep(1)
        print("训练完成")

    def predict(self):
        time.sleep_ms(20)
        if random.random() > 0.3:
            self.id = random.randint(0, self.class_num-1)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id, self.max_score = None, None

    def save_classifier(self, name):
        print(f"保存分类器: {name}")

    def load_classifier(self, name):
        print(f"加载分类器: {name}")

class YOLO(object):
    def __init__(self, uart):
        self.uart = uart
        self.category_list = OBJ_TYPE
        self.id = None
        self.max_score = None
        self.lock = False
        self.count = 0
        self.status = False
        print("YOLO物体识别初始化完成")

    def recognize(self):
        self.count += 1
        time.sleep_ms(20)
        if random.random() > 0.3:
            self.id = random.randint(0, len(self.category_list)-1)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id, self.max_score = None, None

class MNIST(object):
    def __init__(self, uart):
        self.uart = uart
        self.id = None
        self.max_score = None
        self.count = 0
        self.lock = False
        print("MNIST数字识别初始化完成")

    def recognize(self):
        time.sleep_ms(10)
        if random.random() > 0.2:
            self.id = random.randint(0, 9)
            self.max_score = round(random.uniform(0.7, 1.0), 2)
        else:
            self.id, self.max_score = None, None

class FACE_DETECT(object):
    def __init__(self, uart):
        self.uart = uart
        self.face_num = None
        self.max_score = None
        self.count = 0
        self.lock = False
        print("人脸检测初始化完成")

    def recognize(self):
        time.sleep_ms(10)
        if random.random() > 0.3:
            self.face_num = random.randint(1, 5)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.face_num, self.max_score = None, None

class Color_recognization(object):
    def __init__(self, uart=None):
        self.uart = uart
        self.id = None
        self.count = 0
        self.lock = False
        print("颜色识别初始化完成")

    def add_color(self, num):
        print(f"添加颜色类别: {num}")
        
    def recognize(self):
        time.sleep_ms(10)
        if random.random() > 0.3:
            self.id = random.randint(0, 7)
        else:
            self.id = None

class QRCode_recognization(object):
    def __init__(self, uart=None):
        self.uart = uart
        self.id = None
        self.info = None
        self.lock = False
        print("二维码识别初始化完成")

    def add_qrcode(self, num):
        print(f"添加二维码: {num}")

    def recognize(self):
        time.sleep_ms(10)
        if random.random() > 0.5:
            self.id = 0
            self.info = "https://www.mpython.cn"
        else:
            self.id = None
            self.info = None

class Guidepost(object):
    def __init__(self, uart):
        self.uart = uart
        self.id = None
        self.max_score = None
        self.labels = ["right","left",'stop']
        self.lock = False
        print("交通标志识别初始化完成")

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.4:
            max_index = random.randint(0, len(self.labels)-1)
            self.id = self.labels[max_index]
            self.max_score = round(random.uniform(0.6, 1.0), 2)
        else:
            self.id, self.max_score = None, None

class V831_MODEL(object):
    def __init__(self, uart, komodel_path=''):
        self.uart = uart
        self.CommandList = AI['kpu_model']
        self.id = None
        self.max_score = None
        self.lock = False
        print(f"自定义模型加载: {komodel_path}")

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.3:
            self.id = random.randint(0, 9)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id, self.max_score = None, None

class Track(object):
    def __init__(self, uart, threshold=[[0, 80, 15, 127, 15, 127]], area_threshold=50):
        self.uart = uart
        self.threshold = threshold 
        self.area_threshold = area_threshold
        self.x = None
        self.y = None
        self.cx = None
        self.cy = None
        self.w = None
        self.h = None
        self.pixels = None
        self.count = None
        self.code = None
        self.lock = False
        print("色块追踪初始化完成")

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.3:
            self.x = random.randint(0, 320)
            self.y = random.randint(0, 240)
            self.cx = random.randint(0, 320)
            self.cy = random.randint(0, 240)
            self.w = random.randint(10, 100)
            self.h = random.randint(10, 100)
            self.pixels = random.randint(100, 10000)
            self.count = random.randint(1, 10)
            self.code = random.randint(0, 15)
        else:
            self.x,self.y,self.cx,self.cy,self.w,self.h,self.pixels,self.count,self.code = None,None,None,None,None,None,None,None,None

    def set_up(self,threshold,area_threshold):
        self.threshold = threshold
        self.area_threshold = area_threshold
        print(f"设置追踪参数: threshold={threshold}, area_threshold={area_threshold}")

class Color_Extracto(object):
    def __init__(self, uart):
        self.uart = uart
        self.LAB_Data = [None,None,None]
        self.L = None
        self.A = None
        self.B = None
        self.lock = False
        print("LAB颜色提取器初始化完成")

    def recognize(self):
        gc.collect()   
        time.sleep_ms(5)
        if random.random() > 0.3:
            self.L = random.randint(0, 100)
            self.A = random.randint(-128, 127)
            self.B = random.randint(-128, 127)
        else:
            self.L,self.A,self.B = None,None,None
        self.LAB_Data = [self.L,self.A,self.B]

class Apriltag(object):
    def __init__(self, uart):
        self.uart = uart
        self.tag_families = 0
        self.tag_family = None
        self.tag_id = None
        self.x_tran = None
        self.y_tran = None
        self.z_tran = None
        self.x_rol = None
        self.y_rol = None
        self.z_rol = None
        self.length = None
        self.lock = False
        self.none_result = None,None,None,None,None,None,None,None,None
        print("AprilTag识别初始化完成")
    
    def update(self,data):
        self.tag_family,self.tag_id,self.x_tran,self.y_tran,self.z_tran,self.x_rol,self.y_rol,self.z_rol,self.length = data

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.4:
            data = (1, random.randint(0, 31), random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0, 2), random.uniform(-180, 180), random.uniform(-180, 180), random.uniform(-180, 180), 0.1)
            self.update(data)
        else:
            self.update(self.none_result)

    def set_tag_families(self, tag_families):
        self.tag_families = tag_families

class YOLO_MODEL(object):
    def __init__(self, uart, labels=["id1","id2",'id3'], model_param='', model_bin='', width=224, height=224, anchors=[]):
        self.uart = uart
        self.CommandList = AI['model_yolo']
        self.id = None
        self.max_score = 0
        self.lock = False
        print(f"YOLO自定义模型: labels={labels}")

    def recognize(self):
        time.sleep_ms(1)
        if random.random() > 0.3:
            self.id = random.randint(0, 2)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id,self.max_score = None,None

class Restnet18_MODEL(object):
    def __init__(self, uart, labels=["id1","id2",'id3'], width=224, height=224, model_param='', model_bin=''):
        self.uart = uart
        self.CommandList = AI['model_restnet18']
        self.id = None
        self.max_score = 0
        self.lock = False
        print(f"ResNet18模型: labels={labels}")

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.3:
            self.id = random.randint(0, 2)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id,self.max_score = None,None

class VisualTracking(object):
    def __init__(self, uart):
        self.uart = uart
        self.lock = False
        self.line_data = {'pixels': None, 'cx': None, 'cy': None, 'angle': None}
        print("视觉寻线初始化完成")

    def recognize(self):
        time.sleep_ms(2)
        gc.collect()
        if random.random() > 0.3:
            self.line_data = {'pixels': random.randint(100, 1000), 'cx': random.randint(0, 320), 'cy': random.randint(0, 240), 'angle': random.uniform(-45, 45)}
        else:
            self.line_data = {'pixels': None, 'cx': None, 'cy': None, 'angle': None}

class Restnet18_MODEL_1000(object):
    def __init__(self, uart):
        self.uart = uart
        self.CommandList = AI['1000class']
        self.id = None
        self.max_score = 0
        self.lock = False
        try:
            from v831.label_1000classes import labels
            self.category_list = labels
        except:
            self.category_list = ["物体"] * 1000
        print("ResNet18 1000类识别初始化完成")

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.3:
            self.id = random.randint(0, 999)
            self.max_score = round(random.uniform(0.3, 1.0), 2)
        else:
            self.id,self.max_score = None,None

class LPR(object):
    def __init__(self, uart):
        self.uart = uart
        self.CommandList = AI['lpr']
        self.lpr_str = None
        self.lock = False
        print("车牌识别初始化完成")

    def recognize(self):
        time.sleep_ms(5)
        if random.random() > 0.5:
            provinces = ['京','沪','粤','浙','苏','鲁','川','冀','豫','云']
            letters = ['A','B','C','D','E','F','G','H','J','K','L','M','N','P','Q','R','S','T','U','V','W','X','Y','Z']
            nums = ['0','1','2','3','4','5','6','7','8','9']
            self.lpr_str = random.choice(provinces) + random.choice(letters) + ''.join(random.choices(letters+nums, k=5))
        else:
            self.lpr_str = None

class IMAGE_CAPTURE(object):
    def __init__(self,uart,path,width,high):
        self.uart = uart
        self.CommandList = AI['image_capture']
        self.lock = False
        print(f"图像采集初始化: path={path}, width={width}, height={high}")
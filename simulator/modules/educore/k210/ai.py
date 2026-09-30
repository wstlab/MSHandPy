import random

class AI:
    def __init__(self):
        self.id = None
        self.max_score = None
        print("K210 AI模块初始化完成")

    def recognize(self):
        if random.random() > 0.3:
            self.id = random.randint(0, 9)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id = None
            self.max_score = None
        return self.id, self.max_score

class FaceDetect:
    def __init__(self):
        self.face_num = None
        self.max_score = None
        print("K210人脸检测初始化完成")

    def recognize(self):
        if random.random() > 0.4:
            self.face_num = random.randint(1, 5)
            self.max_score = round(random.uniform(0.6, 1.0), 2)
        else:
            self.face_num = None
            self.max_score = None
        return self.face_num, self.max_score

class FaceRecognize:
    def __init__(self, face_num=1):
        self.face_num = face_num
        self.id = None
        self.max_score = None
        print(f"K210人脸识别初始化: face_num={face_num}")

    def add_face(self):
        print("添加人脸")

    def recognize(self):
        if random.random() > 0.4:
            self.id = random.randint(0, self.face_num-1)
            self.max_score = round(random.uniform(0.7, 1.0), 2)
        else:
            self.id = None
            self.max_score = None
        return self.id, self.max_score

class MNIST:
    def __init__(self):
        self.id = None
        self.max_score = None
        print("K210 MNIST数字识别初始化完成")

    def recognize(self):
        if random.random() > 0.2:
            self.id = random.randint(0, 9)
            self.max_score = round(random.uniform(0.7, 1.0), 2)
        else:
            self.id = None
            self.max_score = None
        return self.id, self.max_score

class YOLO:
    def __init__(self):
        self.category_list = ['飞机','自行车','鸟','船','瓶子','公交车','汽车','猫','椅子','奶牛','餐桌','狗','屋子','摩托','人','盆栽','羊','沙发','火车','电视']
        self.id = None
        self.max_score = None
        print("K210 YOLO物体识别初始化完成")

    def recognize(self):
        if random.random() > 0.3:
            self.id = random.randint(0, len(self.category_list)-1)
            self.max_score = round(random.uniform(0.5, 1.0), 2)
        else:
            self.id = None
            self.max_score = None
        return self.id, self.max_score
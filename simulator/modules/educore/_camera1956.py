import time

class Camera1956:
    def __init__(self, tx=15, rx=16):
        self.tx = tx
        self.rx = rx
        self.mode = 0
        self.lock = False
        print(f"Camera1956初始化: tx={tx}, rx={rx}")
        time.sleep(0.5)
        print("Camera1956通信成功")

    def face_detect_init(self):
        self.mode = 1
        print("人脸检测模式")

    def mnist_init(self):
        self.mode = 2
        print("数字识别模式")

    def yolo_detect_init(self):
        self.mode = 3
        print("物体识别模式")

    def face_recognize_init(self, face_num=1, accuracy=80):
        self.mode = 4
        print(f"人脸识别模式: face_num={face_num}, accuracy={accuracy}")

    def self_learning_classifier_init(self, class_num=1, sample_num=5):
        self.mode = 5
        print(f"自学习分类模式: class_num={class_num}, sample_num={sample_num}")

    def qrcode_init(self):
        self.mode = 6
        print("二维码识别模式")

    def color_init(self):
        self.mode = 7
        print("颜色识别模式")

    def track_init(self):
        self.mode = 8
        print("色块追踪模式")

    def find_line_init(self):
        self.mode = 9
        print("视觉寻线模式")

    def switcher_mode(self, mode=-1):
        if self.mode == mode:
            print('模式相同，未切换')
            return
        self.mode = mode
        time.sleep(0.5)
        print(f"切换到模式: {mode}")
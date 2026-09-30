from v831.public import *
from v831.ai import *

def face_detect_demo(uart):
    print("人脸检测演示")
    fd = FACE_DETECT(uart)
    while True:
        fd.recognize()
        if fd.face_num:
            print(f"检测到人脸: {fd.face_num}个, 置信度: {fd.max_score}")
        else:
            print("未检测到人脸")
        time.sleep(1)

def yolo_demo(uart):
    print("YOLO物体识别演示")
    yolo = YOLO(uart)
    while True:
        yolo.recognize()
        if yolo.id is not None:
            print(f"识别到: {yolo.category_list[yolo.id]}, 置信度: {yolo.max_score}")
        else:
            print("未识别到物体")
        time.sleep(1)

def mnist_demo(uart):
    print("MNIST数字识别演示")
    mnist = MNIST(uart)
    while True:
        mnist.recognize()
        if mnist.id is not None:
            print(f"识别数字: {mnist.id}, 置信度: {mnist.max_score}")
        else:
            print("未识别到数字")
        time.sleep(1)

def color_demo(uart):
    print("颜色识别演示")
    color = Color_recognization(uart)
    colors = ["红色", "绿色", "蓝色", "黄色", "橙色", "紫色", "青色", "白色"]
    while True:
        color.recognize()
        if color.id is not None:
            print(f"识别颜色: {colors[color.id]}")
        else:
            print("未识别到颜色")
        time.sleep(1)

def qrcode_demo(uart):
    print("二维码识别演示")
    qr = QRCode_recognization(uart)
    while True:
        qr.recognize()
        if qr.info:
            print(f"识别二维码: {qr.info}")
        else:
            print("未识别到二维码")
        time.sleep(1)

def guidepost_demo(uart):
    print("交通标志识别演示")
    gp = Guidepost(uart)
    while True:
        gp.recognize()
        if gp.id:
            print(f"识别标志: {gp.id}, 置信度: {gp.max_score}")
        else:
            print("未识别到标志")
        time.sleep(1)

def track_demo(uart):
    print("色块追踪演示")
    track = Track(uart)
    while True:
        track.recognize()
        if track.x is not None:
            print(f"色块位置: ({track.x},{track.y}), 中心: ({track.cx},{track.cy}), 大小: {track.w}x{track.h}")
        else:
            print("未找到色块")
        time.sleep(0.5)

def visual_tracking_demo(uart):
    print("视觉寻线演示")
    vt = VisualTracking(uart)
    while True:
        vt.recognize()
        if vt.line_data['pixels']:
            print(f"线条像素: {vt.line_data['pixels']}, 中心: ({vt.line_data['cx']},{vt.line_data['cy']}), 角度: {vt.line_data['angle']}")
        else:
            print("未找到线条")
        time.sleep(0.5)

def face_recognition_demo(uart):
    print("人脸识别演示")
    fr = Face_recogization(uart, face_num=3)
    print("请按提示添加人脸...")
    for i in range(3):
        print(f"添加人脸 {i+1}")
        fr.add_face()
        time.sleep(2)
    print("人脸识别开始...")
    while True:
        fr.recognize()
        if fr.id is not None:
            print(f"识别到人脸 {fr.id}, 置信度: {fr.max_score}")
        else:
            print("未识别到人脸")
        time.sleep(1)

def self_learning_demo(uart):
    print("自学习分类演示")
    slc = Self_learning_classfier(uart, class_num=2, sample_num=5)
    print("请按提示添加样本...")
    for i in range(2):
        print(f"添加类别 {i+1} 的样本")
        for j in range(5):
            slc.add_class_img()
            time.sleep(0.5)
    slc.train()
    print("分类开始...")
    while True:
        slc.predict()
        if slc.id is not None:
            print(f"分类结果: 类别 {slc.id}, 置信度: {slc.max_score}")
        else:
            print("未分类")
        time.sleep(1)

def lpr_demo(uart):
    print("车牌识别演示")
    lpr = LPR(uart)
    while True:
        lpr.recognize()
        if lpr.lpr_str:
            print(f"识别车牌: {lpr.lpr_str}")
        else:
            print("未识别到车牌")
        time.sleep(1)

def apriltag_demo(uart):
    print("AprilTag识别演示")
    at = Apriltag(uart)
    while True:
        at.recognize()
        if at.tag_id is not None:
            print(f"Tag家族: {at.tag_family}, Tag ID: {at.tag_id}")
        else:
            print("未识别到AprilTag")
        time.sleep(1)

def color_extracto_demo(uart):
    print("LAB颜色提取演示")
    ce = Color_Extracto(uart)
    while True:
        ce.recognize()
        if ce.L is not None:
            print(f"LAB值: L={ce.L}, A={ce.A}, B={ce.B}")
        else:
            print("未提取到颜色")
        time.sleep(1)

def resnet1000_demo(uart):
    print("ResNet18 1000类识别演示")
    rn = Restnet18_MODEL_1000(uart)
    while True:
        rn.recognize()
        if rn.id is not None:
            print(f"识别到: {rn.category_list[rn.id]}, 置信度: {rn.max_score}")
        else:
            print("未识别到物体")
        time.sleep(1)
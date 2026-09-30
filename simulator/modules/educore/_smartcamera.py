from camera import CameraV831

class EduSmartCamera(CameraV831):
    def __init__(self, tx=16, rx=15):
        super().__init__(rx=rx, tx=tx)
        print("EduSmartCamera初始化完成")
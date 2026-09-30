import random

class ASR:
    def __init__(self):
        self.result = None
        print("K210 ASR语音识别初始化完成")

    def recognize(self):
        commands = ["前进", "后退", "左转", "右转", "停止", "开灯", "关灯", "唱歌", "跳舞", "拍照"]
        if random.random() > 0.4:
            self.result = random.choice(commands)
        else:
            self.result = None
        return self.result

    def listen(self):
        print("正在听...")
        return self.recognize()
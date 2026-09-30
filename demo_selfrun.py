# -*- coding: utf-8 -*-
"""
Sim-Handpy · 自包含一键演示（无需 Thonny、无需外部服务）
运行本脚本即可：
  1) 进程内启动 VM Server(7778) + Virtual USB(7777)
  2) 弹出悬浮掌控板窗口（右侧置顶）
  3) 自动运行演示（OLED → RGB → 传感器 → 蜂鸣器 → 按键交互监听）
用法: python demo_selfrun.py
"""
import os
import sys
import time
import threading
import tkinter as tk

# ---- 路径准备：把本项目各模块目录加入搜索路径，保证从任意位置运行都能 import ----
ROOT = os.path.dirname(os.path.abspath(__file__))                # 本文件所在目录 = 项目根目录
sys.path.insert(0, ROOT)                                         # 根目录（vm_server 等核心模块）
sys.path.insert(0, os.path.join(ROOT, 'simulator'))              # 硬件模拟器（GUI、多语言）
sys.path.insert(0, os.path.join(ROOT, 'simulator', 'modules'))   # 底层模块（虚拟 USB 等）
sys.path.insert(0, os.path.join(ROOT, 'clients'))                # 客户端库（mpython_client）
os.chdir(ROOT)  # 切换工作目录，保证程序内相对路径资源（字体/图片/语言包）能被找到


def start_services():
    """在当前进程内启动两个后台服务（无需单独开命令行窗口）"""
    from vm_server import VMServer                               # VM Server：接收客户端指令、驱动虚拟硬件
    from simulator.modules.virtual_usb import start_virtual_usb  # Virtual USB：模拟掌控板 USB 串口桥（供 Mind+ 识别）

    server = VMServer(port=7778)
    threading.Thread(target=server.start, daemon=True).start()  # daemon=True：主程序退出时服务自动结束
    try:
        start_virtual_usb(port=7777)
    except Exception as e:
        print('Virtual USB 启动失败: %s' % e)  # 不阻塞主流程：USB 桥仅 Mind+ 联动需要，普通演示没有也能跑
    return server


def run_demo():
    """演示序列：OLED → RGB → 传感器 → 蜂鸣器 → 按键交互监听"""
    from mpython_client import connect
    import time as _t

    client = connect(port=7778)
    if not client:
        print('连接失败')
        return

    print('已连接虚拟掌控板')
    # connect() 自动连上本进程 127.0.0.1:7778 的 VM Server；
    # 之后 client.oled / client.rgb / client.light 等 API 与真机 mPython 库同名同用法

    # 1. OLED：fill(0) 清屏 → DispChar(文本, x, y, 字号) 写字 → show() 统一刷新到屏幕
    client.oled.fill(0)
    client.oled.DispChar("Hello Thonny!", 0, 0, 1)
    client.oled.DispChar("Sim-Handpy", 0, 16, 1)
    client.oled.show()
    _t.sleep(2.5)

    # 2. RGB：板上有 3 颗灯，rgb[0..2] 分别设置颜色 (R, G, B)（0~255），write() 一次性点亮
    client.rgb[0] = (255, 0, 0)
    client.rgb[1] = (0, 255, 0)
    client.rgb[2] = (0, 0, 255)
    client.rgb.write()
    _t.sleep(2.5)

    # 3. 传感器：读取虚拟环境中的光线/声音/加速度模拟值（接口名与真机一致）
    light = client.light.read()
    sound = client.sound.read()
    accel = client.accelerometer.get()
    print('光线:', light, ' 声音:', sound, ' 加速度:', accel)
    _t.sleep(2.5)

    # 5. 蜂鸣器：buzzer.on(频率Hz) 开始发声、buzzer.off() 停止；
    #    play([(频率, 毫秒), ...]) 按节拍播放旋律——悬浮窗 Buzzer 栏会同步显示音调
    client.buzzer.on(880)   # 先来一声 A5 高音提示
    _t.sleep(0.6)
    client.buzzer.off()
    _t.sleep(0.3)

    melody = [              # 《小星星》片段：do do sol sol la la sol——
        (523, 250), (523, 250),   # C5 C5
        (784, 250), (784, 250),   # G5 G5
        (880, 250), (880, 250),   # A5 A5
        (784, 500),               # G5（长音）
    ]
    print('♪ 播放旋律（小星星片段），注意听悬浮板发声...')
    client.buzzer.play(melody)
    _t.sleep(1.0)

    # 6. 按键交互：后台线程轮询 A/B 键（is_pressed 为非阻塞查询），
    #    在悬浮窗口上点击按键即可触发；线程为 daemon，随主程序一起退出
    def watch():
        try:
            while True:
                if client.button_a.is_pressed():
                    print('按键A被按下！')
                if client.button_b.is_pressed():
                    print('按键B被按下！')
                time.sleep(0.1)  # 100ms 轮询一次，兼顾响应速度与 CPU 占用
        except Exception:
            pass

    threading.Thread(target=watch, daemon=True).start()
    print('演示完成，点击悬浮窗按键 A/B 试试（关闭窗口退出）')
    # 演示序列结束后保持主线程存活，让用户自由体验按键交互
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('已退出')


def main():
    """启动顺序：先起后台服务 → 再弹悬浮窗 → 最后跑演示线程"""
    server = start_services()
    time.sleep(1.2)  # 等服务端口就绪，避免窗口/客户端过早连接失败

    from display_gui import DisplayGUI
    root = tk.Tk()
    DisplayGUI(root, vm_port=7778)  # 悬浮掌控板窗口，连接本进程内的 7778 服务

    # 把窗口贴到屏幕右侧（宽 400 × 高 820），不遮挡左边的编辑器
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()       # 关闭 DPI 缩放，取真实像素尺寸
        sw = ctypes.windll.user32.GetSystemMetrics(0)   # 0 = 屏幕宽度
        bx = max(0, sw - 445)                           # 左边缘 = 屏宽 - 窗宽 400 - 边距 45
        root.geometry('400x820+%d+22' % bx)
    except Exception:
        pass  # 非 Windows 系统没有 user32，忽略（窗口停在默认位置）
    root.update()  # 先渲染一帧，确保演示开始时窗口已可见

    threading.Thread(target=run_demo, daemon=True).start()  # 演示序列放后台线程，不卡 UI
    root.mainloop()  # Tk 主事件循环；关闭窗口后才会继续往下执行

    server.stop()  # 窗口已关闭：停掉 VM Server，释放 7778 端口
    print('演示结束')


if __name__ == '__main__':
    main()

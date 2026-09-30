# -*- coding: utf-8 -*-
"""
Sim-Handpy · Thonny 联动演示
在 Thonny 中打开本文件，按 F5 运行。
观察右侧悬浮掌控板窗口的实时反馈。
"""
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'clients'))

from mpython_client import connect

print("=" * 50)
print("   Sim-Handpy 虚拟掌控板 · Thonny 演示")
print("=" * 50)

client = connect(port=7778)
if not client:
    print("连接失败，请先启动 VM Server(7778)")
    sys.exit(1)
print("已连接虚拟掌控板")

print("1. OLED 显示文字")
client.oled.fill(0)
client.oled.DispChar("Hello Thonny!", 0, 0, 1)
client.oled.DispChar("Sim-Handpy", 0, 16, 1)
client.oled.show()
time.sleep(2.5)

print("2. RGB 三色灯点亮")
client.rgb[0] = (255, 0, 0)
client.rgb[1] = (0, 255, 0)
client.rgb[2] = (0, 0, 255)
client.rgb.write()
time.sleep(2.5)

print("3. 读取传感器")
print("   光线:", client.light.read())
print("   声音:", client.sound.read())
accel = client.accelerometer.get()
if isinstance(accel, dict):
    print("   加速度: x=%.2f y=%.2f z=%.2f" % (accel.get('x', 0), accel.get('y', 0), accel.get('z', 0)))
else:
    print("   加速度:", accel)
time.sleep(2.5)


def watch_buttons():
    try:
        while True:
            if client.button_a.is_pressed():
                print("按键A被按下！")
            if client.button_b.is_pressed():
                print("按键B被按下！")
            time.sleep(0.1)
    except Exception:
        pass


threading.Thread(target=watch_buttons, daemon=True).start()
print("4. 按键交互中... 点击悬浮窗的 Button A/B 试试")

time.sleep(3)
print("演示完成，保持监听按键交互（Ctrl+C 退出）")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("已退出")

# -*- coding: utf-8 -*-
"""
PinPong 模式演示（需先运行「一键启动.bat」启动虚拟掌控板）
本脚本只连接已运行的虚拟板，不会另开窗口。
演示内容：OLED → RGB → 按键（PinPong 语义：按下=0，松开=1）→ 传感器 → 按键交互
"""
import sys
import os
import socket

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'clients'))


def board_running(port=7778):
    """检查虚拟掌控板服务（VM Server）是否已在运行"""
    try:
        s = socket.create_connection(('127.0.0.1', port), timeout=0.5)
        s.close()
        return True
    except OSError:
        return False


print("=" * 50)
print("   PinPong 库 - 演示程序")
print("=" * 50)

if not board_running():
    print("\n❌ 未检测到虚拟掌控板服务（端口 7778）")
    print("   请先双击「一键启动.bat」启动虚拟掌控板窗口，再运行本演示")
    input("按回车键退出...")
    sys.exit(1)

print("\n🔹 初始化 PinPong")
from pinpong_client import *
init()
print("   ✅ PinPong 已初始化（已连接正在运行的虚拟掌控板）")

print("\n🔹 OLED显示")
oled = get_oled()
oled.clear()
oled.write("PinPong Mode\nOLED Test")
oled.show()
print("   ✅ OLED已更新")

print("\n🔹 RGB灯控制")
rgb = get_rgb()
rgb.write_color('red')
delay(500)
rgb.write_color('green')
delay(500)
rgb.write_color('blue')
delay(500)
rgb.write(255, 255, 0)
print("   ✅ RGB已更新")

print("\n🔹 读取按键（PinPong 上拉语义：0=按下，1=松开）")
btn_a = get_pin(0)   # P0 = 按键A
btn_b = get_pin(1)   # P1 = 按键B
print("   按键A状态:", btn_a.read_digital())
print("   按键B状态:", btn_b.read_digital())

print("\n🔹 读取传感器")
light = Sensor(3)
sound = Sensor(4)
print("   光线:", light.read())
print("   声音:", sound.read())

print("\n🔹 交互测试")
print("   点击虚拟板窗口的按键A/B，每次按下/松开各提示一次")
print("   按 Ctrl+C 退出")

last_a = last_b = False
try:
    while True:
        # is_pressed() 等价于 read_digital() == 0（上拉结构：按下为低电平）
        a = btn_a.is_pressed()
        b = btn_b.is_pressed()
        if a != last_a:      # 边沿检测：只在状态变化时提示，避免刷屏
            print("   ⚡ 按键A%s" % ("被按下！" if a else "已松开"))
            rgb.write_color('red' if a else 'blue')
            last_a = a
        if b != last_b:
            print("   ⚡ 按键B%s" % ("被按下！" if b else "已松开"))
            rgb.write_color('green' if b else 'blue')
            last_b = b
        delay(50)
except KeyboardInterrupt:
    rgb.off()
    oled.clear()
    oled.write("Goodbye!")
    oled.show()
    print("\n🛑 程序已退出")

print("=" * 50)

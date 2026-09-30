# -*- coding: utf-8 -*-
"""
mPython 模式演示（需先运行「一键启动.bat」启动虚拟掌控板）
本脚本只连接已运行的虚拟板，不会另开窗口。
演示内容：OLED → RGB → 传感器 → 按键交互（每次按下只提示一次）
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
print("   Sim-Handpy 虚拟掌控板 - 演示程序")
print("=" * 50)

if not board_running():
    print("\n❌ 未检测到虚拟掌控板服务（端口 7778）")
    print("   请先双击「一键启动.bat」启动虚拟掌控板窗口，再运行本演示")
    input("按回车键退出...")
    sys.exit(1)

from mpython_client import connect

client = connect()

if client:
    print("\n🔹 控制OLED显示")
    client.oled.fill(0)
    client.oled.DispChar("Hello Thonny!", 0, 0, 1)
    client.oled.DispChar("Sim-Handpy", 0, 16, 1)
    client.oled.show()
    print("   ✅ OLED已更新")

    print("\n🔹 控制RGB灯")
    client.rgb[0] = (255, 0, 0)   
    client.rgb[1] = (0, 255, 0)   
    client.rgb[2] = (0, 0, 255)   
    client.rgb.write()
    print("   ✅ RGB已更新（红、绿、蓝）")

    print("\n🔹 读取传感器")
    light_val = client.light.read()
    sound_val = client.sound.read()
    accel = client.accelerometer.get()
    print(f"   光线: {light_val}")
    print(f"   声音: {sound_val}")
    if isinstance(accel, list) and len(accel) == 3:
        print(f"   加速度: x={accel[0]:.2f}, y={accel[1]:.2f}, z={accel[2]:.2f}")
    elif isinstance(accel, dict):
        print(f"   加速度: x={accel.get('x', 0):.2f}, y={accel.get('y', 0):.2f}, z={accel.get('z', 0):.2f}")
    else:
        print(f"   加速度: {accel}")

    print("\n🔹 交互测试")
    print("   点击虚拟板窗口的按键A/B，每次按下只提示一次")
    print("   按 Ctrl+C 退出")

    try:
        import time
        while True:
            # was_pressed() 自带边沿检测：只在「松开→按下」瞬间返回 True，不刷屏
            if client.button_a.was_pressed():
                print("   ⚡ 按键A被按下！")
            if client.button_b.was_pressed():
                print("   ⚡ 按键B被按下！")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\n🛑 程序已退出")
else:
    print("\n❌ 连接失败")
    print("   请确保 vm_server.py 已启动")

print("=" * 50)
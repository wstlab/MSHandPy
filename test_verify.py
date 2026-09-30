"""Sim-Handpy 虚拟掌控板 - Thonny 联动验证脚本
运行前提：悬浮虚拟板窗口已打开（vm_server 已在 7778 端口运行）
验证内容：OLED 显示 / RGB 彩灯 / 传感器读取 / 按键交互
操作方式：在 Thonny 中打开本文件，点击【运行】；按 Ctrl+C 结束
"""
import sys
import os
import time

# 把项目根目录和 clients 目录加入搜索路径（无论从哪里打开都能运行）
try:
    _ROOT = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Thonny 的 %Run -c 模式没有 __file__，回退到当前工作目录
    _ROOT = os.getcwd()
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, 'clients'))

from mpython_client import connect

print("=" * 50)
print("  Sim-Handpy 虚拟掌控板 - 验证测试")
print("=" * 50)

mp = connect()

if not mp:
    print("❌ 连接失败：请先运行 start_vm.py 打开虚拟板窗口")
    sys.exit(1)

print("✅ 已连接到虚拟掌控板\n")

# ---------- 1. OLED 显示测试 ----------
print("🔹 [1/4] OLED 显示测试")
mp.oled.fill(0)
mp.oled.DispChar("Hello Thonny!", 0, 0, 1)
mp.oled.DispChar("Board Test", 0, 16, 1)
mp.oled.show()
print("   -> 看悬浮窗口 OLED 是否显示两行文字\n")

# ---------- 2. RGB 彩灯测试 ----------
print("🔹 [2/4] RGB 彩灯依次变色（红→绿→蓝→黄）")
COLORS = [((255, 0, 0), "红"), ((0, 255, 0), "绿"),
          ((0, 0, 255), "蓝"), ((255, 255, 0), "黄")]
for color, name in COLORS:
    mp.rgb.fill(color)
    time.sleep(0.8)
mp.rgb.clear()
print("   -> 看悬浮窗口三颗灯是否依次变色\n")

# ---------- 3. 传感器读取测试 ----------
print("🔹 [3/4] 传感器读取")
light = mp.light.read()
sound = mp.sound.read()
accel = mp.accelerometer.get()
print(f"   光线: {light}")
print(f"   声音: {sound}")
print(f"   加速度: x={accel['x']:.2f}  y={accel['y']:.2f}  z={accel['z']:.2f}")
print("   -> 可在虚拟板窗口拖动滑杆改变数值，再运行一次对比\n")

# ---------- 4. 交互循环测试 ----------
print("🔹 [4/4] 交互测试（按 Ctrl+C 结束）")
print("   点击虚拟板上的按键 A / B，或触摸 P Y T H O N 触摸键")
print("-" * 50)

oled_lines = 0
try:
    while True:
        if mp.button_a.was_pressed():
            print("   ⚡ 按键 A 被按下！")
            mp.rgb[0] = (255, 0, 0)   # A 键 -> 第一颗灯变红
            mp.rgb.write()
        if mp.button_b.was_pressed():
            print("   ⚡ 按键 B 被按下！")
            mp.rgb[0] = (0, 0, 255)   # B 键 -> 第一颗灯变蓝
            mp.rgb.write()

        # 触摸键检测（P/Y/T/H/O/N）
        for ch in "PYTHON":
            if mp.touch[ch].is_touched():
                print(f"   ⚡ 触摸键 {ch} 被触摸！")

        # OLED 实时刷新传感器数值
        light = mp.light.read()
        sound = mp.sound.read()
        mp.oled.fill(0)
        mp.oled.DispChar(f"Light:{light}", 0, 0, 1)
        mp.oled.DispChar(f"Sound:{sound}", 0, 16, 1)
        mp.oled.show()

        time.sleep(0.1)
except KeyboardInterrupt:
    mp.rgb.clear()
    mp.oled.fill(0)
    mp.oled.DispChar("Test PASS!", 0, 0, 1)
    mp.oled.show()
    print("\n🛑 测试结束：OLED 已显示 Test PASS!，RGB 已熄灭")
    mp.disconnect()

print("=" * 50)

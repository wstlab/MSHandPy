# -*- coding: utf-8 -*-
"""验证 Thonny 联动版链路：mpython_client 连接 → OLED/RGB/传感器/按键"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'clients'))

from mpython_client import connect

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print("[%s] %s %s" % ("OK " if ok else "FAIL", name, detail), flush=True)

client = connect()
check("connect", client is not None)

if client:
    # OLED
    try:
        client.oled.fill(0)
        client.oled.DispChar("Hello Thonny!", 0, 0, 1)
        client.oled.DispChar("Sim-Handpy", 0, 16, 1)
        client.oled.show()
        check("oled", True, "Hello Thonny!")
    except Exception as e:
        check("oled", False, repr(e))
    # RGB
    try:
        client.rgb[0] = (255, 0, 0)
        client.rgb[1] = (0, 255, 0)
        client.rgb[2] = (0, 0, 255)
        client.rgb.write()
        check("rgb", True, "R/G/B")
    except Exception as e:
        check("rgb", False, repr(e))
    # 传感器
    try:
        time.sleep(0.5)
        light = client.light.read()
        sound = client.sound.read()
        accel = client.accelerometer.get()
        check("sensors", light is not None and sound is not None, "light=%s sound=%s accel=%s" % (light, sound, accel))
    except Exception as e:
        check("sensors", False, repr(e))
    # 按键（程序内读取，不点击）
    try:
        a = client.button_a.is_pressed()
        b = client.button_b.is_pressed()
        check("buttons", a in (True, False) and b in (True, False), "A=%s B=%s" % (a, b))
    except Exception as e:
        check("buttons", False, repr(e))

    # 等待用户可观察显示窗 2 秒
    time.sleep(2)
    try:
        client.disconnect()
    except Exception:
        pass

failed = [r for r in results if not r[1]]
print("=" * 50)
print("总项数=%d 失败=%d" % (len(results), len(failed)))
sys.exit(1 if failed else 0)

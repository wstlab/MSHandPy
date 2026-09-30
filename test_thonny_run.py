# -*- coding: utf-8 -*-
"""
验证真实 Thonny 能否运行 Sim-Handpy 客户端代码：
1) 本进程启动 VM Server(7778) + Virtual USB(7777)
2) 启动 Thonny 打开 thonny_demo.py
3) 模拟按 F5 运行
4) 轮询 VM Server 状态，确认 OLED 显示 "Hello Thonny!"（证明 Thonny 真实执行成功）
"""
import os
import sys
import time
import subprocess
import threading
import ctypes
from ctypes import wintypes

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'simulator'))
sys.path.insert(0, os.path.join(ROOT, 'simulator', 'modules'))

from vm_server import VMServer

user32 = ctypes.windll.user32
user32.keybd_event.restype = None
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulong]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]

ENUM_CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

found = []

@ENUM_CB
def _enum_cb(hwnd, lparam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if 'Thonny' in buf.value:
            found.append((hwnd, buf.value))
    return True


def find_thonny(timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        found.clear()
        user32.EnumWindows(_enum_cb, 0)
        if found:
            return found[0]
        time.sleep(0.5)
    return None


def send_f5():
    user32.keybd_event(0x74, 0, 0, 0)   # VK_F5 down
    time.sleep(0.05)
    user32.keybd_event(0x74, 0, 2, 0)   # VK_F5 up
    print("F5 已发送", flush=True)


def main():
    server = VMServer(port=7778)
    threading.Thread(target=server.start, daemon=True).start()
    try:
        from simulator.modules.virtual_usb import start_virtual_usb
        start_virtual_usb(port=7777)
    except Exception as e:
        print("virtual_usb 启动失败: %s" % e, flush=True)
    time.sleep(1.5)

    demo = os.path.join(ROOT, 'thonny_demo.py')
    # 自动探测 Thonny 安装路径（兼容不同 Python 版本），找不到时报错
    thonny = None
    _appdata = os.environ.get('APPDATA', '')
    _candidates = [
        os.path.join(_appdata, 'Python', f'Python{sys.version_info.major}{sys.version_info.minor}', 'Scripts', 'thonny.exe'),
        os.path.join(_appdata, 'Python', 'Python312', 'Scripts', 'thonny.exe'),
        os.path.join(_appdata, 'Python', 'Python311', 'Scripts', 'thonny.exe'),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Thonny', 'thonny.exe'),
    ]
    for _p in _candidates:
        if os.path.exists(_p):
            thonny = _p
            break
    if not thonny:
        print("FAIL Thonny not found in standard locations", flush=True)
        sys.exit(1)
    # 重定向 Thonny 用户目录到沙箱允许写入的路径（原路径写日志会被拦截导致启动失败）
    os.environ['THONNY_USER_DIR'] = os.path.join(ROOT, '_thonny_user')
    os.makedirs(os.environ['THONNY_USER_DIR'], exist_ok=True)
    print("THONNY_USER_DIR=%s" % os.environ['THONNY_USER_DIR'], flush=True)
    print("启动 Thonny...", flush=True)
    proc = subprocess.Popen([thonny, demo], env=os.environ)
    print("Thonny PID=%d" % proc.pid, flush=True)

    win = find_thonny()
    if not win:
        print("FAIL 未找到 Thonny 窗口", flush=True)
        proc.kill()
        sys.exit(1)
    hwnd, title = win
    print("找到 Thonny 窗口: %s (hwnd=%d)" % (title, hwnd), flush=True)

    # 置前台并最大化
    user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)
    send_f5()

    # 轮询 VM Server 状态，确认 OLED 更新
    import socket, json
    def get_state():
        try:
            s = socket.create_connection(('127.0.0.1', 7778), timeout=2)
            s.sendall(b'{"action":"get_state"}\n')
            resp = b""
            while b"\n" not in resp:
                chunk = s.recv(4096)
                if not chunk:
                    break
                resp += chunk
            s.close()
            return json.loads(resp.split(b"\n")[0].decode('utf-8', 'replace'))
        except Exception as e:
            return {'error': str(e)}

    ok_oled = False
    ok_rgb = False
    deadline = time.time() + 20
    while time.time() < deadline:
        st = get_state()
        oled = st.get('oled_text', [])
        if any('Hello Thonny' in t for t in oled):
            ok_oled = True
        rgb = st.get('rgb_colors', [])
        if len(rgb) >= 3 and any(c != (0, 0, 0) for c in rgb):
            ok_rgb = True
        if ok_oled and ok_rgb:
            break
        time.sleep(0.5)
        if time.time() > deadline - 10:
            print("  当前 oled=%s rgb=%s" % (oled, rgb), flush=True)

    print("OLED 已更新: %s | RGB 已更新: %s" % (ok_oled, ok_rgb), flush=True)
    if ok_oled and ok_rgb:
        print("RESULT: Thonny 联动运行验证通过", flush=True)
    else:
        print("RESULT: 验证失败", flush=True)

    # 清理
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    server.stop()
    print("DONE", flush=True)


if __name__ == '__main__':
    main()

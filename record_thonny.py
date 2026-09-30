# -*- coding: utf-8 -*-
"""
Sim-Handpy · Thonny 联动版 演示录制（无声 · 带解释字幕）
单进程内：VM Server(7778) + Virtual USB(7777) + 悬浮掌控板窗口(DisplayGUI)，
自动启动真实 Thonny 打开 thonny_demo.py 并按 F5 运行，
全屏录制 Thonny 运行窗口 + 悬浮掌控板实时反馈，底部叠加解释字幕。

用法: python -B record_thonny.py [输出mp4路径]   （必须用阻塞模式运行）
"""
import os
import sys
import time
import socket
import json
import subprocess
import threading
import ctypes
from ctypes import wintypes

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'simulator'))
sys.path.insert(0, os.path.join(ROOT, 'simulator', 'modules'))
sys.path.insert(0, os.path.join(ROOT, 'clients'))
os.chdir(ROOT)

OUT_MP4 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser('~'), 'Desktop', 'Sim-Handpy-Thonny-Intro.mp4')
# 自动探测 Thonny 安装路径（兼容不同 Python 版本）
THONNY_EXE = None
_appdata = os.environ.get('APPDATA', '')
for _p in [
    os.path.join(_appdata, 'Python', f'Python{sys.version_info.major}{sys.version_info.minor}', 'Scripts', 'thonny.exe'),
    os.path.join(_appdata, 'Python', 'Python312', 'Scripts', 'thonny.exe'),
    os.path.join(_appdata, 'Python', 'Python311', 'Scripts', 'thonny.exe'),
    os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Thonny', 'thonny.exe'),
]:
    if os.path.exists(_p):
        THONNY_EXE = _p
        break

# 字体：优先微软雅黑，缺失时回退到宋体/ Arial（英文 Windows 无雅黑）
_font_path = 'C:/Windows/Fonts/msyh.ttc'
if not os.path.exists(_font_path):
    _font_path = 'C:/Windows/Fonts/simsun.ttc' if os.path.exists('C:/Windows/Fonts/simsun.ttc') else None
FONT_NORMAL = _font_path
_font_bold_path = 'C:/Windows/Fonts/msyhbd.ttc'
if not os.path.exists(_font_bold_path):
    _font_bold_path = 'C:/Windows/Fonts/simhei.ttf' if os.path.exists('C:/Windows/Fonts/simhei.ttf') else _font_path
FONT_BOLD = _font_bold_path

try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD), ('biWidth', ctypes.c_long), ('biHeight', ctypes.c_long),
        ('biPlanes', wintypes.WORD), ('biBitCount', wintypes.WORD), ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD), ('biXPelsPerMeter', ctypes.c_long), ('biYPelsPerMeter', ctypes.c_long),
        ('biClrUsed', wintypes.DWORD), ('biClrImportant', wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]


user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.keybd_event.restype = None
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulong]
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.EnumWindows.restype = wintypes.BOOL
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
ENUM_CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                            ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]


def grab_screen():
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    if w <= 0 or h <= 0:
        return None
    hdc_scr = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_scr)
    hbm = gdi32.CreateCompatibleBitmap(hdc_scr, w, h)
    gdi32.SelectObject(hdc_mem, hbm)
    gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_scr, 0, 0, 0x00CC0020)
    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = w
    bmi.bmiHeader.biHeight = -h
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = 32
    bmi.bmiHeader.biCompression = 0
    buf = np.empty((h, w, 4), dtype=np.uint8)
    gdi32.GetDIBits(hdc_mem, hbm, 0, h, buf.ctypes.data, ctypes.byref(bmi), 0)
    gdi32.SelectObject(hdc_mem, 0)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc_scr)
    return buf[:, :, :3].copy()


# ---------------- 文本渲染 ----------------
def _font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_NORMAL, size)


def make_cover(title, subtitle, footer, w, h):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (16, 18, 28)
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    cx = w // 2
    d.rounded_rectangle([cx - 190, int(h * 0.40), cx + 190, int(h * 0.40) + 6], radius=3, fill=(80, 170, 255, 255))
    d.text((cx, int(h * 0.44)), title, font=_font(54, True), fill=(255, 255, 255, 255), anchor='mm')
    d.text((cx, int(h * 0.53)), subtitle, font=_font(28), fill=(170, 210, 255, 255), anchor='mm')
    d.text((cx, int(h * 0.87)), footer, font=_font(24), fill=(140, 150, 170, 255), anchor='mm')
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def draw_caption_bar(img, caption, sub=None):
    h, w = img.shape[:2]
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert('RGBA')
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    bar_h = 74 if sub is None else 102
    y0 = h - bar_h - 10
    d.rounded_rectangle([14, y0, w - 14, h - 6], radius=14, fill=(10, 12, 20, 185))
    d.text((34, y0 + 10), caption, font=_font(30), fill=(255, 255, 255, 255))
    if sub:
        d.text((34, y0 + 56), sub, font=_font(22), fill=(150, 200, 255, 255))
    out = Image.alpha_composite(pil, overlay)
    return cv2.cvtColor(np.asarray(out), cv2.COLOR_RGBA2BGR)


def dim_frame(img, text, sub=None):
    """启动阶段：整屏压暗 + 居中提示文字，隐藏桌面杂乱"""
    h, w = img.shape[:2]
    dark = np.full_like(img, (14, 16, 24))
    img = cv2.addWeighted(img, 0.35, dark, 0.65, 0)
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    cx = w // 2
    d.rounded_rectangle([cx - 260, int(h * 0.40), cx + 260, int(h * 0.40) + 5], radius=3, fill=(80, 170, 255, 255))
    d.text((cx, int(h * 0.46)), text, font=_font(36, True), fill=(255, 255, 255, 255), anchor='mm')
    if sub:
        d.text((cx, int(h * 0.55)), sub, font=_font(24), fill=(170, 210, 255, 255), anchor='mm')
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


# 全局：F5 触发时间（由等待线程设置）
F5_LOCK = threading.Lock()
F5_TIME = None
THONNY_ALIVE = True


def set_f5_time(t):
    global F5_TIME
    with F5_LOCK:
        F5_TIME = t


def get_f5_time():
    with F5_LOCK:
        return F5_TIME


# ---------------- 录制线程 ----------------
class Recorder(threading.Thread):
    def __init__(self, t0):
        super().__init__(daemon=True)
        self.t0 = t0
        self.error = None
        self.frames = []
        self.finished = False

    def run(self):
        try:
            frame0 = grab_screen()
            if frame0 is None:
                self.error = '无法获取屏幕画面'
                return
            h, w = frame0.shape[:2]
            COVER2 = ('让每个孩子都有一块掌控板', '开源免费 · MIT License', 'GitHub: lmxylyc/Sim-Handpy-VirtualBoard')
            MAX_DURATION = 100
            while True:
                el = time.time() - self.t0
                if el > MAX_DURATION:
                    break
                f5 = get_f5_time()
                end = min(MAX_DURATION, (f5 + 62) if f5 else 60)
                if el > end:
                    break
                screen = grab_screen()
                if screen is None:
                    time.sleep(0.02)
                    continue
                if el < 5.0:
                    img = make_cover('Sim-Handpy', 'Thonny 联动版 · 项目演示', '服务器 / 客户端架构 · 悬浮掌控板窗口', w, h)
                elif end - el <= 6.0:
                    img = make_cover(*COVER2, w, h)
                elif f5 is None:
                    img = dim_frame(screen, '正在启动 Thonny 与虚拟掌控板服务...',
                                    'VM Server 7778 · Virtual USB 7777 · 悬浮显示窗')
                else:
                    rel = el - f5
                    cap = None
                    if rel < 1.0:
                        cap = ('已连接 · 代码开始运行', 'Thonny 按 F5 运行 thonny_demo.py')
                    elif rel < 8.0:
                        cap = ('示例1 · OLED 显示文字', 'Hello Thonny! —— 客户端驱动悬浮窗')
                    elif rel < 15.0:
                        cap = ('示例2 · RGB 三色灯点亮', '红 / 绿 / 蓝 实时反馈')
                    elif rel < 23.0:
                        cap = ('示例3 · 实时读取传感器', '光线 / 声音 / 加速度')
                    elif rel < 33.0:
                        cap = ('示例4 · 按键交互', '悬浮窗 Button A / B 与程序同步')
                    elif rel < 41.0:
                        cap = ('示例5 · 触摸按键与动作感应', 'P / Y / T 触摸 · 加速度晃动')
                    else:
                        cap = ('在 Thonny 中写代码 · 悬浮掌控板实时反馈', '服务器 / 客户端架构')
                    if cap:
                        img = draw_caption_bar(screen, cap[0], cap[1])
                ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 88])
                if ok:
                    self.frames.append((el, buf))
                time.sleep(0.02)
            if self.frames:
                t_first = self.frames[0][0]
                t_last = self.frames[-1][0]
                n = len(self.frames)
                fps = max(1.0, (n - 1) / max(1e-3, t_last - t_first))
                vw = cv2.VideoWriter(OUT_MP4, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                if not vw.isOpened():
                    self.error = 'VideoWriter 打开失败: ' + OUT_MP4
                    return
                for _, buf in self.frames:
                    vw.write(cv2.imdecode(buf, cv2.IMREAD_COLOR))
                vw.release()
        except Exception as e:
            self.error = repr(e)
        finally:
            self.finished = True


# ---------------- 工具 ----------------
def find_thonny(timeout=45):
    found = []

    @ENUM_CB
    def _cb(hwnd, lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if 'Thonny' in buf.value:
                found.append((hwnd, buf.value))
        return True

    deadline = time.time() + timeout
    while time.time() < deadline:
        found.clear()
        user32.EnumWindows(_cb, 0)
        if found:
            return found[0]
        time.sleep(0.5)
    return None


def send_f5(method='keybd'):
    if method == 'post':
        # 直接投递 WM_KEYDOWN/UP 到 Thonny 窗口（不受前台锁影响）
        hwnd = find_thonny(timeout=2)
        if hwnd:
            user32.PostMessageW(hwnd[0], 0x0100, 0x74, 0)
            time.sleep(0.03)
            user32.PostMessageW(hwnd[0], 0x0101, 0x74, 0)
        return
    user32.keybd_event(0x74, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(0x74, 0, 2, 0)


def vm_command(action, **kw):
    try:
        s = socket.create_connection(('127.0.0.1', 7778), timeout=2)
        s.sendall((json.dumps({'action': action, **kw}) + "\n").encode('utf-8'))
        resp = b""
        while b"\n" not in resp:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
        s.close()
        try:
            return json.loads(resp.split(b"\n")[0].decode('utf-8', 'replace'))
        except Exception:
            return {}
    except Exception:
        return {}


def wait_oled_hello(timeout=8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        st = vm_command('get_state')
        if any('Hello Thonny' in t for t in st.get('oled_text', [])):
            return True
        time.sleep(0.4)
    return False


def wait_thonny_and_run():
    win = find_thonny()
    if not win:
        print('未找到 Thonny 窗口', flush=True)
        return
    hwnd, title = win
    print('Thonny 窗口: %s' % title, flush=True)
    user32.SetWindowPos(hwnd, 0, 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1) - 130, 0x0040)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.5)

    # 发送 F5，最多 3 次（先键盘注入，再窗口消息投递），直到确认 Thonny 真正运行了代码
    f5 = None
    for attempt in range(3):
        now = time.time()
        set_f5_time(now)
        send_f5('keybd' if attempt == 0 else 'post')
        print('F5 已发送 (第%d次)' % (attempt + 1), flush=True)
        if wait_oled_hello(8):
            f5 = now
            print('Thonny 运行确认成功', flush=True)
            break
        print('未检测到运行，重试 F5...', flush=True)
    if f5 is None:
        print('Thonny 未能运行代码', flush=True)
        return

    # 演示事件（相对确认后的 F5）
    def schedule(offset, fn):
        def waiter():
            time.sleep(max(0, offset - (time.time() - f5)))
            fn()
        threading.Thread(target=waiter, daemon=True).start()

    def press(btn, on):
        vm_command('button_press' if on else 'button_release', button=btn)

    def touch(pad, on):
        vm_command('touch_press' if on else 'touch_release', pad=pad)

    schedule(24.0, lambda: press('A', True))
    schedule(25.0, lambda: press('A', False))
    schedule(26.5, lambda: press('B', True))
    schedule(27.5, lambda: press('B', False))
    schedule(29.0, lambda: press('A', True))
    schedule(30.0, lambda: press('A', False))
    schedule(32.0, lambda: touch('P', True))
    schedule(33.0, lambda: touch('P', False))
    schedule(34.0, lambda: touch('Y', True))
    schedule(35.0, lambda: touch('Y', False))
    schedule(36.0, lambda: touch('T', True))
    schedule(37.0, lambda: touch('T', False))
    schedule(39.0, lambda: vm_command('sensor_set', sensor='accelerometer',
                                      value={'x': 2.0, 'y': 0.5, 'z': 0.5}))


# ---------------- 主流程 ----------------
def main():
    import tkinter as tk
    from vm_server import VMServer
    from simulator.modules.virtual_usb import start_virtual_usb
    from display_gui import DisplayGUI

    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)

    # 服务线程
    server = VMServer(port=7778)
    threading.Thread(target=server.start, daemon=True).start()
    try:
        start_virtual_usb(port=7777)
    except Exception as e:
        print('virtual_usb 启动失败: %s' % e, flush=True)
    time.sleep(1.2)

    # 悬浮掌控板窗口（置顶，移到屏幕右侧，避免遮挡 Thonny 代码区）
    root = tk.Tk()
    app = DisplayGUI(root, vm_port=7778)
    bx = max(0, sw - 445)
    root.geometry('400x820+%d+22' % bx)
    root.update()

    T0 = time.time()
    rec = Recorder(T0)

    # 启动 Thonny（重定向用户目录到可写路径）
    os.environ['THONNY_USER_DIR'] = os.path.join(ROOT, '_thonny_user')
    os.makedirs(os.environ['THONNY_USER_DIR'], exist_ok=True)
    thonny_proc = subprocess.Popen([THONNY_EXE, os.path.join(ROOT, 'thonny_demo.py')], env=os.environ)
    print('Thonny PID=%d' % thonny_proc.pid, flush=True)

    rec.start()

    # 等待 Thonny 窗口 → 调整位置 → F5（后台线程）
    threading.Thread(target=wait_thonny_and_run, daemon=True).start()

    def check_done():
        if rec.finished:
            root.destroy()
        else:
            root.after(500, check_done)

    root.after(500, check_done)
    root.after(102000, root.destroy)  # 兜底
    root.mainloop()

    try:
        rec.join(timeout=15)
    except Exception:
        pass
    try:
        thonny_proc.terminate()
        thonny_proc.wait(timeout=4)
    except Exception:
        try:
            thonny_proc.kill()
        except Exception:
            pass
    server.stop()
    print('RESULT frames=%d err=%s out=%s' % (len(rec.frames), rec.error, OUT_MP4), flush=True)


if __name__ == '__main__':
    main()

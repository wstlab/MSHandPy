# -*- coding: utf-8 -*-
"""
Sim-Handpy 项目介绍 · 无声录屏演示
自动启动桌面版应用 -> 按时间轴演示 4 个示例 -> 同时录制屏幕并叠加中文字幕。
用法: python -B record_demo.py [输出mp4路径]
"""
import os
import sys
import time
import socket
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
os.chdir(ROOT)

# 输出：直接写 mp4（需以阻塞模式运行本脚本，避免沙箱限制）
OUT_MP4 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.expanduser('~'), 'Desktop', 'Sim-Handpy-项目介绍.mp4')

FPS = 20
FONT_NORMAL = 'C:/Windows/Fonts/msyh.ttc'
FONT_BOLD = 'C:/Windows/Fonts/msyhbd.ttc'

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


# ---- 声明函数签名（64 位句柄/指针必须显式声明，否则默认按 32 位 int 截断） ----
user32.GetDC.restype = wintypes.HDC
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND

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


def _grab_rect(x, y, w, h):
    if w <= 0 or h <= 0:
        return None
    hdc_scr = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_scr)
    hbm = gdi32.CreateCompatibleBitmap(hdc_scr, w, h)
    gdi32.SelectObject(hdc_mem, hbm)
    gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_scr, x, y, 0x00CC0020)  # SRCCOPY
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
    return buf[:, :, :3].copy()  # BGRA -> BGR


def grab_client(hwnd):
    """抓取窗口客户区（BGR ndarray）"""
    rc = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    w, h = rc.right, rc.bottom
    if w <= 0 or h <= 0:
        return None
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return _grab_rect(pt.x, pt.y, w, h)


def grab_window(hwnd):
    rc = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rc))
    return _grab_rect(rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top)


def grab_screen():
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return _grab_rect(0, 0, w, h)


# ---------------- 字幕渲染 ----------------
def _font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_NORMAL, size)


def render_caption(img, caption, sub=None):
    h, w = img.shape[:2]
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).convert('RGBA')
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    bar_h = 72 if sub is None else 100
    y0 = h - bar_h - 14
    d.rounded_rectangle([16, y0, w - 16, h - 8], radius=14, fill=(10, 12, 20, 175))
    d.text((36, y0 + 10), caption, font=_font(30), fill=(255, 255, 255, 255))
    if sub:
        d.text((36, y0 + 56), sub, font=_font(22), fill=(150, 200, 255, 255))
    out = Image.alpha_composite(pil, overlay)
    return cv2.cvtColor(np.asarray(out), cv2.COLOR_RGBA2BGR)


def make_cover(title, subtitle, footer, w, h):
    img = np.zeros((h, w, 3), np.uint8)
    img[:] = (16, 18, 28)
    pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil)
    cx = w // 2
    d.rounded_rectangle([cx - 180, int(h * 0.40), cx + 180, int(h * 0.40) + 6], radius=3, fill=(80, 170, 255, 255))
    d.text((cx, int(h * 0.44)), title, font=_font(56, True), fill=(255, 255, 255, 255), anchor='mm')
    d.text((cx, int(h * 0.53)), subtitle, font=_font(30), fill=(170, 210, 255, 255), anchor='mm')
    d.text((cx, int(h * 0.86)), footer, font=_font(24), fill=(140, 150, 170, 255), anchor='mm')
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


# ---------------- 录制线程 ----------------
class Recorder(threading.Thread):
    def __init__(self, hwnd_getter, t0, duration):
        super().__init__(daemon=True)
        self.hwnd_getter = hwnd_getter
        self.t0 = t0
        self.duration = duration
        self._stop_ev = threading.Event()
        self.covers = []
        self.captions = []
        self.error = None
        self.frames = []  # (elapsed, jpeg_bytes)

    def run(self):
        try:
            hwnd = self.hwnd_getter()
            frame = grab_client(hwnd)
            if frame is None:
                frame = grab_window(hwnd)
            if frame is None:
                frame = grab_screen()
            if frame is None:
                self.error = '无法获取屏幕画面'
                return
            h, w = frame.shape[:2]
            while not self._stop_ev.is_set():
                el = time.time() - self.t0
                if el > self.duration:
                    break
                img = None
                for s, e, c in self.covers:
                    if s <= el < e:
                        img = make_cover(*c, w, h)
                        break
                if img is None:
                    img = grab_client(hwnd)
                    if img is None or img.shape[1] != w:
                        img = grab_screen()
                    cap = None
                    for s, e, caption, sub in self.captions:
                        if s <= el < e:
                            cap = (caption, sub)
                            break
                    if cap:
                        img = render_caption(img, cap[0], cap[1])
                if img is not None and img.shape[1] == w:
                    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    if ok:
                        self.frames.append((el, buf))
                time.sleep(0.02)
            # 编码：按真实采集间隔计算帧率
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


# ---------------- 主流程 ----------------
def main():
    import tkinter as tk
    from integrated_vm import IntegratedVMApp
    import vm_server

    # 延长代码执行超时（默认 3 秒对演示太短）
    _orig_exec = vm_server.VMServer._execute_code

    def _exec_long(self, code, timeout=60):
        return _orig_exec(self, code, timeout)

    vm_server.VMServer._execute_code = _exec_long

    root = tk.Tk()
    app = IntegratedVMApp(root)
    root.geometry('1440x900+120+40')
    root.update()

    # 让应用窗口置顶并获取焦点，避免录制时被其他窗口遮挡
    hwnd0 = user32.FindWindowW(None, 'Sim-Handpy - 具身智能学习平台')
    if not hwnd0:
        try:
            hwnd0 = int(root.winfo_id())
        except Exception:
            hwnd0 = 0
    if hwnd0:
        try:
            user32.SetWindowPos(hwnd0, -1, 0, 0, 0, 0, 0x0001 | 0x0002)  # HWND_TOPMOST, NOMOVE|NOSIZE
            user32.SetForegroundWindow(hwnd0)
        except Exception:
            pass
    root.attributes('-topmost', True)
    root.lift()
    root.focus_force()
    root.update()

    # 关闭内置自动连接（避免与演示驱动抢连接），由本脚本控制连接时机
    app._auto_connect = lambda: None

    # 窗口句柄（复用置顶时的句柄）
    hwnd = hwnd0

    T0 = time.time()
    rec = Recorder(lambda: hwnd, T0, 54)
    rec.covers = [
        (0.0, 4.2, ('Sim-Handpy', '虚拟掌控板 · 项目演示', '青少年具身智能学习工具 · 开源免费')),
        (46.0, 54.0, ('让每个孩子都有一块掌控板', '开源免费 · MIT License', 'GitHub: lmxylyc/Sim-Handpy-VirtualBoard')),
    ]
    rec.captions = [
        (4.2, 8.0, '一键启动 · 无需实体硬件', '软件完整仿真 mPython 掌控板硬件'),
        (8.0, 14.5, '示例1 · RGB 三色灯循环闪烁', '代码运行，虚拟板实时响应'),
        (14.5, 20.5, '示例2 · OLED 实时显示传感器数据', '加速度 / 光线 / 声音 实时刷新'),
        (20.5, 28.0, '示例3 · 物理按键控制 RGB 灯', '点击虚拟板上的按键 A / B'),
        (28.0, 37.0, '示例4 · 六路触摸交互', 'P / Y / T 触摸输入'),
        (37.0, 46.0, '完整硬件仿真', 'OLED · RGB · 按键 · 触摸 · 传感器'),
    ]

    def at(sec, fn):
        delay = max(0, int((sec - (time.time() - T0)) * 1000))
        root.after(delay, fn)

    def ensure_connected():
        if app.connect_status:
            return
        try:
            s = socket.create_connection(('127.0.0.1', 7777), timeout=2)
            if app.vm_socket:
                try:
                    app.vm_socket.close()
                except Exception:
                    pass
            app.vm_socket = s
            s.sendall(b'\r\n\x03\x03')
            time.sleep(0.2)
            s.sendall(b'\r\n\x01')
            time.sleep(0.4)
            s.settimeout(1.5)
            try:
                s.recv(1024)
            except Exception:
                pass
            app.connect_status = True
            app._update_status('已连接', app.theme.SUCCESS)
            app.add_output('✅ 演示驱动已连接虚拟掌控板')
        except OSError:
            at(0.8, ensure_connected)

    def run_example():
        if not app.connect_status:
            at(0.8, run_example)
            return
        app.load_example()
        app.run_code()

    def stop_and_run_next(sec_next):
        app.stop_code()
        at(sec_next, run_example)

    # ---- 演示时间轴 ----
    at(1.0, app.start_vm)
    at(3.0, ensure_connected)
    at(8.0, run_example)                  # 示例1 RGB
    at(13.0, lambda: stop_and_run_next(14.5))   # 示例2 OLED
    at(19.0, lambda: stop_and_run_next(20.5))   # 示例3 按键
    at(21.5, lambda: app._toggle_button('A'))
    at(23.0, lambda: app._toggle_button('A'))
    at(24.0, lambda: app._toggle_button('B'))
    at(25.5, lambda: app._toggle_button('B'))
    at(26.0, lambda: (app._toggle_button('A'), app._toggle_button('B')))
    at(27.5, lambda: (app._toggle_button('A'), app._toggle_button('B')))
    at(28.0, lambda: stop_and_run_next(29.5))   # 示例4 触摸
    at(31.0, lambda: app._set_touch('P', True))
    at(32.5, lambda: app._set_touch('P', False))
    at(33.0, lambda: app._set_touch('Y', True))
    at(34.5, lambda: app._set_touch('Y', False))
    at(35.0, lambda: app._set_touch('T', True))
    at(36.5, lambda: app._set_touch('T', False))
    at(37.0, app.stop_code)

    def finish():
        # 不停止录制线程，让其录满 duration 秒（含结尾封面）
        root.after(400, root.destroy)

    at(46.0, finish)

    rec.start()
    root.mainloop()
    try:
        rec.join(timeout=25)
    except Exception:
        pass
    print('RESULT frames=%d err=%s out=%s' % (len(rec.frames), rec.error, OUT_MP4), flush=True)


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""Mind+ 模块深度自检"""
import sys, os, py_compile, subprocess, socket, ctypes

base = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
sys.path.insert(0, base)
os.chdir(base)

print("=" * 60)
print("  Mind+ 模块深度自检")
print("=" * 60)

# 1. 语法检查
print("\n[1] Python 语法检查:")
for f in ["mindplus_usb.py", "mindplus_transpiler.py", "vm_server.py",
          "start_vm.py", "display_gui.py"]:
    if os.path.exists(f):
        try:
            py_compile.compile(f, doraise=True)
            print(f"  OK  {f}")
        except py_compile.PyCompileError as e:
            print(f"  ERR {f}: {e}")
    else:
        print(f"  SKIP {f}")

# 2. import 检查
print("\n[2] 关键 import 检查:")
for mod in ["serial", "serial.tools.list_ports", "winreg", "ctypes",
            "socket", "threading", "json"]:
    try:
        __import__(mod)
        print(f"  OK  {mod}")
    except ImportError as e:
        print(f"  ERR {mod}: {e}")

# 3. mindplus_usb 模块
print("\n[3] mindplus_usb 模块:")
try:
    import mindplus_usb
    print(f"  OK  imported, VID={mindplus_usb.CH9102_VID}, PID={mindplus_usb.CH9102_PID}")
except Exception as e:
    print(f"  ERR: {e}")

# 4. transpiler
print("\n[4] mindplus_transpiler 模块:")
try:
    from mindplus_transpiler import is_mindplus_code, transpile
    print("  OK  is_mindplus_code + transpile")
except Exception as e:
    print(f"  ERR: {e}")

# 5. com0com
print("\n[5] com0com 驱动:")
com0com_paths = [
    r"C:\Program Files\com0com\setupc.exe",
    r"C:\Program Files (x86)\com0com\setupc.exe",
    r"C:\Program Files\com0com\setupc64.exe",
    r"C:\Program Files (x86)\com0com\setupc64.exe",
]
com0com_found = False
for p in com0com_paths:
    if os.path.exists(p):
        com0com_found = True
        print(f"  OK  found: {p}")
        try:
            r = subprocess.run([p, "list"], capture_output=True, text=True,
                               timeout=10, cwd=os.path.dirname(p),
                               stdin=subprocess.DEVNULL)
            if r.stdout.strip():
                print(f"  已有设备对:\n{r.stdout.strip()}")
            else:
                print("  无已有设备对")
        except OSError as e:
            print(f"  WARN setupc list 需要管理员权限，跳过: {e}")
        except Exception as e:
            print(f"  WARN setupc list 执行失败: {e}")
        inf = os.path.join(os.path.dirname(p), "com0com.inf")
        print(f"  com0com.inf: {'exists' if os.path.exists(inf) else 'MISSING'}")
        break
if not com0com_found:
    print("  WARN com0com not installed")

# 6. 管理员权限
print("\n[6] 管理员权限:")
is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
print(f"  is_admin = {is_admin}")

# 7. 串口列表
print("\n[7] 当前串口:")
try:
    import serial.tools.list_ports
    ports = [p.device for p in serial.tools.list_ports.comports()]
    if ports:
        for p in ports:
            print(f"  {p}")
    else:
        print("  (无串口)")
except Exception as e:
    print(f"  ERR: {e}")

# 8. 端口占用
print("\n[8] 关键端口:")
for port in [7776, 7777, 7778, 7779]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect(("127.0.0.1", port))
        print(f"  port {port}: IN USE")
    except:
        print(f"  port {port}: free")
    finally:
        s.close()

# 9. 类和方法检查
print("\n[9] 类方法检查:")
try:
    from mindplus_usb import MindPlusDirectServer, MindPlusNetworkDiscovery, MindPlusUSBBridge, _DirectSession
    print("  OK  4 classes imported")
    checks = {
        "MindPlusDirectServer": ["start", "stop", "_accept_loop", "_serve_client", "_send_to_vm"],
        "_DirectSession": ["run", "_process_byte", "_execute_code", "_send_response"],
        "MindPlusNetworkDiscovery": ["start", "stop", "_discovery_loop"],
        "MindPlusUSBBridge": ["start", "stop", "_bridge_loop", "_data_loop",
                               "_find_com0com", "_download_and_install_com0com",
                               "_create_virtual_serial_port", "_register_ch9102_device_info"],
    }
    for cls_name, methods in checks.items():
        cls = eval(cls_name)
        missing = [m for m in methods if not hasattr(cls, m)]
        if missing:
            print(f"  WARN {cls_name} missing: {missing}")
        else:
            print(f"  OK  {cls_name} ({len(methods)} methods)")
except Exception as e:
    print(f"  ERR: {e}")

# 10. _create_virtual_serial_port 逻辑验证
print("\n[10] CNCA/CNCB 命名逻辑:")
try:
    import inspect
    src = inspect.getsource(MindPlusUSBBridge._create_virtual_serial_port)
    if "CNCA20" in src or "f'CNCA{port_suffix}'" in src:
        print("  ERR 仍使用 CNCA{port_suffix} 旧逻辑!")
    elif "CNCA{i}" in src and "range(10)" in src:
        print("  OK  使用 CNCA0~CNCA9 遍历逻辑")
    else:
        print("  WARN 命名逻辑需人工确认")
except Exception as e:
    print(f"  ERR: {e}")

# 11. WebSocket 模块
print("\n[11] WebSocket 服务:")
try:
    import vm_websocket_server
    if hasattr(vm_websocket_server, "VMWebSocketServer"):
        print("  OK  VMWebSocketServer class exists")
    else:
        print("  WARN class not found")
except Exception as e:
    print(f"  ERR: {e}")

# 12. bat 编码检查
print("\n[12] bat 编码:")
bat_path = os.path.join(base, "一键启动.bat")
if os.path.exists(bat_path):
    with open(bat_path, "rb") as f:
        raw = f.read()
    non_ascii = sum(1 for b in raw if b > 127)
    crlf = raw.count(b"\r\n")
    lone_lf = raw.count(b"\n") - crlf
    has_chcp = b"chcp 65001" in raw
    print(f"  non-ASCII={non_ascii} CRLF={crlf} loneLF={lone_lf} chcp65001={has_chcp}")
else:
    print("  SKIP bat not found")

print("\n" + "=" * 60)
print("  自检完成")
print("=" * 60)

"""
Sim-Handpy 一键启动器
启动 VM Server (7778)、Virtual USB (7777)、悬浮显示窗与 Thonny IDE。
增强：端口可配置、异常兜底、子进程退出监控、优雅停机。
支持 --mode {thonny,mindplus,both} 选择启动模式：
  - thonny  (默认): VM Server + Virtual USB + 显示窗 + Thonny
  - mindplus      : VM Server + 显示窗 + Mind+ 桥接（占用 7777，跳过 Virtual USB）
  - both          : Thonny + Mind+ 桥接同时启动
"""

import argparse
import subprocess
import sys
import os
import time
import signal
import threading

IS_WINDOWS = sys.platform.startswith('win')
CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if IS_WINDOWS else 0

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON_EXE = sys.executable

# 端口配置（可通过环境变量覆盖，便于多实例/端口冲突时调整）
VM_SERVER_PORT = int(os.environ.get('Sim-Handpy_VM_SERVER_PORT', '7778'))
VM_USB_PORT = int(os.environ.get('Sim-Handpy_VM_USB_PORT', '7777'))

# 支持的启动模式
VALID_MODES = ('thonny', 'mindplus', 'both')


def _port_in_use(port):
    """探测端口是否已被占用"""
    import socket as _sock
    s = _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        s.connect(('127.0.0.1', port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _wait_port(port, timeout=5.0, want_open=True):
    """等待端口达到期望状态"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _port_in_use(port) == want_open:
            return True
        time.sleep(0.2)
    return False


def _safe_terminate(proc):
    """安全终止子进程：先 terminate，超时后 kill"""
    if proc is None:
        return
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _start_service(name, cmd, port, check_exit=True):
    """启动一个服务子进程并等待端口就绪，返回 (proc, ok)"""
    print(f"\n🔌 启动 {name} (port {port})...")
    if _port_in_use(port):
        print(f"   ⚠️ 端口 {port} 已被占用，跳过启动 {name}")
        return None, True  # 视为"已就绪"（可能是外部实例）
    try:
        proc = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW)
    except Exception as e:
        print(f"   ❌ {name} 进程启动失败: {e}")
        return None, False
    if _wait_port(port, timeout=8.0, want_open=True):
        print(f"   ✅ {name} 已就绪 (port {port})")
        return proc, True
    # 端口未开：检查进程是否提前退出
    if check_exit and proc.poll() is not None:
        print(f"   ❌ {name} 启动失败（进程已退出，退出码 {proc.returncode}）")
        return proc, False
    print(f"   ⚠️ {name} 端口未开放（服务可能仍在初始化）")
    return proc, True


def main():
    parser = argparse.ArgumentParser(description="Sim-Handpy one-click launcher")
    parser.add_argument('--mode', choices=VALID_MODES, default='thonny',
                        help='launch mode: thonny (default), mindplus, or both')
    args = parser.parse_args()
    mode = args.mode

    include_mindplus = mode in ('mindplus', 'both')
    include_thonny = mode in ('thonny', 'both')
    # Virtual USB (port 7777) 与 mindplus_usb.py 的 MindPlusDirectServer (同样 7777) 冲突：
    # 当 Mind+ 模式启用时，跳过 Virtual USB，改由 mindplus_usb.py 接管 7777。
    include_virtual_usb = not include_mindplus

    print("=" * 60)
    print(f"   Sim-Handpy - One-Click Launch (mode={mode})")
    print("=" * 60)

    procs = []
    ok = True
    mindplus_started = False

    # 1. VM Server（端口通过命令行参数传递，与端口配置保持一致）
    server_proc, server_ok = _start_service(
        "VM Server",
        [PYTHON_EXE, os.path.join(PROJECT_DIR, 'vm_server.py'), '--port', str(VM_SERVER_PORT)],
        VM_SERVER_PORT)
    if server_proc:
        procs.append(server_proc)
    ok = ok and server_ok

    # 2. Virtual USB（仅在非 Mind+ 模式下启动，避免与 MindPlusDirectServer 端口 7777 冲突）
    if include_virtual_usb:
        usb_cmd = [PYTHON_EXE, '-c',
                   f"import sys; sys.path.insert(0, r'{PROJECT_DIR}'); "
                   f"from simulator.modules.virtual_usb import start_virtual_usb; "
                   f"start_virtual_usb(port={VM_USB_PORT}); "
                   f"import time; time.sleep(3600)"]
        usb_proc, usb_ok = _start_service("Virtual USB Service", usb_cmd, VM_USB_PORT)
        if usb_proc:
            procs.append(usb_proc)
        ok = ok and usb_ok
    else:
        print(f"\nℹ️ 跳过 Virtual USB Service（mode={mode}，端口 {VM_USB_PORT} 由 Mind+ 服务接管）")

    time.sleep(1)

    # 3. 悬浮显示窗（连接 VM Server 的端口保持一致）
    print("\n🖥️ 启动 Virtual Board Display (always on top)...")
    try:
        display_proc = subprocess.Popen(
            [PYTHON_EXE, os.path.join(PROJECT_DIR, 'display_gui.py'), '--port', str(VM_SERVER_PORT)])
        procs.append(display_proc)
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ 显示窗启动失败: {e}")
        display_proc = None

    # 4. 声音自检：播放两声测试音，确认蜂鸣器发声链路正常（独立线程，不阻塞后续启动）
    if IS_WINDOWS:
        print("\n🔊 声音自检：正在播放两声测试音，听到「哔-哔」表示蜂鸣器声音正常...")
        def _sound_check():
            try:
                import winsound
                time.sleep(0.8)          # 略等窗口/声卡就绪
                winsound.Beep(880, 180)  # 低音「哔」
                winsound.Beep(1320, 260) # 高音「哔」
                print("   ✅ 声音自检完成（若没听到声音，请检查系统音量是否被静音）")
            except Exception as e:
                print(f"   ⚠️ 声音自检失败: {e}")
        threading.Thread(target=_sound_check, daemon=True).start()
    else:
        print("\n🔊 声音自检：仅 Windows 支持（winsound），已跳过")

    # 5. Mind+ 桥接服务（仅当 mode 包含 mindplus 时启动）
    #    mindplus_usb.py 顶层 import winreg（仅 Windows），此处 try/except 包裹以兼容非 Windows 环境
    if include_mindplus:
        print("\n" + "=" * 60)
        print("   Mind+ 桥接服务启动")
        print("=" * 60)

        # 5a. 前置检查：管理员权限、com0com、pyserial
        print("\n🔍 Mind+ 前置环境检查:")
        preflight_ok = True

        # 管理员权限
        if IS_WINDOWS:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                print("   ✅ 管理员权限: 是（可自动安装 com0com）")
            else:
                print("   ⚠️ 管理员权限: 否（com0com 安装/串口创建将失败）")
                print("      请右键 bat → 以管理员身份运行")
                preflight_ok = False

        # com0com 检查
        com0com_paths = [
            r"C:\Program Files\com0com\setupc.exe",
            r"C:\Program Files (x86)\com0com\setupc.exe",
            r"C:\Program Files\com0com\setupc64.exe",
            r"C:\Program Files (x86)\com0com\setupc64.exe"
        ]
        com0com_found = any(os.path.exists(p) for p in com0com_paths)
        if com0com_found:
            com0com_path = next(p for p in com0com_paths if os.path.exists(p))
            print(f"   ✅ com0com: 已安装 ({com0com_path})")
        else:
            print("   ⚠️ com0com: 未安装（将尝试自动下载安装，需管理员权限）")

        # pyserial 检查
        try:
            import serial
            print(f"   ✅ pyserial: {serial.__version__}")
        except ImportError:
            print("   ❌ pyserial: 未安装（Mind+ 串口桥不可用）")
            preflight_ok = False

        # 5b. 启动 Mind+ 服务
        print("\n🧩 启动 Mind+ 服务组件:")
        try:
            from mindplus_usb import start_mindplus_services, stop_mindplus_services
            start_mindplus_services(tcp_port=VM_USB_PORT, serial_port='COM20')
            mindplus_started = True
        except Exception as e:
            print(f"   ❌ Mind+ 服务启动失败: {e}")
            print("   ⚠️ Mind+ 模式将不可用。请检查：")
            print("      - com0com 是否已安装（首次运行需管理员权限自动下载安装）")
            print("      - mindplus_usb.py 及其依赖（pyserial）是否可用")
            mindplus_started = False

        # 5c. Mind+ 服务健康检查
        if mindplus_started:
            print("\n" + "-" * 60)
            print("  Mind+ 服务健康检查:")
            print("-" * 60)
            time.sleep(2)  # 等服务完全启动

            health_items = []

            # 直接连接服务 (7777)
            if _port_in_use(VM_USB_PORT):
                print(f"  ✅ 直接连接服务 (端口 {VM_USB_PORT})    运行中")
                health_items.append(("直接连接服务", VM_USB_PORT, True))
            else:
                print(f"  ❌ 直接连接服务 (端口 {VM_USB_PORT})    未监听")
                health_items.append(("直接连接服务", VM_USB_PORT, False))

            # 网络发现服务 (7776)
            if _port_in_use(7776):
                print(f"  ✅ 网络发现服务 (端口 7776)        运行中")
                health_items.append(("网络发现服务", 7776, True))
            else:
                print(f"  ⚠️ 网络发现服务 (端口 7776)        未监听")
                health_items.append(("网络发现服务", 7776, False))

            # WebSocket 服务 (7779)
            if _port_in_use(7779):
                print(f"  ✅ WebSocket 服务 (端口 7779)      运行中")
                health_items.append(("WebSocket 服务", 7779, True))
            else:
                print(f"  ⚠️ WebSocket 服务 (端口 7779)      未监听")
                health_items.append(("WebSocket 服务", 7779, False))

            # 串口检查
            try:
                import serial.tools.list_ports
                ports = [p.device for p in serial.tools.list_ports.comports()]
                if 'COM20' in ports:
                    print(f"  ✅ 虚拟串口 COM20              已创建")
                    if 'COM19' in ports:
                        print(f"  ✅ 虚拟串口 COM19              已创建")
                        health_items.append(("虚拟串口对 COM19↔COM20", 0, True))
                    else:
                        print(f"  ⚠️ 虚拟串口 COM19              未找到")
                        health_items.append(("虚拟串口对 COM19↔COM20", 0, False))
                else:
                    print(f"  ❌ 虚拟串口 COM20              未创建（需管理员权限 + com0com）")
                    health_items.append(("虚拟串口对 COM19↔COM20", 0, False))
            except Exception as e:
                print(f"  ⚠️ 串口检查失败: {e}")

            # 汇总
            ok_count = sum(1 for _, _, ok in health_items if ok)
            total = len(health_items)
            print("-" * 60)
            if ok_count == total:
                print(f"  🎉 Mind+ 全部服务正常 ({ok_count}/{total})")
            elif ok_count > 0:
                print(f"  ⚠️ Mind+ 部分服务异常 ({ok_count}/{total} 正常)")
                print("      异常项不影响已正常的连接方式")
            else:
                print(f"  ❌ Mind+ 全部服务异常 ({ok_count}/{total})")
                print("      请以管理员身份重新运行")
            print("-" * 60)

    # 6. Thonny IDE（仅当 mode 包含 thonny 时启动；找不到时仅提示，不阻塞）
    if include_thonny:
        print("\n💻 启动 Thonny IDE...")
        thonny_proc = None
        thonny_candidates = []
        if IS_WINDOWS and 'APPDATA' in os.environ:
            py_ver = f"Python{sys.version_info.major}{sys.version_info.minor}"
            thonny_candidates.append(os.path.join(os.environ['APPDATA'], 'Python', py_ver, 'Scripts', 'thonny.exe'))
            thonny_candidates.append(os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'Thonny', 'thonny.exe'))
        else:
            thonny_candidates.append('/usr/local/bin/thonny')
            thonny_candidates.append('/usr/bin/thonny')
            thonny_candidates.append('/Applications/Thonny.app/Contents/MacOS/thonny')

        for tp in thonny_candidates:
            if os.path.exists(tp):
                try:
                    demo_path = os.path.join(PROJECT_DIR, 'demo_pinpong.py')
                    thonny_proc = subprocess.Popen([tp, demo_path])
                    procs.append(thonny_proc)
                    break
                except Exception as e:
                    print(f"   ⚠️ Thonny 启动失败: {e}")
                    thonny_proc = None
                    break
        else:
            print("   ⚠️ Thonny not found, please start manually")
    else:
        print(f"\nℹ️ 跳过 Thonny IDE（mode={mode}）")

    # 7. 状态与使用说明（按模式输出不同指引）
    print("\n" + "=" * 60)
    if ok:
        print("   All services started successfully!")
    else:
        print("   ⚠️ 部分服务启动失败，请查看上方日志")
    print("=" * 60)
    print("\n📋 Usage:")
    if include_thonny:
        print("   [Thonny]")
        print("   1. Virtual Board display is always on top")
        print("   2. Open demo.py or demo_pinpong.py in Thonny")
        print("   3. Click Run button to see effects")
    if include_mindplus and mindplus_started:
        print("   [Mind+]")
        print("   - 实时模式: Mind+ → 扩展 → 用户库 → 加载 mindplus_extension/config.json")
        print("     积木连接到 127.0.0.1:7779 (WebSocket)")
        print("   - 串口模式: Mind+ → 上传到设备 → 选择虚拟串口（默认 COM19 ↔ COM20 对）")
        print(f"   - TCP 直连: Mind+ → 网络连接 → 127.0.0.1:{VM_USB_PORT}")
        print("   - 首次使用需以管理员身份运行，自动下载安装 com0com 并创建虚拟串口")
    if not include_mindplus:
        print(f"\n🔗 Mind+ Connection (if needed):")
        print(f"   Connect via TCP: 127.0.0.1:{VM_USB_PORT}")
        if IS_WINDOWS:
            print("   Or use serial bridge: COM20 → 127.0.0.1:%d" % VM_USB_PORT)
    print("\nPress Ctrl+C to stop all services")
    print("=" * 60 + "\n")

    # 主循环：监控子进程退出，任一服务崩溃时提示
    try:
        while True:
            time.sleep(1)
            for proc in procs:
                if proc.poll() is not None:
                    name = getattr(proc, '_Sim-Handpy_name', '服务')
                    print(f"⚠️ 检测到 {name} 已退出（退出码 {proc.returncode}）")
                    procs.remove(proc)
                    break
    except KeyboardInterrupt:
        print("\n🛑 Stopping all services...")
    finally:
        # 先停 Mind+ 服务（释放 7777 端口及相关资源），再终止子进程
        if mindplus_started:
            try:
                from mindplus_usb import stop_mindplus_services
                stop_mindplus_services()
            except Exception as e:
                print(f"   ⚠️ Mind+ 服务停止失败: {e}")
        for proc in procs:
            _safe_terminate(proc)
        print("✅ All services stopped")


if __name__ == "__main__":
    main()

import socket
import threading
import time
import sys
import os
import json
import winreg
import ctypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from mindplus_transpiler import is_mindplus_code, transpile

CH9102_VID = "1A86"
CH9102_PID = "5512"

class MindPlusUSBBridge:
    def __init__(self, tcp_host='127.0.0.1', tcp_port=7777, serial_port='COM20'):
        self.tcp_host = tcp_host
        self.tcp_port = tcp_port
        self.serial_port = serial_port
        self.running = False
        self._thread = None
        self._serial = None
        self._tcp_socket = None
        self._com_port_created = False
        
        self._vm_server_host = '127.0.0.1'
        self._vm_server_port = 7778
        
        self._com0com_path = None
        self._other_port = None
    
    def _find_com0com(self):
        paths = [
            r"C:\Program Files\com0com\setupc.exe",
            r"C:\Program Files (x86)\com0com\setupc.exe",
            r"C:\Program Files\com0com\setupc64.exe",
            r"C:\Program Files (x86)\com0com\setupc64.exe"
        ]
        for path in paths:
            if os.path.exists(path):
                self._com0com_path = path
                print(f"✅ 找到com0com: {path}")
                return True
        print("❌ 未找到com0com，正在尝试自动下载安装...")
        return self._download_and_install_com0com()
    
    def _download_and_install_com0com(self):
        import urllib.request
        import zipfile
        import shutil
        
        download_url = "https://sourceforge.net/projects/com0com/files/com0com/3.0.0.0/com0com-3.0.0.0-x64-signed.zip/download"
        download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        zip_path = os.path.join(download_dir, "com0com.zip")
        extract_dir = os.path.join(download_dir, "com0com")
        
        try:
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
            
            print(f"📥 正在下载com0com...")
            print(f"   来源: {download_url}")
            
            try:
                urllib.request.urlretrieve(download_url, zip_path)
            except:
                download_url = "https://github.com/igor-k/com0com/releases/download/v3.0.0.0/com0com-3.0.0.0-x64-signed.zip"
                print(f"📥 尝试备用下载源: {download_url}")
                urllib.request.urlretrieve(download_url, zip_path)
            
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) < 10000:
                print("❌ 下载失败，文件大小异常")
                return False
            
            print(f"✅ 下载完成: {zip_path}")
            
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            
            print(f"📦 正在解压...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            print(f"✅ 解压完成: {extract_dir}")
            
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            
            if is_admin:
                install_dir = r"C:\Program Files (x86)\com0com"
                print(f"📁 正在安装到: {install_dir}")
                if os.path.exists(install_dir):
                    shutil.rmtree(install_dir)
                shutil.copytree(extract_dir, install_dir)

                self._com0com_path = os.path.join(install_dir, "setupc.exe")

                print(f"✅ com0com安装成功!")
                print(f"   路径: {self._com0com_path}")

                import subprocess

                # 预装驱动：用 pnputil 静默安装 com0com.inf，避免硬件向导弹出找不到文件
                inf_path = os.path.join(install_dir, "com0com.inf")
                if os.path.exists(inf_path):
                    print(f"📦 正在预装驱动 ({inf_path})...")
                    subprocess.run(
                        ['pnputil', '/add-driver', inf_path, '/install'],
                        capture_output=True, text=True, timeout=30
                    )

                # 运行 setupc.exe 时设置 cwd 为 com0com 目录，让向导能找到 inf 文件
                result = subprocess.run(
                    [self._com0com_path, 'install', 'CNCA0', 'CNCB0'],
                    capture_output=True, text=True, timeout=30,
                    cwd=install_dir
                )
                if result.returncode == 0:
                    print(f"✅ 已创建默认串口对")
                else:
                    print(f"⚠️ setupc 输出: {result.stdout}")
                    print(f"⚠️ setupc 错误: {result.stderr}")

                subprocess.run(
                    [self._com0com_path, 'set', 'CNCA0', 'PortName=COM19'],
                    capture_output=True, text=True, timeout=30,
                    cwd=install_dir
                )
                subprocess.run(
                    [self._com0com_path, 'set', 'CNCB0', 'PortName=COM20'],
                    capture_output=True, text=True, timeout=30,
                    cwd=install_dir
                )

                print(f"✅ 已配置串口: COM19 ↔ COM20")
                
                time.sleep(2)
                
                import serial.tools.list_ports
                ports = [p.device for p in serial.tools.list_ports.comports()]
                if 'COM19' in ports and 'COM20' in ports:
                    print(f"✅ 虚拟串口创建成功!")
                    return True
                else:
                    print(f"⚠️ 虚拟串口未在系统中显示，可能需要重启")
                    return False
            else:
                print("⚠️ 当前没有管理员权限，无法自动安装")
                print(f"   解压位置: {extract_dir}")
                print("   请手动运行安装程序或使用管理员权限重新运行")
                return False
                
        except Exception as e:
            print(f"❌ 下载安装com0com失败: {e}")
            print("   请手动下载安装:")
            print("   https://sourceforge.net/projects/com0com/")
            return False
    
    def _create_virtual_serial_port(self):
        import serial.tools.list_ports

        ports = [p.device for p in serial.tools.list_ports.comports()]

        # COM20 已存在，直接用
        if self.serial_port in ports:
            print(f"✅ 串口 {self.serial_port} 已存在，直接使用")
            self._other_port = 'COM19' if 'COM19' in ports else 'COM19'
            self._find_com0com()
            return True

        if not self._find_com0com():
            return False

        # 默认配对端口
        self._other_port = 'COM19'

        # 如果 COM19 已被其他设备占用，找空闲端口
        if self._other_port in ports:
            for i in range(10, 30):
                candidate = f"COM{i}"
                if candidate not in ports and candidate != self.serial_port:
                    self._other_port = candidate
                    break

        print(f"📋 目标虚拟串口对: {self._other_port} <-> {self.serial_port}")

        try:
            import subprocess

            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            if not is_admin:
                print("⚠️ 当前没有管理员权限，无法自动创建虚拟串口")
                print("   请右键 bat -> 以管理员身份运行")
                return False

            com0com_dir = os.path.dirname(self._com0com_path)

            # 预装驱动
            inf_path = os.path.join(com0com_dir, "com0com.inf")
            if os.path.exists(inf_path):
                print(f"📦 预装驱动 ({inf_path})...")
                r = subprocess.run(
                    ['pnputil', '/add-driver', inf_path, '/install'],
                    capture_output=True, text=True, timeout=30
                )
                if r.stdout.strip():
                    print(f"   pnputil: {r.stdout.strip()[:200]}")

            # 解析 setupc list 输出，格式:
            # CNCA0 [EmuBit=yes] ... [PortName=COM3]
            # CNCB0 [EmuBit=yes] ... [PortName=COM4]
            def run_setupc(args):
                return subprocess.run(
                    [self._com0com_path] + args,
                    capture_output=True, text=True, timeout=10,
                    cwd=com0com_dir, stdin=subprocess.DEVNULL
                )

            list_result = run_setupc(['list'])
            list_output = list_result.stdout or list_result.stderr or ""
            print(f"📋 当前 com0com 设备列表:")
            for line in list_output.strip().split('\n'):
                print(f"   {line.strip()}")

            # 解析所有设备对，提取名称和 PortName
            pairs = []  # [(name, portname_or_None), ...]
            for line in list_output.split('\n'):
                line = line.strip()
                if line.startswith('CNCA') or line.startswith('CNCB'):
                    name = line.split('[')[0].strip()
                    port = None
                    if 'PortName=' in line:
                        port = line.split('PortName=')[1].split(']')[0].strip()
                    pairs.append((name, port))

            # 找一对可以分配 COM19/COM20 的设备对
            # 策略: 找 CNCA/CNCB 配对(同名后缀)，且两端端口都可覆盖
            cnca_name = None
            cncb_name = None

            # 按 CNCA 和 CNCB 分组
            cnca_list = [(n, p) for n, p in pairs if n.startswith('CNCA')]
            cncb_list = [(n, p) for n, p in pairs if n.startswith('CNCB')]

            # 尝试匹配已有配对(CNCA0 配 CNCB0, CNCA1 配 CNCB1, ...)
            for a_name, a_port in cnca_list:
                suffix = a_name[4:]  # CNCA0 -> 0
                b_name = f'CNCB{suffix}'
                # 找对应的 CNCB
                b_match = [(n, p) for n, p in cncb_list if n == b_name]
                if not b_match:
                    continue
                b_port = b_match[0][1]
                # 检查这两端是否都可以重新分配
                # 可以重新分配的条件: 端口为 None，或端口不在使用中(不等于 COM19/COM20)
                a_ok = (a_port is None) or (a_port not in ports)
                b_ok = (b_port is None) or (b_port not in ports)
                if a_ok and b_ok:
                    cnca_name = a_name
                    cncb_name = b_name
                    print(f"📌 复用已有设备对: {cnca_name}({a_port}) <-> {cncb_name}({b_port})")
                    break

            # 如果没有找到合适的已有对，尝试创建新的
            if not cnca_name:
                print("   未找到可复用的设备对，尝试创建新对 ...")
                # 方法1: setupc install (无参数)
                r = run_setupc(['install'])
                if r.returncode == 0:
                    print("✅ 新设备对创建成功")
                    time.sleep(1)
                    # 重新 list 找新对
                    list2 = run_setupc(['list'])
                    out2 = list2.stdout or ""
                    for line in out2.split('\n'):
                        line = line.strip()
                        if line.startswith('CNCA') and line not in list_output:
                            cnca_name = line.split('[')[0].strip()
                        if line.startswith('CNCB') and line not in list_output:
                            cncb_name = line.split('[')[0].strip()
                else:
                    print(f"⚠️ setupc install 输出: {r.stdout}")
                    print(f"⚠️ setupc install 错误: {r.stderr}")

                # 方法2: 如果 install 失败，尝试用 setupc 命令行参数
                if not cnca_name:
                    # 尝试 install with pair names
                    for i in range(10):
                        a = f'CNCA{i}'
                        b = f'CNCB{i}'
                        if a not in list_output and b not in list_output:
                            r2 = run_setupc(['install', a, b])
                            if r2.returncode == 0:
                                cnca_name = a
                                cncb_name = b
                                print(f"✅ 设备对 {a}/{b} 创建成功")
                                break
                            else:
                                # 可能是格式问题，尝试 install --
                                r3 = run_setupc(['install', '--', a, b])
                                if r3.returncode == 0:
                                    cnca_name = a
                                    cncb_name = b
                                    print(f"✅ 设备对 {a}/{b} 创建成功 (via --)")
                                    break

            if not cnca_name or not cncb_name:
                print("❌ 无法创建或找到可用的 com0com 设备对")
                print(f"   setupc list 输出:\n{list_output}")
                print("   可能需要手动运行 setupc.exe 创建设备对")
                return False

            # 设置端口号
            print(f"📌 设置端口: {cnca_name}={self._other_port}, {cncb_name}={self.serial_port}")
            r1 = run_setupc(['set', cnca_name, f'PortName={self._other_port}'])
            r2 = run_setupc(['set', cncb_name, f'PortName={self.serial_port}'])
            if r1.returncode != 0:
                print(f"⚠️ set {cnca_name} 输出: {r1.stdout} {r1.stderr}")
            if r2.returncode != 0:
                print(f"⚠️ set {cncb_name} 输出: {r2.stdout} {r2.stderr}")

            print(f"✅ 已配置串口: {self._other_port} <-> {self.serial_port}")
            time.sleep(2)

            ports_after = [p.device for p in serial.tools.list_ports.comports()]
            if self.serial_port in ports_after:
                print(f"✅ 串口 {self.serial_port} 创建成功")
                self._com_port_created = True
                return True
            else:
                print(f"❌ 串口 {self.serial_port} 未在系统中出现")
                print(f"   当前可用串口: {ports_after if ports_after else '无'}")
                print(f"   可能需要重启电脑让驱动生效")
                return False

        except PermissionError:
            print("⚠️ 创建虚拟串口失败: 需要管理员权限")
            print("   请右键 bat → 以管理员身份运行")
            return False
        except Exception as e:
            print(f"⚠️ 创建虚拟串口失败: {e}")
            return False
    
    def _register_ch9102_device_info(self):
        try:
            base_path = rf"SYSTEM\CurrentControlSet\Enum\USB\VID_{CH9102_VID}&PID_{CH9102_PID}"
            
            device_instance = "0000"
            device_path = os.path.join(base_path, device_instance)
            
            try:
                winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, device_path)
            except:
                pass
            
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, device_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "FriendlyName", 0, winreg.REG_SZ, "USB Serial Port")
                winreg.SetValueEx(key, "PortName", 0, winreg.REG_SZ, self.serial_port)
                winreg.SetValueEx(key, "DeviceDesc", 0, winreg.REG_SZ, "USB Serial Port (CH9102)")
            
            print(f"✅ 已注册CH9102设备信息 (VID={CH9102_VID}, PID={CH9102_PID})")
            return True
        except Exception as e:
            print(f"⚠️ 设备信息注册失败: {e}")
            return False
    
    def start(self):
        print("🔌 启动Mind+ USB桥接服务...")
        
        self._register_ch9102_device_info()
        
        self._create_virtual_serial_port()
        
        self.running = True
        self._thread = threading.Thread(target=self._bridge_loop, daemon=True)
        self._thread.start()
        
        print(f"✅ Mind+ USB桥接服务已启动")
        if self._other_port:
            print(f"   Mind+请连接串口: {self._other_port}")
            print(f"   内部桥接串口: {self.serial_port}")
        else:
            print(f"   串口: {self.serial_port}")
        print(f"   TCP目标: {self.tcp_host}:{self.tcp_port}")
    
    def stop(self):
        self.running = False
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
        if self._tcp_socket:
            try:
                self._tcp_socket.close()
            except:
                pass
            self._tcp_socket = None
        print("⏹ Mind+ USB桥接服务已停止")
    
    def _bridge_loop(self):
        import serial
        
        PARITY_NONE = getattr(serial, 'PARITY_NONE', 'N')
        STOPBITS_1 = getattr(serial, 'STOPBITS_1', 1)
        EIGHTBITS = getattr(serial, 'EIGHTBITS', 8)
        
        while self.running:
            try:
                self._serial = serial.Serial(
                    self.serial_port,
                    115200,
                    timeout=0.1,
                    parity=PARITY_NONE,
                    stopbits=STOPBITS_1,
                    bytesize=EIGHTBITS
                )
                print(f"✅ 已连接串口 {self.serial_port}")
                
                while self.running:
                    try:
                        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        tcp_socket.connect((self.tcp_host, self.tcp_port))
                        self._tcp_socket = tcp_socket
                        
                        self._data_loop(tcp_socket)
                        
                    except ConnectionRefusedError:
                        print(f"⚠️ TCP连接被拒绝，正在重试...")
                        time.sleep(1)
                    except Exception as e:
                        print(f"⚠️ TCP连接错误: {e}")
                        time.sleep(2)
                        
                    self._tcp_socket = None
                    
            except serial.SerialException as e:
                print(f"⚠️ 串口连接失败({self.serial_port}): {e}")
                print(f"   请确保已安装虚拟串口驱动(com0com)并创建端口对")
                print(f"   将一端设置为 {self.serial_port}")
                time.sleep(3)
            except Exception as e:
                print(f"⚠️ 未知错误: {e}")
                time.sleep(2)
            
            if self._serial:
                try:
                    self._serial.close()
                except:
                    pass
                self._serial = None
    
    def _data_loop(self, tcp_socket):
        tcp_socket.settimeout(0.01)
        self._serial.timeout = 0.01
        
        print(f"🔄 开始数据转发: {self.serial_port} ↔ {self.tcp_host}:{self.tcp_port}")
        
        while self.running and self._serial and tcp_socket:
            try:
                serial_data = self._serial.read(1024)
                if serial_data:
                    tcp_socket.send(serial_data)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"⚠️ 串口读取错误: {e}")
                break
            
            try:
                tcp_data = tcp_socket.recv(1024)
                if tcp_data:
                    self._serial.write(tcp_data)
            except socket.timeout:
                pass
            except Exception as e:
                print(f"⚠️ TCP读取错误: {e}")
                break
            
            time.sleep(0.001)
    
    def _send_to_vm(self, command):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self._vm_server_host, self._vm_server_port))
            sock.sendall(json.dumps(command).encode('utf-8') + b"\n")
            response = ""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data.decode('utf-8')
                if "\n" in response:
                    response = response.split("\n")[0]
                    break
            sock.close()
            return json.loads(response) if response else {'status': 'error', 'message': 'No response'}
        except:
            return {'status': 'error', 'message': 'VM server not available'}


class MindPlusNetworkDiscovery:
    def __init__(self):
        self.running = False
        self._thread = None
        self._udp_socket = None
        self._tcp_socket = None
    
    def start(self):
        print("🔍 启动Mind+网络发现服务...")
        self.running = True
        
        self._thread = threading.Thread(target=self._discovery_loop, daemon=True)
        self._thread.start()
        
        print("✅ Mind+网络发现服务已启动")
    
    def stop(self):
        self.running = False
        if self._udp_socket:
            try:
                self._udp_socket.close()
            except:
                pass
            self._udp_socket = None
        print("⏹ Mind+网络发现服务已停止")
    
    def _discovery_loop(self):
        try:
            self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._udp_socket.bind(('0.0.0.0', 7776))
            self._udp_socket.settimeout(1.0)
            
            while self.running:
                try:
                    data, addr = self._udp_socket.recvfrom(1024)
                    message = data.decode('utf-8', errors='ignore')
                    
                    if 'mindplus' in message.lower() or 'mpython' in message.lower() or 'chongzuo' in message.lower():
                        print(f"📡 收到发现请求: {addr} - {message}")
                        
                        response = json.dumps({
                            'device': 'Sim-Handpy',
                            'vid': CH9102_VID,
                            'pid': CH9102_PID,
                            'port': 7777,
                            'type': 'virtual'
                        })
                        self._udp_socket.sendto(response.encode('utf-8'), addr)
                        print(f"📤 发送响应: {response}")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"⚠️ 发现服务错误: {e}")
                        
        except Exception as e:
            print(f"⚠️ 启动发现服务失败: {e}")


class _DirectSession:
    """单个 Mind+ 连接的 Raw REPL 会话（每连接独立状态，互不干扰）"""

    def __init__(self, server, conn, addr):
        self.server = server
        self.conn = conn
        self.addr = addr
        self._buffer = b""
        self._repl_active = False
        self._raw_repl = False
        self._cmd_buffer = b""

    def run(self):
        while self.server.running:
            try:
                data = self.conn.recv(1024)
                if not data:
                    break

                hex_data = ' '.join(f'{b:02x}' for b in data)
                print(f"📥 收到数据: {hex_data}")

                for byte in data:
                    self._process_byte(byte)
                self._send_response()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"⚠️ 连接处理错误: {e}")
                break

    def _process_byte(self, byte):
        if not self._repl_active:
            if byte == 0x03:
                self._repl_active = True
                self._buffer += b"\r\n"
                print("📋 进入REPL模式")
            elif byte == 0x01:
                self._repl_active = True
                self._raw_repl = True
                self._cmd_buffer = b""
                self._buffer += b"raw REPL; CTRL-B to exit\r\n>"
                print("📋 进入RAW REPL模式")
            return

        if self._raw_repl:
            if byte == 0x02:
                self._raw_repl = False
                self._repl_active = False
                self._cmd_buffer = b""
                self._buffer += b"\r\n>>>"
                print("📋 退出RAW REPL模式")
            elif byte == 0x03:
                self._cmd_buffer = b""
                self._buffer += b"\r\n>>> "
            elif byte == 0x04:
                result = self._execute_code()
                self._buffer += b"OK" + result + b"\x04\x04>"
                print("✅ 代码执行完成")
            elif byte == 0x0D:
                self._cmd_buffer += b"\n"
            elif byte == 0x0A:
                pass
            else:
                self._cmd_buffer += bytes([byte])

    def _execute_code(self):
        if not self._cmd_buffer.strip():
            return b""
        code = self._cmd_buffer.decode('utf-8', errors='ignore')
        self._cmd_buffer = b""

        print(f"📝 待执行代码: {code[:100]}...")

        try:
            if is_mindplus_code(code):
                print("🔄 检测到Mind+代码，正在转译...")
                code = transpile(code)
                print(f"📝 转译后代码: {code[:100]}...")

            result = self.server._send_to_vm({'action': 'execute', 'code': code})
            output = result.get('output', '')
            return str(output).encode('utf-8')
        except Exception as e:
            print(f"❌ 执行错误: {e}")
            return str(e).encode('utf-8')

    def _send_response(self):
        if self._buffer:
            try:
                self.conn.send(self._buffer)
                hex_data = ' '.join(f'{b:02x}' for b in self._buffer)
                print(f"📤 发送响应: {hex_data}")
            except Exception:
                pass
            self._buffer = b""


class MindPlusDirectServer:
    def __init__(self, host='127.0.0.1', port=7777):
        self.host = host
        self.port = port
        self.server = None
        self.running = False
        self._thread = None
        self._sessions = []

        self._vm_server_host = '127.0.0.1'
        self._vm_server_port = 7778

    def start(self):
        print(f"🚀 启动Mind+直接连接服务 ({self.host}:{self.port})...")
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        # backlog 留足余量：Mind+ 频繁重连时新连接也能立即被内核排队
        self.server.listen(5)
        self.server.settimeout(1.0)
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        print("✅ Mind+直接连接服务已启动")

    def stop(self):
        self.running = False
        if self.server:
            try:
                self.server.close()
            except:
                pass
        print("⏹ Mind+直接连接服务已停止")

    def _send_to_vm(self, command):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # 加超时，避免 VM Server 异常时长时间占住连接线程，导致后续连接饿死
            sock.settimeout(10.0)
            sock.connect((self._vm_server_host, self._vm_server_port))
            sock.sendall(json.dumps(command).encode('utf-8') + b"\n")
            response = ""
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                response += data.decode('utf-8')
                if "\n" in response:
                    response = response.split("\n")[0]
                    break
            return json.loads(response) if response else {'status': 'error', 'message': 'No response'}
        except Exception as e:
            return {'status': 'error', 'message': f'VM server not available: {e}'}
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server.accept()
                print(f"🔌 Mind+客户端已连接: {addr}")
                conn.settimeout(0.1)
                # 每个连接独立线程 + 独立会话：任何单连接卡住/异常都不影响 accept
                t = threading.Thread(target=self._serve_client,
                                     args=(conn, addr), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except OSError:
                if self.running:
                    break

    def _serve_client(self, conn, addr):
        try:
            session = _DirectSession(self, conn, addr)
            self._sessions.append(session)
            session.run()
        except Exception as e:
            if self.running:
                print(f"⚠️ 客户端服务异常: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
            print(f"🔌 Mind+客户端已断开: {addr}")


_bridge = None
_discovery = None
_direct_server = None


def start_mindplus_services(tcp_port=7777, serial_port='COM20'):
    global _bridge, _discovery, _direct_server
    
    print("=" * 60)
    print("   Mind+ 连接服务启动")
    print("=" * 60)
    
    _direct_server = MindPlusDirectServer(port=tcp_port)
    _direct_server.start()
    
    _discovery = MindPlusNetworkDiscovery()
    _discovery.start()
    
    _bridge = MindPlusUSBBridge(tcp_port=tcp_port, serial_port=serial_port)
    _bridge.start()
    
    print("🚀 启动WebSocket服务器 (用于Mind+实时模式)...")
    try:
        import vm_websocket_server
        _websocket_server = vm_websocket_server.VMWebSocketServer(port=7779)
        _websocket_server.start()
        print("✅ WebSocket服务器已启动 (端口7779)")
    except Exception as e:
        print(f"⚠️ WebSocket服务器启动失败: {e}")
        _websocket_server = None
    
    other_port = _bridge._other_port if _bridge else None
    
    print("=" * 60)
    print("   所有Mind+服务已启动")
    print("=" * 60)
    print(f"\n📋 使用说明:")
    
    print(f"\n   ── 方法1: 实时模式用户库 (推荐) ──")
    print(f"     Mind+ → 实时模式 → 扩展 → 用户库")
    print(f"     加载: {os.path.join(os.path.dirname(__file__), 'mindplus_extension', 'config.json')}")
    print(f"     使用积木连接到 127.0.0.1:7779")
    
    print(f"\n   ── 方法2: 串口连接 ──")
    print(f"     Mind+ → 上传到设备 → 选择串口")
    if other_port:
        print(f"     请选择串口: {other_port}")
    else:
        print(f"     请选择串口: {serial_port}")
    
    print(f"\n   ── 方法3: TCP直连 ──")
    print(f"     如果Mind+支持网络连接:")
    print(f"     Mind+ → 网络连接 → 127.0.0.1:{tcp_port}")
    
    print(f"\n   设备信息 (用于驱动配置):")
    print(f"     VID: {CH9102_VID}")
    print(f"     PID: {CH9102_PID}")
    print(f"     设备名称: USB Serial Port (CH9102)")
    print(f"\n按 Ctrl+C 停止服务")
    print("=" * 60 + "\n")
    
    return _bridge, _discovery, _direct_server


def stop_mindplus_services():
    global _bridge, _discovery, _direct_server
    
    if _bridge:
        _bridge.stop()
        _bridge = None
    if _discovery:
        _discovery.stop()
        _discovery = None
    if _direct_server:
        _direct_server.stop()
        _direct_server = None


def is_running():
    global _bridge, _discovery, _direct_server
    return (_direct_server is not None and _direct_server.running) or \
           (_discovery is not None and _discovery.running) or \
           (_bridge is not None and _bridge.running)


if __name__ == "__main__":
    start_mindplus_services()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        stop_mindplus_services()
        print("✅ 所有服务已停止")